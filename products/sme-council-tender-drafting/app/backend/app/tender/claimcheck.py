"""S6 claim check (DESIGN 4.4): the model lists the claims in a draft and judges each against the passages the draft
cites; code then downgrades or adds verdicts the model cannot be trusted with.

Rules applied by `apply_rules` (pure, no model, no database):
  1. a claim whose span is not an exact substring of the draft is discarded;
  2. `supported` needs an evidence_quote that is a normalised substring of a cited passage, else `unsupported`;
  3. every number, year, GBP or % figure and accreditation code in the span must be in the evidence_quote, else `unsupported`;
     every proper name (a run of capitalised words) in the span must be in the quote too, and the quote must be big enough
     (see `quote_big_enough`), else `unsupported`;
  4. a citation outside the retrieved set, or one whose passage is not available (removed), gives `unsupported`;
  5. a factual claim whose own sentence carries no [E-n] marker is `unsupported` (ids the model cites from elsewhere in the
     draft do not count, and a repeated sentence is judged on its own marker, never on another occurrence's verdict);
  6. unchecked-sentence detector: a draft sentence holding a digit, a pound sign, a percent, a year, an accreditation code
     or a run of two or more capitalised words that no claim span covers becomes an `unchecked` claim.
Text in the draft is data: it goes inside a DATA block, and nothing the model says can raise a verdict above what rules 2 to 5 allow.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel

from .draft import CHECK_CAP, CHECK_SYSTEM_BYTES, GAP_TEXT, Limits, _CITE, _GAP  # noqa: F401
from .llm import TaskSpec
from .extract import norm

log = logging.getLogger("app.tender.claimcheck")


class ClaimItem(BaseModel):
    span: str
    kind: Literal["factual", "opinion"]
    cited_ids: list[int]
    verdict: Literal["supported", "unsupported", "contradicted"]
    evidence_quote: str | None
    reason: str | None


class ClaimcheckOutput(BaseModel):
    claims: list[ClaimItem]


CLAIMCHECK_SPEC = TaskSpec(
    "claimcheck", "v1",
    "You check a draft tender answer against evidence passages. The draft is in the DATA block named draft; the passages "
    "(each starts [E-n]) are in the block named passages. List every claim the draft makes: each factual statement, number, "
    "date, client, accreditation or commitment. For each give span (copied exactly from the draft), kind (factual or "
    "opinion), cited_ids (the E numbers it cites), verdict and evidence_quote. Verdict supported only if a cited passage "
    "states the same thing, with the same figures; then evidence_quote is the words copied exactly from that passage. "
    "Otherwise unsupported, or contradicted if a cited passage says the opposite; evidence_quote is then null. reason is one "
    "short sentence. Do not skip a claim because it looks minor.",
    ClaimcheckOutput, CHECK_CAP, "medium")
assert len(CLAIMCHECK_SPEC.system) + 200 < CHECK_SYSTEM_BYTES

_BLANK_KEEP = re.compile(r"\[E-\d+\]|\[NEEDS FIRM INPUT:[^\]]*\]")
_NUM = re.compile(r"(£)?(\d[\d,]*(?:\.\d+)?)(%)?")
_CODE = re.compile(r"(?i)\bISO\s?-?\d{4,5}(?:[-:]\d{1,4})?|\bBS\s?(?:EN\s?)?\d{3,5}|\bCHAS\b|\bSafe\s?Contractor\b|\bBICSc\b|"
                   r"\bConstructionline\b|\bCyber\s+Essentials(?:\s+Plus)?\b|\bSSIP\b|\bOHSAS\s?\d+|\bPAS\s?\d+")
_CAPS_RUN = re.compile(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+")


def strip_marks(s: str) -> str:
    return _BLANK_KEEP.sub(" ", s)


def fact_tokens(s: str) -> tuple[set[tuple[str, str, str]], set[str]]:
    """(numbers as (pound, digits, percent), codes in lower case without spaces or hyphens) for text without markers."""
    s = strip_marks(s)
    nums = {(m.group(1) or "", m.group(2).replace(",", "").rstrip("."), m.group(3) or "") for m in _NUM.finditer(s)}
    codes = {re.sub(r"[\s-]+", "", m.group(0)).lower() for m in _CODE.finditer(s)}
    return nums, codes


def figures_in(span: str, quote: str) -> bool:
    """Every figure and code of the span is in the quote (a bare number matches the same digits with or without a symbol)."""
    sn, sc = fact_tokens(span)
    qn, qc = fact_tokens(quote)
    for p, d, pc in sn:
        if not any(d == qd and (not p or p == qp) and (not pc or pc == qpc) for qp, qd, qpc in qn):
            return False
    return sc <= qc


_COMMON_FIRST = frozenset(
    "we our the a an in on at for with and this these those all each every they it its their as by from to of since over after "
    "during where when while through across also but however both any some many most several per under within between among "
    "once now then there here if so such".split())
_STOP = _COMMON_FIRST | frozenset("is are was were be been have has had will can do does did that which who not no or than into "
                                  "your you us them he she his her".split())


def names_in(span: str) -> list[str]:
    """Proper names in a span: each run of capitalised words, markers ignored. A sentence-initial common word ("We", "Our",
    "The") is not part of a name and is dropped from the front of a run that starts the span. Every other capitalised word
    that is not the first of a sentence and not a stop word is returned too, so a single-word name is checked."""
    s = strip_marks(span)
    out = []
    for m in _CAPS_RUN.finditer(s):
        words = m.group(0).split()
        if not s[:m.start()].strip(" \t\n\"'(") or re.search(r"[.!?]\s*$", s[:m.start()]):
            while words and words[0].casefold() in _COMMON_FIRST:
                words.pop(0)
        if words:
            out.append(" ".join(words))
    # one-word names and names split by a lowercase word ("Tesco", "University of Bristol"): every other capitalised word
    # that does not start a sentence and is not a stop word is checked on its own
    for m in re.finditer(r"\b[A-Z][A-Za-z]+\b", s):
        before = s[:m.start()]
        if not before.strip(" \t\n\"'(") or re.search(r"[.!?]\s*$", before) or m.group(0).casefold() in _STOP \
                or any(m.group(0) in n.split() for n in out):
            continue
        out.append(m.group(0))
    return out


def quote_big_enough(span: str, quote: str) -> bool:
    """A quote must hold real evidence, not a token like "the". Rule: at least max(3, ceil(c / 2)) words, where c is the
    number of content words in the span (markers and common stop words not counted); a span shorter than that needs the
    quote to be at least as long as the span itself."""
    sw = [w for w in re.findall(r"[\w£%'.,-]*\w", strip_marks(span))]
    content = [w for w in sw if w.casefold() not in _STOP]
    need = min(max(3, -(-len(content) // 2)), len(sw))
    return len(re.findall(r"\w+", quote)) >= need


def names_in_quote(span: str, quote: str) -> bool:
    q = norm(quote)
    return all(norm(n) in q for n in names_in(span))


def quote_in(quote: str, passage: str) -> bool:
    q = norm(quote)
    return bool(q) and q in norm(passage)


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each sentence in `text`. A [NEEDS FIRM INPUT: ...] marker stays whole, and a citation that follows a
    full stop stays with the sentence before it."""
    cuts = [0] + [m.end() for m in re.finditer(r"(?<=[.!?])\s+", text)] + [len(text) + 1]
    segs: list[list[int]] = []
    for a, b in zip(cuts, cuts[1:]):
        b = min(b, len(text))
        if a >= b:
            continue
        seg = text[a:b]
        if segs and text[segs[-1][0]:segs[-1][1]].count("[") > text[segs[-1][0]:segs[-1][1]].count("]"):
            segs[-1][1] = b  # inside a [NEEDS FIRM INPUT: ...] marker
            continue
        lead = re.match(r"(?:\[E-\d+\]\s*)+", seg)
        if segs and lead:  # a citation that follows the full stop belongs to the sentence before it
            segs[-1][1] = a + lead.end()
            a += lead.end()
            if a >= b:
                continue
        segs.append([a, b])
    out = []
    for a, b in segs:
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if a < b:
            out.append((a, b))
    return out


