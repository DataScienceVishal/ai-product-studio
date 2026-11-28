"""S5 drafting: retrieval to draft, the gap path, citation and length checks, versioning (DESIGN 4.4, 4.5).

The model writes; code checks. With no retrieved evidence the draft is a gap marker and the model is never called.
A citation that is not in the retrieved set is recorded on the draft (outside_ids, flag citation_outside_set) and the
claim check (S6) turns it into `unsupported`. An answer over the word limit gets one "shorten" retry, then trailing
sentences are dropped until it fits.
"""
from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from ..ai import AIUnavailable, reservation_estimate
from ..billing import ai_access
from ..deps import subscription_of
from ..errors import AppError
from ..tender_models import AITask, Draft, Requirement, TenderPack
from . import runner
from .evidence import Hit, search_evidence
from .llm import AppBudget, TaskSpec, build_user, full_system, run_task

log = logging.getLogger("app.tender.draft")

GAP_TEXT = "[NEEDS FIRM INPUT: no evidence found for this question]"
RETRIEVAL_FLOOR = 0.0          # minimum retrieval rank (a code match passes regardless); tuned in L1 (a hit below it counts as no evidence)
# App-path sizing (R3). Trial tenants have 30k tokens a day, and a reservation is input bytes + cap + headroom, so a
# draft and its re-check must reserve at most 30k between them. The harness passes its own, larger limits.
APP_PASSAGES = 8                # largest k that keeps the worst-case reservations in budget (DESIGN 4.3, test_app_passages_is_the_largest_k_that_fits_the_budget)
APP_PASSAGE_CHARS = 1000
QUESTION_CHARS = 1500
CHECK_CAP = 6000               # claimcheck output cap (DESIGN 4.4); the check itself is S6
CHECK_SYSTEM_BYTES = 2000      # upper bound for the claimcheck system prompt
APP_PAIR_BUDGET = 30_000
REDRAFTS_PER_REQUIREMENT_PER_DAY = 5
MAX_PER_TASK = 40
DRAFT_PACK_STATES = ("drafting", "checking", "ready")  # the routes use the same set

_CITE = re.compile(r"\[E-(\d+)\]")
_GAP = re.compile(r"\[NEEDS FIRM INPUT:[^\]]*\]")


class DraftOutput(BaseModel):
    answer: str
    gaps: list[str]
    used_ids: list[int]


DRAFT_SPEC = TaskSpec(
    "draft", "v1",
    "You draft one answer to a UK public-sector tender question for a small firm, using ONLY the numbered passages "
    "provided (each starts [E-n]). Cite every factual claim with its passage marker, for example [E-12]. Never cite a "
    "number that is not in the passages and never invent facts, figures, clients or accreditations. Stay within the "
    "word limit if one is given. Where the passages do not answer part of the question, write the exact marker "
    "[NEEDS FIRM INPUT: what is missing] instead of guessing. Return JSON: answer, gaps (the markers you wrote), "
    "used_ids (the E numbers you cited).",
    DraftOutput, 4000, "low")


SHORTEN_SPEC = TaskSpec(
    "draft", "v1-shorten",
    "You shorten a draft tender answer. Rewrite the text in previous_answer so that it has at most the number of words "
    "in word_limit. Keep the [E-n] markers on the claims they support, keep any [NEEDS FIRM INPUT: ...] marker, and do "
    "not add facts, figures or citations. Return JSON: answer, gaps (the markers present), used_ids (the E numbers cited).",
    DraftOutput, 1500, "low")


def count_words(text_: str) -> int:
    """Words as the sign-off counts them: [E-n] markers excluded, gap markers included."""
    return sum(1 for w in _CITE.sub(" ", text_).split() if any(c.isalnum() for c in w))


_ABBREV = re.compile(r"(?:\b(?:Ltd|Plc|Inc|Co|Corp|No|Nos|Mr|Mrs|Ms|Dr|St|Ref|Approx|Est|vs|etc|incl|min|max)|\b(?:e\.g|i\.e))\.$", re.I)


