import copy
import json
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH))
import score  # noqa: E402
import taxonomy as tx  # noqa: E402

DATA = BENCH / "data"


@pytest.fixture(scope="module")
def loaded():
    truths, _, texts, messy = score.load_set("test", "/nonexistent")
    return truths, texts, messy


def perfect(truth):
    """A prediction derived from truth (what a perfect extractor would return)."""
    return copy.deepcopy(truth)


def run(loaded, preds, cost=0.1):
    truths, texts, messy = loaded
    return score.score_set(truths, preds, texts, messy, {s: cost for s in truths})


def test_perfect_prediction_scores_100_and_passes(loaded):
    truths, _, _ = loaded
    r = run(loaded, {s: perfect(t) for s, t in truths.items()})
    o = r["overall"]
    assert o["field_accuracy"] == 1.0 and r["messy10"]["field_accuracy"] == 1.0
    assert o["untraced"] == 0 and o["fabricated"] == 0
    assert o["missing_handling"] == 1.0 and o["conflict_flag"] == 1.0
    assert o["slots"] == 457 and o["counts"]["conflict_slots"] == 22 and o["counts"]["missing_slots"] == 128
    assert r["pass"], r["checks"]


def test_tuning_perfect(tmp_path):
    truths, _, texts, _ = score.load_set("tuning", "/nonexistent")
    r = score.score_set(truths, {s: perfect(t) for s, t in truths.items()}, texts, set(), None, require_cost=False)
    assert r["overall"]["field_accuracy"] == 1.0 and r["overall"]["untraced"] == 0


def test_empty_prediction_fails_everything(loaded):
    r = run(loaded, {})
    assert r["overall"]["field_accuracy"] == 0 and not r["pass"]
    assert r["overall"]["missing_handling"] == 0 and r["overall"]["unflagged_conflicts"] == 22


def _first(truths, status, slot="weight_g"):
    for sid, t in truths.items():
        for i, c in enumerate(t["components"]):
            if slot in c and c[slot]["status"] == status:
                return sid, i
    raise AssertionError


def test_fabrication_counts_and_is_wrong(loaded):
    truths, _, _ = loaded
    preds = {s: perfect(t) for s, t in truths.items()}
    sid, i = next((s, i) for s, t in truths.items() for i, c in enumerate(t["components"])
                  if c["colour"]["status"] == "missing")
    preds[sid]["components"][i]["colour"] = {"status": "present", "value": "blue",
                                             "refs": [{"page": 1, "quote": "blue"}]}
    r = run(loaded, preds)
    assert r["overall"]["fabricated"] == 1
    assert r["overall"]["counts"]["missing_ok"] == 127 and r["overall"]["counts"]["correct"] == 456
    assert not r["checks"]["4a_missing_handling>=0.95"] or r["overall"]["missing_handling"] >= 0.95


def test_conflict_silent_pick_flag_without_values_and_false_conflict(loaded):
    truths, _, _ = loaded
    sid, i = _first(truths, "conflict")
    t = truths[sid]["components"][i]["weight_g"]
    # silent pick
    p = {s: perfect(x) for s, x in truths.items()}
    p[sid]["components"][i]["weight_g"] = {"status": "present", "value": t["conflict_values"][0],
                                           "refs": [t["refs"][0]]}
    o = run(loaded, p)["overall"]["counts"]
    assert o["conflict_ok"] == 21 and o["unflagged_conflicts"] == 1
    # flag with one value only
    p = {s: perfect(x) for s, x in truths.items()}
    p[sid]["components"][i]["weight_g"]["conflict_values"] = [t["conflict_values"][0]]
    o = run(loaded, p)["overall"]["counts"]
    assert o["conflict_ok"] == 21 and o["conflict_flagged"] == 22
    # false conflict on a present weight
    sid2, j = _first(truths, "present")
    p = {s: perfect(x) for s, x in truths.items()}
    w = truths[sid2]["components"][j]["weight_g"]
    p[sid2]["components"][j]["weight_g"] = {"status": "conflict", "conflict_values": [w["value"], w["value"] + 5],
                                            "refs": w["refs"]}
    o = run(loaded, p)["overall"]["counts"]
    assert o["false_conflicts"] == 1 and o["correct"] == 456


def test_conflict_values_in_tolerance_and_order_free(loaded):
    truths, _, _ = loaded
    sid, i = _first(truths, "conflict")
    t = truths[sid]["components"][i]["weight_g"]
    p = {s: perfect(x) for s, x in truths.items()}
    a, b = t["conflict_values"]
    p[sid]["components"][i]["weight_g"]["conflict_values"] = [b * 1.005, a]
    assert run(loaded, p)["overall"]["counts"]["conflict_ok"] == 22


