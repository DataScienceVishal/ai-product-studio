"""T-124: contract_weekly_basic validation (QA L3) and the glued-prefix NI decision."""
import os
import re
import unittest

from tests.test_audit import Base, H, L, run_cli
from ingest.loader import _NI_SHAPE, _NI_NEVER, _looks_like_ni

WH = "worker_id,worker_type,contract_weekly_basic\n"
HIST = H + "".join(f"W1,2025-05-{d:02d},basic,400\n" for d in (3, 10, 17))


class ContractBasic(Base):
    def go_workers(self, workers):
        out = os.path.join(self.tmp.name, "out")
        code, err = run_cli("--history", self.write("h.csv", HIST), "--leave", self.write("l.csv", L + "W1,2025-05-17\n"),
                            "--workers", self.write("w.csv", workers), "--out", out)
        report = ""
        if code == 0:
            with open(f"{out}/report.md") as fh:
                report = fh.read()
        return code, err, report

    def test_fixed_pay_zero_rejected_with_line(self):
        self.has(self.issues(HIST, workers=WH + "W1,fixed_pay,0\n"), "w.csv:2", "greater than 0")
        self.has(self.issues(HIST, workers=WH + "W1,fixed_pay,0.00\n"), "w.csv:2", "greater than 0")

    def test_fixed_pay_negative_rejected(self):
        self.has(self.issues(HIST, workers=WH + "W1,fixed_pay,-5\n"), "w.csv:2", "contract_weekly_basic")

    def test_zero_rejected_exit_2(self):
        code, err, _ = self.go_workers(WH + "W1,fixed_pay,0\n")
        self.assertEqual(code, 2)
        self.assertIn("w.csv:2", err)

    def test_fixed_pay_positive_and_blank_ok(self):
        for v in ("400", ""):
            code, err, _ = self.go_workers(WH + f"W1,fixed_pay,{v}\n")
            self.assertEqual(code, 0, err)

    def test_variable_hours_value_warns_not_fails(self):
        code, err, report = self.go_workers(WH + "W1,variable_hours,400\n")
        self.assertEqual(code, 0, err)
        self.assertIn("contract_weekly_basic ignored", err)
        self.assertIn("## Warning: contract_weekly_basic ignored", report)
        self.assertIn("W1: contract_weekly_basic ignored", report)

    def test_no_warning_when_not_given(self):
        code, err, report = self.go_workers(WH + "W1,variable_hours,\n")
        self.assertEqual(code, 0, err)
        self.assertNotIn("ignored", err)
        self.assertNotIn("contract_weekly_basic ignored", report)


PAYROLL_IDS = ("EMP0001 EMP1234 EMP100234 EMP100234A ABC123456 PAY-2024-001 W12345 W001 E-1234 STAFF42 STAFF100234A "
               "HRM000123 HRM123456 STORE12-123456 EMPLOYEE1042 CAT1234567 TEMP000123 TEMP000123B AGY-000456 "
               "CONTR100234 WK2024001 DRV00045 DRIVER000789 SITE3-0042 KIT123456 OPS100234A X12345678 ID123456 "
               "TECH000999 CARE00123").split()


class GluedNiDecision(unittest.TestCase):
    """A scan for an NI-shaped window after letters was measured and rejected: too many false positives."""

    @staticmethod
    def _glued_scan(wid):
        w = wid.upper()
        for m in re.finditer(r"(?=([A-Z]{2}[0-9]{6}[A-D]?))", w):
            i = m.start()
            if i > 0 and w[i - 1].isalpha() and _NI_SHAPE.match(m.group(1)) and m.group(1)[:2] not in _NI_NEVER:
                return True
        return False

    def test_scan_false_positive_rate_is_unacceptable(self):
        self.assertEqual(len(PAYROLL_IDS), len(set(PAYROLL_IDS)))
        hits = [i for i in PAYROLL_IDS if self._glued_scan(i) and not _looks_like_ni(i)]
        self.assertGreaterEqual(len(hits), 5, hits)       # includes the recommended EMP100234 shape
        self.assertTrue(self._glued_scan("EMP100234"))

    def test_glued_ni_still_undetected_and_plausible_ids_allowed(self):
        self.assertFalse(_looks_like_ni("EMPAB123456C"))
        for i in PAYROLL_IDS:
            self.assertFalse(_looks_like_ni(i), i)

    def test_doc_says_glued_not_detected(self):
        with open(os.path.join(os.path.dirname(__file__), "..", "ingest", "FORMAT.md")) as fh:
            doc = fh.read()
        self.assertIn("EMPAB123456C", doc)
        self.assertIn("deliberately not detected", doc)
