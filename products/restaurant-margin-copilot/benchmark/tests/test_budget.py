import json

import pytest

import budget as b


def test_check_refuses_before_spending_past_the_cap(tmp_path):
    bud = b.Budget(tmp_path / "l.jsonl", max_usd=0.05)
    bud.check(2000, 16000)  # worst case 0.0325: fits
    bud.record("p1", 2000, 16000)  # billed in full: 0.0325
    with pytest.raises(b.BudgetExceeded):
        bud.check(2000, 16000)  # another 0.0325 would reach 0.065


def test_spend_is_cumulative_across_runs_via_the_ledger(tmp_path):
    led = tmp_path / "l.jsonl"
    b.Budget(led).record("a", 1_000_000, 1_000_000)  # 0.25 + 2.00
    again = b.Budget(led)
    assert again.spent_usd == pytest.approx(2.25)
    with pytest.raises(b.BudgetExceeded):
        b.Budget(led, max_usd=2.27).check(1000, 16000)


def test_spend_recomputed_from_tokens_not_stored_usd(tmp_path):
    led = tmp_path / "l.jsonl"
    led.write_text(json.dumps({"label": "x", "input_tokens": 1_000_000, "output_tokens": 0, "usd": 0.0, "model": "gpt-5-mini"}) + "\n")
    assert b.Budget(led).spent_usd == pytest.approx(0.25)


def test_unknown_model_never_priced_at_zero(tmp_path):
    with pytest.raises(b.UnknownModel):
        b.Budget(tmp_path / "l.jsonl", model="gpt-5.4-pro")  # the pro deployment must not be used here


def test_default_cap_is_five_dollars():
    assert b.MAX_USD == 5.0
