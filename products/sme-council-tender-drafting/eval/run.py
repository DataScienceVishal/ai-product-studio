"""Eval harness driver: phases E1-E4, T1-T3, R1, R2, every model call through LedgerBudget (DESIGN 8.1, 8.3, 8.5).

    python -m eval.run E1                # DRY RUN (default): ScriptedFakeAI, no spend, ledger.dry.jsonl
    python -m eval.run config            # prints the EVAL.md "Run configuration" facts (prompt hashes, caps)

    python -m eval.run T1 --live         # LIVE, tuning phases T1-T3 only (T-219): real Azure OpenAI client, eval/ledger.jsonl
`--live` is refused for E1-E4, R1, R2 (and config/retrieval) until the L1 configuration freeze (EVAL.md TBD rows filled and
committed). Live needs AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT_MINI in the environment.
Item results are appended to eval/results/<phase>.jsonl; a re-run skips finished items (the T-56 resume rule).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

PRODUCT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCT / "app" / "backend"))

from .ledger import (DEFAULT_CONFIG, HERE, BudgetExceeded, Ledger, LedgerBudget, ModelMismatch, load_budget_config,
                     preflight_scored)

KEYS_DIR = HERE / "keys"
RESULTS_DIR = HERE / "results"          # live results are committed after every phase (DESIGN 8.5); results/dry/ is ignored
DRY_RESULTS_DIR = RESULTS_DIR / "dry"
DRY_LEDGER = HERE / "ledger.dry.jsonl"
LIVE_LEDGER = HERE / "ledger.jsonl"
DEMO_PACKS = 3
LIVE_PHASES = frozenset({"T1", "T2", "T3"})       # the only phases that may call the model (T-219); E and R wait for L1
LIVE_ENV = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT_MINI")
LIVE_RETRIES = 2                                  # per call; backoff is the client's own (_pause). A 5xx is not billed; a post-send drop is charged worst case
LIVE_TIMEOUT_SECONDS = 180.0                      # as the app's worker provider
CACHE_CLEAR_PHASES = {"T2", "T3", "R2"}          # repeat passes and the A9 stopwatch must not be answered from ai_cache


RESEED_NOTE = ("the demo tenant's ai_cache was cleared (it held the recorded demo cache): re-run `python -m eval.seed` "
               "before any demo")


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
    claimcheck: Callable[..., list] | None = None          # (budget, draft_text, hits[, retrieved_ids]) -> [claim dicts]; None = the real one
    load_pack: Callable[[str], list[tuple[int, str]]] | None = None   # pack name -> [(page, text)]
    keys_dir: Path = KEYS_DIR
    results_dir: Path = RESULTS_DIR
    packs_dir: Path = PRODUCT / "demo-data" / "packs"
    dry: bool = True

    def __post_init__(self):
        if self.claimcheck is None or getattr(self.claimcheck, "is_default_claimcheck", False):
            # also rebuilt for a copy (dataclasses.replace): a default closure must never keep the old context's provider/tenant
            self.claimcheck = default_claimcheck(self)
        headroom = getattr(self.provider, "output_headroom", None)
        if headroom != self.ledger.cfg.headroom:
            raise PhaseNotReady(f"provider output_headroom is {headroom!r}, the ledger assumes {self.ledger.cfg.headroom}: "
                                f"worst-case pricing would under-reserve")


# ---------- inputs ----------

def _need(path: Path, what: str) -> Path:
    if not path.is_file():
        raise PhaseNotReady(f"{what} not found at {path} (written by qa, task D3; Q-20 for the packs)")
    return path


def drafting_heldout(ctx: Context) -> list[str]:
    """The 3 held-out packs used for drafting, named in manifest.json as "drafting_heldout" (each must be in "heldout")."""
    manifest = ctx.packs_dir / "manifest.json"
    if not manifest.is_file():
        raise PhaseNotReady(f"{manifest} is required: it must name the 3 \"drafting_heldout\" packs")
    m = json.loads(manifest.read_text(encoding="utf-8"))
    names = list(m.get("drafting_heldout") or [])
    if len(names) != DEMO_PACKS or len(set(names)) != DEMO_PACKS or not set(names) <= set(m.get("heldout", [])):
        raise PhaseNotReady(f"manifest.json drafting_heldout must list exactly {DEMO_PACKS} distinct packs from heldout")
    return names


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


DEMO_QUESTIONS_PER_PACK = 5      # T-221: draft + claim-check items per demo pack and pass (DESIGN 8.3 "extraction plus 5 questions")
TUNING_QUESTIONS_PER_PACK = 3    # tuning_demo (T2) only: 3 packs x 3 passes x 3 questions keeps T2's worst case ($1.62) under the $2.00 tuning cap
DEMO_QUESTIONS_FILE = "retrieval_labels.json"   # no demo-pack answer keys exist (keys are held-out only); qa's hand labels hold the
#                                                 3 demo packs' real question refs and text, in pack order. Read only, nothing invented.


def demo_questions(ctx: Context, pack: str, n: int = DEMO_QUESTIONS_PER_PACK) -> list[dict]:
    """The first n question items of a demo pack, from the frozen hand labels (ref and text as the pack prints them). The pack
    prints no word limit in the labels, so none is passed (the draft uses the app default)."""
    packs = _json(ctx, DEMO_QUESTIONS_FILE, "the demo packs' labelled questions").get("packs", {})
    items = packs.get(Path(pack).stem) or packs.get(pack)
    if not items:
        raise PhaseNotReady(f"no labelled questions for demo pack {pack} in {ctx.keys_dir / DEMO_QUESTIONS_FILE}")
    return [{"id": f"{Path(pack).stem}:{i['ref']}", "question": i["text"], "word_limit": None} for i in items[:n]]


def _draft_items(questions: list[dict], passes: int = 1) -> list[Item]:
    return [Item(f"draft:{q['id']}:p{i}", "draft", q) for i in range(passes) for q in questions]


def build_plan(phase: str, ctx: Context) -> list[Item]:
    demo, held = pack_names(ctx)
    builder = PHASES[phase].plan
    if builder == "extract_heldout":
        return _extract_items(ctx, held)
    if builder == "draft_heldout":
        qs = []
        for n in drafting_heldout(ctx):   # named in the manifest (the first of each sector in SOURCES.md order)
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
        passes = 3 if builder == "tuning_demo" else 1
        per_pack = TUNING_QUESTIONS_PER_PACK if builder == "tuning_demo" else DEMO_QUESTIONS_PER_PACK
        qs = [q for n in names for q in demo_questions(ctx, n, per_pack)]
        items: list[Item] = []
        for i in range(passes):          # per pass: the packs' extraction, then the drafts (each runs the claim check)
            items += [Item(f"extract:{n}:p{i}", "extract", {"pack": n, "pass": i}) for n in names]
            items += [Item(f"draft:{q['id']}:p{i}", "draft", q) for q in qs]
        return items
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
    out["claims"] = _check(ctx, phase, q["id"], d.text, hits)
    return out


def default_claimcheck(ctx: Context) -> Callable[..., list]:
    """The real claim check (app.tender.claimcheck.check_draft) on the harness's provider and LedgerBudget. Same inputs as the
    app: the draft and its cited live passages. Returns claim dicts (span, kind, cited_ids, verdict, ...) for the scorers."""
    def run(budget, text: str, hits: list, retrieved_ids: list[int] | None = None) -> list[dict]:
        from dataclasses import asdict
        from app.tender import claimcheck as cc
        from app.tender.draft import Limits
        ids = {int(n) for n in cc._CITE.findall(text)}
        with ctx.sessions() as db:
            passages = cc.live_passages(db, ctx.tenant_id, ids, Limits())
            db.rollback()
        retrieved = retrieved_ids if retrieved_ids is not None else [h.display_no for h in hits]
        claims, _, _ = cc.check_draft(text, retrieved, ctx.tenant_id, budget, passages, provider=ctx.provider, sessions=ctx.sessions)
        return [asdict(c) for c in claims]
    run.is_default_claimcheck = True
    return run


def _check(ctx: Context, phase: str, draft_id: str, text: str, hits: list, retrieved_ids: list[int] | None = None) -> list[dict]:
    from app.tender.draft import CHECK_CAP       # the claimcheck output cap (DESIGN 4.4), not a copy of it
    budget = LedgerBudget(ctx.ledger, phase, "claimcheck", CHECK_CAP, label=draft_id)
    if ctx.claimcheck is None:
        raise PhaseNotReady("ctx.claimcheck is None: the claim check phase has nothing to call")
    kw = {} if retrieved_ids is None else {"retrieved_ids": retrieved_ids}
    return ctx.claimcheck(budget, text, hits, **kw)


def _run_item(ctx: Context, phase: str, item: Item) -> dict:
    if item.kind == "extract":
        return _extract(ctx, phase, item)
    if item.kind == "draft":
        return _draft(ctx, phase, item)
    return {"id": item.data["id"], "claims": _check(ctx, phase, item.data["id"], item.data["text"], [],
                                                    item.data.get("retrieved_ids"))}


def clear_ai_cache(ctx: Context) -> None:
    """Delete the demo tenant's ai_cache rows so a repeat pass or the A9 stopwatch really calls the model."""
    from sqlalchemy import delete
    from app.tender_models import AICache
    with ctx.sessions() as db:
        db.execute(delete(AICache).where(AICache.tenant_id == ctx.tenant_id))
        db.commit()


