"""Hard spend guard. Cumulative across invocations (persisted), thread-safe, worst-case reservation."""
import json, threading
from pathlib import Path

PRICE_IN, PRICE_OUT = 15.0, 120.0     # USD per million tokens (assumed; reasoning counts as output)


class BudgetRefused(Exception):
    pass


class Budget:
    def __init__(self, path, cap_usd=11.50, max_calls=15):
        self.path, self.cap, self.max_calls = Path(path), cap_usd, max_calls
        self.lock = threading.Lock()
        self.inflight_usd = 0.0; self.inflight_calls = 0
        s = json.loads(self.path.read_text()) if self.path.exists() else {}
        self.calls = s.get("calls", 0); self.usd = s.get("usd", 0.0)
        self.input_tokens = s.get("input_tokens", 0); self.output_tokens = s.get("output_tokens", 0)
        self.log = s.get("log", [])

    @staticmethod
    def cost(inp, out):
        return inp * PRICE_IN / 1e6 + out * PRICE_OUT / 1e6

    def reserve(self, est_input_tokens, max_output_tokens):
        worst = self.cost(est_input_tokens, max_output_tokens)
        with self.lock:
            if self.calls + self.inflight_calls + 1 > self.max_calls:
                raise BudgetRefused(f"call cap {self.max_calls} reached")
            if self.usd + self.inflight_usd + worst > self.cap + 1e-9:
                raise BudgetRefused(f"worst case ${worst:.2f} would cross cap ${self.cap:.2f} (spent ${self.usd:.2f}, in flight ${self.inflight_usd:.2f})")
            self.inflight_usd += worst; self.inflight_calls += 1
        return worst

    def settle(self, worst, label, usage=None, charge_worst=False, note=""):
        """usage: dict with input_tokens/output_tokens. charge_worst: unknown outcome (timeout): bill the worst case."""
        with self.lock:
            self.inflight_usd -= worst; self.inflight_calls -= 1
            i = (usage or {}).get("input_tokens") or 0; o = (usage or {}).get("output_tokens") or 0
            c = worst if charge_worst else self.cost(i, o)
            self.calls += 1; self.usd = round(self.usd + c, 6)
            self.input_tokens += i; self.output_tokens += o
            self.log.append({"label": label, "input_tokens": i, "output_tokens": o, "usd": round(c, 4), "note": note})
            self.path.write_text(json.dumps(self.state(), indent=1))

    def state(self):
        return {"cap_usd": self.cap, "max_calls": self.max_calls, "price_per_m_input": PRICE_IN, "price_per_m_output": PRICE_OUT,
                "calls": self.calls, "usd": round(self.usd, 4), "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "log": self.log}