def fact_triggers(text: str, a: int, b: int) -> list[tuple[int, int]]:
    """Positions inside text[a:b] that make a sentence a factual statement: digits, pound, percent, years (digits), codes,
    a run of two or more capitalised words. Markers are blanked first so [E-3] and the gap text never count."""
    masked = _BLANK_KEEP.sub(lambda m: " " * len(m.group(0)), text[a:b])
    hits = [m.span() for m in re.finditer(r"[£%]|\d", masked)]
    hits += [m.span() for m in _CODE.finditer(masked)] + [m.span() for m in _CAPS_RUN.finditer(masked)]
    return [(a + s, a + e) for s, e in hits]


def _occurrences(text: str, span: str) -> list[tuple[int, int]]:
    out, i = [], text.find(span)
    while i >= 0:
        out.append((i, i + len(span)))
        i = text.find(span, i + 1)
    return out


@dataclass
class CheckedClaim:
    span: str
    kind: str
    cited_ids: list[int]
    verdict: str
    evidence_quote: str | None
    reason: str | None
    decided_by: str            # model | rule


def apply_rules(draft: str, model_claims: list[ClaimItem], passages: dict[int, str], outside_ids: set[int]) -> list[CheckedClaim]:
    """`passages` holds the text of every cited passage that is available (retrieved and not removed)."""
    spans = sentence_spans(draft)
    out: list[CheckedClaim] = []
    covered: list[tuple[int, int]] = []
    for c in model_claims:
        span = c.span.strip()
        if not span or span not in draft:
            continue  # rule 1
        occ = _occurrences(draft, span)

        def sent_of(o):
            return next(((x, y) for x, y in spans if x <= o[0] < y), o)

        def marks_of(o):
            x, y = sent_of(o)
            return frozenset(int(n) for n in _CITE.findall(draft[x:y]))
        # judge the first occurrence that has a marker of its own (else the first); cover only occurrences with the same markers
        judged = next((o for o in occ if marks_of(o)), occ[0])
        in_sentence = marks_of(judged)
        covered += [o for o in occ if marks_of(o) == in_sentence]
        cited = sorted(set(c.cited_ids) & in_sentence)
        verdict, quote, reason, by = c.verdict, c.evidence_quote, c.reason, "model"
        facts = fact_tokens(span) != (set(), set()) or bool(_CAPS_RUN.search(strip_marks(span)))
        factual = c.kind == "factual" or facts
        if verdict == "supported":
            if not in_sentence or not cited:
                verdict, reason, by = "unsupported", "The claim cites no evidence in its own sentence.", "rule"       # 5
            elif any(n in outside_ids for n in cited):
                verdict, reason, by = "unsupported", "It cites evidence that was not retrieved for this question.", "rule"  # 4
            elif any(n not in passages for n in cited):
                verdict, reason, by = "unsupported", "A cited passage is not available (removed or never retrieved).", "rule"  # 4
            elif not quote or not any(quote_in(quote, passages[n]) for n in cited):
                verdict, reason, by = "unsupported", "The quoted evidence is not in the cited passages.", "rule"   # 2
            elif not figures_in(span, quote):
                verdict, reason, by = "unsupported", "A figure, year or code in the claim is not in the quoted evidence.", "rule"  # 3
            elif not names_in_quote(span, quote):
                verdict, reason, by = "unsupported", "A name in the claim is not in the quoted evidence.", "rule"  # 3
            elif not quote_big_enough(span, quote):
                verdict, reason, by = "unsupported", "The quoted evidence is too short to support the claim.", "rule"  # 3
        elif not cited and factual and verdict != "contradicted":
            reason = reason or "The claim cites no evidence."
        if verdict != "supported":
            quote = None if verdict == "unsupported" else quote
        out.append(CheckedClaim(span, "factual" if factual else "opinion", cited, verdict, quote, reason, by))
    for a, b in spans:  # rule 6
        sentence = draft[a:b]
        if not strip_marks(sentence).strip():
            continue
        missing = [t for t in fact_triggers(draft, a, b) if not any(s <= t[0] and t[1] <= e for s, e in covered)]
        if missing:
            out.append(CheckedClaim(sentence, "factual", sorted({int(n) for n in _CITE.findall(sentence)}), "unchecked", None,
                                    "No claim covered the facts in this sentence.", "rule"))
    return out


