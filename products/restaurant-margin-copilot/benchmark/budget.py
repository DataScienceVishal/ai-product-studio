"""Spend guard for the T-80 proof test: a JSONL ledger and a hard USD cap (adapted from T-56's extractor/budget.py).

KILL-TEST.md: the cap is USD 5 in total for dev, test and retries, enforced by a ledger. Before every call the worst case
(estimated input tokens + the call's max_output_tokens, because reasoning tokens count inside it) is added to the spend so
far; if that could pass the cap the call is refused. After each call the billed tokens are appended to the ledger. A call
that may have run but left no usable answer (timeout, unreadable 200) is charged its worst case. Spend is recomputed from
each row's tokens at the current price, so the stored `usd` is informational. Runs share one ledger file; no file lock, so run
dev and test one after the other.
"""
from __future__ import annotations

import json
import math
import os
import threading
from pathlib import Path

# model name -> (USD per 1M input tokens, USD per 1M output tokens including reasoning tokens).
# gpt-5-mini 0.25 / 2.00: OpenAI model page, as used by T-56 (Q-12 A) and quoted in KILL-TEST.md. These are list-price
# assumptions, not read from the Azure bill; the studio's own cost guard (state/BUDGET.md) is the second check.
PRICES = {"gpt-5-mini": (0.25, 2.00)}
MAX_USD = 5.0


class BudgetExceeded(RuntimeError):
    pass


class UnknownModel(ValueError):
    pass


def price_for(model: str) -> tuple[float, float]:
    if model not in PRICES:
        raise UnknownModel(f"no price for model {model!r}; known: {sorted(PRICES)}")
    return PRICES[model]


def usd(input_tokens: int, output_tokens: int, model: str) -> float:
    p_in, p_out = price_for(model)
    return input_tokens * p_in / 1e6 + output_tokens * p_out / 1e6


class Budget:
    def __init__(self, ledger, model: str = "gpt-5-mini", max_usd: float = MAX_USD):
        price_for(model)
        max_usd = float(max_usd)
        if not math.isfinite(max_usd) or not 0 < max_usd <= MAX_USD:
            raise ValueError(f"max_usd must be finite and in (0, {MAX_USD}]")
        self.model, self.max_usd = model, max_usd
        self.ledger = Path(ledger)
        self.spent_usd = 0.0
        self._lock = threading.Lock()
        if self.ledger.exists():
            for line in self.ledger.read_text().splitlines():
                if line.strip():
                    e = json.loads(line)
                    self.spent_usd += usd(int(e["input_tokens"]), int(e["output_tokens"]), e["model"])

    def check(self, est_input_tokens: int, max_output_tokens: int, label: str = "") -> float:
        """Raise BudgetExceeded unless this call's worst case still fits under the cap. Returns the worst case in USD."""
        worst = usd(est_input_tokens, max_output_tokens, self.model)
        with self._lock:
            spent = self.spent_usd
        if spent + worst > self.max_usd:
            raise BudgetExceeded(f"{label}: worst case USD {worst:.4f} on top of USD {self.spent_usd:.4f} spent could pass "
                                 f"the USD {self.max_usd:.2f} cap; call refused")
        return worst

    def record(self, label: str, input_tokens: int, output_tokens: int, estimated: bool = False, note: str = "") -> dict:
        p_in, p_out = price_for(self.model)
        entry = {"label": label, "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
                 "usd": round(usd(input_tokens, output_tokens, self.model), 6), "price_in": p_in, "price_out": p_out,
                 "model": self.model, "estimated": estimated, "note": note}
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(self.ledger, "a") as f:
                f.write(json.dumps(entry) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self.spent_usd += entry["usd"]
        return entry
