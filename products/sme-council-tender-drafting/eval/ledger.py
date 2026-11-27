"""LedgerBudget: the eval harness's spend guard, a port of the T-80 `benchmark/budget.py` ledger (DESIGN 4.3, 8.5).

* Caps come from the committed `eval/budget.json`, which names the approving question. `load_budget_config` refuses a
  config whose question is not in `state/QUESTIONS.md` marked answered with the matching option.
* A JSONL ledger records every call (phase, task, tokens, model). Spend is recomputed from tokens at the configured
  price, so the stored `usd` is informational (as in T-80).
* Before each call the worst case (everything the hold estimates, priced as if as much of it as the output cap allows were
  output) must fit the phase group's sub-cap AND the total cap, or the call is refused with BudgetExceeded.
* A call that may have run but left nothing usable (failed with zero tokens reported) is charged its worst case.
* Reasoning headroom must be 0 so the cap sent is the cap in the table.
* It implements the `Budget` protocol of `app.tender.llm` (hold/settle) but imports nothing from `app`: it never calls
  `reserve()` and never writes `ai_usage`, so the harness is bound by this ledger and not by the app's tenant caps.
"""
from __future__ import annotations

import json
import math
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "budget.json"
DEFAULT_LEDGER = HERE / "ledger.jsonl"
DRY_MODEL = "fake"


class BudgetExceeded(RuntimeError):
    pass


class BudgetConfigError(ValueError):
    pass


class ModelMismatch(RuntimeError):
    """The provider reported a model other than the approved one: the run stops (DESIGN 8.5)."""


@dataclass(frozen=True)
class BudgetConfig:
    approved_by: str
    model: str
    price_in: float
    price_out: float
    total_cap: float
    group_caps: dict
    phase_group: dict
    scored_preflight_worst: float
    headroom: int

    def group_of(self, phase: str) -> str:
        if phase not in self.phase_group:
            raise BudgetConfigError(f"phase {phase!r} is not in any budget group")
        return self.phase_group[phase]


def find_questions_file(start: Path = HERE) -> Path | None:
    for parent in [start, *start.parents]:
        candidate = parent / "state" / "QUESTIONS.md"
        if candidate.is_file():
            return candidate
    return None


def question_answered(qid: str, answer: str, questions_text: str) -> bool:
    """True when `## Q-19 (status: answered A ...` exists. Only the header line of that question is read."""
    for line in questions_text.splitlines():
        m = re.match(rf"^##\s+{re.escape(qid)}\s*\(status:\s*answered\s+([A-Z])\b", line)
        if m:
            return m.group(1) == answer
    return False


def load_budget_config(path: Path | str = DEFAULT_CONFIG, questions_file: Path | str | None = None) -> BudgetConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    qid, answer = raw.get("approved_by"), raw.get("answer")
    if not qid or not answer:
        raise BudgetConfigError("budget.json must name the approving question (approved_by) and the answer")
    qf = Path(questions_file) if questions_file else find_questions_file()
    if qf is None or not qf.is_file():
        raise BudgetConfigError("state/QUESTIONS.md not found: cannot confirm the approving question exists")
    if not question_answered(qid, answer, qf.read_text(encoding="utf-8")):
        raise BudgetConfigError(f"{qid} is not recorded as answered {answer} in {qf.name}: no spend is allowed")
    model = raw["model"]
    price = raw["prices_usd_per_million"][model]
    total = float(raw["total_cap_usd"])
    if not math.isfinite(total) or total <= 0:
        raise BudgetConfigError("total_cap_usd must be finite and above 0")
    groups, phase_group = {}, {}
    for name, g in raw["groups"].items():
        groups[name] = float(g["cap_usd"])
        for phase in g["phases"]:
            if phase in phase_group:
                raise BudgetConfigError(f"phase {phase} is in two groups")
            phase_group[phase] = name
    if sum(groups.values()) > total + 1e-9:
        raise BudgetConfigError("group caps add up to more than the total cap")
    headroom = int(raw.get("reasoning_headroom", 0))
    if headroom != 0:
        raise BudgetConfigError("reasoning_headroom must be 0 in the harness (the worst case is the cap sent)")
    return BudgetConfig(qid, model, float(price["input"]), float(price["output"]), total, groups, phase_group,
                        float(raw["scored_preflight_worst_usd"]), headroom)


