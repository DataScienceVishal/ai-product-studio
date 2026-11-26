"""T-126: rolled-up holiday pay check for irregular_rolled_up workers, and the wording guardrail."""
import csv
import io
import os
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from decimal import Decimal as D

import audit as cli
from ingest import load_workers, ValidationError
from report import check_week, audit_rolled_up, audit
from tests.test_audit import Base, H, L, run_cli, SAMPLES

RU = "rolled_up_holiday_pay"
W = "worker_id,worker_type,contract_weekly_basic\n"
T = D("0.01")


def week(d, **pay):
    return check_week("W1", d, {k: D(str(v)) for k, v in pay.items()}, T)


class Rules(unittest.TestCase):
    def test_correct_week_is_not_an_exception(self):
        r = week(date(2025, 6, 7), basic=100, rolled_up_holiday_pay="12.07")
        self.assertEqual((r["due"], r["difference"], r["exception"], r["flags"]), (D("12.07"), D("0.00"), False, []))

    def test_pre_2024_year_with_rolled_up_pay_is_flagged_without_recalc(self):
        r = week(date(2024, 3, 30), basic=100, rolled_up_holiday_pay="12.07")
        self.assertEqual((r["flags"], r["exception"], r["due"]), (["rolled_up_before_2024_rules"], True, None))

    def test_leave_year_boundary(self):
        # a week belongs to the leave year containing its week-ending date
        self.assertEqual(week(date(2024, 3, 31), basic=100, rolled_up_holiday_pay="12.07")["flags"], ["rolled_up_before_2024_rules"])
        r = week(date(2024, 4, 1), basic=100, rolled_up_holiday_pay="12.07")
        self.assertEqual((r["flags"], r["leave_year_start"], r["exception"]), ([], date(2024, 4, 1), False))
        self.assertEqual(week(date(2024, 3, 30), basic=100, rolled_up_holiday_pay="12.07")["leave_year_start"], date(2023, 4, 1))

    def test_pre_2024_without_rolled_up_or_with_zero_is_nothing(self):
        self.assertIsNone(week(date(2024, 3, 30), basic=100))
        self.assertIsNone(week(date(2024, 3, 30)))
        self.assertIsNone(check_week("W1", date(2024, 3, 30), {"basic": D(100), RU: D("0.00")}, T))

    def test_not_shown_separately(self):
        r = week(date(2025, 6, 7), basic=100, commission=20)
        self.assertEqual((r["flags"], r["exception"], r["paid"], r["counts"]), (["rolled_up_not_shown_separately"], True, D("0.00"), D("120.00")))

    def test_not_shown_separately_needs_pay_that_counts(self):
        # only excluded items, holiday pay or nothing: nothing to compare, no row
        self.assertIsNone(week(date(2025, 6, 7), excluded_week=90, expense_excluded=10, bonus_non_regular=50, holiday_pay=100))
        self.assertIsNone(week(date(2025, 6, 7)))

    def test_zero_pay_week_with_rolled_up_row_is_overpaid(self):
        r = week(date(2025, 6, 7), rolled_up_holiday_pay="5.00")
        self.assertEqual((r["due"], r["difference"], r["exception"]), (D("0.00"), D("-5.00"), True))
        z = week(date(2025, 6, 7), rolled_up_holiday_pay="0.00")
        self.assertEqual((z["due"], z["exception"]), (D("0.00"), False))

    def test_zero_rolled_up_row_with_pay_is_underpaid(self):
        r = week(date(2025, 6, 7), basic=100, rolled_up_holiday_pay="0.00")
        self.assertEqual((r["flags"], r["difference"], r["exception"]), ([], D("12.07"), True))

    def test_pay_that_counts_excludes_expenses_bonus_statutory_and_holiday_pay_and_rolled_up(self):
        r = week(date(2025, 6, 7), basic=100, regular_overtime=10, commission=10, allowance=10, bonus_non_regular=999,
                 expense_excluded=999, excluded_week=999, holiday_pay=999, rolled_up_holiday_pay="16.28")
        self.assertEqual((r["counts"], r["due"], r["difference"]), (D("130.00"), D("15.69"), D("-0.59")))

    def test_threshold_is_strictly_greater(self):
        # 12.07% of 100 = 12.07
        at = check_week("W1", date(2025, 6, 7), {"basic": D(100), RU: D("12.08")}, D("0.01"))
        over = check_week("W1", date(2025, 6, 7), {"basic": D(100), RU: D("12.09")}, D("0.01"))
        self.assertEqual((at["difference"], at["exception"]), (D("-0.01"), False))
        self.assertEqual((over["difference"], over["exception"]), (D("-0.02"), True))
        self.assertTrue(check_week("W1", date(2025, 6, 7), {"basic": D(100), RU: D("12.08")}, D("0"))["exception"])
        # a rule flag is an exception whatever the threshold
        self.assertTrue(check_week("W1", date(2024, 3, 30), {RU: D(1)}, D(1000000))["exception"])

    def test_rounds_to_the_penny(self):
        self.assertEqual(week(date(2025, 6, 7), basic=150, rolled_up_holiday_pay="18.11")["due"], D("18.11"))   # 18.105
        self.assertEqual(week(date(2025, 6, 7), basic="0.04", rolled_up_holiday_pay="0.00")["due"], D("0.00"))  # 0.0048


