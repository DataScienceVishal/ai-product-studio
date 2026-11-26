"""T-127: per-worker leave_year_start (MM-DD, default 04-01), distinct-week counts and stdout wording."""
import csv
import gc
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from decimal import Decimal as D

import audit as cli
from ingest import load_workers
from report import audit, check_week
from tests.test_audit import Base, H, L, SAMPLES

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden")
W = "worker_id,worker_type,contract_weekly_basic,leave_year_start\n"
T = D("0.01")


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def run(*args):
    gc.collect()   # unclosed sockets leaked by other test modules would otherwise warn on our captured stderr
    so, se = io.StringIO(), io.StringIO()
    with redirect_stdout(so), redirect_stderr(se):
        code = cli.main(list(args))
    return code, so.getvalue(), se.getvalue()


class DefaultUnchanged(Base):
    """With no leave_year_start column the outputs are byte-identical to those of main before T-127."""

    def test_sample_with_workers_matches_main(self):
        out = os.path.join(self.tmp.name, "o")
        code, _, err = run("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv",
                           "--workers", f"{SAMPLES}/workers.csv", "--out", out)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(read(f"{out}/exceptions.csv"), read(f"{GOLDEN}/main_exceptions.csv"))
        self.assertEqual(read(f"{out}/report.md"), read(f"{GOLDEN}/main_report.md"))

    def test_sample_without_workers_matches_main(self):
        out = os.path.join(self.tmp.name, "o")
        code, _, err = run("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv", "--out", out)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(read(f"{out}/exceptions.csv"), read(f"{GOLDEN}/main_nw_exceptions.csv"))
        self.assertEqual(read(f"{out}/report.md"), read(f"{GOLDEN}/main_nw_report.md"))

    def test_explicit_04_01_for_everyone_equals_default(self):
        with open(f"{SAMPLES}/workers.csv", newline="") as fh:
            rows = list(csv.DictReader(fh))
        text = W + "".join(f"{r['worker_id']},{r['worker_type']},{r['contract_weekly_basic']},04-01\n" for r in rows)
        out = os.path.join(self.tmp.name, "o")
        code, _, err = run("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv",
                           "--workers", self.write("w.csv", text), "--out", out)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(read(f"{out}/exceptions.csv"), read(f"{GOLDEN}/main_exceptions.csv"))

    def test_loader_default_and_blank(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100\n")
        l = self.write("l.csv", L + "W1,2025-06-07\n")
        self.assertEqual(load_workers(h, l)["W1"].leave_year_start, (4, 1))
        self.assertEqual(load_workers(h, l, self.write("w.csv", W + "W1,variable_hours,,\n"))["W1"].leave_year_start, (4, 1))
        self.assertEqual(load_workers(h, l, self.write("w2.csv", W + "W1,variable_hours,,01-01\n"))["W1"].leave_year_start, (1, 1))


class RolledUp(unittest.TestCase):
    def wk(self, d, start, **pay):
        return check_week("W1", d, {k: D(str(v)) for k, v in pay.items()}, T, start)

    def test_jan_start_flags_apr_to_dec_2024(self):
        pay = dict(basic=100, rolled_up_holiday_pay="12.07")
        for d in (date(2024, 4, 6), date(2024, 8, 3), date(2024, 12, 28)):
            r = self.wk(d, (1, 1), **pay)
            self.assertEqual((r["flags"], r["exception"], r["due"], r["leave_year_start"]),
                             (["rolled_up_before_2024_rules"], True, None, date(2024, 1, 1)), d)
            # the default April start would recalculate the same week
            self.assertEqual(self.wk(d, (4, 1), **pay)["flags"], [])
        # the next leave year starts 2025-01-01: recalculated again
        r = self.wk(date(2025, 1, 4), (1, 1), **pay)
        self.assertEqual((r["flags"], r["leave_year_start"]), ([], date(2025, 1, 1)))

    def test_week_ending_exactly_on_start_date(self):
        pay = dict(basic=100, rolled_up_holiday_pay="12.07")
        # start 07-01: a week ending 2024-07-01 is in the year starting that day (rules apply); the week before is not
        on = self.wk(date(2024, 7, 1), (7, 1), **pay)
        self.assertEqual((on["flags"], on["leave_year_start"]), ([], date(2024, 7, 1)))
        before = self.wk(date(2024, 6, 24), (7, 1), **pay)
        self.assertEqual((before["flags"], before["leave_year_start"]), (["rolled_up_before_2024_rules"], date(2023, 7, 1)))
        # start 04-02: a week ending 2024-04-01 is still in the old year
        self.assertEqual(self.wk(date(2024, 4, 1), (4, 2), **pay)["flags"], ["rolled_up_before_2024_rules"])
        self.assertEqual(self.wk(date(2024, 4, 2), (4, 2), **pay)["flags"], [])
        # a start on or after 2024-04-01 before the week is fine; start 12-31, week 2024-12-31 is the first day
        self.assertEqual(self.wk(date(2024, 12, 31), (12, 31), **pay)["leave_year_start"], date(2024, 12, 31))

    def test_end_to_end_flag_via_workers_file(self):
        base = date(2024, 4, 6)    # Saturday
        hist = "".join(f"W1,{base + timedelta(days=7 * i)},{c},{a}\n" for i in range(3)
                       for c, a in (("basic", "100"), ("rolled_up_holiday_pay", "12.07")))
        with tempfile.TemporaryDirectory() as tmp:
            def w(n, t):
                p = os.path.join(tmp, n)
                with open(p, "w") as fh:
                    fh.write(t)
                return p
            h, l = w("h.csv", H + hist), w("l.csv", L + f"W1,{base}\n")
            flagged = {}
            for start in ("01-01", "04-01"):
                out = os.path.join(tmp, "o" + start)
                code, so, se = run("--history", h, "--leave", l, "--workers",
                                   w("w.csv", W + f"W1,irregular_rolled_up,,{start}\n"), "--out", out)
                self.assertEqual((code, se), (0, ""))
                with open(f"{out}/exceptions.csv", newline="") as fh:
                    flagged[start] = [r["flags"] for r in csv.DictReader(fh)]
        self.assertEqual(flagged["01-01"], ["rolled_up_before_2024_rules"] * 3)
        self.assertEqual(flagged["04-01"], [])


class FirstFourWeeks(Base):
    def rows(self, start_text, leave_dates):
        d0 = date(2023, 12, 6)    # Wednesday
        weeks = [d0 + timedelta(days=7 * i) for i in range(0, 62)]
        leave = {date.fromisoformat(x) for x in leave_dates}
        hist = ""
        for d in weeks:
            hist += f"W1,{d},basic,100\nW1,{d},commission,50\n" if d not in leave else f"W1,{d},holiday_pay,100\n"
        h = self.write("h.csv", H + hist)
        l = self.write("l.csv", L + "".join(f"W1,{x}\n" for x in sorted(leave_dates)))
        w = self.write("w.csv", W + f"W1,variable_hours,,{start_text}\n") if start_text is not None else None
        rows, _ = audit(load_workers(h, l, w))
        return [r for r in rows if r.get("kind") != "rolled_up"]

    LEAVE = ["2024-12-11", "2024-12-18", "2024-12-25", "2025-01-01", "2025-01-08", "2025-01-15", "2025-01-22", "2025-01-29"]

    def test_counting_restarts_on_a_january_start(self):
        rows = self.rows("01-01", self.LEAVE)
        self.assertEqual([(str(r["week_end"]), str(r["leave_year_start"]), r["normal_weeks"], r["basic_weeks"]) for r in rows], [
            ("2024-12-11", "2024-01-01", 1, 0), ("2024-12-18", "2024-01-01", 1, 0), ("2024-12-25", "2024-01-01", 1, 0),
            ("2025-01-01", "2025-01-01", 1, 0), ("2025-01-08", "2025-01-01", 1, 0), ("2025-01-15", "2025-01-01", 1, 0),
            ("2025-01-22", "2025-01-01", 1, 0), ("2025-01-29", "2025-01-01", 0, 1)])

    def test_default_april_start_counts_all_eight_in_one_year(self):
        for text in (None, "04-01"):
            rows = self.rows(text, self.LEAVE)
            self.assertEqual([(r["normal_weeks"], r["basic_weeks"]) for r in rows],
                             [(1, 0)] * 4 + [(0, 1)] * 4, text)
            self.assertEqual({str(r["leave_year_start"]) for r in rows}, {"2024-04-01"})

    def test_unlisted_holiday_week_flag_uses_the_workers_year(self):
        # holiday_pay on 2024-12-25 is not in leave.csv: with a 01-01 start it is in the previous leave year, so it does not
        # disturb the count in 2025; with the default April start it is in the same year as the 2025 leave weeks
        h = self.write("h.csv", H + "".join(f"W1,{date(2024, 12, 4) + timedelta(days=7 * i)},basic,100\n" for i in range(8))
                       + "W1,2024-12-25,holiday_pay,100\n")
        l = self.write("l.csv", L + "W1,2025-01-08\nW1,2025-01-15\n")
        w = self.write("w.csv", W + "W1,variable_hours,,01-01\n")
        rows, _ = audit(load_workers(h, l, w))
        self.assertTrue(all("holiday_pay_week_not_in_leave_file" not in r["flags"] for r in rows))
        rows, _ = audit(load_workers(h, l, self.write("w2.csv", W + "W1,variable_hours,,04-01\n")))
        self.assertTrue(all("holiday_pay_week_not_in_leave_file" in r["flags"] for r in rows))


class Invalid(Base):
    def check(self, value, line=2):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100\n")
        l = self.write("l.csv", L + "W1,2025-06-07\n")
        w = self.write("w.csv", W + f"W1,variable_hours,,{value}\n")
        out = os.path.join(self.tmp.name, "out")
        code, so, se = run("--history", h, "--leave", l, "--workers", w, "--out", out)
        self.assertEqual((code, so), (2, ""))
        self.assertFalse(os.path.exists(out))
        self.assertIn(f"w.csv:{line}: leave_year_start", se)
        self.assertIn(f"'{value[:2]}...' ({len(value)} chars)", se)
        self.assertNotIn(f"'{value}'", se)
        return se

    def test_invalid_values_exit_2_with_line_number(self):
        for v in ("13-01", "00-10", "02-29", "02-30", "04-31", "1-1", "01/01", "2025-04-01", "April", "01-1", "1-01", "01-01-01",
                  "0101", "99-99"):
            with self.subTest(v=v):
                self.check(v)

    def test_cell_is_not_echoed_in_full(self):
        se = self.check("SECRET-CELL-VALUE-123")
        self.assertNotIn("SECRET-CELL-VALUE-123", se)
        self.assertIn("'SE...' (21 chars)", se)

    def test_line_number_of_second_row(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100\nW2,2025-06-07,basic,100\n")
        l = self.write("l.csv", L + "W1,2025-06-07\n")
        w = self.write("w.csv", W + "W1,variable_hours,,04-01\nW2,variable_hours,,02-29\n")
        code, so, se = run("--history", h, "--leave", l, "--workers", w, "--out", os.path.join(self.tmp.name, "o"))
        self.assertEqual(code, 2)
        self.assertIn("w.csv:3: leave_year_start", se)
        self.assertNotIn("w.csv:2:", se)

    def test_valid_dates_accepted(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100\n")
        l = self.write("l.csv", L + "W1,2025-06-07\n")
        for v, parsed in (("01-01", (1, 1)), ("12-31", (12, 31)), ("02-28", (2, 28)), ("07-15", (7, 15))):
            self.assertEqual(load_workers(h, l, self.write("w.csv", W + f"W1,variable_hours,,{v}\n"))["W1"].leave_year_start, parsed)


if __name__ == "__main__":
    unittest.main()
