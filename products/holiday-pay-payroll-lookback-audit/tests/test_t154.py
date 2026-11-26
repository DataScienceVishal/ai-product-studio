"""T-154: G1 excluded_week (no reason), G6 masked worker_id in messages, G8 name-like worker_id warning."""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import audit as cli
from ingest import load_workers, ValidationError, name_like_id_warnings

H = "worker_id,week_ending,element_category,amount\n"
L = "worker_id,week_ending\n"


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def f(self, name, text):
        p = os.path.join(self.tmp.name, name)
        with open(p, "w") as fh:
            fh.write(text)
        return p

    def issues(self, h, l=L + "AB1234,2025-06-07\n", w=None):
        with self.assertRaises(ValidationError) as cm:
            load_workers(self.f("h.csv", h), self.f("l.csv", l), self.f("w.csv", w) if w else None)
        return [str(i) for i in cm.exception.issues]


class G1(Case):
    def test_statutory_is_refused_with_clear_message(self):
        msgs = self.issues(H + "AB1234,2025-06-07,statutory,116.75\n")
        self.assertTrue(any("'statutory' is no longer accepted" in m and "excluded_week" in m for m in msgs), msgs)

    def test_excluded_week_nonzero_amount_refused(self):
        msgs = self.issues(H + "AB1234,2025-06-07,excluded_week,116.75\n")
        self.assertTrue(any("excluded_week must have amount 0" in m for m in msgs), msgs)
        self.assertFalse(any("116.75" in m for m in msgs))

    def test_excluded_week_zero_accepted_and_skipped_like_before(self):
        rows = "".join(f"AB1234,2025-{m}-{d:02d},basic,300\n" for m, d in [("05", 3), ("05", 10), ("05", 17)])
        w = load_workers(self.f("h.csv", H + rows + "AB1234,2025-05-24,excluded_week,0\n"
                                + "AB1234,2025-05-31,basic,300\n"), self.f("l.csv", L + "AB1234,2025-05-31\n"))
        self.assertIn("excluded_week", w["AB1234"].history[__import__("datetime").date(2025, 5, 24)])

    def test_sample_has_no_statutory(self):
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, "samples", "history.csv")) as fh:
            text = fh.read()
        self.assertNotIn("statutory", text)
        self.assertIn("excluded_week,0", text)


class G6(Case):
    def test_messages_mask_worker_id(self):
        wid = "SECRETID99"
        msgs = self.issues(
            H + f"{wid},2025-06-07,basic,1\n{wid},2025-06-07,basic,2\n{wid},2025-06-09,basic,2\n",
            L + f"{wid},2025-06-07\n{wid},2025-06-07\n{wid},2025-06-09\nOTHERID77,2025-06-07\n",
            "worker_id,worker_type,contract_weekly_basic\n"
            f"{wid},fixed_pay,0\n{wid},variable_hours,\nNOHISTORY1,variable_hours,\n")
        self.assertGreaterEqual(len(msgs), 6)
        for m in msgs:
            self.assertNotIn("SECRETID99", m)
            self.assertNotIn("OTHERID77", m)
            self.assertNotIn("NOHISTORY1", m)
        self.assertTrue(any("SE***" in m for m in msgs))


class G8(Case):
    def test_name_like_ids_warn_masked_and_run_succeeds(self):
        h = "".join(f"john.smith,2025-{m}-{d:02d},basic,300\n" for m, d in [("05", 3), ("05", 10), ("05", 17)])
        hp = self.f("h.csv", H + h)
        lp = self.f("l.csv", L + "john.smith,2025-05-17\n")
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            code = cli.main(["--history", hp, "--leave", lp, "--out", os.path.join(self.tmp.name, "out")])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn("looks like a person's name", err.getvalue())
        self.assertIn("jo***", err.getvalue())
        self.assertNotIn("john.smith", err.getvalue())

    def test_detection(self):
        ws = {k: None for k in ("john.smith", "mary_jones", "john-smith", "EMP100234", "JSmith1990", "AB1234", "w-001")}
        got = name_like_id_warnings(ws)
        self.assertEqual(len(got), 3)
        self.assertTrue(all("***" in g for g in got))


if __name__ == "__main__":
    unittest.main()
