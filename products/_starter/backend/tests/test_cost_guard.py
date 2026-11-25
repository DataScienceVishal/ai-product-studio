"""Harness for infra/cost-guard.sh: hand-made templates shaped like `az bicep build` output (no bicep CLI needed)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "infra" / "cost-guard.sh"
pytestmark = pytest.mark.skipif(shutil.which("jq") is None or shutil.which("bash") is None, reason="needs jq and bash")


def run(tmp_path, parameters, extra=None, budget=None, name="t.json", env_extra=None):
    template = {"parameters": parameters, **(extra or {})}
    path = tmp_path / name
    path.write_text(json.dumps(template))
    env = {"PATH": __import__("os").environ["PATH"], **({"AI_MONTHLY_BUDGET_USD": budget} if budget else {}), **(env_extra or {})}
    done = subprocess.run(["bash", str(SCRIPT), str(path)], capture_output=True, text=True, env=env, timeout=30)
    return done.returncode, done.stdout + done.stderr


def ai(tokens, price):
    return {"aiGlobalDailyTokens": {"type": "int", "defaultValue": tokens},
            "aiPricePerMillionTokens": {"type": "string", "defaultValue": price}}


def test_shipped_defaults_pass(tmp_path):
    assert run(tmp_path, ai(100000, "2.00"))[0] == 0


def test_no_ai_parameters_pass(tmp_path):
    assert run(tmp_path, {})[0] == 0


@pytest.mark.parametrize("tokens, price, budget, code", [
    (100000, "2.00", None, 0), (100001, "2.00", None, 1), (100000, "120", None, 1), (1666, "120", None, 0),
    (1667, "120", None, 1), (100000, "2.00", "1", 1), (100000, "2.00", "20", 0),
])
def test_budget_boundary(tmp_path, tokens, price, budget, code):
    assert run(tmp_path, ai(tokens, price), budget=budget)[0] == code


def test_over_budget_message_shows_two_decimals(tmp_path):
    code, out = run(tmp_path, ai(100000, "120"))
    assert code == 1 and "$372.00 a month" in out and "$6.20 AI budget" in out


@pytest.mark.parametrize("tokens, price, words", [
    (100000, "abc", "not a number"), ("=expr", "2.00", "not a number"), (100000, "-5", "above 0"),
    (100000, "0", "above 0"), (0, "2.00", "above 0"),
])
def test_bad_values_fail_closed(tmp_path, tokens, price, words):
    code, out = run(tmp_path, ai(tokens, price))
    assert code == 1 and words in out


def test_cap_without_default_fails_and_price_is_optional(tmp_path):
    # the price may be empty now (the table decides, T-91); the cap must still have a default to be checked
    assert run(tmp_path, {"aiGlobalDailyTokens": {"type": "int", "defaultValue": 5}})[0] == 0
    assert run(tmp_path, {"aiGlobalDailyTokens": {"type": "int", "defaultValue": 5}}, env_extra={"AI_PROVIDER": "azure"})[0] == 1  # unknown deployment ''
    assert run(tmp_path, {"aiGlobalDailyTokens": {"type": "int"}, "aiPricePerMillionTokens": {"type": "string"}})[0] == 1


@pytest.mark.parametrize("budget", ["abc", "0", "-3"])
def test_bad_budget_variable_fails_closed_and_names_itself(tmp_path, budget):
    code, out = run(tmp_path, ai(100000, "2.00"), budget=budget)
    assert code == 2 and "AI_MONTHLY_BUDGET_USD" in out


@pytest.mark.parametrize("extra", [
    {"resources": [{"properties": {"workloadProfileType": "D4"}}]},
    {"resources": [{"properties": {"vnetConfiguration": {}}}]},
    {"resources": [{"type": "Microsoft.Network/privateEndpoints"}]},
])
def test_fixed_charge_features_are_refused(tmp_path, extra):
    assert run(tmp_path, {}, extra)[0] == 1


def test_consumption_profile_passes(tmp_path):
    assert run(tmp_path, {}, {"resources": [{"properties": {"workloadProfileType": "Consumption"}}]})[0] == 0


# T-91: the price comes from the deployed model, not a fixed number.
def table_ai(tokens=100000, price="", deployment="gpt-5-mini"):
    p = ai(tokens, price)
    p["azureOpenAiDeployment"] = {"type": "string", "defaultValue": deployment}
    return p


AZURE = {"AI_PROVIDER": "azure"}


def test_pro_deployment_from_env_fails_at_default_cap_without_printing_it(tmp_path):
    code, out = run(tmp_path, table_ai(), env_extra={**AZURE, "AZURE_OPENAI_DEPLOYMENT": "gpt-5.4-pro"})
    assert code == 1 and "$558.00 a month" in out and "gpt-5.4-pro" not in out


def test_known_cheap_deployment_passes(tmp_path):
    assert run(tmp_path, table_ai(), env_extra={**AZURE, "AZURE_OPENAI_DEPLOYMENT": "gpt-5-mini"})[0] == 0


def test_unknown_deployment_without_price_fails_with_azure(tmp_path):
    code, out = run(tmp_path, table_ai(), env_extra={**AZURE, "AZURE_OPENAI_DEPLOYMENT": "mystery-name"})
    assert code == 1 and "AI_PRICE_PER_MILLION_TOKENS" in out and "mystery-name" not in out


def test_unknown_deployment_with_explicit_env_price_passes(tmp_path):
    env = {**AZURE, "AZURE_OPENAI_DEPLOYMENT": "mystery-name", "AI_PRICE_PER_MILLION_TOKENS": "2.00"}
    assert run(tmp_path, table_ai(), env_extra=env)[0] == 0


def test_explicit_env_price_can_only_raise_a_table_price(tmp_path):
    over = {**AZURE, "AZURE_OPENAI_DEPLOYMENT": "gpt-5-mini", "AI_PRICE_PER_MILLION_TOKENS": "180"}
    assert run(tmp_path, table_ai(), env_extra=over)[0] == 1
    low = {**AZURE, "AZURE_OPENAI_DEPLOYMENT": "gpt-5.4-pro", "AI_PRICE_PER_MILLION_TOKENS": "0.0001"}
    assert run(tmp_path, table_ai(), env_extra=low)[0] == 1  # the bypass the review found
    assert run(tmp_path, table_ai(price="0.0001"), env_extra={**AZURE, "AZURE_OPENAI_DEPLOYMENT": "gpt-5.4-pro"})[0] == 1


def test_dash_deployment_name_is_a_value_and_nothing_leaks(tmp_path):
    code, out = run(tmp_path, table_ai(), env_extra={**AZURE, "AZURE_OPENAI_DEPLOYMENT": "--secret-name",
                                                      "AZURE_OPENAI_API_KEY": "SUPERSECRETKEY123"})
    assert code == 1 and "price table" in out and "usage:" not in out
    assert "secret-name" not in out and "SUPERSECRETKEY123" not in out


@pytest.mark.parametrize("price", ["nan", "inf", "0", "-3", "abc"])
def test_bad_env_price_rejected(tmp_path, price):
    assert run(tmp_path, table_ai(), env_extra={**AZURE, "AI_PRICE_PER_MILLION_TOKENS": price})[0] == 1


def test_fake_provider_needs_no_price(tmp_path):
    assert run(tmp_path, table_ai(deployment="mystery-name"), env_extra={"AI_PROVIDER": "fake", "AZURE_OPENAI_DEPLOYMENT": "mystery-name"})[0] == 0
    assert run(tmp_path, table_ai(), env_extra={"AZURE_OPENAI_DEPLOYMENT": "gpt-5.4-pro"})[0] == 0


def test_azure_falls_back_to_the_template_deployment_default(tmp_path):
    assert run(tmp_path, table_ai(deployment="gpt-5.4-pro"), env_extra=AZURE)[0] == 1
    assert run(tmp_path, table_ai(deployment="gpt-5-mini"), env_extra=AZURE)[0] == 0
