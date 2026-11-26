import csv
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal as D

import audit as cli
from ingest import load_workers, ValidationError
from samples import generate

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(HERE, "samples")
H = "worker_id,week_ending,element_category,amount\n"
L = "worker_id,week_ending\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        p = os.path.join(self.tmp.name, name)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return p

    def issues(self, history, leave=L + "W1,2025-06-14\n", workers=None):
        h, l = self.write("h.csv", history), self.write("l.csv", leave)
        w = self.write("w.csv", workers) if workers is not None else None
        with self.assertRaises(ValidationError) as cm:
            load_workers(h, l, w)
        return [str(i) for i in cm.exception.issues]

    def has(self, issues, *words):
        self.assertTrue(any(all(w in i for w in words) for i in issues), (words, issues))


class Validation(Base):
    def test_valid_minimal(self):
        h = self.write("h.csv", H + "W1,2025-06-07,basic,100.00\nW1,2025-06-14,holiday_pay,100\n")
        w = load_workers(h, self.write("l.csv", L + "W1,2025-06-14\n"))
        self.assertEqual(w["W1"].history[next(iter(w["W1"].history))], {"basic": D("100.00")})
        self.assertEqual(len(w["W1"].leave), 1)

    def test_collects_all_errors_with_line_numbers(self):
        iss = self.issues(H + "W1,2025-13-01,basic,1\nW1,2025-06-07,bogus,1\nW1,2025-06-07,basic,abc\n"
                          "W1,2025-06-07,basic,NaN\nW1,2025-06-07,basic,Infinity\nW1,2025-06-07,basic,-5\n")
        for line in range(2, 8):
            self.has(iss, f"h.csv:{line}:")
        self.has(iss, "valid YYYY-MM-DD"); self.has(iss, "unknown element_category 'bogus'")
        self.has(iss, "NaN"); self.has(iss, "Infinity")

    def test_missing_and_extra_columns(self):
        iss = self.issues("worker_id,week_ending,amount,colour\nW1,2025-06-07,1,red\n")
        self.has(iss, "h.csv:1", "missing column 'element_category'")
        self.has(iss, "unexpected column 'colour'")

    def test_bad_field_count(self):
        self.has(self.issues(H + "W1,2025-06-07,basic\n"), "h.csv:2", "expected 4 fields")

    def test_duplicates(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\nW1,2025-06-07,basic,2\nW1,2025-06-14,basic,1\n",
                          leave=L + "W1,2025-06-14\nW1,2025-06-14\n")
        self.has(iss, "h.csv:3", "duplicate row", "line 2")
        self.has(iss, "l.csv:3", "duplicate leave week")

    def test_week_pattern_alignment(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\nW1,2025-06-14,basic,1\nW1,2025-06-21,basic,1\nW1,2025-06-25,basic,1\n",
                          leave=L + "W1,2025-06-18\n")
        self.has(iss, "h.csv:5", "Wednesday", "Saturday")
        self.has(iss, "l.csv:2", "Wednesday")

    def test_empty_files(self):
        h, l = self.write("h.csv", ""), self.write("l.csv", L)
        with self.assertRaises(ValidationError) as cm:
            load_workers(h, l)
        msgs = [str(i) for i in cm.exception.issues]
        self.has(msgs, "h.csv: file is empty"); self.has(msgs, "l.csv: no data rows")

    def test_personal_data_header_refused(self):
        for col in ("name", "ni_number", "Employee Name", "email"):
            iss = self.issues(f"worker_id,{col},week_ending,element_category,amount\nW1,x,2025-06-07,basic,1\n")
            self.has(iss, "personal data")

    def test_ni_number_in_worker_id_refused(self):
        iss = self.issues(H + "QQ123456C,2025-06-07,basic,1\nqq 12 34 56 c,2025-06-07,basic,1\n", leave=L + "QQ123456C,2025-06-14\n")
        self.has(iss, "h.csv:2", "National Insurance"); self.has(iss, "h.csv:3", "National Insurance")
        self.has(iss, "l.csv:2", "National Insurance")

    def test_leave_and_worker_settings_errors(self):
        iss = self.issues(H + "W1,2025-06-07,basic,1\n", leave=L.strip() + ",weeks\nW9,2025-06-07,1\nW1,2025-06-07,0\n",
                          workers="worker_id,worker_type\nW1,magic\nW1,fixed_pay\nW8,fixed_pay\n")
        self.has(iss, "l.csv:2", "no payroll history"); self.has(iss, "l.csv:3", "greater than 0")
        self.has(iss, "w.csv:2", "worker_type 'magic'"); self.has(iss, "w.csv:3", "duplicate settings")
        self.has(iss, "w.csv:4", "no payroll history")


