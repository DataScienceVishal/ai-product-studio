"""Eval harness driver: phases E1-E4, T1-T3, R1, R2, every model call through LedgerBudget (DESIGN 8.1, 8.3, 8.5).

    python -m eval.run E1                # DRY RUN (default): ScriptedFakeAI, no spend, ledger.dry.jsonl
    python -m eval.run config            # prints the EVAL.md "Run configuration" facts (prompt hashes, caps)

There is no live path in S9. `--live` is refused until L1 (a reviewer PASS on this slice, the keys committed, Q-20 settled).
Item results are appended to eval/results/<phase>.jsonl; a re-run skips finished items (the T-56 resume rule).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

PRODUCT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCT / "app" / "backend"))

from .ledger import (DEFAULT_CONFIG, HERE, BudgetExceeded, Ledger, LedgerBudget, load_budget_config, preflight_scored)

KEYS_DIR = HERE / "keys"
RESULTS_DIR = HERE / "results"
DRY_LEDGER = HERE / "ledger.dry.jsonl"
LIVE_LEDGER = HERE / "ledger.jsonl"
DEMO_PACKS = 3


class PhaseNotReady(RuntimeError):
    """An input the phase needs does not exist yet (keys, packs, claim check). The message says which."""


@dataclass(frozen=True)
class Phase:
    name: str
    group: str
    what: str
    worst_usd: float          # DESIGN 8.3
    plan: str                 # builder name in PLANS


PHASES = {p.name: p for p in [
    Phase("E1", "scored", "A1-A3 extraction, 9 held-out packs", 0.62, "extract_heldout"),
    Phase("E2", "scored", "A4-A8 drafting and check, 3 held-out packs x 15 questions", 1.00, "draft_heldout"),
    Phase("E3", "scored", "A8 trap set, 30 questions, draft and check", 0.66, "draft_trap"),
    Phase("E4", "scored", "A6a checker alone on the 20 fixture drafts", 0.26, "check_fixtures"),
    Phase("T1", "tuning", "calibration: 1 demo pack end to end", 0.40, "end_to_end_1"),
    Phase("T2", "tuning", "tuning: 3 demo packs x 3 passes", 1.62, "tuning_demo"),
    Phase("T3", "tuning", "dev trap set x 3 passes", 0.66, "draft_dev_trap_x3"),
    Phase("R1", "recording", "recording: 3 demo packs end to end", 1.20, "end_to_end_3"),
    Phase("R2", "recording", "A9 stopwatch: 1 demo pack, cache cleared", 0.40, "end_to_end_1"),
]}


@dataclass
class Item:
    id: str
    kind: str                 # extract | draft | check
    data: dict


@dataclass
class Context:
    provider: object
    ledger: Ledger
    sessions: object
    tenant_id: object
    retrieve: Callable[[str], list] | None = None          # question -> list[Hit]
    claimcheck: Callable[..., list] | None = None          # (budget, draft_text, hits) -> [claim dicts]
    load_pack: Callable[[str], list[tuple[int, str]]] | None = None   # pack name -> [(page, text)]
    keys_dir: Path = KEYS_DIR
    results_dir: Path = RESULTS_DIR
    packs_dir: Path = PRODUCT / "demo-data" / "packs"
    dry: bool = True


# ---------- inputs ----------

def _need(path: Path, what: str) -> Path:
    if not path.is_file():
        raise PhaseNotReady(f"{what} not found at {path} (written by qa, task D3; Q-20 for the packs)")
    return path


def pack_names(ctx: Context) -> tuple[list[str], list[str]]:
    """(demo, held_out) pack names. manifest.json {"demo": [...], "heldout": [...]} wins; else the first 3 files are demo."""
    manifest = ctx.packs_dir / "manifest.json"
    if manifest.is_file():
        m = json.loads(manifest.read_text(encoding="utf-8"))
        return list(m.get("demo", [])), list(m.get("heldout", []))
    files = sorted(p.name for p in ctx.packs_dir.glob("*") if p.is_file() and p.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}) \
        if ctx.packs_dir.is_dir() else []
    if not files:
        raise PhaseNotReady(f"no tender pack files in {ctx.packs_dir} (Q-20 pending)")
    return files[:DEMO_PACKS], files[DEMO_PACKS:]


def _key_items(ctx: Context, pack: str) -> list[dict]:
    key = json.loads(_need(ctx.keys_dir / f"{Path(pack).stem}.json", f"answer key for {pack}").read_text(encoding="utf-8"))
    return key["items"]


def _json(ctx: Context, name: str, what: str):
    return json.loads(_need(ctx.keys_dir / name, what).read_text(encoding="utf-8"))


def _extract_items(ctx: Context, names: list[str], passes: int = 1) -> list[Item]:
    if not names:
        raise PhaseNotReady("no packs for this phase")
    return [Item(f"extract:{n}:p{i}", "extract", {"pack": n, "pass": i}) for i in range(passes) for n in names]


def _draft_items(questions: list[dict], passes: int = 1) -> list[Item]:
    return [Item(f"draft:{q['id']}:p{i}", "draft", q) for i in range(passes) for q in questions]


def build_plan(phase: str, ctx: Context) -> list[Item]:
    demo, held = pack_names(ctx)
    builder = PHASES[phase].plan
    if builder == "extract_heldout":
        return _extract_items(ctx, held)
    if builder == "draft_heldout":
        qs = []
        for n in held[:DEMO_PACKS]:   # the rule (first of each sector in SOURCES.md order) is applied by the manifest order
            qs += [{"id": f"{Path(n).stem}:{k['ref']}", "question": k["text"], "word_limit": k.get("word_limit")}
                   for k in [i for i in _key_items(ctx, n) if i.get("kind") == "question"][:15]]
        return _draft_items(qs)
    if builder == "draft_trap":
        return _draft_items(_json(ctx, "trap_set.json", "the 30-question trap set"))
    if builder == "draft_dev_trap_x3":
        return _draft_items(_json(ctx, "dev_trap_set.json", "the 10-question dev trap set"), passes=3)
    if builder == "check_fixtures":
        return [Item(f"check:{d['id']}", "check", d) for d in _json(ctx, "fixture_drafts.json", "the 20 fixture drafts")]
    if builder in ("end_to_end_1", "end_to_end_3", "tuning_demo"):
        names = demo[:1] if builder == "end_to_end_1" else demo[:DEMO_PACKS]
        return _extract_items(ctx, names, passes=3 if builder == "tuning_demo" else 1)
    raise PhaseNotReady(f"no plan for {phase}")


# ---------- execution ----------

def _extract(ctx: Context, phase: str, item: Item) -> dict:
    from app.tender import extract as ex
    from app.tender.llm import run_task
    if ctx.load_pack is None:
        raise PhaseNotReady("no pack loader")
    pages = ctx.load_pack(item.data["pack"])
    budget = LedgerBudget(ctx.ledger, phase, "extract", ex.EXTRACT_SPEC.max_output_tokens, label=item.id)
    found: list[dict] = []
    for chunk in ex.make_chunks(pages):
        res = run_task(ex.EXTRACT_SPEC, {"chunk": ex.chunk_text(chunk)}, ctx.tenant_id, budget, provider=ctx.provider,
                       sessions=ctx.sessions, allow_double_cap=True)
        found = ex.merge_items([i.model_dump() for i in res.output.items], found)
    return {"pack": item.data["pack"], "items": found}


def _draft(ctx: Context, phase: str, item: Item) -> dict:
    from app.tender import draft as dr
    if ctx.retrieve is None:
        raise PhaseNotReady("no retrieval (seed the demo tenant first: python -m eval.seed)")
    q = item.data
    hits = ctx.retrieve(q["question"])
    budget = LedgerBudget(ctx.ledger, phase, "draft", dr.DRAFT_SPEC.max_output_tokens, label=item.id)
    d = dr.draft_answer(q["question"], q.get("word_limit"), q.get("marks"), hits, ctx.tenant_id, budget,
                        provider=ctx.provider, sessions=ctx.sessions)
    out = {"id": q["id"], "text": d.text, "retrieved_ids": d.retrieved_ids, "cited_ids": d.cited_ids,
           "word_limit": q.get("word_limit"), "flags": d.flags}
    if ctx.claimcheck is not None:
        out["claims"] = _check(ctx, phase, q["id"], d.text, hits)
    return out


def _check(ctx: Context, phase: str, draft_id: str, text: str, hits: list) -> list[dict]:
    if ctx.claimcheck is None:
        raise PhaseNotReady("the claim check (T-190, app/tender/claimcheck) is not available: pass a claimcheck callable")
    budget = LedgerBudget(ctx.ledger, phase, "claimcheck", 6000, label=draft_id)
    return ctx.claimcheck(budget, text, hits)


def _run_item(ctx: Context, phase: str, item: Item) -> dict:
    if item.kind == "extract":
        return _extract(ctx, phase, item)
    if item.kind == "draft":
        return _draft(ctx, phase, item)
    return {"id": item.data["id"], "claims": _check(ctx, phase, item.data["id"], item.data["text"], [])}


def run_phase(phase: str, ctx: Context) -> dict:
    """Run a phase's plan. Finished items (in results/<phase>.jsonl) are skipped. A refused hold stops the phase cleanly."""
    if phase not in PHASES:
        raise PhaseNotReady(f"unknown phase {phase!r}; known: {', '.join(PHASES)}")
    if PHASES[phase].group == "scored":
        preflight_scored(ctx.ledger)
    plan = build_plan(phase, ctx)
    ctx.results_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.results_dir / f"{phase}.jsonl"
    done = {json.loads(l)["item"] for l in path.read_text(encoding="utf-8").splitlines() if l.strip()} if path.exists() else set()
    ran = skipped = 0
    stopped = None
    for item in plan:
        if item.id in done:
            skipped += 1
            continue
        try:
            result = _run_item(ctx, phase, item)
        except BudgetExceeded as e:
            stopped = str(e)
            break
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"item": item.id, "result": result}, sort_keys=True, default=str) + "\n")
        ran += 1
    return {"phase": phase, "planned": len(plan), "ran": ran, "skipped": skipped, "stopped": stopped, "dry_run": ctx.dry}


