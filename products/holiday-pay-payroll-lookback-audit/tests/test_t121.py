"""T-121 regression tests: QA M1-M3, L1-L3 and security M-1, L-1, L-2."""
import csv
import os
import unittest
from datetime import date, timedelta

from tests.test_audit import Base, H, L, run_cli
from ingest.loader import _looks_like_ni, _mask


def weeks(n, start=date(2024, 6, 1)):
    return [start + timedelta(days=7 * i) for i in range(n)]


def hist_csv(rows):
    return H + "".join(f"{w},{d},{c},{a}\n" for w, d, c, a in rows)


class Run(Base):
    def go(self, history, leave, *extra):
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", self.write("h.csv", history), "--leave", self.write("l.csv", leave),
                            "--out", out, *extra)
        rows, report = [], ""
        if code == 0:
            with open(f"{out}/exceptions.csv", newline="") as fh:
                rows = list(csv.DictReader(fh))
            with open(f"{out}/report.md") as fh:
                report = fh.read()
        return code, err, rows, report


class UnlistedHolidayPay(Run):
    def test_m1_unlisted_holiday_pay_weeks_warn_and_flag(self):
        ws = weeks(70)
        rows = [("A", d, "basic", "400.00") for d in ws[:60]] + [("A", d, "holiday_pay", "430.00") for d in ws[60:65]]
        code, err, ex, report = self.go(hist_csv(rows), L + f"A,{ws[64]}\n", "--include-flagged")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(ex), 1)
        self.assertIn("holiday_pay_week_not_in_leave_file", ex[0]["flags"])
        self.assertIn("## Warning: holiday pay recorded but no leave row", report)
        self.assertIn("A: 4 week(s)", report)

    def test_m1_no_warning_when_all_listed(self):
        ws = weeks(62)
        rows = [("A", d, "basic", "400.00") for d in ws[:60]] + [("A", ws[60], "holiday_pay", "400.00")]
        code, err, ex, report = self.go(hist_csv(rows), L + f"A,{ws[60]}\n", "--include-flagged")
        self.assertNotIn("not_in_leave_file", "".join(r["flags"] for r in ex))
        self.assertNotIn("no leave row", report)


class LeaveWithoutHolidayPay(Run):
    def test_m2_leave_week_paid_as_basic_is_flagged_and_shows_other_pay(self):
        ws = weeks(61)
        rows = [("A", d, "basic", "400.00") for d in ws]
        code, err, ex, report = self.go(hist_csv(rows), L + f"A,{ws[60]}\n", "--include-flagged")
        self.assertEqual(code, 0, err)
        self.assertIn("leave_week_without_holiday_pay", ex[0]["flags"])
        self.assertIn("not marked as holiday pay: £400.00", report)

    def test_m2_not_flagged_when_holiday_pay_present(self):
        ws = weeks(61)
        rows = [("A", d, "basic", "400.00") for d in ws[:60]] + [("A", ws[60], "holiday_pay", "400.00")]
        _, _, ex, _ = self.go(hist_csv(rows), L + f"A,{ws[60]}\n", "--include-flagged")
        self.assertEqual(ex, [])


class CannotCheck(Run):
    def test_m3_leave_before_any_history_is_listed_not_dropped(self):
        rows = [("W1", "2025-06-07", "basic", "400.00"), ("W1", "2025-06-14", "basic", "400.00")]
        code, err, ex, report = self.go(hist_csv(rows), L + "W1,2025-05-31\n")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(ex), 1)
        self.assertEqual(ex[0]["direction"], "cannot_check")
        self.assertIn("could not be checked: 1", report)
        self.assertIn("CANNOT BE CHECKED", report)
        self.assertNotIn("Exceptions: None", report)
        self.assertNotIn("overpaid by", report)

    def test_m3_unchecked_rows_not_counted_as_over_or_under(self):
        rows = [("W1", "2025-06-07", "basic", "400.00"), ("W1", "2025-06-14", "basic", "400.00"),
                ("W1", "2025-05-31", "holiday_pay", "100.00")]
        _, _, ex, report = self.go(hist_csv(rows), L + "W1,2025-05-31\n")
        self.assertIn("Overpayments: 0", report)


