import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import score, gen

T = [{"date": "2026-04-06", "description": "DD ELMSTEAD UNITS RENT", "amount": -350.0, "balance": 100.0, "category": "premises"},
     {"date": "2026-04-07", "description": "BACS FROM ASHBY JOINERY LTD", "amount": 500.0, "balance": 600.0, "category": "turnover"}]


def P(**kw):
    base = {"date": "2026-04-06", "description": "DD ELMSTEAD UNITS RENT", "amount": -350.0, "balance": 100.0,
            "category": "premises", "confidence": 0.95}
    base.update(kw); return base


def test_perfect():
    s = score.score_doc(T, [P(), P(date="2026-04-07", description="BACS FROM ASHBY JOINERY LTD", amount=500.0, balance=600.0, category="turnover")])
    assert s["amount_acc"] == s["date_acc"] == s["category_acc"] == 1.0
    assert s["routed_to_review"] == 0 and s["auto_category_acc"] == 1.0


def test_missing_line_counts_as_review_and_miss():
    s = score.score_doc(T, [P()])
    assert s["lines_missed"] == 1 and s["amount_acc"] == 0.5 and s["routed_to_review"] == 0.5


def test_low_confidence_routed_and_excluded_from_auto():
    s = score.score_doc(T[:1], [P(category="other_expenses", confidence=0.5)])
    assert s["routed_to_review"] == 1.0 and s["auto_lines"] == 0 and s["auto_category_acc"] is None


def test_confident_wrong_is_undetected_error():
    s = score.score_doc(T[:1], [P(category="repairs", confidence=0.9)])
    assert s["undetected_errors_in_auto"] == 1 and s["auto_category_acc"] == 0.0


def test_amount_must_be_exact():
    s = score.score_doc(T[:1], [P(amount=-350.01)])
    assert s["lines_matched"] == 0 and s["amount_acc"] == 0.0


def test_review_time_halves_when_most_auto():
    truth = [dict(T[0], date=f"2026-04-{d:02d}", amount=-float(d)) for d in range(1, 31)]
    pred = [P(date=t["date"], amount=t["amount"]) for t in truth]
    s = score.score_doc(truth, pred)
    assert s["review_time_halved"] and s["review_time_ratio"] < 0.5


def test_amount_parsing_and_fuzzy_desc():
    assert score.to_amount("£1,234.50") == 1234.5 and score.to_amount("x") is None
    assert score.desc_sim("Card Payment to Quickfix Tyres", "CARD PAYMENT TO QUICKFIX TYRES") == 1.0


def test_generator_truth_consistent(tmp_path):
    t, op = gen.make_txns(7)
    assert 25 <= len(t) <= 40
    assert {x["category"] for x in t} <= set(gen.CATS)
    bal = op
    for x in t:
        bal = round(bal + x["amount"], 2); assert bal == x["balance"]