class Pipeline(Base):
    def load(self, history, leave, workers):
        return load_workers(self.write("h.csv", history), self.write("l.csv", leave), self.write("w.csv", workers))

    def test_loader_accepts_type_and_category(self):
        w = self.load(H + f"W1,2025-06-07,basic,100\nW1,2025-06-07,{RU},12.07\n", L + "W1,2025-06-07\n",
                      W + "W1,irregular_rolled_up,\n")
        self.assertEqual(w["W1"].worker_type, "irregular_rolled_up")
        self.assertEqual(w["W1"].history[date(2025, 6, 7)][RU], D("12.07"))

    def test_mixed_worker_types_keep_their_own_rules(self):
        h = H + ("W1,2025-06-07,basic,400\nW1,2025-06-14,holiday_pay,300\n"          # variable_hours: look-back, underpaid
                 "W2,2025-06-07,basic,100\nW2,2025-06-14,basic,100\n"               # rolled-up, no row: flagged
                 f"W3,2025-06-07,basic,500\nW3,2025-06-14,holiday_pay,500\n")        # fixed_pay: correct
        l = L + "W1,2025-06-14\nW3,2025-06-14\nW2,2025-06-14\n"
        w = self.load(h, l, W + "W1,variable_hours,\nW2,irregular_rolled_up,\nW3,fixed_pay,500.00\n")
        rows, exc = audit(w)
        lb = [r for r in rows if r.get("kind") != "rolled_up"]
        self.assertEqual([(r["worker_id"], r["difference"]) for r in lb], [("W1", D("100.00")), ("W3", D("0.00"))])
        self.assertEqual([(r["worker_id"], r["flags"]) for r in exc if r.get("kind") == "rolled_up"],
                         [("W2", ["rolled_up_not_shown_separately"])] * 2)

    def test_rolled_up_worker_leave_week_not_relooked_back(self):
        # W1's leave week would be "cannot be checked" and flagged by the look-back; it is skipped for this type
        w = self.load(H + f"W1,2025-06-07,basic,100\nW1,2025-06-07,{RU},12.07\nW1,2025-06-14,holiday_pay,100\n",
                      L + "W1,2025-06-14\n", W + "W1,irregular_rolled_up,\n")
        rows, exc = audit(w)
        self.assertEqual(rows, audit_rolled_up(w, T)[0])
        self.assertEqual(len(rows), 2)   # no look-back row; the pay week and the holiday_pay flag
        self.assertEqual([r["flags"] for r in exc], [["holiday_pay_paid_to_rolled_up_worker"]])

    def test_non_rolled_up_worker_with_rolled_up_rows_warns(self):
        h = self.write("h.csv", H + f"W1,2025-06-07,basic,100\nW1,2025-06-07,{RU},12.07\nW1,2025-06-14,holiday_pay,100\n")
        l = self.write("l.csv", L + "W1,2025-06-14\n")
        out = os.path.join(self.tmp.name, "out")
        self.assertEqual(run_cli("--history", h, "--leave", l, "--out", out, "--include-flagged")[0], 0)
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("## Warning: rolled-up holiday pay for a worker not set as irregular_rolled_up", md)
        self.assertIn("- W1: 1 week(s): 2025-06-07", md)
        self.assertIn("Workers with rolled-up pay but not set as irregular_rolled_up: 1", md)
        # rolled-up pay does not count as normal pay: the average is the 100.00 basic, and it is not "other pay"
        self.assertIn("= £100.00 / 1 = £100.00", md)

    def test_unknown_worker_type_message_lists_new_type(self):
        h, l = self.write("h.csv", H + "W1,2025-06-07,basic,1\n"), self.write("l.csv", L + "W1,2025-06-07\n")
        with self.assertRaises(ValidationError) as cm:
            load_workers(h, l, self.write("w.csv", W + "W1,bogus,\n"))
        self.assertIn("irregular_rolled_up", str(cm.exception.issues[0]))


