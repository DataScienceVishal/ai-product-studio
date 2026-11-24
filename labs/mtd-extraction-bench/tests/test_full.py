import json, sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pytest, budget, gen2, calib, score


def test_cost_formula():
    assert budget.Budget.cost(1_000_000, 0) == 15.0 and budget.Budget.cost(0, 1_000_000) == 120.0


def test_refuses_when_worst_case_crosses_cap(tmp_path):
    b = budget.Budget(tmp_path / "b.json", cap_usd=1.0, max_calls=15)
    w = b.reserve(1000, 6000)               # 0.015 + 0.72
    with pytest.raises(budget.BudgetRefused):
        b.reserve(1000, 6000)               # in flight counts: 0.735*2 > 1.0
    b.settle(w, "a", {"input_tokens": 1000, "output_tokens": 1000})
    assert b.calls == 1 and abs(b.usd - 0.135) < 1e-9
    b.reserve(1000, 6000)                   # 0.135 + 0.735 < 1.0 ok


def test_call_cap_and_persistence(tmp_path):
    p = tmp_path / "b.json"; b = budget.Budget(p, cap_usd=100, max_calls=2)
    for _ in range(2):
        b.settle(b.reserve(10, 10), "x", {"input_tokens": 10, "output_tokens": 10})
    with pytest.raises(budget.BudgetRefused):
        b.reserve(10, 10)
    b2 = budget.Budget(p, cap_usd=100, max_calls=2)     # a fresh process cannot reset the counter
    assert b2.calls == 2
    with pytest.raises(budget.BudgetRefused):
        b2.reserve(10, 10)


def test_unknown_outcome_billed_at_worst_case(tmp_path):
    b = budget.Budget(tmp_path / "b.json", cap_usd=5, max_calls=5)
    w = b.reserve(1000, 6000); b.settle(w, "t", None, charge_worst=True)
    assert abs(b.usd - w) < 1e-9


def test_parallel_reservations_never_exceed_cap(tmp_path):
    b = budget.Budget(tmp_path / "b.json", cap_usd=2.0, max_calls=50); ok = []
    def go():
        try:
            ok.append(b.reserve(1000, 6000))
        except budget.BudgetRefused:
            pass
    ts = [threading.Thread(target=go) for _ in range(10)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sum(ok) <= 2.0 and len(ok) == 2


@pytest.mark.parametrize("name,kind,layout,persona,seed", [p for p in gen2.PLAN if p[1] in ("pdf", "csv", "xlsx")])
def test_deterministic_extraction_matches_truth(tmp_path, name, kind, layout, persona, seed):
    import random
    tx, op = gen2.make_txns(persona, seed)
    if kind == "pdf":
        gen2.write_layout(layout, tmp_path / "d.pdf", tx, op); got = gen2.parse_pdf(layout, tmp_path / "d.pdf", op)
    elif kind == "csv":
        gen2.write_csv_layout(layout, tmp_path / "d.csv", tx); got = gen2.parse_csv_layout(layout, tmp_path / "d.csv")
    else:
        import gen
        rows = gen.write_messy_csv(tmp_path / "m.csv", tx, seed); gen.write_xlsx(tmp_path / "m.xlsx", rows)
        got = gen2.parse_sheet(tmp_path / "m.xlsx")
        tx = [{**t, "description": t["sheet_description"]} for t in tx]
    assert len(got) == len(tx)
    for g, t in zip(got, tx):
        assert (g["date"], g["amount"]) == (t["date"], t["amount"]) and score.desc_sim(g["description"], t["description"]) > 0.9


def test_calibration_rules_override_and_flag():
    rules = calib.build_rules([{"description": "CARD PAYMENT TO QUICKFIX TYRES", "category": "repairs"}])
    L = [{"description": "CARD PAYMENT TO QUICKFIX TYRES", "category": "car_van_travel", "confidence": 0.9},
         {"description": "DD STREAMBOX SUBSCRIPTION", "category": "other_expenses", "confidence": 0.95}]
    o = calib.apply(L, rules)
    assert o[0]["category"] == "repairs" and o[0]["confidence"] < 0.8        # disagreement: fixed and flagged
    assert o[1]["confidence"] <= 0.79                                       # risky category capped to review


def test_silent_error_penalty():
    T = [{"date": "2026-04-06", "description": "A", "amount": -1.0, "balance": None, "category": "repairs"}]
    P = [{"date": "2026-04-06", "description": "A", "amount": -1.0, "category": "premises", "confidence": 0.95}]
    s = score.score_doc(T, P)
    assert s["silent_errors"] == 1 and s["assisted_seconds_silent"] == s["assisted_seconds"] + 120
