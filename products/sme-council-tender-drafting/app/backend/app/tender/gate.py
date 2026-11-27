"""The export gate (DESIGN 4.5): a pure function, no database and no AI, so it can be tested exhaustively (A6b).

`export_allowed` takes plain values (the dataclasses below; `load_gate_inputs` in claimcheck_store builds them from
rows) and returns (allowed, reasons). Each reason is "code: message". There is no override: a block is fixed by editing
or removing the text, or by re-checking.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

STATEMENT_VERSION = "v1"
PACK_STATES_BEFORE_CONFIRM = frozenset({"uploaded", "extracting", "review"})
# Allow-list (fail closed): export is legitimate only from these states. A new, misspelt or unknown status blocks.
PACK_STATES_EXPORTABLE = frozenset({"ready", "signed", "exported"})

_CITE = re.compile(r"\[E-(\d+)\]")


def count_words(text: str) -> int:
    """Words as the sign-off counts them: [E-n] markers excluded, gap markers included."""
    return sum(1 for w in _CITE.sub(" ", text).split() if any(c.isalnum() for c in w))


@dataclass(frozen=True)
class GatePack:
    status: str


@dataclass(frozen=True)
class GateReq:
    id: str
    kind: str
    status: str            # proposed | confirmed | removed
    word_limit: int | None


@dataclass(frozen=True)
class GateDraft:
    id: str
    requirement_id: str
    version: int
    text: str
    text_sha256: str
    check_sha256: str | None


@dataclass(frozen=True)
class GateClaim:
    draft_id: str
    verdict: str
    cited_ids: Sequence[int] = field(default_factory=tuple)


@dataclass(frozen=True)
class GateSignoff:
    statement_version: str
    drafts_digest: str


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def latest_drafts(drafts: Iterable[GateDraft]) -> dict[str, GateDraft]:
    out: dict[str, GateDraft] = {}
    for d in drafts:
        if d.requirement_id not in out or d.version > out[d.requirement_id].version:
            out[d.requirement_id] = d
    return out


def drafts_digest(requirements: Iterable[GateReq], drafts: Iterable[GateDraft]) -> str:
    """What a sign-off covers: every confirmed requirement (so an added or removed one changes it, and so does a changed
    word limit) and the text hash of each question's latest draft."""
    latest = latest_drafts(drafts)
    parts = []
    for r in sorted((r for r in requirements if r.status == "confirmed"), key=lambda r: r.id):
        d = latest.get(r.id)
        parts.append(f"{r.id}|{r.kind}|{r.word_limit or ''}|{(d.text_sha256 + ':' + str(d.version)) if d else ''}")
    return sha("\n".join(parts))


def export_allowed(pack: GatePack, requirements: Sequence[GateReq], drafts: Sequence[GateDraft],
                   claims: Sequence[GateClaim], signoff: GateSignoff | None, live_evidence_ids: Iterable[int],
                   statement_version: str = STATEMENT_VERSION) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    live = set(live_evidence_ids)
    if pack.status in PACK_STATES_BEFORE_CONFIRM:
        reasons.append("not_confirmed: the checklist has not been confirmed")
    elif pack.status not in PACK_STATES_EXPORTABLE:
        reasons.append(f"pack_not_ready: the pack is in state '{pack.status}', not one export is allowed from")
    questions = [r for r in requirements if r.status == "confirmed" and r.kind == "question"]
    latest = latest_drafts(drafts)
    by_draft: dict[str, list[GateClaim]] = {}
    for c in claims:
        by_draft.setdefault(c.draft_id, []).append(c)
    if not questions:
        reasons.append("no_questions: there are no confirmed questions to answer")
    for r in questions:
        d = latest.get(r.id)
        if d is None:
            reasons.append(f"missing_draft: question {r.id} has no draft")
            continue
        # the text hash is recomputed: a row whose text no longer matches its hash can never count as checked
        if d.check_sha256 is None or d.check_sha256 != d.text_sha256 or d.text_sha256 != sha(d.text):
            reasons.append(f"not_checked: the latest answer to question {r.id} has no claim check for its current text")
        mine = by_draft.get(d.id, [])
        bad = [c for c in mine if c.verdict != "supported"]  # unsupported, contradicted, unchecked or anything unknown
        if bad:
            reasons.append(f"claims_blocked: {len(bad)} claim(s) in question {r.id} are not supported by evidence")
        cited = {int(n) for n in _CITE.findall(d.text)} | {int(n) for c in mine for n in c.cited_ids}
        gone = sorted(cited - live)
        if gone:
            reasons.append("evidence_removed: evidence "
                           + ", ".join(f"E-{n}" for n in gone) + f" cited in question {r.id} was removed; re-check")
        if r.word_limit is not None and count_words(d.text) > r.word_limit:
            reasons.append(f"over_limit: the answer to question {r.id} is over its {r.word_limit}-word limit")
    if signoff is None:
        reasons.append("no_signoff: the pack has not been signed off")
    else:
        if signoff.statement_version != statement_version:
            reasons.append("statement_changed: the responsibility statement changed since sign-off; sign off again")
        if signoff.drafts_digest != drafts_digest(requirements, drafts):
            reasons.append("digest_mismatch: the answers or the checklist changed since sign-off; sign off again")
    return (not reasons, reasons)


def reason_codes(reasons: Iterable[str]) -> set[str]:
    return {r.split(":", 1)[0] for r in reasons}
