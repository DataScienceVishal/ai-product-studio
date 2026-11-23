"""Tests for scripts/azure_spend.py. Run: python3 -m unittest discover -s scripts/tests"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "azure_spend.py"
spec = importlib.util.spec_from_file_location("azure_spend", SCRIPT)
spend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spend)

CFG = {"group": "rg-ai-studio", "since": "2026-11-01", "cap": 80.0}
BUDGET = """# Azure budget

Cap: $80 of Azure for Students credit, resource group `rg-ai-studio` only.

Month-to-date spend: not reported yet (board task T-2)

| Resource | Product | Created (UTC) | Estimated $ per month | Status |
|---|---|---|---|---|
| ca-starter-demo (Container App) | _starter | 2026-11-20 | 0 | live |
"""


def result(columns, rows):
    return {"properties": {"columns": [{"name": c, "type": "x"} for c in columns], "rows": rows}}


def results(mtd, since, resources):
    return {
        "month_to_date": result(["totalCost", "Currency"], [[mtd, "USD"]]),
        "since_start": result(["totalCost", "Currency"], [[since, "USD"]]),
        "by_resource": result(["totalCost", "ResourceId", "Currency"],
                              [[c, f"/subscriptions/x/resourcegroups/rg-ai-studio/providers/p/t/{n}", "USD"]
                               for n, c in resources]),
    }


class Parsing(unittest.TestCase):
    def test_total_sums_rows_and_reads_currency(self):
        r = result(["PreTaxCost", "Currency"], [[1.234, "GBP"], [2.0, "GBP"]])
        self.assertEqual(spend.total(r), (3.23, "GBP"))

    def test_empty_and_no_content_are_zero(self):
        self.assertEqual(spend.total({}), (0.0, "USD"))
        self.assertEqual(spend.total(result(["totalCost"], [])), (0.0, "USD"))

    def test_by_resource_groups_by_last_path_segment_and_drops_zero(self):
        r = results(0, 0, [("db1", 1.0), ("db1", 0.5), ("free-thing", 0.001)])["by_resource"]
        self.assertEqual(spend.by_resource(r), [("db1", 1.5)])

    def test_custom_query_covers_since_to_today(self):
        body = spend.bodies("2026-11-01", "2026-11-23")["since_start"]
        self.assertEqual(body["timeframe"], "Custom")
        self.assertEqual(body["timePeriod"], {"from": "2026-11-01T00:00:00Z", "to": "2026-11-23T23:59:59Z"})


class Render(unittest.TestCase):
    def test_first_run_replaces_line_and_appends_block(self):
        text, alert, unlisted = spend.render(BUDGET, CFG, results(1.5, 1.5, [("ca-starter-demo", 1.5)]), "T")
        self.assertIn("Month-to-date spend: $1.50 USD (as of T", text)
        self.assertNotIn("not reported yet", text)
        self.assertEqual(text.count(spend.START), 1)
        self.assertIn("| ca-starter-demo | 1.50 | yes |", text)
        self.assertIsNone(alert)
        self.assertEqual(unlisted, [])

    def test_second_run_replaces_block_in_place(self):
        once, _, _ = spend.render(BUDGET, CFG, results(1, 1, []), "T1")
        twice, _, _ = spend.render(once, CFG, results(2, 2, []), "T2")
        self.assertEqual(twice.count(spend.START), 1)
        self.assertEqual(twice.count("Month-to-date spend:"), 1)
        self.assertIn("$2.00 of $80 cap", twice)
        self.assertNotIn("T1", twice)

    def test_manual_table_is_preserved(self):
        text, _, _ = spend.render(BUDGET, CFG, results(0, 0, []), "T")
        self.assertIn("| ca-starter-demo (Container App) | _starter |", text)
        self.assertIn("(no costs recorded yet)", text)

    def test_unlisted_resource_is_flagged(self):
        text, _, unlisted = spend.render(BUDGET, CFG, results(3, 3, [("pg-shared", 3.0)]), "T")
        self.assertEqual(unlisted, ["pg-shared"])
        self.assertIn("| pg-shared | 3.00 | no: add it |", text)

    def test_alert_fires_once_per_level(self):
        text, alert, _ = spend.render(BUDGET, CFG, results(41, 41, []), "T")
        self.assertEqual(alert, 50)
        text, alert, _ = spend.render(text, CFG, results(45, 45, []), "T")
        self.assertIsNone(alert)
        text, alert, _ = spend.render(text, CFG, results(77, 77, []), "T")
        self.assertEqual(alert, 95)
        self.assertIn("Last alert level: 95%", text)

    def test_below_first_level_no_alert(self):
        _, alert, _ = spend.render(BUDGET, CFG, results(39.99, 39.99, []), "T")
        self.assertIsNone(alert)


class Cli(unittest.TestCase):
    def test_report_from_saved_responses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "state").mkdir()
            (root / "scripts" / "azure_spend.py").write_text(SCRIPT.read_text())
            (root / "state" / "BUDGET.md").write_text(BUDGET)
            saved = root / "saved"
            saved.mkdir()
            for name, body in results(60.4, 60.4, [("pg-shared", 60.4)]).items():
                (saved / f"{name}.json").write_text(json.dumps(body))
            (saved / "by_resource.json").write_text("")  # a 204 saved as empty
            out = subprocess.run([sys.executable, str(root / "scripts" / "azure_spend.py"), "report",
                                  "--from-dir", str(saved)], capture_output=True, text=True, check=True)
            self.assertIn("ALERT 75", out.stdout)
            self.assertIn("$60.40 of $80", (root / "state" / "BUDGET.md").read_text())


if __name__ == "__main__":
    unittest.main()
