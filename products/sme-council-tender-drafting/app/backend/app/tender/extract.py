"""S4 extraction: page chunks with overlap, the extract task, merge, and the checks that run after the model (DESIGN 4.4).

The model proposes; code checks. A quote that is not on its page makes the item amber (quote_verified=false), and a
limit the page states in words that disagrees with the model is flagged. Neither removes the item.
"""
from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import sessionmaker

from ..ai import AIUnavailable  # noqa: F401  (re-exported for callers that catch it)
from ..billing import ai_access
from ..deps import subscription_of
from ..errors import AppError
from ..tender_models import AITask, DocumentPage, Requirement, SourceDocument, TenderPack
from . import runner
from .llm import AppBudget, TaskSpec, run_task

log = logging.getLogger("app.tender.extract")

CHUNK_PAGES = 5      # pages per chunk (about 6k tokens)
OVERLAP_PAGES = 1    # the last page of a chunk is the first of the next
_settings = None


def configure(settings) -> None:
    global _settings
    _settings = settings


class ExtractItem(BaseModel):
    ref: str
    kind: str
    text: str
    word_limit: Optional[int]
    page_limit: Optional[int]
    marks: Optional[int]
    weight_pct: Optional[int]
    pass_fail: Optional[bool]
    deadline: Optional[str]
    source_page: int
    source_quote: str


class ExtractOutput(BaseModel):
    items: list[ExtractItem]


EXTRACT_SPEC = TaskSpec(
    "extract", "v1",
    "You read UK public-sector tender documents. List every question the bidder must answer, every mandatory or "
    "pass/fail requirement and every deadline. For each give the buyer's reference, its exact words as source_quote "
    "(copied from the page), the page number, and any stated word or page limit, marks or weighting. Do not invent items.",
    ExtractOutput, 6000, "low")


def make_chunks(pages: list[tuple[int, str]], size: int = CHUNK_PAGES, overlap: int = OVERLAP_PAGES) -> list[list[tuple[int, str]]]:
    """pages is [(page_no, text)] in order. Chunks share `overlap` pages so a requirement on a boundary is seen whole."""
    if not pages:
        return []
    step = max(size - overlap, 1)
    chunks, i = [], 0
    while True:
        chunks.append(pages[i:i + size])
        if i + size >= len(pages):
            return chunks
        i += step


def chunk_text(chunk: list[tuple[int, str]]) -> str:
    return "\n\n".join(f"[page {n}]\n{t}" for n, t in chunk)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).casefold()
    s = s.replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = re.sub(r"[‐-―\-]+", "-", s)
    return re.sub(r"\s+", " ", s).strip()


def quote_ok(quote: str, page_text: str) -> bool:
    q = norm(quote)
    return bool(q) and q in norm(page_text)


_LIMIT = re.compile(r"(?:maximum(?: of)?|max\.?|no more than|not exceed(?:ing)?|up to|limit(?:ed)? to)\s+(\d[\d,]*)\s+words", re.I)


def stated_word_limit(page_text: str, near: str = "") -> int | None:
    """The word limit the page states in words, preferring the sentence that holds the item's own quote."""
    text = page_text
    if near:
        i = norm(page_text).find(norm(near)[:60])
        if i >= 0:
            window = page_text[max(0, i - 200): i + len(near) + 400]
            m = _LIMIT.search(window)
            if m:
                return int(m.group(1).replace(",", ""))
    m = _LIMIT.search(text)
    return int(m.group(1).replace(",", "")) if m else None


def _trigrams(s: str) -> set[str]:
    s = f"  {norm(s)} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def similarity(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def merge_items(items: list[dict]) -> list[dict]:
    """Drop duplicates seen in overlap pages: the same non-empty ref, or text with trigram similarity >= 0.9 on the
    same or adjacent pages. The first one seen wins."""
    kept: list[dict] = []
    for it in items:
        dup = False
        for k in kept:
            same_ref = bool(it["ref"]) and it["ref"].strip().casefold() == k["ref"].strip().casefold()
            near = abs(it["source_page"] - k["source_page"]) <= 1 and similarity(it["text"], k["text"]) >= 0.9
            if same_ref or near:
                dup = True
                break
        if not dup:
            kept.append(it)
    return kept