class Ledger:
    """Append-only JSONL, fsynced per row. Spend is recomputed from tokens, never read from the stored usd."""

    def __init__(self, path: Path | str, cfg: BudgetConfig, *, dry_run: bool = False):
        self.path, self.cfg, self.dry_run = Path(path), cfg, dry_run
        self._lock = threading.Lock()

    def usd(self, input_tokens: int, output_tokens: int, model: str) -> float:
        if model == DRY_MODEL and self.dry_run:
            return 0.0
        if model != self.cfg.model and not model.startswith(self.cfg.model + "-"):
            raise ModelMismatch(f"model {model!r} is not the approved {self.cfg.model!r}")
        return input_tokens * self.cfg.price_in / 1e6 + output_tokens * self.cfg.price_out / 1e6

    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def spent(self, group: str | None = None) -> float:
        total = 0.0
        for e in self.rows():
            if (group is None or self.cfg.phase_group.get(e["phase"]) == group) and e["model"] != DRY_MODEL:
                total += e["input_tokens"] * self.cfg.price_in / 1e6 + e["output_tokens"] * self.cfg.price_out / 1e6
        return total

    def append(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
                f.flush()
                os.fsync(f.fileno())


class LedgerBudget:
    """One per (phase, task). `output_cap` is the task's max_output_tokens; the double-cap truncation retry is allowed,
    so a single hold may be priced for up to twice that as output."""

    def __init__(self, ledger: Ledger, phase: str, task: str, output_cap: int, *, label: str = ""):
        self.ledger, self.cfg, self.phase, self.task, self.label = ledger, ledger.cfg, phase, task, label
        self.group = self.cfg.group_of(phase)
        self.output_cap = int(output_cap)
        self._n = 0
        self._holds: dict[int, float] = {}
        self._lock = threading.Lock()

    def worst_usd(self, estimate: int) -> float:
        """Upper bound for a call whose hold is `estimate` tokens (input estimate + output cap + headroom 0). The split is
        unknown here, so as much as the (doubled) output cap allows is priced as output and the rest as input: that
        never prices below the true worst case, because output costs more per token than input."""
        out = min(int(estimate), self.output_cap * 2)
        return (int(estimate) - out) * self.cfg.price_in / 1e6 + out * self.cfg.price_out / 1e6

    def check(self, worst: float) -> None:
        if self.ledger.dry_run:
            return
        group_spent, total_spent = self.ledger.spent(self.group), self.ledger.spent()
        if group_spent + worst > self.cfg.group_caps[self.group] + 1e-9:
            raise BudgetExceeded(f"{self.phase}/{self.task}: worst case ${worst:.4f} on ${group_spent:.4f} spent could pass "
                                 f"the {self.group} sub-cap ${self.cfg.group_caps[self.group]:.2f}; call refused")
        if total_spent + worst > self.cfg.total_cap + 1e-9:
            raise BudgetExceeded(f"{self.phase}/{self.task}: worst case ${worst:.4f} on ${total_spent:.4f} spent could pass "
                                 f"the total cap ${self.cfg.total_cap:.2f}; call refused")

    def hold(self, estimate: int) -> int:
        worst = self.worst_usd(estimate)
        with self._lock:
            self.check(worst)
            self._n += 1
            self._holds[self._n] = worst
            return self._n

    def settle(self, handle: int, input_tokens: int, output_tokens: int, model: str, failed: bool = False) -> None:
        with self._lock:
            worst = self._holds.pop(handle, 0.0)
        charged_worst = failed and input_tokens + output_tokens == 0 and not self.ledger.dry_run
        if charged_worst:
            # The request may have run and billed: charge the worst case, as 'output tokens at the output price'.
            model = self.cfg.model
            input_tokens, output_tokens = 0, round(worst * 1e6 / self.cfg.price_out)
        entry = {"phase": self.phase, "task": self.task, "label": self.label, "model": model,
                 "input_tokens": int(input_tokens), "output_tokens": int(output_tokens), "failed": bool(failed),
                 "charged_worst": charged_worst}
        approved = model == self.cfg.model or model.startswith(self.cfg.model + "-")
        dry = model == DRY_MODEL and self.ledger.dry_run
        # An unapproved or unknown model is still priced (at the approved model's price) so the spend is never hidden.
        entry["usd"] = 0.0 if dry else round(
            input_tokens * self.cfg.price_in / 1e6 + output_tokens * self.cfg.price_out / 1e6, 6)
        self.ledger.append(entry)
        if model != "unknown" and not approved and not dry:
            raise ModelMismatch(f"provider reported model {model!r}; only {self.cfg.model!r} is approved: run stopped")


def preflight_scored(ledger: Ledger) -> None:
    """DESIGN 8.5: before E1 the remaining scored reserve must cover the scored worst case."""
    if ledger.dry_run:
        return
    cfg = ledger.cfg
    remaining = cfg.group_caps["scored"] - ledger.spent("scored")
    if remaining < cfg.scored_preflight_worst:
        raise BudgetExceeded(f"scored reserve ${remaining:.2f} is below the scored worst case ${cfg.scored_preflight_worst:.2f}")
