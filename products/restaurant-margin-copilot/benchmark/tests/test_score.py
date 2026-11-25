import copy
import json
from pathlib import Path

import pytest

import score as s

DATA = Path(__file__).resolve().parents[1] / "data" / "dev"
LINE_KEYS = ("description", "pack_size", "unit", "qty", "unit_price", "line_total", "vat_rate")


def truth(name="DEV-008"):
    return json.loads((DATA / f"{name}.json").read_text())


def page_records(t, mutate=None, status="ok"):
    """Perfect page records for a truth invoice, optionally with the predicted lines of each page changed by `mutate`."""
    recs = []
    for n in range(1, t["pages"] + 1):
        lines = [{k: ln[k] for k in LINE_KEYS} for ln in t["lines"] if ln["page"] == n]
        last = n == t["pages"]
        data = {"supplier_name": t["supplier"], "invoice_number": t["invoice_no"], "invoice_date": t["date"],
                "is_credit_note": t["credit_note"], "lines": lines,
                "totals": {"net": t["totals"]["net"], "vat": t["totals"]["vat"], "gross": t["totals"]["gross"]} if last
                else {"net": None, "vat": None, "gross": None}}
        recs.append({"page_id": f"{t['id']}_p{n}", "invoice_id": t["id"], "page_no": n, "status": status, "latency_s": 10.0,
                     "input_tokens": 1500, "output_tokens": 800, "cost_usd": 0.003, "retries": 0,
                     "data": data if status == "ok" else None})
    if mutate:
        mutate(recs)
    return recs


def test_perfect_extraction_scores_100():
    t = truth()
    r = s.score_invoice(t, page_records(t))
    assert r["correct"] == r["truth_lines"] and r["hallucinated"] == 0 and r["wrong_lines"] == 0
    assert r["reconciled"] and not r["silent_error"]
    assert all(r["header"].values())


def test_perfect_multipage_and_credit_note():
    for name in ("DEV-001", "DEV-006"):
        t = truth(name)
        r = s.score_invoice(t, page_records(t))
        assert r["wrong_lines"] == 0 and r["reconciled"], name


def test_one_wrong_price_is_one_wrong_line():
    t = truth()

    def mutate(recs):
        recs[0]["data"]["lines"][2]["unit_price"] += 0.01

    r = s.score_invoice(t, page_records(t, mutate))
    assert r["correct"] == r["truth_lines"] - 1
    assert [d["errors"] for d in r["line_errors"]] == [["unit_price"]]
    # the line total is untouched, so the totals still reconcile: this wrong price is a silent error
    assert r["reconciled"] and r["silent_error"]


def test_price_within_half_a_penny_is_accepted():
    t = truth()

    def mutate(recs):
        recs[0]["data"]["lines"][0]["unit_price"] += 0.004

    assert s.score_invoice(t, page_records(t, mutate))["wrong_lines"] == 0


def test_wrong_line_total_breaks_reconciliation_and_is_not_silent():
    t = truth()

    def mutate(recs):
        recs[0]["data"]["lines"][1]["line_total"] += 5.00

    r = s.score_invoice(t, page_records(t, mutate))
    assert r["wrong_lines"] == 1 and not r["reconciled"] and not r["silent_error"]


def test_missing_line():
    t = truth()

    def mutate(recs):
        del recs[0]["data"]["lines"][3]

    r = s.score_invoice(t, page_records(t, mutate))
    assert r["correct"] == r["truth_lines"] - 1 and r["hallucinated"] == 0
    assert len(r["missing"]) == 1 and not r["reconciled"]


def test_extra_line_lowers_accuracy():
    t = truth()

    def mutate(recs):
        recs[0]["data"]["lines"].append({"description": "ZZZ INVENTED THING", "pack_size": "", "unit": "each", "qty": 1.0,
                                         "unit_price": 1.0, "line_total": 1.0, "vat_rate": 0})

    r = s.score_invoice(t, page_records(t, mutate))
    assert r["correct"] == r["truth_lines"] and r["hallucinated"] == 1 and r["wrong_lines"] == 1
    acc = s.acc([r])["accuracy"]
    assert acc == pytest.approx(r["truth_lines"] / (r["truth_lines"] + 1))


def test_wrong_pack_and_vat_and_qty_each_fail_the_line():
    t = truth("DEV-001")

    def mutate(recs):
        ls = recs[0]["data"]["lines"]
        ls[0]["pack_size"], ls[0]["unit"] = "", "each"  # a case read as a single each
        ls[1]["vat_rate"] = 5
        ls[2]["qty"] += 1

    r = s.score_invoice(t, page_records(t, mutate))
    kinds = sorted(e for d in r["line_errors"] for e in d["errors"])
    assert "pack" in kinds and "vat_rate" in kinds and "qty" in kinds


