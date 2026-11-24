"""Spend and token guard (kill-test amendment: hard USD 12, 3M tokens for the whole proof test, tuning included).

Price follows the model. PRICES below is the only place a price lives; benchmark/score.py uses entry_usd. Reasoning
tokens count as output. Every ledger row is priced at the price of its OWN `model` field (rows of two models can share one
ledger and one cap); a row whose model is missing or not in the table raises UnknownModel, it is never priced at zero.
Before each call: worst case = input estimate + max_output_tokens (reasoning counts inside it) at the price of the model
being called (Budget.model).
The call is refused if it could take the total past either cap. After each call the billed tokens and USD are appended
to a JSONL ledger; a failed call that may have run is charged its worst case. The ledger is the source of truth and is
read on start-up; spend is recomputed from each row's billed tokens at the current price (the stored `usd` of old rows
used the old price and is ignored), so tuning and test runs share one budget when they share a ledger file."""
import json
import os
from pathlib import Path

# model name -> (USD per 1M input tokens, USD per 1M output tokens incl. reasoning)
PRICES = {
    # OpenAI model page https://developers.openai.com/api/docs/models/gpt-5.4-pro and Microsoft's Foundry launch post
    # (corrected 2026-11-24, T-58; the earlier 15/120 was an assumption)
    "gpt-5.4-pro": (30.0, 180.0),
    # OpenAI model page https://developers.openai.com/api/docs/models/gpt-5-mini (Q-12 A, Amendment 6)
    "gpt-5-mini": (0.25, 2.00),
}
# Azure deployment name -> price-table model name. Deployments here are named after their model; a name not listed is
# refused (no silent zero price).
DEPLOYMENT_MODELS = {name: name for name in PRICES}
MAX_USD = 12.0
MAX_TOKENS = 3_000_000


PER_SHEET_USD = 0.316  # pass mark 5 (GBP 0.25)
PER_SHEET_TOKENS = 20_000  # typical input + output per sheet, token analogue of the per-sheet allowance
WORST_INPUT_TOKENS = 20_000  # worst-case input estimate for one sheet (2 images + text), used for the pre-flight


def preflight(budget, n_sheets, max_output_tokens):
    """Refuse a one-shot run that the guard would cut short: remaining budget must cover n_sheets at the per-sheet bar
    plus one call's worst-case reservation, in USD and in tokens. Raises BudgetExceeded with the shortfall."""
    # per-sheet reservation: the pass-mark allowance, or less when a whole worst-case call at this model's price is cheaper
    # (gpt-5-mini: about USD 0.017 a call). The guard still checks every call's worst case against both caps.
    one_call = usd(WORST_INPUT_TOKENS, max_output_tokens, budget.model)
    need_usd = n_sheets * min(PER_SHEET_USD, one_call) + one_call
    need_tok = n_sheets * PER_SHEET_TOKENS + WORST_INPUT_TOKENS + max_output_tokens
    left_usd, left_tok = budget.max_usd - budget.spent_usd, budget.max_tokens - budget.tokens
    if left_usd < need_usd:
        raise BudgetExceeded(f"pre-flight: USD {left_usd:.2f} left, need {need_usd:.2f} (short by {need_usd - left_usd:.2f})")
    if left_tok < need_tok:
        raise BudgetExceeded(f"pre-flight: {left_tok} tokens left, need {need_tok} (short by {need_tok - left_tok})")


class BudgetExceeded(RuntimeError):
    pass


class UnknownModel(ValueError):
    pass


def price_for(model):
    """(USD/1M in, USD/1M out) for a price-table model name; raises UnknownModel for an empty or unknown name."""
    if model not in PRICES:
        raise UnknownModel(f"no price for model {model!r}; known: {sorted(PRICES)}")
    return PRICES[model]


def price_model_for_deployment(deployment):
    """Price-table model of an Azure deployment name; raises UnknownModel if the deployment is not in the table."""
    if deployment not in DEPLOYMENT_MODELS:
        raise UnknownModel(f"deployment {deployment!r} has no price; known: {sorted(DEPLOYMENT_MODELS)}")
    return DEPLOYMENT_MODELS[deployment]


def usd(input_tokens, output_tokens, model):
    p_in, p_out = price_for(model)
    return input_tokens * p_in / 1e6 + output_tokens * p_out / 1e6


def entry_usd(entry):
    """USD of one ledger row, recomputed from its billed tokens at the price of the row's own `model` field."""
    return usd(int(entry["input_tokens"]), int(entry["output_tokens"]), entry.get("model"))


class Budget:
    def __init__(self, ledger, model=None, deployment=None, max_usd=MAX_USD, max_tokens=MAX_TOKENS):
        """`model`: price-table name of the model being called (check/record/preflight need it; reading old rows does not)."""
        if model is not None:
            price_for(model)
        self.model, self.deployment = model, deployment
        self.ledger = Path(ledger)
        self.max_usd, self.max_tokens = max_usd, max_tokens
        self.spent_usd, self.tokens = 0.0, 0
        if self.ledger.exists():
            for line in self.ledger.read_text().splitlines():
                if line.strip():
                    e = json.loads(line)
                    self.spent_usd += entry_usd(e)
                    self.tokens += int(e["input_tokens"]) + int(e["output_tokens"])

    def check(self, est_input_tokens, max_output_tokens, label=""):
        """Raise BudgetExceeded unless the worst case of this call still fits under both caps."""
        worst_usd = usd(est_input_tokens, max_output_tokens, self.model)
        worst_tokens = est_input_tokens + max_output_tokens
        if self.spent_usd + worst_usd > self.max_usd:
            raise BudgetExceeded(f"{label}: worst case USD {worst_usd:.3f} on top of USD {self.spent_usd:.3f} spent "
                                 f"could pass the USD {self.max_usd:.2f} cap; call refused")
        if self.tokens + worst_tokens > self.max_tokens:
            raise BudgetExceeded(f"{label}: worst case {worst_tokens} tokens on top of {self.tokens} used could pass "
                                 f"the {self.max_tokens} token cap; call refused")

    def record(self, sheet_id, input_tokens, output_tokens, model=None, estimated=False, note="", served_model=""):
        """`model` defaults to the budget's own; it must be a price-table name. `served_model` is what the API reported."""
        model = model or self.model
        p_in, p_out = price_for(model)
        entry = {"sheet_id": sheet_id, "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
                 "usd": round(usd(input_tokens, output_tokens, model), 6),
                 "price_in": p_in, "price_out": p_out, "model": model, "deployment": self.deployment or model,
                 "served_model": served_model, "estimated": estimated, "note": note}
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.spent_usd += entry["usd"]
        self.tokens += entry["input_tokens"] + entry["output_tokens"]
        return entry