def split_sentences(text_: str) -> list[str]:
    """Sentences, keeping a trailing [E-n] with its sentence and a [NEEDS FIRM INPUT: ...] marker whole."""
    out: list[str] = []
    for seg in re.split(r"(?<=[.!?])\s+", text_.strip()):
        if not seg:
            continue
        if out and out[-1].count("[") > out[-1].count("]"):  # inside a [NEEDS FIRM INPUT: ...] marker
            out[-1] += " " + seg
            continue
        if out and _ABBREV.search(out[-1]) and seg[:1].isalnum() and not seg[:1].isupper():  # "Ltd. and", "e.g. cleaning" (T-189 nit 10)
            out[-1] += " " + seg
            continue
        lead = re.match(r"(?:\[E-\d+\]\s*)+", seg)
        if out and lead:  # a citation that follows the full stop belongs to the sentence before it
            out[-1] += " " + lead.group(0).strip()
            seg = seg[lead.end():]
        if seg:
            out.append(seg)
    return out


def fit_to_limit(answer: str, limit: int) -> str:
    """Drop trailing sentences until the answer is at or under `limit` words (a single oversize sentence is cut)."""
    sentences = split_sentences(answer)
    while sentences and count_words(" ".join(sentences)) > limit:
        sentences.pop()
    if sentences:
        return " ".join(sentences)
    words = answer.split()
    cut = []
    for w in words:
        if count_words(" ".join(cut + [w])) > limit:
            break
        cut.append(w)
    return _balance(" ".join(cut))


def _balance(t: str) -> str:
    """Remove a bracket marker left open by a cut."""
    i = t.rfind("[")
    return t[:i].rstrip() if i >= 0 and t.find("]", i) < 0 else t


@dataclass
class Limits:
    passages: int = APP_PASSAGES
    passage_chars: int = APP_PASSAGE_CHARS
    question_chars: int = QUESTION_CHARS


def passage_block(hits: list[Hit], limits: Limits) -> str:
    """One line per passage, `[E-n] text`, whitespace collapsed (the ScriptedFakeAI heuristic reads line by line)."""
    return "\n".join(f"[E-{h.display_no}] " + " ".join(h.text.split())[:limits.passage_chars]
                     for h in hits[:limits.passages])


def draft_payload(req_text: str, word_limit: int | None, marks: int | None, hits: list[Hit], limits: Limits) -> dict:
    return {"question": " ".join(req_text.split())[:limits.question_chars],
            "word_limit": f"{word_limit} words" if word_limit else "no limit stated",
            "marks": str(marks) if marks is not None else "not stated",
            "passages": passage_block(hits, limits)}


def draft_reservation(provider, payload: dict) -> int:
    return reservation_estimate(provider, full_system(DRAFT_SPEC), build_user(payload, "0" * 16), DRAFT_SPEC.max_output_tokens)


def shorten_reservation(provider, answer: str, word_limit: int) -> int:
    payload = {"word_limit": f"{word_limit} words", "previous_answer": answer}
    return reservation_estimate(provider, full_system(SHORTEN_SPEC), build_user(payload, "0" * 16),
                                SHORTEN_SPEC.max_output_tokens)


def check_reservation(provider, answer: str, cited_passages: str) -> int:
    """What the re-check will reserve on the app path: the draft and the cited passages only (S6 sends the same)."""
    user = build_user({"draft": answer, "passages": cited_passages}, "0" * 16)
    return reservation_estimate(provider, "x" * CHECK_SYSTEM_BYTES, user, CHECK_CAP)


@dataclass
class Drafted:
    text: str
    cited_ids: list[int]
    outside_ids: list[int]
    gap_count: int
    flags: list[str] = field(default_factory=list)
    retrieved_ids: list[int] = field(default_factory=list)
    model: str | None = None
    prompt_version: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


