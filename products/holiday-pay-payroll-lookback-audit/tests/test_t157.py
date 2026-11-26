"""T-157 regression tests: header echo, excluded_week with pay, name-like cap, wording, leave_year_start, non-UTF-8."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import audit as cli
from ingest import load_workers, ValidationError

H = "worker_id,week_ending,element_category,amount\n"
L = "worker_id,week_ending\n"


def weeks(n=8):
    from datetime import date, timedelta
    return [date(2025, 1, 4) + timedelta(days=7 * i) for i in range(n)]


def hist(wid="W1", extra=""):
    return H + "".join(f"{wid},{d},basic,100.00\n" for d in weeks()) + extra


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "out")

    def f(self, name, text, mode="w"):
        p = os.path.join(self.tmp.name, name)
        with open(p, mode) as fh:
            fh.write(text)
        return p

    def run_cli(self, h, l, w=None):
        argv = ["--history", h, "--leave", l, "--out", self.out] + (["--workers", w] if w else []) + ["--include-flagged"]
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            rc = cli.main(argv)
        return rc, err.getvalue()

    def report(self):
        with open(os.path.join(self.out, "report.md")) as fh:
            return fh.read()

    def test_headerless_file_does_not_echo_cells(self):
        h = self.f("h.csv", "EMP-SECRET-ID-0042,2025-01-04,basic,1234.56\n")
        rc, err = self.run_cli(h, self.f("l.csv", L + "W1,2025-02-22\n"))
        self.assertEqual(rc, 2)
        for secret in ("EMP-SECRET-ID-0042", "2025-01-04", "1234.56", "basic", "EMP"):
            self.assertNotIn(secret, err)
        self.assertIn("column 1 is not a recognised header", err)
        self.assertFalse(os.path.exists(self.out))

    def test_name_header_not_echoed(self):
        h = self.f("h.csv", "John Smith,week_ending,element_category,amount\nW1,2025-01-04,basic,1\n")
        rc, err = self.run_cli(h, self.f("l.csv", L + "W1,2025-02-22\n"))
        self.assertEqual(rc, 2)
        self.assertNotIn("John", err)
        self.assertNotIn("Smith", err)

    def pay_excluded(self):
        return self.f("h.csv", hist(extra="W1,2025-01-11,excluded_week,0\n"))

    def test_excluded_week_with_pay_warns(self):
        rc, err = self.run_cli(self.pay_excluded(), self.f("l.csv", L + "W1,2025-02-22\n"))
        self.assertEqual(rc, 0)
        self.assertIn("excluded_week marked on a week that also has pay; the week was used as a normal week", err)
        self.assertIn("W1***", err)
        self.assertIn("2025-01-11", err)
        self.assertNotIn("100.00", err)
        rep = self.report()
        self.assertIn("excluded_week marked on a week that also has pay; the week was used as a normal week", rep)
        self.assertIn("2025-01-11", rep)
        self.assertNotIn("100.00", rep.split("excluded_week on weeks")[1].split("\n## ")[0])

    def test_excluded_week_with_pay_does_not_change_numbers(self):
        l = self.f("l.csv", L + "W1,2025-02-22\n")
        self.run_cli(self.f("a.csv", hist()), l)
        a = open(os.path.join(self.out, "exceptions.csv")).read()
        self.run_cli(self.pay_excluded(), l)
        b = open(os.path.join(self.out, "exceptions.csv")).read()
        self.assertEqual(a, b)

    def test_excluded_week_alone_no_warning(self):
        h = self.f("h.csv", hist(extra="W1,2025-03-01,excluded_week,0\n"))
        rc, err = self.run_cli(h, self.f("l.csv", L + "W1,2025-02-22\n"))
        self.assertEqual(rc, 0)
        self.assertNotIn("excluded_week marked", err)
        self.assertNotIn("excluded_week on weeks", self.report())

    def test_name_like_cap_and_report_count(self):
        ids = [f"ab.name{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(60)]
        rows = H + "".join(f"{i},{d},basic,100.00\n" for i in ids for d in weeks(2))
        h = self.f("h.csv", rows)
        l = self.f("l.csv", L + f"{ids[0]},2025-01-11\n")
        rc, err = self.run_cli(h, l)
        self.assertEqual(rc, 0)
        self.assertEqual(err.count("looks like a person's name"), 50)
        self.assertIn("and 10 more worker_id warning(s)", err)
        self.assertIn("Worker IDs that look like a person's name: 60", self.report())
        # identical masked ids are distinguishable
        self.assertIn("history line", err)
        self.assertEqual(len(set(l for l in err.splitlines() if "looks like" in l)), 50)

    def test_not_truncated_wording(self):
        # 3 leave weeks with exceptions, per-worker detail cap exceeded
        import report.builder as b
        rs = [{"week_end": d} for d in weeks(3)]
        text = b._weeks_in_csv(rs)
        self.assertNotIn("All of them,", text)
        self.assertTrue(text.startswith("Their week endings: "))
        self.assertTrue(text.endswith("All of them are in exceptions.csv."))

    def lys(self, v):
        h = self.f("h.csv", hist())
        l = self.f("l.csv", L + "W1,2025-02-22\n")
        w = self.f("w.csv", f"worker_id,worker_type,leave_year_start\nW1,variable_hours,{v}\n")
        with self.assertRaises(ValidationError) as cm:
            load_workers(h, l, w)
        return str(cm.exception.issues[0])

    def test_leave_year_start_message(self):
        for v in ("13-01", "04-31", "04/01"):
            self.assertNotIn("02-29", self.lys(v))
        self.assertIn("02-29 is not accepted", self.lys("02-29"))

    def test_non_utf8(self):
        h = self.f("h.csv", hist().encode("utf-8") + "W1,2025-03-01,basic,5\n".encode() + b"W\xe9,2025-03-08,basic,5\n", "wb")
        rc, err = self.run_cli(h, self.f("l.csv", L + "W1,2025-02-22\n"))
        self.assertEqual(rc, 2)
        self.assertIn("h.csv:11:", err)
        self.assertIn("save the file as UTF-8 (CSV UTF-8 in Excel)", err)
        self.assertNotIn("codec", err)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
