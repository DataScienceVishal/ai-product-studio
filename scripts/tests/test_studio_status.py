"""Tests for studio.py's budget line. Run: python3 -m unittest discover -s scripts/tests"""
import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "studio.py"
spec = importlib.util.spec_from_file_location("studio", SCRIPT)
studio = importlib.util.module_from_spec(spec)
sys.modules["studio"] = studio
spec.loader.exec_module(studio)

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)
START, END = "<!-- spend:auto:start -->", "<!-- spend:auto:end -->"


class BudgetLine(unittest.TestCase):
    def line(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            studio.STATE = Path(tmp)
            (studio.STATE / "BUDGET.md").write_text(text)
            return studio.budget_line(NOW)

    def block(self, body):
        return f"# Azure budget\n\n{START}\n{body}\n{END}\n"

    def test_no_report_yet(self):
        self.assertIn("no spend report yet", self.line("# Azure budget\n"))

    def test_fresh_ok_report_shows_the_figures(self):
        text = self.block("- Updated: 2026-11-23T06:17:00Z. x\n- Status: ok\n- Since 2026-11-01: $41.00 of $80 cap (51%)")
        line = self.line(text)
        self.assertIn("$41.00 of $80 cap", line)
        self.assertNotIn("STALE", line)

    def test_stale_report_is_flagged(self):
        text = self.block("- Updated: 2026-11-21T06:17:00Z. x\n- Status: ok\n- Since 2026-11-01: $1.00 of $80 cap (1%)")
        self.assertIn("STALE", self.line(text))

    def test_unknown_spend_shows_the_status(self):
        text = self.block("- Updated: 2026-11-23T06:17:00Z. x\n- Status: no_data: Azure returned no cost rows. Spend is unknown.")
        self.assertIn("no_data", self.line(text))

    def test_hand_written_lines_outside_the_block_are_ignored(self):
        text = "- Updated: 2020-01-01T00:00:00Z (a note someone wrote)\n" + self.block(
            "- Updated: 2026-11-23T06:17:00Z. x\n- Status: ok\n- Since 2026-11-01: $2.00 of $80 cap (3%)")
        line = self.line(text)
        self.assertNotIn("STALE", line)
        self.assertIn("$2.00", line)


if __name__ == "__main__":
    unittest.main()
