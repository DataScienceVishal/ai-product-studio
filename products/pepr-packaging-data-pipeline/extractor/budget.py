"""Spend and token guard (kill-test amendment: hard USD 12, 3M tokens for the whole proof test, tuning included).

Price: gpt-5.4-pro is USD 30 per 1M input and USD 180 per 1M output tokens (reasoning counts as output), per OpenAI's model
page and Microsoft's Foundry launch post (corrected 2026-11-24, T-58; the earlier 15/120 was an assumption). The two
constants below are the only place the price lives; benchmark/score.py imports them.
Before each call: worst case = input estimate + max_output_tokens (reasoning counts inside it) at that price.
The call is refused if it could take the total past either cap. After each call the billed tokens and USD are appended
to a JSONL ledger; a failed call that may have run is charged its worst case. The ledger is the source of truth and is
read on start-up; spend is recomputed from each row's billed tokens at the current price (the stored `usd` of old rows
used the old price and is ignored), so tuning and test runs share one budget when they share a ledger file."""
import json
import os
from pathlib import Path

USD_PER_M_IN = 30.0
USD_PER_M_OUT = 180.0
MAX_USD = 12.0
MAX_TOKENS = 3_000_000


PER_SHEET_USD = 0.316  # pass mark 5 (GBP 0.25)
PER_SHEET_TOKENS = 20_000  # typical input + output per sheet, token analogue of the per-sheet allowance
WORST_INPUT_TOKENS = 20_000  # worst-case input estimate for one sheet (2 images + text), used for the pre-flight


def preflight(budget, n_sheets, max_output_tokens):
    """Refuse a one-shot run that the guard would cut short: remaining budget must cover n_sheets at the per-sheet bar
    plus one call's worst-case reservation, in USD and in tokens. Raises BudgetExceeded with the shortfall."""
    need_usd = n_sheets * PER_SHEET_USD + usd(WORST_INPUT_TOKENS, max_output_tokens)
    need_tok = n_sheets * PER_SHEET_TOKENS + WORST_INPUT_TOKENS + max_output_tokens
    left_usd, left_tok = budget.max_usd - budget.spent_usd, budget.max_tokens - budget.tokens
    if left_usd < need_usd:
        raise BudgetExceeded(f"pre-flight: USD {left_usd:.2f} left, need {need_usd:.2f} (short by {need_usd - left_usd:.2f})")
    if left_tok < need_tok:
        raise BudgetExceeded(f"pre-flight: {left_tok} tokens left, need {need_tok} (short by {need_tok - left_tok})")


class BudgetExceeded(RuntimeError):
    pass


def usd(input_tokens, output_tokens):
    return input_tokens * USD_PER_M_IN / 1e6 + output_tokens * USD_PER_M_OUT / 1e6


def entry_usd(entry):
    """USD of one ledger row, recomputed from its billed tokens at the current price constants."""
    return usd(int(entry["input_tokens"]), int(entry["output_tokens"]))


class Budget:
    def __init__(self, ledger, max_usd=MAX_USD, max_tokens=MAX_TOKENS):
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
        worst_usd = usd(est_input_tokens, max_output_tokens)
        worst_tokens = est_input_tokens + max_output_tokens
        if self.spent_usd + worst_usd > self.max_usd:
            raise BudgetExceeded(f"{label}: worst case USD {worst_usd:.3f} on top of USD {self.spent_usd:.3f} spent "
                                 f"could pass the USD {self.max_usd:.2f} cap; call refused")
        if self.tokens + worst_tokens > self.max_tokens:
            raise BudgetExceeded(f"{label}: worst case {worst_tokens} tokens on top of {self.tokens} used could pass "
                                 f"the {self.max_tokens} token cap; call refused")

    def record(self, sheet_id, input_tokens, output_tokens, model="", estimated=False, note=""):
        entry = {"sheet_id": sheet_id, "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
                 "usd": round(usd(input_tokens, output_tokens), 6),
                 "price_in": USD_PER_M_IN, "price_out": USD_PER_M_OUT, "model": model, "estimated": estimated,
                 "note": note}
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.spent_usd += entry["usd"]
        self.tokens += entry["input_tokens"] + entry["output_tokens"]
        return entry