def _phase_rows(ctx: Context, phase: str) -> bool:
    return any(r["phase"] == phase for r in ctx.ledger.rows())


def run_phase(phase: str, ctx: Context) -> dict:
    """Run a phase's plan. Finished items (in results/<phase>.jsonl) are skipped. A refused hold stops the phase cleanly.
    A failed item (the model's answer was invalid or truncated) is recorded with its error code and counts against the bar."""
    if phase not in PHASES:
        raise PhaseNotReady(f"unknown phase {phase!r}; known: {', '.join(PHASES)}")
    if phase not in LIVE_PHASES and (not ctx.dry or getattr(ctx.provider, "name", None) != "fake"):
        raise PhaseNotReady(live_refusal(phase))        # defence in depth: no scored or recording phase can reach a real model
    plan = build_plan(phase, ctx)
    if PHASES[phase].group == "scored":
        preflight_scored(ctx.ledger, phase, [(n, p.worst_usd) for n, p in PHASES.items() if p.group == "scored"])
    path = ctx.results_dir / f"{phase}.jsonl"
    if not ctx.dry and not path.exists() and _phase_rows(ctx, phase):
        raise PhaseNotReady(f"the ledger has {phase} rows but {path} is missing: results are committed after every phase, so "
                            f"restore it from git. If the phase truly produced no finished item, create the empty file.")
    ctx.results_dir.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)       # marks the phase as started: a live phase with ledger rows and no file is refused above
    done = {json.loads(l)["item"] for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
    was_cacheable = getattr(ctx.provider, "cacheable", True)
    # T-219 review S1: ai_cache is read before every call whatever the provider says, so a live phase clears it before every item
    # (and tuning phases write nothing back), or a later item or phase could be answered with no ledger row and no cost measured.
    live_clear = not ctx.dry
    if live_clear and PHASES[phase].group == "tuning":
        ctx.provider.cacheable = False
    try:
        return _run_plan(phase, ctx, plan, path, done, was_cacheable, live_clear)
    finally:
        if live_clear and PHASES[phase].group == "tuning":
            ctx.provider.cacheable = was_cacheable


def _run_plan(phase: str, ctx: Context, plan: list[Item], path: Path, done: set, was_cacheable: bool, live_clear: bool) -> dict:
    from app.tender.llm import TaskFailed
    from app.ai import AIUnavailable
    from app.errors import AppError
    ran = skipped = failed = 0
    stopped = None
    cache_cleared = False
    model_mismatch = False
    for item in plan:
        if item.id in done:
            skipped += 1
            continue
        if live_clear or (phase in CACHE_CLEAR_PHASES and was_cacheable):    # a live read of ai_cache happens whatever `cacheable` says
            clear_ai_cache(ctx)
            cache_cleared = True
        try:
            result = _run_item(ctx, phase, item)
        except BudgetExceeded as e:
            stopped = str(e)
            break
        except ModelMismatch as e:                  # the settle row is already written (priced); the item is not recorded
            stopped = f"MODEL MISMATCH: {e}"
            model_mismatch = True
            break
        except AIUnavailable as e:                  # infrastructure: stop for a resume, do not record the item
            stopped = f"AI unavailable: {type(e).__name__}; resume later"
            break
        except TaskFailed as e:                     # invalid or truncated output: a result, not a crash. Any other AppError
            #                                         (tenant or DB lookup, plan) is infrastructure and propagates: the phase is fatal.
            result = {"error": getattr(e, "code", type(e).__name__)}
            failed += 1
        except AppError as e:
            if not str(getattr(e, "code", "")).startswith("ai_"):
                raise                               # tenant, DB or plan errors are fatal, as before
            # T-219 review S4: a provider error (an HTTP 400 is ai_rejected) stops the run cleanly. The hold was settled at the
            # worst case by run_task, so the ledger is right; the item is not recorded and a resume retries it.
            stopped = f"AI error {e.code}: {e.message}"
            break
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"item": item.id, "result": result}, sort_keys=True, default=str) + "\n")
        ran += 1
    res = {"phase": phase, "planned": len(plan), "ran": ran, "failed": failed, "skipped": skipped, "stopped": stopped,
           "dry_run": ctx.dry}
    if model_mismatch:
        res["model_mismatch"] = True
    if cache_cleared:
        res["reseed_required"] = RESEED_NOTE
        print(f"eval.run: {RESEED_NOTE}", file=sys.stderr)
    return res