def check_item(item: dict, pages: dict[int, str]) -> tuple[bool, list[str]]:
    """(quote_verified, flags) for one model item against the stored pages."""
    page_text = pages.get(item["source_page"], "")
    verified = quote_ok(item["source_quote"], page_text)
    flags = []
    if item.get("word_limit") is not None or stated_word_limit(page_text, item["source_quote"]) is not None:
        stated = stated_word_limit(page_text, item["source_quote"])
        if stated is not None and item.get("word_limit") != stated:
            flags.append("limit_mismatch")
    return verified, flags


def extract_handler(sessions: sessionmaker, task: AITask, heartbeat, provider) -> tuple[int, int]:
    """Runs every chunk of the pack's tender documents through the extract task, then rewrites the proposed list."""
    settings = _settings
    with sessions() as db:
        sub = subscription_of(db, task.tenant_id)
        allowed = ai_access(sub, settings)
        doc_ids = list(db.scalars(select(SourceDocument.id).where(
            SourceDocument.tenant_id == task.tenant_id, SourceDocument.pack_id == task.pack_id,
            SourceDocument.kind == "tender").order_by(SourceDocument.created_at)))
        per_doc = {d: [(p.page_no, p.text) for p in db.scalars(select(DocumentPage).where(
            DocumentPage.tenant_id == task.tenant_id, DocumentPage.document_id == d).order_by(DocumentPage.page_no))]
            for d in doc_ids}
        budget = AppBudget.for_subscription(sessions, task.tenant_id, sub, settings, "extract")
        db.rollback()
    if not allowed:
        raise AppError(402, "plan_required", "Your trial or plan has ended.")
    tin = tout = 0
    collected: list[tuple[uuid.UUID, dict, dict]] = []
    for doc_id in doc_ids:
        pages = dict(per_doc[doc_id])
        found = []
        for chunk in make_chunks(per_doc[doc_id]):
            res = run_task(EXTRACT_SPEC, {"chunk": chunk_text(chunk)}, task.tenant_id, budget, provider=provider,
                           sessions=sessions, before_call=heartbeat)
            tin, tout = tin + res.input_tokens, tout + res.output_tokens
            found += [i.model_dump(mode="json") for i in res.output.items]
        for it in merge_items(found):
            collected.append((doc_id, it, pages))
    with sessions() as db:
        db.execute(delete(Requirement).where(Requirement.tenant_id == task.tenant_id, Requirement.pack_id == task.pack_id,
                                             Requirement.origin == "model", Requirement.status == "proposed"))
        base = db.scalar(select(func.coalesce(func.max(Requirement.seq), 0)).where(
            Requirement.tenant_id == task.tenant_id, Requirement.pack_id == task.pack_id)) or 0
        for n, (doc_id, it, pages) in enumerate(collected, 1):
            verified, flags = check_item(it, pages)
            kind = it["kind"] if it["kind"] in ("question", "mandatory", "deadline", "other") else "other"
            db.add(Requirement(tenant_id=task.tenant_id, pack_id=task.pack_id, seq=base + n, ref=it["ref"][:40], kind=kind,
                               text=it["text"], word_limit=it["word_limit"], page_limit=it["page_limit"], marks=it["marks"],
                               weight_pct=it["weight_pct"], pass_fail=bool(it["pass_fail"]), source_document_id=doc_id,
                               source_page=it["source_page"], source_quote=it["source_quote"], quote_verified=verified,
                               origin="model", status="proposed", model_json=it, flags=flags))
        db.execute(update(TenderPack).where(TenderPack.tenant_id == task.tenant_id, TenderPack.id == task.pack_id)
                   .values(status="review"))
        db.commit()
    return tin, tout


runner.HANDLERS["extract"] = extract_handler