class ContractBasicAndHolidayPay(Base):
    def run_files(self, h, l, w):
        out = os.path.join(self.tmp.name, "out")
        so, se = io.StringIO(), io.StringIO()
        with redirect_stdout(so), redirect_stderr(se):
            code = cli.main(["--history", self.write("h.csv", h), "--leave", self.write("l.csv", l),
                             "--workers", self.write("w.csv", w), "--out", out])
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        with open(f"{out}/exceptions.csv", newline="") as fh:
            rows = list(csv.DictReader(fh))
        return code, se.getvalue(), md, rows

    def test_basic_on_rolled_up_worker_gets_its_own_wording(self):
        for basic in ("300", "0"):
            code, err, md, _ = self.run_files(H + "W1,2025-06-07,basic,100\nW1,2025-06-07,rolled_up_holiday_pay,12.07\n",
                                              L + "W1,2025-06-07\n", W + f"W1,irregular_rolled_up,{basic}\n")
            self.assertEqual(code, 0, basic)
            self.assertIn("not set as fixed_pay", err)
            self.assertNotIn("variable_hours", err)
            self.assertIn("- W1: contract_weekly_basic ignored (irregular_rolled_up)", md)
            self.assertIn("checked as 12.07% of pay that counts, so a weekly basic is not used", md)
            for bad in ("variable_hours", "fixed_pay", "52-week average"):
                self.assertNotIn(bad, md.split("## Warning: contract_weekly_basic ignored")[1], (basic, bad))

    def test_holiday_pay_for_rolled_up_worker_is_flagged(self):
        h = H + ("W1,2025-06-07,basic,100\nW1,2025-06-07,rolled_up_holiday_pay,12.07\n"
                 "W1,2025-06-14,basic,100\nW1,2025-06-14,rolled_up_holiday_pay,12.07\nW1,2025-06-14,holiday_pay,80\n")
        code, err, md, rows = self.run_files(h, L + "W1,2025-06-14\n", W + "W1,irregular_rolled_up,\n")
        self.assertEqual(code, 0)
        self.assertEqual([(r["leave_week"], r["paid"], r["direction"], r["flags"], r["check"]) for r in rows],
                         [("2025-06-14", "80.00", "rule_flag", "holiday_pay_paid_to_rolled_up_worker", "rolled_up_pay")])
        self.assertIn("## Warning: holiday_pay recorded for an irregular_rolled_up worker", md)
        self.assertIn("- W1: 1 week(s): 2025-06-14", md)
        self.assertIn("### W1, pay week ending 2025-06-14", md)

    def test_holiday_pay_in_pre_2024_week_and_alongside_a_difference(self):
        h = H + "W1,2024-03-30,holiday_pay,50\nW1,2025-06-07,basic,100\nW1,2025-06-07,holiday_pay,5\n"
        _, _, _, rows = self.run_files(h, L + "W1,2025-06-07\n", W + "W1,irregular_rolled_up,\n")
        self.assertEqual([(r["leave_week"], r["flags"]) for r in rows], [
            ("2024-03-30", "holiday_pay_paid_to_rolled_up_worker"),
            ("2025-06-07", "rolled_up_not_shown_separately"), ("2025-06-07", "holiday_pay_paid_to_rolled_up_worker")])

    def test_no_holiday_warning_for_other_worker_types(self):
        _, _, md, _ = self.run_files(H + "W1,2025-06-07,basic,100\nW1,2025-06-14,holiday_pay,100\n",
                                     L + "W1,2025-06-14\n", W + "W1,variable_hours,\n")
        self.assertNotIn("irregular_rolled_up worker", md)