def analyse(answer: str, retrieved: set[int]) -> tuple[list[int], list[int], int]:
    ids = sorted({int(n) for n in _CITE.findall(answer)})
    return [n for n in ids if n in retrieved], [n for n in ids if n not in retrieved], len(_GAP.findall(answer))


def draft_answer(req_text: str, word_limit: int | None, marks: int | None, hits: list[Hit], tenant_id: uuid.UUID, budget,
                 *, provider, sessions: sessionmaker, limits: Limits | None = None, before_call=None) -> Drafted:
    """The whole drafting step for one requirement, given what retrieval found. No database session is held here."""
    limits = limits or Limits()
    shown = hits[:limits.passages]
    retrieved = [h.display_no for h in shown]
    if not shown:  # the gap path: no model call, nothing to hold on the budget (A8 is deterministic here)
        return Drafted(GAP_TEXT, [], [], 1, ["no_evidence"], [], None, "gap")
    payload = draft_payload(req_text, word_limit, marks, shown, limits)
    res = run_task(DRAFT_SPEC, payload, tenant_id, budget, provider=provider, sessions=sessions, before_call=before_call)
    answer, tin, tout, flags = res.output.answer.strip(), res.input_tokens, res.output_tokens, []
    if word_limit and count_words(answer) > word_limit:
        # the instruction lives in SHORTEN_SPEC's system prompt; the prior draft is data. No passages are re-sent, which
        # keeps the retry's reservation small (R3).
        retry = {"word_limit": f"{word_limit} words", "previous_answer": answer}
        try:
            again = run_task(SHORTEN_SPEC, retry, tenant_id, budget, provider=provider, sessions=sessions,
                             before_call=before_call)
            answer, flags = again.output.answer.strip(), ["shortened"]
            tin, tout = tin + again.input_tokens, tout + again.output_tokens
        except (AppError, AIUnavailable) as error:  # a refused or failed retry falls through to the sentence drop
            log.info("shorten retry failed", extra={"code": getattr(error, "code", "ai_unavailable")})
            tin, tout = tin + error.task_tokens[0], tout + error.task_tokens[1]  # a failed retry may have been billed
        if count_words(answer) > word_limit:
            answer, flags = fit_to_limit(answer, word_limit), [f for f in flags if f != "shortened"] + ["trimmed"]
    cited, outside, gaps = analyse(answer, set(retrieved))
    if outside:
        flags.append("citation_outside_set")
    return Drafted(answer, cited, outside, gaps, flags, retrieved, res.model, DRAFT_SPEC.prompt_version, tin, tout)


def save_version(db: Session, tenant_id: uuid.UUID, requirement_id: uuid.UUID, d: Drafted, *, author: str,
                 word_limit: int | None, status: str = "drafted") -> Draft:
    """Append a new version. A per-requirement advisory lock makes max+1 safe; the unique constraint is the backstop."""
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"draft:{requirement_id}"})
    version = (db.scalar(select(func.coalesce(func.max(Draft.version), 0)).where(
        Draft.tenant_id == tenant_id, Draft.requirement_id == requirement_id)) or 0) + 1
    row = Draft(tenant_id=tenant_id, requirement_id=requirement_id, version=version, text=d.text,
                text_sha256=hashlib.sha256(d.text.encode("utf-8")).hexdigest(), word_count=count_words(d.text),
                word_limit_snapshot=word_limit, retrieved_ids=d.retrieved_ids, cited_ids=d.cited_ids,
                outside_ids=d.outside_ids, gap_count=d.gap_count, flags=d.flags, author=author,
                prompt_version=d.prompt_version, model=d.model, status=status)
    db.add(row)
    db.flush()
    return row