# ---------- run configuration (EVAL.md) ----------

def run_configuration() -> dict:
    from app.tender import claimcheck as cc, draft as dr, extract as ex
    specs = [ex.EXTRACT_SPEC, dr.DRAFT_SPEC, dr.SHORTEN_SPEC]
    prompts = {f"{s.name}:{s.prompt_version}": {"sha256": hashlib.sha256(s.system.encode()).hexdigest(), "effort": s.effort,
                                               "output_cap": s.max_output_tokens} for s in specs}
    cfg = load_budget_config()
    return {"model": cfg.model, "approved_by": cfg.approved_by, "total_cap_usd": cfg.total_cap, "group_caps_usd": cfg.group_caps,
            "reasoning_headroom": cfg.headroom, "prompts": prompts, "claimcheck_prompt": {f"{cc.CLAIMCHECK_SPEC.name}:{cc.CLAIMCHECK_SPEC.prompt_version}": {
                "sha256": hashlib.sha256(cc.CLAIMCHECK_SPEC.system.encode()).hexdigest(), "effort": cc.CLAIMCHECK_SPEC.effort,
                "output_cap": cc.CLAIMCHECK_SPEC.max_output_tokens}}}


def retrieval_diagnostic(sessions, tenant_id, labels: dict, k: int = 8, labels_sha256: str | None = None) -> dict:
    """DESIGN 4.2 retrieval check: the app's own search (search_evidence with the per-document cap and RETRIEVAL_FLOOR, called
    the way the draft task and the draft route call it, except at depth k=8 instead of limit=APP_PASSAGES; the /evidence/search
    route uses the defaults and no floor) on each labelled question's text, scored by score.retrieval_recall. `labels_sha256`
    (sha256 of the labels file bytes, passed by main) is recorded so a stale results file can be told from a current one.
    No model call, no ledger, nothing written to the DB."""
    from app.tender import draft as dr
    from app.tender.evidence import search_evidence
    from . import score as sc
    retrieved: dict[str, dict[str, list[int]]] = {}
    with sessions() as db:
        for pack, items in (labels.get("packs") or {}).items():
            for it in items:
                hits = search_evidence(db, tenant_id, it["text"], limit=k, min_score=dr.RETRIEVAL_FLOOR)
                retrieved.setdefault(pack, {})[it["ref"]] = [h.display_no for h in hits]
        db.rollback()
    res = sc.retrieval_recall(labels, retrieved, k=k)
    res["retrieved"] = retrieved
    res["app_passages"] = dr.APP_PASSAGES        # the draft task shows the model only this many; recall at that depth is informational
    res["at_app_passages"] = sc.retrieval_recall(labels, retrieved, k=dr.APP_PASSAGES)["pooled"]
    res["retrieval_floor"] = dr.RETRIEVAL_FLOOR
    if labels_sha256 is not None:
        res["labels_sha256"] = labels_sha256
    return res