def test_credit_note_sign_is_checked():
    t = truth("DEV-003")  # a credit note
    assert t["credit_note"]

    def mutate(recs):
        recs[0]["data"]["lines"][0]["qty"] = -recs[0]["data"]["lines"][0]["qty"]

    r = s.score_invoice(t, page_records(t, mutate))
    assert any("qty" in d["errors"] for d in r["line_errors"])


def test_failed_page_counts_all_its_lines_as_wrong():
    t = truth("DEV-001")  # two pages
    recs = page_records(t)
    recs[1] = {**recs[1], "status": "failed", "data": None}
    r = s.score_invoice(t, recs)
    on_page2 = sum(1 for ln in t["lines"] if ln["page"] == 2)
    assert r["correct"] == r["truth_lines"] - on_page2 and r["failed_pages"] == [2] and not r["reconciled"]


def test_page_with_no_result_at_all_is_wrong_not_dropped():
    t = truth()
    r = s.score_invoice(t, [])
    assert r["correct"] == 0 and r["wrong_lines"] == r["truth_lines"]


def test_matching_is_one_to_one_with_duplicate_descriptions():
    truth_lines = [{"description": "MILK 2L"}, {"description": "MILK 2L"}]
    pred = [{"description": "MILK 2L"}]
    assert len(s.match_lines(truth_lines, pred)) == 1


def test_description_similarity_threshold():
    t = truth()
    t_line = t["lines"][0]

    def mutate(recs):
        recs[0]["data"]["lines"][0]["description"] = t_line["description"][:-4]  # chopped: below 0.95

    r = s.score_invoice(t, page_records(t, mutate))
    assert r["line_errors"] and r["line_errors"][0]["errors"] == ["description"]

    def tiny(recs):
        recs[0]["data"]["lines"][0]["description"] = t_line["description"].lower().replace(" ", "  ")  # case and spacing only

    assert s.score_invoice(t, page_records(t, tiny))["wrong_lines"] == 0


def test_levenshtein_and_p95_and_hungarian():
    assert s.levenshtein("kitten", "sitting") == 3
    assert s.p95(list(range(1, 101))) == 95  # nearest rank
    assert s.p95([5.0]) == 5.0 and s.p95([]) is None
    cols = s.hungarian([[4, 1, 3], [2, 0, 5], [3, 2, 2]])
    assert sum([[4, 1, 3], [2, 0, 5], [3, 2, 2]][i][c] for i, c in enumerate(cols)) == 5


def test_set_scoring_subsets_and_costs(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    for f in sorted(DATA.glob("DEV-*.json")):
        if f.name == "MANIFEST.json":
            continue
        t = json.loads(f.read_text())
        for r in page_records(t):
            (ext / f"{r['page_id']}.json").write_text(json.dumps(r))
    res = s.score_set(DATA, ext)
    m = res["metrics"]
    assert m["overall"]["accuracy"] == 1.0 and m["reconciliation_rate"] == 1.0 and m["silent_errors"] == 0
    assert m["failure_rate"] == 0 and m["pages"] == 14
    assert m["cost_per_page_usd"] == pytest.approx(0.003)
    assert m["p95_latency_s"] == 10.0
    for k in ("clean", "distorted", "dev_layouts", "credit_notes", "multipage"):
        assert m["subsets"][k]["invoices"] > 0 and m["subsets"][k]["accuracy"] == 1.0
    assert m["subsets"]["heldout"]["invoices"] == 0
    assert "Verdict" in s.report_md(res, "t")


def test_missing_pages_count_as_unscored_failures(tmp_path):
    ext = tmp_path / "ext"
    ext.mkdir()
    res = s.score_set(DATA, ext)
    m = res["metrics"]
    assert m["overall"]["accuracy"] == 0 and m["failure_rate"] == 1.0 and m["pages_unscored_no_result"] == 14


def test_verdict_bars():
    base = {"overall": {"accuracy": 0.96}, "subsets": {"distorted": {"accuracy": 0.92}, "heldout": {"accuracy": 0.93}},
            "silent_errors": 0, "cost_per_page_usd": 0.01, "failure_rate": 0.0, "reconciliation_rate": 0.95, "p95_latency_s": 30}
    assert s.verdict(base)["result"] == "PASS"
    assert s.verdict({**base, "overall": {"accuracy": 0.87}})["result"] == "KILL"
    assert s.verdict({**base, "silent_errors": 3})["result"] == "KILL"
    assert s.verdict({**base, "silent_errors": 2})["result"] == "INCONCLUSIVE"
    assert s.verdict({**base, "cost_per_page_usd": 0.06})["result"] == "KILL"
    assert s.verdict({**base, "p95_latency_s": 120})["result"] == "INCONCLUSIVE"
    assert s.verdict(copy.deepcopy({**base, "failure_rate": 0.06}))["result"] == "KILL"