# ---------- run configuration (EVAL.md) ----------

def run_configuration() -> dict:
    from app.tender import draft as dr, extract as ex
    specs = [ex.EXTRACT_SPEC, dr.DRAFT_SPEC, dr.SHORTEN_SPEC]
    prompts = {f"{s.name}:{s.prompt_version}": {"sha256": hashlib.sha256(s.system.encode()).hexdigest(), "effort": s.effort,
                                               "output_cap": s.max_output_tokens} for s in specs}
    cfg = load_budget_config()
    return {"model": cfg.model, "approved_by": cfg.approved_by, "total_cap_usd": cfg.total_cap, "group_caps_usd": cfg.group_caps,
            "reasoning_headroom": cfg.headroom, "prompts": prompts, "claimcheck_prompt": "not built yet (T-190)"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="eval.run")
    ap.add_argument("phase", help="E1..E4, T1..T3, R1, R2, or 'config'")
    ap.add_argument("--live", action="store_true", help="refused in S9")
    args = ap.parse_args(argv)
    if args.live:
        print("eval.run: live runs are not enabled in S9 (no live model calls until L1).", file=sys.stderr)
        return 3
    if args.phase == "config":
        print(json.dumps(run_configuration(), indent=2))
        return 0
    from app.tender.scripted_ai import ScriptedFakeAI
    cfg = load_budget_config()
    ledger = Ledger(DRY_LEDGER, cfg, dry_run=True)
    from sqlalchemy import select
    from app.config import Settings
    from app.db import Database
    from app.models import Tenant
    from .seed import FIRM
    db = Database(Settings().database_url)       # a local database only: never the deployed app's
    sessions = db.sessions
    with sessions() as s:
        tenant_id = s.scalar(select(Tenant.id).where(Tenant.name == FIRM))
    if tenant_id is None:
        print("eval.run: demo tenant not found; run `python -m eval.seed` first", file=sys.stderr)
        return 4
    ctx = Context(ScriptedFakeAI(), ledger, sessions, tenant_id, dry=True)
    try:
        print(json.dumps(run_phase(args.phase, ctx), indent=2))
    except PhaseNotReady as e:
        print(f"eval.run: not ready: {e}", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