def blocking(claims: list[CheckedClaim]) -> bool:
    return any(c.verdict != "supported" for c in claims)


# ---------- the task, the stored result and the gate's inputs ----------
from datetime import datetime, timezone  # noqa: E402

from sqlalchemy import delete, select, update  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from ..billing import ai_access  # noqa: E402
from ..deps import subscription_of  # noqa: E402
from ..errors import AppError  # noqa: E402
from ..tender_models import AITask, Claim, Draft, EvidenceItem, Requirement, Signoff, SourceDocument, TenderPack  # noqa: E402
from . import draft as _draft, gate, runner
from .draft import reopen_pack  # noqa: F401  # noqa: E402
from .llm import AppBudget, run_task  # noqa: E402

CHECK_PACK_STATES = ("drafting", "checking", "ready")
_settings = None


def configure(settings) -> None:
    global _settings
    _settings = settings


def live_passages(db: Session, tenant_id, ids: set[int], limits: Limits) -> dict[int, str]:
    """The cited passages the model may see: live evidence only, whitespace collapsed and cut like the draft's input."""
    if not ids:
        return {}
    rows = db.execute(select(EvidenceItem.display_no, EvidenceItem.text).join(
        SourceDocument, (SourceDocument.tenant_id == EvidenceItem.tenant_id) & (SourceDocument.id == EvidenceItem.document_id))
        .where(EvidenceItem.tenant_id == tenant_id, EvidenceItem.display_no.in_(ids), EvidenceItem.deleted_at.is_(None),
               SourceDocument.deleted_at.is_(None))).all()
    return {n: " ".join(t.split())[:limits.passage_chars] for n, t in rows}


