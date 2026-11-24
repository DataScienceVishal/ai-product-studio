"""Harness for infra/cost-guard.sh: hand-made templates shaped like `az bicep build` output (no bicep CLI needed)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "infra" / "cost-guard.sh"
pytestmark = pytest.mark.skipif(shutil.which("jq") is None or shutil.which("bash") is None, reason="needs jq and bash")


def run(tmp_path, parameters, extra=None, budget=None, name="t.json"):
    template = {"parameters": parameters, **(extra or {})}
    path = tmp_path / name
    path.write_text(json.dumps(template))
    env = {"PATH": __import__("os").environ["PATH"], **({"AI_MONTHLY_BUDGET_USD": budget} if budget else {})}
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
    (101666, "2.00", None, 0), (101667, "2.00", None, 1), (100000, "120", None, 1), (1690, "120", None, 0),
    (1700, "120", None, 1), (100000, "2.00", "1", 1), (100000, "2.00", "20", 0),
])
def test_budget_boundary(tmp_path, tokens, price, budget, code):
    assert run(tmp_path, ai(tokens, price), budget=budget)[0] == code


def test_over_budget_message_shows_two_decimals(tmp_path):
    code, out = run(tmp_path, ai(100000, "120"))
    assert code == 1 and "$360.00 a month" in out and "$6.10 AI budget" in out


@pytest.mark.parametrize("tokens, price, words", [
    (100000, "abc", "not a number"), ("=expr", "2.00", "not a number"), (100000, "-5", "above 0"),
    (100000, "0", "above 0"), (0, "2.00", "above 0"),
])
def test_bad_values_fail_closed(tmp_path, tokens, price, words):
    code, out = run(tmp_path, ai(tokens, price))
    assert code == 1 and words in out


def test_one_parameter_or_no_default_fails(tmp_path):
    assert run(tmp_path, {"aiGlobalDailyTokens": {"type": "int", "defaultValue": 5}})[0] == 1
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
