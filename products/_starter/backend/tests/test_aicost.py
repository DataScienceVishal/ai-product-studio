"""T-91: the daily AI cap must be affordable at the price of the model that is actually deployed."""
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import aicost
from app.aicost import check_ai_budget, resolve_price
from app.config import Settings

AICOST = Path(aicost.__file__)


def make(**kw):
    base = {"env": "test", "database_url": "postgresql+psycopg://u:p@localhost/x"}
    return Settings(_env_file=None, **{**base, **kw})


def test_known_model_under_budget_passes():
    s = make(ai_provider="azure", azure_openai_deployment="gpt-5-mini")  # 100k x 30 x 2.00 = $6.00 <= $6.10
    assert s.ai_price_per_million_tokens is None
    assert check_ai_budget("gpt-5-mini", None, 100_000, 6.10) == pytest.approx(6.0)


def test_deployment_name_match_ignores_case_and_spaces():
    assert resolve_price(" GPT-5-Mini ") == 2.0


def test_pro_model_at_default_cap_fails_at_startup():
    with pytest.raises(ValidationError, match=r"\$540\.00 a month, over the \$6\.10 AI budget"):
        make(ai_provider="azure", azure_openai_deployment="gpt-5.4-pro")


def test_pro_model_with_small_enough_cap_passes():
    make(ai_provider="azure", azure_openai_deployment="gpt-5.4-pro", ai_global_daily_tokens=1_100)  # $5.94


def test_pro_model_one_token_over_fails():
    with pytest.raises(ValidationError):
        make(ai_provider="azure", azure_openai_deployment="gpt-5.4-pro", ai_global_daily_tokens=1_130)  # $6.10 -> over by rounding
    make(ai_provider="azure", azure_openai_deployment="gpt-5.4-pro", ai_global_daily_tokens=1_129)


def test_unknown_model_without_price_fails_and_hides_the_name():
    with pytest.raises(ValidationError) as err:
        make(ai_provider="azure", azure_openai_deployment="my-secret-deployment-name")
    assert "AI_PRICE_PER_MILLION_TOKENS" in str(err.value)
    assert "my-secret-deployment-name" not in str(err.value).split("input_value")[0]


def test_unknown_model_with_explicit_price_passes():
    make(ai_provider="azure", azure_openai_deployment="custom", ai_price_per_million_tokens=2.0)


def test_explicit_price_overrides_the_table_both_ways():
    # table says 2.00 (fine); explicit 180 makes the same cap fail
    with pytest.raises(ValidationError, match="over the"):
        make(ai_provider="azure", azure_openai_deployment="gpt-5-mini", ai_price_per_million_tokens=180)
    # table says 180 (fails); explicit 2.00 lets the default cap through
    make(ai_provider="azure", azure_openai_deployment="gpt-5.4-pro", ai_price_per_million_tokens=2.0)


def test_budget_setting_raises_the_ceiling():
    make(ai_provider="azure", azure_openai_deployment="gpt-5.4-pro", ai_monthly_budget_usd=600)


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf", "0", "-1", "abc", float("nan"), float("inf"), 0, -2.5])
def test_bad_prices_are_rejected_with_either_provider(bad):
    for provider in ("fake", "azure"):
        with pytest.raises(ValidationError):
            make(ai_provider=provider, azure_openai_deployment="gpt-5-mini", ai_price_per_million_tokens=bad)


@pytest.mark.parametrize("bad", ["nan", "inf", "0", "-1"])
def test_bad_budget_rejected(bad):
    with pytest.raises(ValidationError):
        make(ai_monthly_budget_usd=bad)


def test_blank_price_means_unset():
    assert make(ai_price_per_million_tokens="  ").ai_price_per_million_tokens is None


def test_fake_provider_needs_no_price_even_for_unknown_or_pro_models():
    make()  # defaults
    make(ai_provider="fake", azure_openai_deployment="not-in-table")
    make(ai_provider="fake", azure_openai_deployment="gpt-5.4-pro")


def test_zero_or_negative_cap_is_refused_by_the_rule():
    for tokens in (0, -5, "x", float("inf")):
        with pytest.raises(ValueError):
            check_ai_budget("gpt-5-mini", None, tokens, 6.10)


def test_table_documents_pro_conservatively():
    assert aicost.MODEL_PRICES_PER_MILLION["gpt-5.4-pro"] >= 180


def run_cli(*args):
    done = subprocess.run([sys.executable, "-I", str(AICOST), "check", *args], capture_output=True, text=True, timeout=30)
    return done.returncode, done.stdout + done.stderr


def test_cli_matches_the_app_rule():
    assert run_cli("--deployment", "gpt-5-mini", "--tokens", "100000")[0] == 0
    code, out = run_cli("--deployment", "gpt-5.4-pro", "--tokens", "100000")
    assert code == 1 and "$540.00" in out
    code, out = run_cli("--deployment", "nope", "--tokens", "100")
    assert code == 1 and "price table" in out and "nope" not in out
    assert run_cli("--deployment", "nope", "--price", "1", "--tokens", "100")[0] == 0
    assert run_cli("--deployment", "gpt-5-mini", "--price", "nan", "--tokens", "100")[0] == 1