# ---------- live mode (T-219: tuning phases only) ----------

def live_refusal(phase: str) -> str:
    return (f"phase {phase} may not run live: only {', '.join(sorted(LIVE_PHASES))} (tuning) may call the model now. "
            f"E1-E4, R1 and R2 wait for the L1 configuration freeze (EVAL.md TBD rows filled and committed).")


def missing_live_env(env=None) -> list[str]:
    env = os.environ if env is None else env
    return [k for k in LIVE_ENV if not (env.get(k) or "").strip()]


def build_live_provider(env=None):
    """The app's real Azure OpenAI Responses client (app.ai.AzureOpenAI) from the environment. Headroom 0 so the cap sent is
    the cap the ledger prices (DESIGN 8.5). The key is passed to the client only: never printed, logged or put in a message.
    Tests monkeypatch this name to inject a fake."""
    from app.ai import AzureOpenAI
    env = os.environ if env is None else env
    return AzureOpenAI(env["AZURE_OPENAI_ENDPOINT"].strip(), env["AZURE_OPENAI_DEPLOYMENT_MINI"].strip(), env["AZURE_OPENAI_API_KEY"],
                       timeout=LIVE_TIMEOUT_SECONDS, deadline=LIVE_TIMEOUT_SECONDS, retries=LIVE_RETRIES, api="responses",
                       reasoning_headroom=0)