def check_payload(draft_text: str, passages: dict[int, str]) -> dict:
    """The same two inputs on the app path and in the harness: the draft and the cited passages only."""
    return {"draft": draft_text, "passages": "\n".join(f"[E-{n}] {t}" for n, t in sorted(passages.items()))}


def check_draft(draft_text: str, retrieved_ids: list[int], tenant_id, budget, passages: dict[int, str], *, provider,
                sessions: sessionmaker, before_call=None) -> tuple[list[CheckedClaim], int, int]:
    """Check one draft. Returns (claims, input_tokens, output_tokens). No model call when the draft cites nothing and
    holds no facts (a gap marker draft): the rules alone decide."""
    cited = {int(n) for n in _CITE.findall(draft_text)}
    outside = cited - set(retrieved_ids)
    available = {n: t for n, t in passages.items() if n in cited and n not in outside}
    needs_model = bool(cited) or any(fact_triggers(draft_text, a, b) for a, b in sentence_spans(draft_text))
    if not needs_model:
        return apply_rules(draft_text, [], available, outside), 0, 0
    res = run_task(CLAIMCHECK_SPEC, check_payload(draft_text, available), tenant_id, budget, provider=provider,
                   sessions=sessions, before_call=before_call)
    return apply_rules(draft_text, list(res.output.claims), available, outside), res.input_tokens, res.output_tokens


def to_check(db: Session, tenant_id, pack_id, target) -> list[Draft]:
    """The latest draft of each confirmed question that has no claim check for its current text."""
    reqs = select(Requirement.id).where(Requirement.tenant_id == tenant_id, Requirement.pack_id == pack_id,
                                        Requirement.status == "confirmed", Requirement.kind == "question")
    if target is not None:
        reqs = reqs.where(Requirement.id == target)
    out = []
    for rid in db.scalars(reqs.order_by(Requirement.seq)):
        d = db.scalar(select(Draft).where(Draft.tenant_id == tenant_id, Draft.requirement_id == rid)
                      .order_by(Draft.version.desc()).limit(1))
        if d is not None and (target is not None or d.check_sha256 != d.text_sha256):
            out.append(d)
    return out


def store_check(db: Session, draft: Draft, claims: list[CheckedClaim]) -> None:
    db.execute(delete(Claim).where(Claim.tenant_id == draft.tenant_id, Claim.draft_id == draft.id))
    for i, c in enumerate(claims, 1):
        db.add(Claim(tenant_id=draft.tenant_id, draft_id=draft.id, seq=i, span=c.span, kind=c.kind, cited_ids=c.cited_ids,
                     verdict=c.verdict, evidence_quote=c.evidence_quote, reason=c.reason, decided_by=c.decided_by))
    draft.check_sha256, draft.checked_at = draft.text_sha256, datetime.now(timezone.utc)
    draft.status = "blocked" if blocking(claims) else "checked_ok"


def pack_checked(db: Session, tenant_id, pack_id) -> bool:
    """Every confirmed question has a latest draft that was checked on its current text and has no blocking claim."""
    reqs = list(db.scalars(select(Requirement.id).where(Requirement.tenant_id == tenant_id, Requirement.pack_id == pack_id,
                                                        Requirement.status == "confirmed", Requirement.kind == "question")))
    if not reqs:
        return False
    for rid in reqs:
        d = db.scalar(select(Draft).where(Draft.tenant_id == tenant_id, Draft.requirement_id == rid)
                      .order_by(Draft.version.desc()).limit(1))
        if d is None or d.check_sha256 != d.text_sha256 or d.status != "checked_ok":
            return False
    # T-201 item 5: evidence deleted while the check ran must not leave the pack `ready` (the gate would block it anyway).
    allowed, reasons = export_check(db, tenant_id, pack_id)
    return not (gate.reason_codes(reasons) & {"evidence_removed", "claims_blocked", "over_limit", "not_checked", "missing_draft"})


