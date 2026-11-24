"""Spend and token guard (kill-test amendment: hard USD 12, 3M tokens for the whole proof test, tuning included).

Before each call: worst case = input estimate + max_output_tokens (reasoning counts inside it) at the assumed price.
The call is refused if it could take the total past either cap. After each call the billed tokens and USD are appended
to a JSONL ledger; a failed call that may have run is charged its worst case. The ledger is the source of truth and is
read on start-up, so tuning and test runs share one budget when they share a ledger file."""
import json
import os
from pathlib import Path

USD_PER_M_IN = 15.0
USD_PER_M_OUT = 120.0
MAX_USD = 12.0
MAX_TOKENS = 3_000_000


class BudgetExceeded(RuntimeError):
    pass


def usd(input_tokens, output_tokens):
    return input_tokens * USD_PER_M_IN / 1e6 + output_tokens * USD_PER_M_OUT / 1e6


class Budget:
    def __init__(self, ledger, max_usd=MAX_USD, max_tokens=MAX_TOKENS):
        self.ledger = Path(ledger)
        self.max_usd, self.max_tokens = max_usd, max_tokens
        self.spent_usd, self.tokens = 0.0, 0
        if self.ledger.exists():
            for line in self.ledger.read_text().splitlines():
                if line.strip():
                    e = json.loads(line)
                    self.spent_usd += float(e["usd"])
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
                 "usd": round(usd(input_tokens, output_tokens), 6), "model": model, "estimated": estimated,
                 "note": note}
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())
        self.spent_usd += entry["usd"]
        self.tokens += entry["input_tokens"] + entry["output_tokens"]
        return entry