def test_untraced_value_is_counted_and_blocks_pass(loaded):
    truths, _, _ = loaded
    p = {s: perfect(t) for s, t in truths.items()}
    sid = "S001"
    p[sid]["components"][0]["material"]["refs"] = [{"page": 1, "quote": "not on the page"}]
    r = run(loaded, p)
    assert r["overall"]["untraced"] == 1 and not r["checks"]["3_untraced==0"] and not r["pass"]
    assert r["overall"]["field_accuracy"] == 1.0  # still correct, only untraced
    p[sid]["components"][0]["material"]["refs"] = []
    assert run(loaded, p)["overall"]["untraced"] == 1
    # wrong page
    p = {s: perfect(t) for s, t in truths.items()}
    ref = p[sid]["components"][0]["weight_g"]["refs"][0]
    ref["page"] = 9
    assert run(loaded, p)["overall"]["untraced"] == 1


def test_scanned_sheet_uses_recorded_page_text(loaded):
    truths, texts, _ = loaded
    assert texts["S021"][0].startswith("Oakridge") or len(texts["S021"][0]) > 50
    r = run(loaded, {s: perfect(t) for s, t in truths.items()})
    assert r["per_sheet"]["S021"]["untraced"] == 0


def test_unmatched_and_extra_components(loaded):
    truths, _, _ = loaded
    p = {s: perfect(t) for s, t in truths.items()}
    p["S001"]["components"].append(copy.deepcopy(p["S001"]["components"][0]))
    p["S001"]["components"][-1]["name"] = "wibble"
    o = run(loaded, p)["overall"]
    assert o["slots"] == 461 and o["counts"]["correct"] == 457  # 4 extra wrong slots for an unknown name
    # drop a component: its slots are all missed
    p = {s: perfect(t) for s, t in truths.items()}
    n = len(tx.PLAUSIBLE[truths["S011"]["components"][0]["name"]])
    p["S011"]["components"].pop(0)
    o = run(loaded, p)["overall"]["counts"]
    assert o["correct"] <= 457 - 3 - n


def test_name_variants_and_wrong_vocabulary(loaded):
    truths, _, _ = loaded
    p = {s: perfect(t) for s, t in truths.items()}
    comp = p["S001"]["components"][0]
    comp["name"] = {"bottle": "bottle body", "cap": "screw cap"}.get(comp["name"], comp["name"])
    assert run(loaded, p)["overall"]["field_accuracy"] == 1.0
    # "PETG" for PET is wrong (no containment matching)
    mats = [(s, i) for s, t in truths.items() for i, c in enumerate(t["components"])
            if c["material"].get("value") == "PET"]
    sid, i = mats[0]
    p = {s: perfect(t) for s, t in truths.items()}
    p[sid]["components"][i]["material"]["value"] = "PETG"
    assert run(loaded, p)["overall"]["counts"]["correct"] == 456


def test_ram_category_only_when_material_present(loaded):
    truths, _, _ = loaded
    sid, i = next((s, i) for s, t in truths.items() for i, c in enumerate(t["components"])
                  if c["material"]["status"] == "missing")
    p = {s: perfect(t) for s, t in truths.items()}
    p[sid]["components"][i]["ram_category"] = "glass"  # ignored: not scored when material is missing
    assert run(loaded, p)["overall"]["field_accuracy"] == 1.0
    sid, i = next((s, i) for s, t in truths.items() for i, c in enumerate(t["components"])
                  if c["material"]["status"] == "present")
    p = {s: perfect(t) for s, t in truths.items()}
    p[sid]["components"][i]["ram_category"] = "other"
    assert run(loaded, p)["overall"]["counts"]["correct"] == 456


def test_cost_check(loaded):
    truths, texts, messy = loaded
    p = {s: perfect(t) for s, t in truths.items()}
    assert score.score_set(truths, p, texts, messy, {s: 0.31 for s in truths})["pass"]
    assert not score.score_set(truths, p, texts, messy, {s: 0.40 for s in truths})["pass"]
    assert not score.score_set(truths, p, texts, messy, None)["pass"]  # no ledger: cost unproven


def test_messy10_threshold_binds(loaded):
    truths, _, messy = loaded
    p = {s: perfect(t) for s, t in truths.items()}
    for sid in messy:  # blank out material, colour and weight in the messy tier
        for c in p[sid]["components"]:
            c["material"] = {"status": "missing"}
            c["colour"] = {"status": "missing"}
            c["weight_g"] = {"status": "missing"}
    r = run(loaded, p)
    assert r["messy10"]["field_accuracy"] < 0.80 and not r["checks"]["2_messy10_field_accuracy>=0.80"]