class CliBounds(Run):
    def test_l1_huge_threshold_exit_2_no_traceback(self):
        for bad in ("1e27", "1e400", "1000001", "-1", "NaN"):
            with self.assertRaises(SystemExit) as cm:
                run_cli("--history", "x", "--leave", "y", "--out", "z", "--threshold", bad)
            self.assertEqual(cm.exception.code, 2, bad)

    def test_threshold_upper_bound_accepted(self):
        import audit
        self.assertEqual(str(audit._threshold("1000000")), "1000000")

    def test_l2_out_of_range_dates_are_line_errors(self):
        for d in ("0001-01-08", "0225-06-07", "2101-01-01", "1999-12-31"):
            iss = self.issues(H + f"W1,{d},basic,1\n")
            self.assertTrue(any(i.startswith("h.csv:2:") and "accepted range" in i for i in iss), (d, iss))

    def test_l2_range_edges_accepted(self):
        from ingest.loader import _date, MIN_DATE, MAX_DATE
        for d in (MIN_DATE, MAX_DATE):
            problems = []
            self.assertEqual(_date("h.csv", 2, {"week_ending": d.isoformat()}, problems), d)
            self.assertEqual(problems, [])

    def test_error_flood_is_capped(self):
        rows = "".join(f"W{i},2025-06-0x,basic,1\n" for i in range(120))
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", self.write("h.csv", H + rows), "--leave", self.write("l.csv", L + "W1,2025-06-14\n"),
                            "--out", out)
        self.assertEqual(code, 2)
        lines = err.strip().splitlines()
        self.assertEqual(sum(1 for x in lines if x.startswith("h.csv:")), 50)
        self.assertTrue(any(x.startswith("... and ") and x.endswith(" more") for x in lines))
        self.assertIn("validation error(s); nothing written", lines[-1])
        self.assertFalse(os.path.exists(out))


class NiDetection(Run):
    def test_m1_security_variants_refused(self):
        for bad in ("QQ.12.34.56.C", "QQ_12_34_56_C", "QQ123456", "EMP-QQ123456C", "qq 12 34 56 c", "QQ-12-34-56",
                    "AB123456C", "AB123456", "EM100234A", "EMP_AB123456", "AB123456C-01", "1985-03-12", "12.03.1985"):
            iss = self.issues(H + f"{bad},2025-06-07,basic,1\n")
            self.assertTrue(any(i.startswith("h.csv:2:") and "National Insurance" in i for i in iss), (bad, iss))

    def test_plausible_payroll_ids_allowed(self):
        for ok in ("EMP100234", "EMP100234A", "W001", "E-1234", "ID123456", "DX123456C", "ZZ123456C", "BG123456A",
                   "STAFF.42", "A1", "12345678"):
            self.assertFalse(_looks_like_ni(ok), ok)

    def test_long_cell_with_many_separators_is_fast(self):
        import time
        for cell in (" ".join(["ab"] * 50000), "a." * 50000, "1 " * 4000):
            t = time.time()
            _looks_like_ni(cell)
            self.assertLess(time.time() - t, 1.0)
        t = time.time()
        iss = self.issues(H + "W1,2025-06-07,basic,1\n" + '"' + " ".join(["word"] * 3000) + '",2025-06-07,basic,1\n')
        self.assertLess(time.time() - t, 1.0)
        self.assertTrue(any(i.startswith("h.csv:3:") for i in iss))

    def test_ni_message_does_not_echo_value(self):
        iss = self.issues(H + "QQ123456C,2025-06-07,basic,1\n")
        self.assertFalse(any("QQ123456" in i for i in iss), iss)


class Masking(Run):
    def test_l1_values_not_echoed(self):
        secret = "QQ123456C John Smith"
        iss = self.issues(H + f"W1,{secret},basic,1\nW1,2025-06-07,{secret},1\nW1,2025-06-14,basic,{secret}\n",
                          workers=f"worker_id,worker_type\nW1,{secret}\n")
        joined = "\n".join(iss)
        self.assertNotIn("John", joined)
        self.assertNotIn("QQ123456C", joined)
        for ln in ("h.csv:2:", "h.csv:3:", "h.csv:4:", "w.csv:2:"):
            self.assertIn(ln, joined)
        self.assertIn("20 chars", joined)

    def test_l1_long_value_is_short_in_message(self):
        iss = self.issues(H + "W1,2025-06-07," + "x" * 5000 + ",1\n")
        self.assertTrue(all(len(i) < 400 for i in iss), [len(i) for i in iss])

    def test_mask(self):
        self.assertEqual(_mask("abcdef"), "'ab...' (6 chars)")

    def test_long_header_truncated(self):
        iss = self.issues("worker_id," + "y" * 500 + ",week_ending,element_category,amount\nW1,x,2025-06-07,basic,1\n")
        self.assertTrue(all(len(i) < 300 for i in iss))

    def test_non_ascii_id_message_says_ascii(self):
        iss = self.issues(H + "कर्म1,2025-06-07,basic,1\n")
        self.assertTrue(any("ASCII" in i for i in iss), iss)


if __name__ == "__main__":
    unittest.main()