class SampleCli(Base):
    def run_sample(self):
        out = os.path.join(self.tmp.name, "out")
        so, se = io.StringIO(), io.StringIO()
        with redirect_stdout(so), redirect_stderr(se):
            code = cli.main(["--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv",
                             "--workers", f"{SAMPLES}/workers.csv", "--out", out, "--include-flagged"])
        self.assertEqual((code, se.getvalue()), (0, ""))
        return out, so.getvalue()

    def test_new_stdout_lines(self):
        out, stdout = self.run_sample()
        self.assertEqual(stdout, f"5 leave weeks checked, 4 exceptions. Written to {out}\n"
                                 "13 rolled-up pay weeks checked, 8 exceptions.\n")

    def test_sample_rolled_up_exceptions(self):
        out, _ = self.run_sample()
        with open(f"{out}/exceptions.csv", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if r["check"] == "rolled_up_pay"]
        self.assertEqual([(r["worker_id"], r["leave_week"], r["paid"], r["due"], r["difference"], r["direction"], r["flags"]) for r in rows], [
            ("W006", "2024-03-16", "24.14", "", "", "rule_flag", "rolled_up_before_2024_rules"),
            ("W006", "2024-03-23", "24.14", "", "", "rule_flag", "rolled_up_before_2024_rules"),
            ("W006", "2024-03-30", "24.14", "", "", "rule_flag", "rolled_up_before_2024_rules"),
            ("W007", "2025-06-21", "0.00", "", "", "rule_flag", "rolled_up_not_shown_separately"),
            ("W007", "2025-06-28", "0.00", "", "", "rule_flag", "rolled_up_not_shown_separately"),
            ("W008", "2025-06-14", "20.00", "24.14", "4.14", "underpaid", ""),
            ("W008", "2025-06-21", "30.00", "24.14", "-5.86", "overpaid", ""),
            ("W008", "2025-06-28", "200.00", "", "", "rule_flag", "holiday_pay_paid_to_rolled_up_worker")])
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        for s in ("Rolled-up pay weeks checked (worker-weeks, each counted once): 13", "Rolled-up pay exceptions: 8 (5 rule flags, 2 differences from 12.07% of pay that counts, 1 holiday_pay week(s) paid to a rolled-up worker)", "## Warning: holiday_pay recorded for an irregular_rolled_up worker", "- W008: 1 week(s): 2025-06-28",
                  "12.07% x £200.00 = £24.14", "underpaid by £4.14", "overpaid by £5.86",
                  "W008 (1)", "Not legal advice; a payroll professional signs off."):
            self.assertIn(s, md)
        self.assertEqual(md.count("## Warning"), 1)   # only the holiday_pay warning

    def test_banned_words_absent_from_every_output(self):
        out, stdout = self.run_sample()
        with open(f"{out}/exceptions.csv", encoding="utf-8") as fh:
            text = fh.read() + "\n" + stdout
        with open(f"{out}/report.md", encoding="utf-8") as fh:
            md = fh.read()
        # also the warning sections, which the clean sample does not trigger
        out2 = os.path.join(self.tmp.name, "out2")
        so = io.StringIO()
        with redirect_stdout(so), redirect_stderr(io.StringIO()):
            cli.main(["--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv", "--out", out2])
        with open(f"{out2}/report.md", encoding="utf-8") as fh:
            md2 = fh.read()
        for body in (text, md, md2, so.getvalue()):
            self.assertIsNone(re.search(r"\b(compliant|compliance|non-compliant|owed|owe|owing|liable|liability)\b", body, re.I), body)
        self.assertIn("recalculated under these settings", md.lower())
        self.assertIn("Recalculated under these settings", md)


if __name__ == "__main__":
    unittest.main()