def draftable(db: Session, tenant_id: uuid.UUID, pack_id: uuid.UUID, target: uuid.UUID | None) -> list[Requirement]:
    q = select(Requirement).where(Requirement.tenant_id == tenant_id, Requirement.pack_id == pack_id,
                                  Requirement.status == "confirmed", Requirement.kind == "question")
    if target is not None:
        return list(db.scalars(q.where(Requirement.id == target)))
    has = select(Draft.requirement_id).where(Draft.tenant_id == tenant_id)
    return list(db.scalars(q.where(Requirement.id.not_in(has)).order_by(Requirement.seq).limit(MAX_PER_TASK)))


_settings = None


def configure(settings) -> None:
    global _settings
    _settings = settings


def draft_handler(sessions: sessionmaker, task: AITask, heartbeat, provider) -> tuple[int, int]:
    """One task drafts one requirement (target_id) or every confirmed question that has no draft yet. Each draft is
    committed as it is made, so a refusal part-way (daily cap) keeps what is done and a re-run continues."""
    settings = _settings
    with sessions() as db:
        sub = subscription_of(db, task.tenant_id)
        allowed = ai_access(sub, settings)
        reqs = [(r.id, r.text, r.word_limit, r.marks) for r in draftable(db, task.tenant_id, task.pack_id, task.target_id)]
        budget = AppBudget.for_subscription(sessions, task.tenant_id, sub, settings, "draft")
        db.rollback()
    if not allowed:
        raise AppError(402, "plan_required", "Your trial or plan has ended.")
    tin = tout = 0
    for rid, rtext, limit, marks in reqs:
        heartbeat()
        with sessions() as db:
            hits = search_evidence(db, task.tenant_id, rtext, limit=APP_PASSAGES, min_score=RETRIEVAL_FLOOR)
            db.rollback()
        try:
            d = draft_answer(rtext, limit, marks, hits, task.tenant_id, budget, provider=provider, sessions=sessions,
                             before_call=heartbeat)
        except AppError as error:  # keep the tokens the drafts already done used, for ai_tasks reporting (T-189 nit 9)
            error.task_tokens = (tin + error.task_tokens[0], tout + error.task_tokens[1])  # earlier drafts + this call's own
            raise
        tin, tout = tin + d.input_tokens, tout + d.output_tokens
        with sessions() as db:
            # Sign-off is a digest of the draft hashes, so no version may be written once the pack is signed or exported.
            # FOR SHARE makes a concurrent sign-off (which updates the pack row) wait for this save, or this save wait for it.
            pack_status = db.scalar(select(TenderPack.status).where(
                TenderPack.tenant_id == task.tenant_id, TenderPack.id == task.pack_id).with_for_update(read=True))
            if pack_status not in DRAFT_PACK_STATES:
                log.info("draft skipped: pack no longer open", extra={"status": pack_status})
                db.rollback()
                break
            if db.scalar(select(Requirement.id).where(Requirement.tenant_id == task.tenant_id, Requirement.id == rid,
                                                      Requirement.status == "confirmed")) is None:
                continue  # removed while drafting
            save_version(db, task.tenant_id, rid, d, author="ai", word_limit=limit)
            reopen_pack(db, task.tenant_id, task.pack_id)
            db.commit()
    return tin, tout


def reopen_pack(db: Session, tenant_id, pack_id) -> None:
    """A change after a pack was `ready` (an edit, a new or changed requirement, removed evidence) makes it `drafting`
    again: readiness is a claim about the current text, and the text moved."""
    db.execute(update(TenderPack).where(TenderPack.tenant_id == tenant_id, TenderPack.id == pack_id,
                                        TenderPack.status == "ready").values(status="drafting"))


def reset_pack_after_exhausted(sessions: sessionmaker, task: AITask) -> None:
    """Failure hook: a pack left in a transient state ('checking') by a dead draft task goes back to 'drafting'."""
    with sessions() as db:
        db.execute(update(TenderPack).where(TenderPack.tenant_id == task.tenant_id, TenderPack.id == task.pack_id,
                                            TenderPack.status == "checking").values(status="drafting"))
        db.commit()


runner.HANDLERS["draft"] = draft_handler
runner.FAILURE_HOOKS["draft"] = reset_pack_after_exhausted
