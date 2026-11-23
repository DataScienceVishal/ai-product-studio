"""Tests for scripts/azure_spend.py. Run: python3 -m unittest discover -s scripts/tests"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "azure_spend.py"
spec = importlib.util.spec_from_file_location("azure_spend", SCRIPT)
spend = importlib.util.module_from_spec(spec)
sys.modules["azure_spend"] = spend  # dataclasses look the module up by name
spec.loader.exec_module(spend)

CFG = {"group": "rg-ai-studio", "since": "2026-11-01", "cap": 80.0}
TODAY = date(2026, 11, 23)
RG = "/subscriptions/s/resourceGroups/rg-ai-studio/providers"
BUDGET = """# Azure budget

Cap: $80 of Azure for Students credit, resource group `rg-ai-studio` only.

Month-to-date spend: not reported yet (board task T-2)

| Resource | Product | Created (UTC) | Estimated $ per month | Status |
|---|---|---|---|---|
| ca-starter-demo (Container App) | _starter | 2026-11-20 | 0 | live |
| pg-shared | all | 2026-11-21 | $12.50 | live |
"""


def result(columns, rows, next_link=None):
    props = {"columns": [{"name": c, "type": "x"} for c in columns], "rows": rows}
    if next_link:
        props["nextLink"] = next_link
    return {"properties": props}


def ok(mtd, since, resources=(), currency="USD"):
    return spend.Outcome(results={
        "month_to_date": result(["totalCost", "Currency"], [[mtd, currency]]),
        "since_start": result(["totalCost", "Currency"], [[since, currency]]),
        "by_resource": result(["totalCost", "ResourceId", "Currency"],
                              [[c, f"{RG}/{rid}", currency] for rid, c in resources]),
    }, inventory=[])


def render(text, outcome, stamp="T"):
    return spend.render(text, CFG, outcome, stamp, TODAY)


class Parsing(unittest.TestCase):
    def test_total_reports_rows_and_currency(self):
        r = result(["PreTaxCost", "Currency"], [[1.234, "USD"], [2.0, "USD"]])
        self.assertEqual(spend.total(r), (3.23, "USD", 2))
        self.assertEqual(spend.total({}), (0.0, None, 0))

    def test_top_level_names_keep_children_distinct(self):
        a = spend.top_level(f"{RG}/Microsoft.Storage/storageAccounts/acc1/blobServices/default")
        b = spend.top_level(f"{RG}/Microsoft.Storage/storageAccounts/acc2/blobServices/default")
        self.assertEqual(a, ("acc1", "acc1/blobServices/default"))
        self.assertNotEqual(a[1], b[1])
        self.assertEqual(spend.top_level(f"{RG}/Microsoft.App/containerApps/ca-x"), ("ca-x", "ca-x"))

    def test_listed_names_are_exact_first_words(self):
        names = spend.listed_names(BUDGET)
        self.assertEqual(names, {"ca-starter-demo", "pg-shared"})
        self.assertNotIn("pg", names)

    def test_projected_monthly_sums_the_estimates_column(self):
        self.assertEqual(spend.projected_monthly(BUDGET), 12.5)

    def test_window_is_clamped_to_the_api_limit(self):
        start, end, clamped = spend.query_window("2025-01-01", TODAY)
        self.assertTrue(clamped)
        self.assertEqual(end, "2026-11-23")
        self.assertEqual(date.fromisoformat(start), date(2025, 11, 24))
        self.assertFalse(spend.query_window("2026-11-01", TODAY)[2])


class Markers(unittest.TestCase):
    def test_first_run_appends_one_block_and_keeps_the_table(self):
        text, *_ = render(BUDGET, ok(1.5, 1.5, [("Microsoft.App/containerApps/ca-starter-demo", 1.5)]))
        self.assertEqual(len(spend.START_LINE.findall(text)), 1)
        self.assertIn("| pg-shared | all |", text)
        self.assertIn("| ca-starter-demo | - | 1.50 | yes |", text)

    def test_second_run_replaces_the_block_in_place(self):
        once, *_ = render(BUDGET, ok(1, 1), stamp="DAY1")
        twice, *_ = render(once, ok(2, 2), stamp="DAY2")
        self.assertEqual(len(spend.START_LINE.findall(twice)), 1)
        self.assertNotIn("DAY1", twice)
        self.assertIn("$2.00 of $80 cap", twice)
        self.assertIn("| pg-shared | all |", twice)

    def test_a_note_that_mentions_the_markers_inline_is_left_alone(self):
        noted = BUDGET.replace("Cap: $80", f"Don't edit between `{spend.START}` and `{spend.END}`.\n\nCap: $80")
        once, *_ = render(noted, ok(1, 1), stamp="DAY1")
        twice, *_ = render(once, ok(2, 2), stamp="DAY2")
        self.assertIn("Don't edit between", twice)
        self.assertNotIn("DAY1", twice)
        self.assertIn("| pg-shared | all |", twice)

    def test_malformed_markers_refuse_to_write(self):
        good, *_ = render(BUDGET, ok(1, 1))
        cases = {
            "missing end": good.replace(spend.END + "\n", ""),
            "missing start": good.replace(spend.START + "\n", ""),
            "end before start": good.replace(spend.START, "TMP").replace(spend.END, spend.START).replace("TMP", spend.END),
            "two blocks": good + "\n" + good[good.index(spend.START):],
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(spend.MarkerError):
                render(text, ok(1, 1))

    def test_rows_added_after_the_block_count_as_listed(self):
        once, *_ = render(BUDGET, ok(1, 1))
        later = once + "| kv-studio (Key Vault) | all | 2026-11-23 | 1 | live |\n"
        _, _, unlisted, _, _ = render(later, ok(1, 1, [("Microsoft.KeyVault/vaults/kv-studio", 0.4)]))
        self.assertEqual(unlisted, [])


class Figures(unittest.TestCase):
    def test_unlisted_costly_resource_is_flagged(self):
        text, _, unlisted, _, _ = render(BUDGET, ok(3, 3, [("Microsoft.Web/sites/pg", 3.0)]))
        self.assertEqual(unlisted, ["pg"])  # "pg-shared" in the table must not count as "pg"
        self.assertIn("| pg | - | 3.00 | no: add it |", text)

    def test_no_rows_is_not_reported_as_zero_spend(self):
        empty = spend.Outcome(results={q: {} for q in spend.QUERIES}, inventory=[])
        text, *_ = render(BUDGET, empty)
        self.assertIn("No cost rows came back", text)
        self.assertIn("Cost rows returned: month to date 0, since start 0, by resource 0", text)

    def test_non_usd_currency_is_not_compared_with_the_cap(self):
        text, alert, _, status, digest = render(BUDGET, ok(70, 70, currency="GBP"))
        self.assertEqual(status, "currency")
        self.assertIsNone(alert)
        self.assertIn("70.00 GBP", text)
        self.assertNotIn("$70.00", text)
        self.assertEqual(digest, [])

    def test_alert_fires_once_per_level_and_goes_to_the_digest(self):
        text, alert, _, _, digest = render(BUDGET, ok(41, 41))
        self.assertEqual(alert, 50)
        self.assertIn("passed 50%", digest[0])
        text, alert, _, _, digest = render(text, ok(45, 45))
        self.assertIsNone(alert)
        self.assertEqual(digest, [])
        text, alert, *_ = render(text, ok(77, 77))
        self.assertEqual(alert, 95)
        self.assertIn("Last alert level: 95% (since 2026-11-01)", text)

    def test_a_new_since_date_resets_the_alert_level(self):
        text, *_ = render(BUDGET, ok(77, 77))
        renewed = dict(CFG, since="2027-11-01")
        _, alert, *_ = spend.render(text, renewed, ok(41, 41), "T", date(2027, 11, 20))
        self.assertEqual(alert, 50)

    def test_next_link_is_mentioned(self):
        outcome = ok(1, 1)
        outcome.results["by_resource"] = result(["totalCost", "ResourceId", "Currency"], [], next_link="https://x")
        text, *_ = render(BUDGET, outcome)
        self.assertIn("nextLink", text)


class Unavailability(unittest.TestCase):
    def test_unavailable_is_written_down_with_its_start_date(self):
        down = spend.Outcome(error=spend.Unavailable("http_400", "BadRequest: offer not supported"),
                             inventory=[{"id": f"{RG}/Microsoft.App/containerApps/ca-new", "name": "ca-new",
                                         "type": "Microsoft.App/containerApps"}])
        text, alert, unlisted, status, digest = render(BUDGET, down)
        self.assertEqual(status, "unavailable")
        self.assertIsNone(alert)
        self.assertIn("Status: unavailable since 2026-11-23: http_400 (BadRequest: offer not supported). Spend is unknown.", text)
        self.assertEqual(unlisted, ["ca-new"])  # cost unknown, so anything unlisted is flagged
        self.assertEqual(len(digest), 1)
        later, *_, digest_again = spend.render(text, CFG, down, "T2", date(2026, 11, 25))
        self.assertIn("unavailable since 2026-11-23", later)  # keeps the first day it went down
        self.assertEqual(digest_again, [])  # and doesn't nag every day
        self.assertIn("Month-to-date spend: see the spend report below (spend unknown (unavailable)", later)

    def test_free_inventory_items_are_not_flagged_when_figures_exist(self):
        outcome = ok(0, 0)
        outcome.inventory = [{"id": f"{RG}/Microsoft.ManagedIdentity/userAssignedIdentities/id-x", "name": "id-x",
                              "type": "Microsoft.ManagedIdentity/userAssignedIdentities"}]
        text, _, unlisted, _, _ = render(BUDGET, outcome)
        self.assertEqual(unlisted, [])
        self.assertIn("| id-x | Microsoft.ManagedIdentity/userAssignedIdentities | - | no (no cost so far) |", text)


class FakeAzure(BaseHTTPRequestHandler):
    script: list = []

    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        status, headers, body = FakeAzure.script.pop(0)
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


class Post(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeAzure)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/query"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def call(self, script):
        FakeAzure.script = list(script)
        waits = []
        try:
            return spend.post(self.url, "token", {}, sleep=waits.append), waits
        except spend.Unavailable as error:
            return error, waits

    def test_no_content_is_empty(self):
        self.assertEqual(self.call([(204, {}, "")]), ({}, []))

    def test_qpu_retry_header_is_honoured(self):
        body = json.dumps(result(["totalCost"], [[1.0]]))
        got, waits = self.call([(429, {"x-ms-ratelimit-microsoft.costmanagement-qpu-retry-after": "30"}, ""),
                                (503, {"Retry-After": "2"}, ""), (200, {}, body)])
        self.assertEqual(waits, [30.0, 2.0])
        self.assertEqual(spend.total(got)[0], 1.0)

    def test_client_errors_are_unavailable_with_the_azure_code(self):
        body = json.dumps({"error": {"code": "BadRequest", "message": "Offer MS-AZR-0170P is not supported."}})
        error, waits = self.call([(400, {}, body)])
        self.assertIsInstance(error, spend.Unavailable)
        self.assertEqual(error.code, "http_400")
        self.assertIn("not supported", error.detail)
        self.assertEqual(waits, [])

    def test_persistent_throttling_gives_up_without_a_final_sleep(self):
        error, waits = self.call([(429, {}, "")] * 5)
        self.assertEqual(error.code, "http_429")
        self.assertIn("throttling", error.detail)
        self.assertEqual(len(waits), 4)


class Cli(unittest.TestCase):
    def run_report(self, outcome: dict, budget: str = BUDGET):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "scripts").mkdir()
        (root / "state").mkdir()
        (root / "scripts" / "azure_spend.py").write_text(SCRIPT.read_text())
        (root / "state" / "BUDGET.md").write_text(budget)
        (root / "state" / "DIGEST_NOTES.md").write_text("# Notes for the next digest\n")
        saved = root / "saved"
        saved.mkdir()
        (saved / "outcome.json").write_text(json.dumps(outcome))
        done = subprocess.run([sys.executable, str(root / "scripts" / "azure_spend.py"), "report", "--from-dir", str(saved)],
                              capture_output=True, text=True)
        return done, root

    def test_report_from_saved_outcome_alerts_and_notes_the_digest(self):
        outcome = {"results": {
            "month_to_date": result(["totalCost", "Currency"], [[60.4, "USD"]]),
            "since_start": result(["totalCost", "Currency"], [[60.4, "USD"]]),
            "by_resource": result(["totalCost", "ResourceId", "Currency"], [])}, "inventory": [], "error": None}
        done, root = self.run_report(outcome)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("STATUS ok", done.stdout)
        self.assertIn("ALERT 75", done.stdout)
        self.assertIn("$60.40 of $80", (root / "state" / "BUDGET.md").read_text())
        self.assertIn("passed 75%", (root / "state" / "DIGEST_NOTES.md").read_text())

    def test_unavailable_outcome_still_writes_and_exits_zero(self):
        done, root = self.run_report({"results": None, "inventory": None, "inventory_error": "az_failed: x",
                                      "error": {"code": "http_403", "detail": "RBACAccessDenied"}})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("STATUS unavailable", done.stdout)
        self.assertIn("unavailable since", (root / "state" / "BUDGET.md").read_text())

    def test_malformed_markers_exit_3_and_leave_the_file_alone(self):
        broken = BUDGET + f"\n{spend.START}\nhalf a block\n"
        done, root = self.run_report({"results": None, "inventory": [], "error": None}, budget=broken)
        self.assertEqual(done.returncode, 3)
        self.assertEqual((root / "state" / "BUDGET.md").read_text(), broken)


if __name__ == "__main__":
    unittest.main()
