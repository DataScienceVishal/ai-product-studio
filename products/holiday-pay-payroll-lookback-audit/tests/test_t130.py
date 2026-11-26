"""T-130: regression tests for T-128 F1-F3 and T-129 L-1, I-1, I-2."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from decimal import Decimal as D

import audit as cli
from ingest import load_workers, ValidationError
from report.rolled_up import explain_rolled_up

HERE = os.path.dirname(os.path.abspath(__file__))
H = "worker_id,week_ending,element_category,amount\n"
LV = "worker_id,week_ending\n"
W = "worker_id,worker_type,leave_year_start\n"


class Case(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def f(self, name, text):
        p = os.path.join(self.d, name)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return p

    def run_cli(self, h, l, w):
        out = os.path.join(self.d, "out")
        so, se = io.StringIO(), io.StringIO()
        with redirect_stdout(so), redirect_stderr(se):
            code = cli.main(["--history", self.f("h.csv", h), "--leave", self.f("l.csv", l),
                             "--workers", self.f("w.csv", w), "--out", out])
        rep = os.path.join(out, "report.md")
        return code, so.getvalue(), se.getvalue(), (open(rep, encoding="utf-8").read() if os.path.exists(rep) else "")


class F1EmptyLeave(Case):
    def test_rolled_up_only_with_header_only_leave_runs(self):
        code, so, se, rep = self.run_cli(H + "R1,2025-06-07,basic,400.00\n", LV, W + "R1,irregular_rolled_up,\n")
        self.assertEqual(code, 0, se)
        self.assertIn("0 leave weeks checked", so)
        self.assertIn("1 rolled-up pay weeks checked, 1 exceptions", so)

    def test_header_only_leave_without_rolled_up_still_refused(self):
        code, so, se, rep = self.run_cli(H + "V1,2025-06-07,basic,400.00\n", LV, W + "V1,variable_hours,\n")
        self.assertEqual(code, 2)
        self.assertIn("no data rows", se)

    def test_header_only_leave_without_workers_file_refused(self):
        with self.assertRaises(ValidationError):
            load_workers(self.f("h.csv", H + "V1,2025-06-07,basic,1\n"), self.f("l.csv", LV))


class F2Visibility(Case):
    def test_idle_rolled_up_worker_noted(self):
        h = H + "R1,2025-06-07,bonus_non_regular,50\nR1,2025-06-14,statutory,50\nV1,2025-06-07,basic,100\n"
        code, so, se, rep = self.run_cli(h, LV + "V1,2025-06-07\n", W + "R1,irregular_rolled_up,\n")
        self.assertEqual(code, 0, se)
        self.assertIn("0 rolled-up pay weeks checked, 0 exceptions", so)
        self.assertIn("note: 1 irregular_rolled_up worker(s) had no pay week to check", so)
        self.assertIn("nothing to check", rep)
        self.assertIn("R1", rep)

    def test_leave_week_missing_from_history_noted(self):
        h = H + "S1,2025-06-07,basic,400\nS1,2025-06-14,basic,400\n"
        code, so, se, rep = self.run_cli(h, LV + "S1,2025-07-05\n", W + "S1,irregular_rolled_up,\n")
        self.assertEqual(code, 0, se)
        self.assertIn("1 leave week(s) of irregular_rolled_up worker(s) are missing from history", so)
        self.assertIn("missing from history", rep)
        self.assertIn("2025-07-05", rep)

    def test_no_note_when_nothing_to_say(self):
        h = H + "S1,2025-06-07,basic,400\n"
        code, so, se, rep = self.run_cli(h, LV + "S1,2025-06-07\n", W + "S1,irregular_rolled_up,\n")
        self.assertNotIn("note:", so)
        self.assertNotIn("nothing to check", rep)


class F3Invisible(Case):
    def test_bom_in_leave_year_start_not_echoed(self):
        code, so, se, rep = self.run_cli(H + "W1,2025-06-07,basic,1\n", LV + "W1,2025-06-07\n",
                                         W + "W1,variable_hours,﻿04-01\n")
        self.assertEqual(code, 2)
        self.assertNotIn("﻿", se)
        self.assertIn("(5 chars, invisible characters removed)", se)
        self.assertIn("'04...'", se)

    def test_zero_width_in_other_cell_not_echoed(self):
        code, so, se, rep = self.run_cli(H + "W1,2025-06-07,basic,​1x\n", LV + "W1,2025-06-07\n", W + "W1,variable_hours,\n")
        self.assertEqual(code, 2)
        self.assertNotIn("​", se)


class L1CapReport(Case):
    def test_report_capped_csv_complete(self):
        start = date(2024, 1, 6)
        h = H
        for i in range(500):   # every week before the 2024 rules: rolled-up pay present, so each week is a rule flag
            d = (start + timedelta(days=7 * i)).isoformat()
            h += f"R1,{d},basic,100\nR1,{d},rolled_up_holiday_pay,12.07\n"
        code, so, se, rep = self.run_cli(h, LV, W + "R1,irregular_rolled_up,01-01\n")
        self.assertEqual(code, 0, se)
        with open(os.path.join(self.d, "out", "exceptions.csv")) as fh:
            ex = fh.read().splitlines()
        self.assertGreater(len(ex) - 1, 20)
        self.assertEqual(rep.count("(rolled-up holiday pay)"), 20)
        self.assertIn("and ", rep)
        self.assertIn("more rolled-up pay exception(s)", rep)
        self.assertIn("exceptions.csv", rep)
        self.assertLess(len(rep), 20000)

    def test_cap_is_per_worker(self):
        h = H
        for wid in ("R1", "R2"):
            for i in range(25):
                d = (date(2024, 1, 6) + timedelta(days=7 * i)).isoformat()
                h += f"{wid},{d},basic,100\n{wid},{d},rolled_up_holiday_pay,12.07\n"
        code, so, se, rep = self.run_cli(h, LV, W + "R1,irregular_rolled_up,01-01\nR2,irregular_rolled_up,01-01\n")
        self.assertEqual(rep.count("(rolled-up holiday pay)"), 40)
        self.assertIn("### R1: and 5 more", rep.replace("\\", ""))
        self.assertIn("### R2: and 5 more", rep.replace("\\", ""))


class I2Escape(unittest.TestCase):
    def test_explain_rolled_up_escapes_by_default(self):
        r = {"worker_id": "a*b[c]", "week_end": date(2025, 6, 7), "leave_year_start": date(2025, 4, 1), "paid": D("1"),
             "counts": D("10"), "due": D("1.21"), "difference": D("0.21"), "flags": []}
        out = explain_rolled_up(r, lambda x: str(x))
        self.assertIn("a\\*b\\[c\\]", out)


class I1Docs(unittest.TestCase):
    def test_format_lists_all_masked_columns(self):
        with open(os.path.join(HERE, "..", "ingest", "FORMAT.md"), encoding="utf-8") as fh:
            t = fh.read()
        for col in ("leave_year_start", "contract_weekly_basic", "`weeks`"):
            self.assertIn(col, t.split("## history.csv")[0])


if __name__ == "__main__":
    unittest.main()