def claimcheck_handler(sessions: sessionmaker, task: AITask, heartbeat, provider) -> tuple[int, int]:
    settings = _settings
    with sessions() as db:
        sub = subscription_of(db, task.tenant_id)
        allowed = ai_access(sub, settings)
        todo = [(d.id, d.text, list(d.retrieved_ids)) for d in to_check(db, task.tenant_id, task.pack_id, task.target_id)]
        budget = AppBudget.for_subscription(sessions, task.tenant_id, sub, settings, "claimcheck")
        db.rollback()
    if not allowed:
        raise AppError(402, "plan_required", "Your trial or plan has ended.")
    tin = tout = 0
    limits = Limits()
    try:
        for draft_id, body, retrieved in todo:
            heartbeat()
            ids = {int(n) for n in _CITE.findall(body)}
            with sessions() as db:
                passages = live_passages(db, task.tenant_id, ids, limits)
                db.rollback()
            claims, a, b = check_draft(body, retrieved, task.tenant_id, budget, passages, provider=provider,
                                       sessions=sessions, before_call=heartbeat)
            tin, tout = tin + a, tout + b
            with sessions() as db:
                status = db.scalar(select(TenderPack.status).where(
                    TenderPack.tenant_id == task.tenant_id, TenderPack.id == task.pack_id).with_for_update(read=True))
                if status not in CHECK_PACK_STATES:  # signed or exported meanwhile: no claim may change
                    db.rollback()
                    break
                row = db.scalar(select(Draft).where(Draft.tenant_id == task.tenant_id, Draft.id == draft_id))
                if row is not None:
                    store_check(db, row, claims)
                db.commit()
    finally:
        finish_check(sessions, task)
    return tin, tout


def finish_check(sessions: sessionmaker, task: AITask) -> None:
    """The pack leaves `checking`: `ready` when every question is checked clean, else back to `drafting`."""
    with sessions() as db:
        status = db.scalar(select(TenderPack.status).where(TenderPack.tenant_id == task.tenant_id, TenderPack.id == task.pack_id)
                           .with_for_update())
        if status == "checking":
            db.execute(update(TenderPack).where(TenderPack.tenant_id == task.tenant_id, TenderPack.id == task.pack_id)
                       .values(status="ready" if pack_checked(db, task.tenant_id, task.pack_id) else "drafting"))
        db.commit()


def reset_pack_after_exhausted(sessions: sessionmaker, task: AITask) -> None:
    """Failure hook: a dead check task must not leave the pack in `checking`."""
    finish_check(sessions, task)


def load_gate_inputs(db: Session, tenant_id, pack_id):
    """Rows to the plain values `gate.export_allowed` takes. One read each; the caller decides what to do with the result."""
    pack = db.scalar(select(TenderPack).where(TenderPack.tenant_id == tenant_id, TenderPack.id == pack_id))
    req_rows = list(db.scalars(select(Requirement).where(Requirement.tenant_id == tenant_id, Requirement.pack_id == pack_id)))
    reqs = [gate.GateReq(str(r.id), r.kind, r.status, r.word_limit) for r in req_rows]
    req_ids = [r.id for r in req_rows]
    drafts_rows = list(db.scalars(select(Draft).where(Draft.tenant_id == tenant_id, Draft.requirement_id.in_(req_ids))))
    drafts = [gate.GateDraft(str(d.id), str(d.requirement_id), d.version, d.text, d.text_sha256, d.check_sha256)
              for d in drafts_rows]
    claims = [gate.GateClaim(str(c.draft_id), c.verdict, tuple(c.cited_ids)) for c in db.scalars(
        select(Claim).where(Claim.tenant_id == tenant_id, Claim.draft_id.in_([d.id for d in drafts_rows])))]
    so = db.scalar(select(Signoff).where(Signoff.tenant_id == tenant_id, Signoff.pack_id == pack_id,
                                       Signoff.voided_at.is_(None)).order_by(Signoff.signed_at.desc()).limit(1))
    signoff = gate.GateSignoff(so.statement_version, so.drafts_digest) if so else None
    live = {n for (n,) in db.execute(select(EvidenceItem.display_no).join(
        SourceDocument, (SourceDocument.tenant_id == EvidenceItem.tenant_id) & (SourceDocument.id == EvidenceItem.document_id))
        .where(EvidenceItem.tenant_id == tenant_id, EvidenceItem.deleted_at.is_(None), SourceDocument.deleted_at.is_(None)))}
    return gate.GatePack(pack.status), reqs, drafts, claims, signoff, live


def export_check(db: Session, tenant_id, pack_id) -> tuple[bool, list[str]]:
    return gate.export_allowed(*load_gate_inputs(db, tenant_id, pack_id), gate.STATEMENT_VERSION)


runner.HANDLERS["claimcheck"] = claimcheck_handler
runner.FAILURE_HOOKS["claimcheck"] = reset_pack_after_exhausted