def pack_loader(packs_dir: Path) -> Callable[[str], list[tuple[int, str]]]:
    """pack file name -> [(page, text)] through the app's own parser (sandboxed worker), as an upload would be parsed."""
    def load(name: str) -> list[tuple[int, str]]:
        from app.tender import ingest
        path = packs_dir / name
        parsed = ingest.parse_upload(path.read_bytes(), allow_text=True, max_pages=60)
        return [(i + 1, p["text"]) for i, p in enumerate(parsed.pages)]
    return load


def retriever(sessions, tenant_id) -> Callable[[str], list]:
    """question -> hits, called as the draft task calls it (limit APP_PASSAGES, RETRIEVAL_FLOOR)."""
    def run(question: str) -> list:
        from app.tender import draft as dr
        from app.tender.evidence import search_evidence
        with sessions() as db:
            hits = search_evidence(db, tenant_id, question, limit=dr.APP_PASSAGES, min_score=dr.RETRIEVAL_FLOOR)
            db.rollback()
        return hits
    return run


def local_database(url: str) -> bool:
    from sqlalchemy.engine import make_url
    return (make_url(url).host or "localhost") in {"localhost", "127.0.0.1", "::1"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="eval.run")
    ap.add_argument("phase", help="E1..E4, T1..T3, R1, R2, 'config', or 'retrieval' (Recall@8 diagnostic, no model call)")
    ap.add_argument("--live", action="store_true", help="call the real model: tuning phases T1-T3 only, through the ledger")
    ap.add_argument("--allow-remote-db", action="store_true", help="allow a DATABASE_URL whose host is not local")
    args = ap.parse_args(argv)
    if args.live and args.phase not in LIVE_PHASES:
        print(f"eval.run: {live_refusal(args.phase)}", file=sys.stderr)
        return 3
    if args.live:
        missing = missing_live_env()
        if missing:
            print(f"eval.run: live run refused, no call made: set {', '.join(missing)} in the environment", file=sys.stderr)
            return 6
    if args.phase == "config":
        print(json.dumps(run_configuration(), indent=2))
        return 0
    labels_path = KEYS_DIR / "retrieval_labels.json"
    if args.phase == "retrieval" and not labels_path.is_file():
        print(f"eval.run: not ready: retrieval labels not found at {labels_path} (written by qa)", file=sys.stderr)
        return 4
    if args.phase != "retrieval":
        from app.tender.scripted_ai import ScriptedFakeAI
        cfg = load_budget_config()
        ledger = Ledger(LIVE_LEDGER if args.live else DRY_LEDGER, cfg, dry_run=not args.live)
    from sqlalchemy import select
    from app.config import Settings
    from app.db import Database
    from app.models import Tenant
    from .seed import FIRM
    url = Settings().database_url
    if not args.allow_remote_db and not local_database(url):
        print("eval.run: DATABASE_URL is not a local database; refusing (pass --allow-remote-db to override)", file=sys.stderr)
        return 5
    db = Database(url)                           # a local database only: never the deployed app's
    sessions = db.sessions
    with sessions() as s:
        tenant_id = s.scalar(select(Tenant.id).where(Tenant.name == FIRM))
    if tenant_id is None:
        print("eval.run: demo tenant not found; run `python -m eval.seed` first", file=sys.stderr)
        return 4
    if args.phase == "retrieval":
        raw = labels_path.read_bytes()
        res = retrieval_diagnostic(sessions, tenant_id, json.loads(raw.decode("utf-8")), labels_sha256=hashlib.sha256(raw).hexdigest())
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        text = json.dumps(res, indent=2, sort_keys=True)
        (RESULTS_DIR / "retrieval.json").write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0
    provider = build_live_provider() if args.live else ScriptedFakeAI()
    ctx = Context(provider, ledger, sessions, tenant_id, retrieve=retriever(sessions, tenant_id),
                  load_pack=pack_loader(PRODUCT / "demo-data" / "packs"),
                  results_dir=RESULTS_DIR if args.live else DRY_RESULTS_DIR, dry=not args.live)
    try:
        res = run_phase(args.phase, ctx)
        print(json.dumps(res, indent=2))
    except PhaseNotReady as e:
        print(f"eval.run: not ready: {e}", file=sys.stderr)
        return 4
    if args.live and res.get("stopped"):
        print(f"eval.run: live phase stopped early: {res['stopped']}", file=sys.stderr)
        return 7 if res.get("model_mismatch") else 8
    return 0


if __name__ == "__main__":
    sys.exit(main())