def run_cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(args))
    return code, err.getvalue()


class EndToEnd(Base):
    def audit(self, *extra):
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv",
                            "--workers", f"{SAMPLES}/workers.csv", "--out", out, *extra)
        self.assertEqual((code, err), (0, ""))
        with open(f"{out}/exceptions.csv", newline="") as fh:
            return out, list(csv.DictReader(fh))

    def test_sample_files_match_generator(self):
        generate.write(os.path.join(self.tmp.name, "gen"))
        for n in ("history.csv", "leave.csv", "workers.csv"):
            with open(f"{SAMPLES}/{n}") as a, open(f"{self.tmp.name}/gen/{n}") as b:
                self.assertEqual(a.read(), b.read(), n)

    def test_known_underpayments_and_totals(self):
        out, rows = self.audit()
        by = {r["worker_id"]: r for r in rows}
        self.assertEqual({k: (v["paid"], v["due"], v["difference"], v["direction"]) for k, v in by.items()}, {
            "W002": ("400.00", "480.00", "80.00", "underpaid"),
            "W003": ("310.00", "300.00", "-10.00", "overpaid"),
            "W004": ("350.00", "400.00", "50.00", "underpaid"),
            "W005": ("300.00", "315.00", "15.00", "underpaid")})
        self.assertEqual(by["W004"]["flags"], "shortened")
        self.assertEqual((by["W003"]["ref_weeks_used"], by["W003"]["ref_weeks_skipped"]), ("52", "5"))
        md = open(f"{out}/report.md", encoding="utf-8").read()
        self.assertIn("Not legal advice; a payroll professional signs off", md.split("\n")[2])
        for s in ("Workers: 5", "Leave weeks checked: 5", "Underpayments: 3, total underpaid £145.00",
                  "Overpayments: 1, total overpaid £10.00", "Workers with flags: 1 (W004)",
                  "### W002, week ending 2025-08-09", "underpaid by £80.00"):
            self.assertIn(s, md)

    def test_threshold(self):
        self.assertEqual(len(self.audit("--threshold", "20")[1]), 3)     # drops W005 (15.00)
        self.assertEqual(len(self.audit("--threshold", "80")[1]), 0)     # strictly greater than
        _, rows = self.audit("--threshold", "80", "--include-flagged")
        self.assertEqual([r["worker_id"] for r in rows], ["W004"])

    def test_validation_failure_exit_2_writes_nothing(self):
        bad = self.write("bad.csv", H + "W1,not-a-date,basic,1\nW1,2025-06-07,zzz,1\n")
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", bad, "--leave", f"{SAMPLES}/leave.csv", "--out", out)
        self.assertEqual(code, 2)
        self.assertIn("bad.csv:2:", err); self.assertIn("bad.csv:3:", err)
        self.assertFalse(os.path.exists(out))

    def test_without_workers_file_defaults_to_variable_hours(self):
        out = os.path.join(self.tmp.name, "o2")
        self.assertEqual(run_cli("--history", f"{SAMPLES}/history.csv", "--leave", f"{SAMPLES}/leave.csv", "--out", out)[0], 0)
        self.assertTrue(os.path.exists(f"{out}/report.md"))


if __name__ == "__main__":
    unittest.main()
