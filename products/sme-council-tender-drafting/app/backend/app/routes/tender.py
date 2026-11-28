"""Tender packs, document upload and the evidence library (DESIGN 4.1, 4.2, 5). Everything is scoped to the caller's
tenant through app.scoped; another tenant's row is a 404 like a missing one."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Current, current
from ..errors import AppError
from ..scoped import get_scoped, scoped
from ..tender import ingest
from ..tender.chunking import chunk_pages
from ..tender.evidence import next_numbers, search_evidence
from ..tender.service import delete_row
from ..tender import draft as _draft
from ..tender import claimcheck as _check
from ..tender import extract as _extract  # noqa: F401  (registers the extract and draft handlers)
from ..tender import gate
from ..tender import export as _export
from ..tender_models import Claim as _Claim, ExportRecord, Signoff as _Signoff, AITask, Draft, DocumentPage, EvidenceItem, Requirement, SourceDocument, TenderPack
from ..textsafe import FreeText, StrippedLine

log = logging.getLogger("app.tender")
router = APIRouter(prefix="/api", tags=["tender"])
CATEGORIES = {"policy", "case_study", "accreditation", "social_value", "company_facts", "past_bid"}


class PackIn(BaseModel):
    title: StrippedLine = Field(min_length=1, max_length=200)
    buyer: StrippedLine = Field(default="", max_length=200)
    deadline: datetime | None = None


def pack_out(p: TenderPack) -> dict:
    return {"id": str(p.id), "title": p.title, "buyer": p.buyer, "status": p.status,
            "deadline": p.deadline.isoformat() if p.deadline else None, "created_at": p.created_at.isoformat()}


def doc_out(d: SourceDocument) -> dict:
    return {"id": str(d.id), "kind": d.kind, "pack_id": str(d.pack_id) if d.pack_id else None, "filename": d.filename,
            "category": d.category, "mime": d.mime, "page_count": d.page_count, "page_mode": d.page_mode,
            "size_bytes": d.size_bytes, "status": d.status, "created_at": d.created_at.isoformat()}


@router.post("/packs", status_code=201)
def create_pack(body: PackIn, me: Current = Depends(current), db: Session = Depends(get_db)):
    pack = TenderPack(tenant_id=me.tenant.id, title=body.title, buyer=body.buyer, deadline=body.deadline)
    db.add(pack)
    db.commit()
    return pack_out(pack)


@router.get("/packs")
def list_packs(me: Current = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(scoped(TenderPack, me.tenant.id).order_by(TenderPack.created_at.desc())).all()
    return {"packs": [pack_out(p) for p in rows]}


@router.delete("/packs/{pack_id}", status_code=204)
def delete_pack(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    delete_row(db, get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack"))
    return Response(status_code=204)


@router.get("/packs/{pack_id}/documents")
def list_pack_documents(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    rows = db.scalars(scoped(SourceDocument, me.tenant.id).where(SourceDocument.pack_id == pack_id)
                      .order_by(SourceDocument.created_at)).all()
    return {"documents": [doc_out(d) for d in rows]}


@router.get("/evidence/documents")
def list_evidence_documents(me: Current = Depends(current), db: Session = Depends(get_db)):
    rows = db.scalars(scoped(SourceDocument, me.tenant.id).where(SourceDocument.kind == "evidence",
                                                                 SourceDocument.deleted_at.is_(None))
                      .order_by(SourceDocument.created_at)).all()
    return {"documents": [doc_out(d) for d in rows]}


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    doc = get_scoped(db, SourceDocument, me.tenant.id, document_id, "document")
    if doc.deleted_at is not None:
        raise AppError(404, "not_found", "That document doesn't exist.")
    if doc.kind == "evidence":
        # Soft delete (T-186 F10): the passages stay for the claim appendix and the audit trail, but nothing can retrieve or
        # cite them, and the export gate treats them as deleted. Packs that were ready have to be checked again.
        now = datetime.now(timezone.utc)
        numbers = list(db.scalars(select(EvidenceItem.display_no).where(
            EvidenceItem.tenant_id == me.tenant.id, EvidenceItem.document_id == doc.id)))
        doc.deleted_at = now
        db.execute(update(EvidenceItem).where(EvidenceItem.tenant_id == me.tenant.id, EvidenceItem.document_id == doc.id,
                                              EvidenceItem.deleted_at.is_(None)).values(deleted_at=now))
        if numbers:
            db.execute(text(
                "UPDATE tender_packs SET status = 'drafting' WHERE tenant_id = :t AND status = 'ready' AND id IN ("
                "SELECT r.pack_id FROM requirements r JOIN drafts d ON d.tenant_id = r.tenant_id AND d.requirement_id = r.id "
                "WHERE r.tenant_id = :t AND d.cited_ids && CAST(:n AS integer[]))"), {"t": me.tenant.id, "n": numbers})
        db.commit()
        return Response(status_code=204)
    delete_row(db, doc)
    return Response(status_code=204)


@router.get("/evidence/search")
def evidence_search(q: str = Query(min_length=1, max_length=2000), me: Current = Depends(current),
                    db: Session = Depends(get_db)):
    hits = search_evidence(db, me.tenant.id, q)
    return {"results": [{"id": str(h.id), "label": f"E-{h.display_no}", "display_no": h.display_no,
                         "document_id": str(h.document_id), "document": h.document_name, "page_from": h.page_from,
                         "page_to": h.page_to, "heading": h.heading, "text": h.text, "rank": round(h.rank, 4),
                         "score": round(h.score, 4)} for h in hits]}


@router.post("/packs/{pack_id}/documents", status_code=201)
def upload_tender_document(pack_id: uuid.UUID, request: Request, file: UploadFile = File(...),
                           me: Current = Depends(current), db: Session = Depends(get_db)):
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    return _ingest(request, db, me, file, kind="tender", pack=pack, category=None)


@router.post("/evidence/documents", status_code=201)
def upload_evidence_document(request: Request, file: UploadFile = File(...), category: str = Form("policy"),
                             me: Current = Depends(current), db: Session = Depends(get_db)):
    if category not in CATEGORIES:
        raise AppError(422, "invalid_input", "Choose a category: " + ", ".join(sorted(CATEGORIES)) + ".")
    return _ingest(request, db, me, file, kind="evidence", pack=None, category=category)


def _ingest(request: Request, db: Session, me: Current, file: UploadFile, *, kind: str, pack: TenderPack | None,
            category: str | None) -> dict:
    s = request.app.state.settings
    tenant_id, user_id, pack_id = me.tenant.id, me.user.id, pack.id if pack else None  # plain ids: the transaction ends below
    request.app.state.limiter.check(f"upload:{tenant_id}", s.uploads_per_hour, 3600.0)
    data = file.file.read(s.upload_max_bytes + 1)
    if len(data) > s.upload_max_bytes:
        raise AppError(413, "too_large", f"That file is over the {s.upload_max_bytes // (1024 * 1024)} MB limit.")
    if not data:
        raise AppError(422, "empty_file", "That file is empty.")
    sha = hashlib.sha256(data).hexdigest()
    if db.scalar(scoped(SourceDocument, tenant_id).where(SourceDocument.sha256 == sha,
                                                         SourceDocument.deleted_at.is_(None))) is not None:
        raise AppError(409, "duplicate_document", "You've already uploaded that file.")
    _check_pack_size(db, s, tenant_id, pack_id, len(data))
    db.rollback()  # end the read transaction: no pooled connection is held while the parser runs (up to 45 s)
    try:
        parsed = ingest.parse_upload(data, allow_text=kind == "evidence", max_pages=s.upload_max_pages)
    except ingest.Refused as refusal:
        log.info("upload refused", extra={"code": refusal.code, "kind": kind})
        raise AppError(refusal.status, refusal.code, refusal.message)
    if kind == "tender" and any(ingest.is_image_only_page(parsed.kind, p["text"]) for p in parsed.pages):
        raise AppError(*_refusal("image_only"))
    # Serialise this tenant's uploads for the checks and the write, so the size and page caps cannot be overshot by
    # parallel requests (the lock is released at commit or rollback).
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"upload:{tenant_id}"})
    if db.scalar(scoped(SourceDocument, tenant_id).where(SourceDocument.sha256 == sha,
                                                         SourceDocument.deleted_at.is_(None))) is not None:
        raise AppError(409, "duplicate_document", "You've already uploaded that file.")
    _check_pack_size(db, s, tenant_id, pack_id, len(data))
    since = datetime.now(timezone.utc) - timedelta(days=1)
    pages_today = db.scalar(select(func.coalesce(func.sum(SourceDocument.page_count), 0))
                            .where(SourceDocument.tenant_id == tenant_id, SourceDocument.created_at > since))
    if pages_today + len(parsed.pages) > s.upload_pages_per_day:
        raise AppError(429, "page_limit", "You've reached today's page limit for uploads. Try again tomorrow.")
    doc = SourceDocument(tenant_id=tenant_id, kind=kind, pack_id=pack_id,
                         filename=ingest.clean_filename(file.filename), category=category, sha256=sha, mime=parsed.mime,
                         page_count=len(parsed.pages), page_mode=parsed.page_mode, size_bytes=len(data),
                         status="parsed", created_by=user_id)
    db.add(doc)
    try:
        db.flush()
        db.add_all(DocumentPage(tenant_id=tenant_id, document_id=doc.id, page_no=i, text=p["text"],
                                char_count=len(p["text"]), image_only=ingest.is_image_only_page(parsed.kind, p["text"]))
                  for i, p in enumerate(parsed.pages, start=1))
        passages = chunk_pages(parsed.pages) if kind == "evidence" else []
        numbers = next_numbers(db, tenant_id, len(passages))
        db.add_all(EvidenceItem(tenant_id=tenant_id, display_no=no, document_id=doc.id, page_from=p.page_from,
                                page_to=p.page_to, heading=p.heading, text=p.text)
                   for no, p in zip(numbers, passages))
        db.commit()
    except IntegrityError:  # backstop: the unique (tenant, sha256) decides
        db.rollback()
        raise AppError(409, "duplicate_document", "You've already uploaded that file.")
    log.info("document parsed", extra={"document_id": str(doc.id), "kind": kind, "pages": len(parsed.pages),
                                       "passages": len(passages)})
    return doc_out(doc) | {"passages": len(passages)}


def _check_pack_size(db: Session, s, tenant_id: uuid.UUID, pack_id: uuid.UUID | None, size: int) -> None:
    if pack_id is None:
        return
    used = db.scalar(select(func.coalesce(func.sum(SourceDocument.size_bytes), 0))
                     .where(SourceDocument.tenant_id == tenant_id, SourceDocument.pack_id == pack_id))
    if used + size > s.upload_max_pack_bytes:
        raise AppError(413, "pack_too_large", "That would take this pack over its size limit.")


def _refusal(code: str) -> tuple[int, str, str]:
    status, message = ingest.REFUSALS[code]
    return status, code, message



# ---------- extraction and the checklist (S4) ----------
class RequirementIn(BaseModel):
    ref: StrippedLine = Field(default="", max_length=40)
    kind: str = Field(default="question", pattern="^(question|mandatory|deadline|other)$")
    text: FreeText = Field(min_length=1, max_length=4000)
    word_limit: int | None = Field(default=None, ge=1, le=100000)
    page_limit: int | None = Field(default=None, ge=1, le=1000)
    marks: int | None = Field(default=None, ge=0, le=100000)
    weight_pct: int | None = Field(default=None, ge=0, le=100)
    pass_fail: bool = False


class RequirementPatch(BaseModel):
    ref: StrippedLine | None = Field(default=None, max_length=40)
    kind: str | None = Field(default=None, pattern="^(question|mandatory|deadline|other)$")
    text: FreeText | None = Field(default=None, min_length=1, max_length=4000)
    word_limit: int | None = Field(default=None, ge=1, le=100000)
    page_limit: int | None = Field(default=None, ge=1, le=1000)
    marks: int | None = Field(default=None, ge=0, le=100000)
    weight_pct: int | None = Field(default=None, ge=0, le=100)
    pass_fail: bool | None = None
    status: str | None = Field(default=None, pattern="^(proposed|confirmed|removed)$")


def req_out(r: Requirement) -> dict:
    return {"id": str(r.id), "pack_id": str(r.pack_id), "seq": r.seq, "ref": r.ref, "kind": r.kind, "text": r.text,
            "word_limit": r.word_limit, "page_limit": r.page_limit, "marks": r.marks, "weight_pct": r.weight_pct,
            "pass_fail": r.pass_fail, "source_document_id": str(r.source_document_id) if r.source_document_id else None,
            "source_page": r.source_page, "source_quote": r.source_quote, "quote_verified": r.quote_verified,
            "origin": r.origin, "status": r.status, "flags": list(r.flags or []), "edited": r.edited_by is not None}


def task_out(t: AITask) -> dict:
    return {"id": str(t.id), "kind": t.kind, "status": t.status, "error_code": t.error_code, "attempts": t.attempts}


@router.post("/packs/{pack_id}/extract", status_code=202)
def queue_extract(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """Idempotent: a queued or running extraction for the pack is returned instead of a second one."""
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    if pack.status not in ("uploaded", "extracting", "review"):  # drafting and later: the checklist is confirmed
        raise AppError(409, "pack_locked", "The checklist for this pack is already confirmed.")
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"extract:{pack_id}"})
    live = db.scalar(scoped(AITask, me.tenant.id).where(AITask.pack_id == pack_id, AITask.kind == "extract",
                                                        AITask.status.in_(("queued", "running"))))
    if live is not None:
        return task_out(live)
    if not db.scalar(select(func.count()).select_from(SourceDocument).where(
            SourceDocument.tenant_id == me.tenant.id, SourceDocument.pack_id == pack_id)):
        raise AppError(409, "no_documents", "Upload the tender document first.")
    task = AITask(tenant_id=me.tenant.id, pack_id=pack_id, kind="extract")
    db.add(task)
    pack.status = "extracting"
    db.commit()
    return task_out(task)


@router.get("/packs/{pack_id}/status")
def pack_status(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    tasks = db.scalars(scoped(AITask, me.tenant.id).where(AITask.pack_id == pack_id).order_by(AITask.created_at.desc()).limit(10))
    return {"pack": pack_out(pack), "tasks": [task_out(t) for t in tasks]}


@router.get("/packs/{pack_id}/requirements")
def list_requirements(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    rows = db.scalars(scoped(Requirement, me.tenant.id).where(Requirement.pack_id == pack_id,
                                                              Requirement.status != "removed").order_by(Requirement.seq))
    return {"requirements": [req_out(r) for r in rows]}


def _lock_pack(db: Session, tenant_id: uuid.UUID, pack_id: uuid.UUID) -> TenderPack:
    """Take the pack row FOR UPDATE and re-read it, so the status checked next is the committed one: a sign-off that commits
    first is seen (pack_locked), and one that comes later waits for this write. FOR UPDATE, not FOR SHARE, because these
    routes then update the row (reopen_pack) and two sharers upgrading at once would deadlock."""
    return db.scalar(scoped(TenderPack, tenant_id).where(TenderPack.id == pack_id).with_for_update()
                     .execution_options(populate_existing=True))


@router.post("/packs/{pack_id}/requirements", status_code=201)
def add_requirement(pack_id: uuid.UUID, body: RequirementIn, me: Current = Depends(current), db: Session = Depends(get_db)):
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    # Lock the pack row first so a concurrent add, sign-off or extraction write waits; the unique (tenant, pack, seq) is the backstop.
    pack = _lock_pack(db, me.tenant.id, pack_id)
    if pack.status in ("signed", "exported"):
        raise AppError(409, "pack_locked", "This pack is already signed off.")
    seq = (db.scalar(select(func.coalesce(func.max(Requirement.seq), 0)).where(
        Requirement.tenant_id == me.tenant.id, Requirement.pack_id == pack_id)) or 0) + 1
    r = Requirement(tenant_id=me.tenant.id, pack_id=pack_id, seq=seq, origin="user", status="proposed", edited_by=me.user.id,
                    **body.model_dump())
    db.add(r)
    _check.reopen_pack(db, me.tenant.id, pack_id)
    db.commit()
    return req_out(r)


@router.patch("/requirements/{req_id}")
def edit_requirement(req_id: uuid.UUID, body: RequirementPatch, me: Current = Depends(current), db: Session = Depends(get_db)):
    """The model's original item stays in model_json; the row keeps origin=model and records who edited it."""
    r = get_scoped(db, Requirement, me.tenant.id, req_id, "requirement")
    get_scoped(db, TenderPack, me.tenant.id, r.pack_id, "tender pack")
    pack = _lock_pack(db, me.tenant.id, r.pack_id)
    if pack.status in ("signed", "exported"):
        raise AppError(409, "pack_locked", "This pack is already signed off.")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        if v is None and k in ("text", "kind", "status", "pass_fail", "ref"):
            raise AppError(422, "invalid_input", f"{k} cannot be empty.")
        setattr(r, k, v)
    if set(changes) - {"status"}:
        r.edited_by = me.user.id
    _check.reopen_pack(db, me.tenant.id, pack.id)
    db.commit()
    return req_out(r)


@router.post("/packs/{pack_id}/confirm")
def confirm_checklist(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    if pack.status not in ("uploaded", "review", "drafting"):  # uploaded: a list written by hand
        raise AppError(409, "not_ready", "Run the extraction and review the list first.")
    rows = list(db.scalars(scoped(Requirement, me.tenant.id).where(Requirement.pack_id == pack_id, Requirement.status == "proposed")))
    if not db.scalar(select(func.count()).select_from(Requirement).where(
            Requirement.tenant_id == me.tenant.id, Requirement.pack_id == pack_id, Requirement.status != "removed")):
        raise AppError(409, "empty_checklist", "There is nothing to confirm yet.")
    for r in rows:
        r.status = "confirmed"
    pack.status, pack.confirmed_by, pack.confirmed_at = "drafting", me.user.id, datetime.now(timezone.utc)
    db.commit()
    return {"confirmed": len(rows), "pack": pack_out(pack)}


# ---------- drafting (S5) ----------
DRAFT_PACK_STATES = _draft.DRAFT_PACK_STATES


class DraftIn(BaseModel):
    text: FreeText = Field(min_length=1, max_length=30000)
    base_version: int | None = Field(default=None, ge=0)  # the version the editor started from; stale is 409


def draft_out(d: Draft) -> dict:
    return {"id": str(d.id), "requirement_id": str(d.requirement_id), "version": d.version, "text": d.text,
            "word_count": d.word_count, "word_limit": d.word_limit_snapshot, "retrieved_ids": list(d.retrieved_ids),
            "cited_ids": list(d.cited_ids), "outside_ids": list(d.outside_ids), "gap_count": d.gap_count,
            "flags": list(d.flags or []), "author": d.author, "status": d.status, "model": d.model,
            "created_at": d.created_at.isoformat()}


def _question(db: Session, me: Current, req_id: uuid.UUID) -> tuple[Requirement, TenderPack]:
    r = get_scoped(db, Requirement, me.tenant.id, req_id, "requirement")
    return r, get_scoped(db, TenderPack, me.tenant.id, r.pack_id, "tender pack")


def _queue_draft(db: Session, me: Current, pack: TenderPack, target: uuid.UUID | None) -> dict:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"draft:{pack.id}:{target}"})
    live = db.scalar(scoped(AITask, me.tenant.id).where(
        AITask.pack_id == pack.id, AITask.kind == "draft", AITask.status.in_(("queued", "running")),
        AITask.target_id.is_(None) if target is None else AITask.target_id == target))
    if live is not None:
        return task_out(live)
    task = AITask(tenant_id=me.tenant.id, pack_id=pack.id, kind="draft", target_id=target)
    db.add(task)
    db.commit()
    return task_out(task)


@router.post("/packs/{pack_id}/draft", status_code=202)
def queue_draft(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """Draft every confirmed question that has no draft yet. Idempotent while a pack-wide task is queued or running."""
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    if pack.status not in DRAFT_PACK_STATES:
        raise AppError(409, "not_ready", "Confirm the checklist first." if pack.status in ("uploaded", "extracting", "review")
                       else "This pack is already signed off.")
    if not _draft.draftable(db, me.tenant.id, pack_id, None):
        raise AppError(409, "nothing_to_draft", "Every question already has a draft. Redraft one if you want a new version.")
    return _queue_draft(db, me, pack, None)


@router.post("/requirements/{req_id}/redraft", status_code=202)
def redraft(req_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    r, pack = _question(db, me, req_id)
    if pack.status not in DRAFT_PACK_STATES:
        raise AppError(409, "not_ready", "Confirm the checklist first." if pack.status in ("uploaded", "extracting", "review")
                       else "This pack is already signed off.")
    if r.status != "confirmed" or r.kind != "question":
        raise AppError(409, "not_draftable", "Only a confirmed question can be drafted.")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    made = db.scalar(select(func.count()).select_from(Draft).where(
        Draft.tenant_id == me.tenant.id, Draft.requirement_id == req_id, Draft.author == "ai", Draft.created_at > since))
    queued = db.scalar(select(func.count()).select_from(AITask).where(
        AITask.tenant_id == me.tenant.id, AITask.kind == "draft", AITask.target_id == req_id,
        AITask.status.in_(("queued", "running"))))
    if not queued and made >= _draft.REDRAFTS_PER_REQUIREMENT_PER_DAY:
        raise AppError(429, "redraft_limit", "You've redrafted this question 5 times today. Edit it by hand or try tomorrow.")
    return _queue_draft(db, me, pack, req_id)


@router.get("/requirements/{req_id}/evidence")
def requirement_evidence(req_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """What retrieval finds for the question, as drafting would see it."""
    r, _ = _question(db, me, req_id)
    hits = search_evidence(db, me.tenant.id, r.text, limit=_draft.APP_PASSAGES, min_score=_draft.RETRIEVAL_FLOOR)
    return {"results": [{"id": str(h.id), "label": f"E-{h.display_no}", "display_no": h.display_no, "document": h.document_name,
                         "page_from": h.page_from, "page_to": h.page_to, "heading": h.heading, "text": h.text,
                         "rank": round(h.rank, 4), "score": round(h.score, 4)} for h in hits],
            "message": None if hits else "No evidence found"}


@router.get("/requirements/{req_id}/draft")
def get_draft(req_id: uuid.UUID, version: int | None = Query(default=None, ge=1), me: Current = Depends(current),
              db: Session = Depends(get_db)):
    req, _ = _question(db, me, req_id)
    rows = list(db.scalars(scoped(Draft, me.tenant.id).where(Draft.requirement_id == req_id).order_by(Draft.version.desc())))
    chosen = next((d for d in rows if version is None or d.version == version), None)
    if version is not None and chosen is None:
        raise AppError(404, "not_found", "That version doesn't exist.")
    return {"requirement": req_out(req), "draft": draft_out(chosen) if chosen else None,
            "versions": [{"version": d.version, "author": d.author, "word_count": d.word_count,
                          "created_at": d.created_at.isoformat()} for d in rows]}


@router.put("/requirements/{req_id}/draft", status_code=201)
def edit_draft(req_id: uuid.UUID, body: DraftIn, me: Current = Depends(current), db: Session = Depends(get_db)):
    """A user edit is a new version (author=user); earlier versions are kept. The text is unchecked until re-checked."""
    r, pack = _question(db, me, req_id)
    pack = _lock_pack(db, me.tenant.id, pack.id)  # before the status check: a concurrent sign-off is seen or waits
    if pack.status in ("signed", "exported"):
        raise AppError(409, "pack_locked", "This pack is already signed off.")
    if r.status != "confirmed" or r.kind != "question":
        raise AppError(409, "not_draftable", "Only a confirmed question can be drafted.")
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"draft:{req_id}"})
    latest = db.scalar(scoped(Draft, me.tenant.id).where(Draft.requirement_id == req_id).order_by(Draft.version.desc()).limit(1))
    if body.base_version is not None and body.base_version != (latest.version if latest else 0):
        raise AppError(409, "stale_version", "This answer changed since you opened it. Reload and edit the latest version.")
    retrieved = list(latest.retrieved_ids) if latest else []
    cited, outside, gaps = _draft.analyse(body.text, set(retrieved))
    d = _draft.Drafted(body.text, cited, outside, gaps, ["citation_outside_set"] if outside else [], retrieved)
    row = _draft.save_version(db, me.tenant.id, req_id, d, author="user", word_limit=r.word_limit)
    _check.reopen_pack(db, me.tenant.id, pack.id)  # an edit does not leave a `ready` pack ready (T-199)
    db.commit()
    return draft_out(row)


# ---------- claim check and the export gate (S6) ----------
@router.post("/packs/{pack_id}/check", status_code=202)
def queue_check(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """Check every latest draft that has no claim check for its current text. Idempotent while a check task is live."""
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    # T-201 item 8: the pack row is taken FOR UPDATE and re-read, so a sign-off or an edit that commits first is seen here.
    pack = db.scalar(scoped(TenderPack, me.tenant.id).where(TenderPack.id == pack_id).with_for_update()
                     .execution_options(populate_existing=True))
    if pack.status not in _check.CHECK_PACK_STATES:
        raise AppError(409, "not_ready", "Confirm the checklist first." if pack.status in ("uploaded", "extracting", "review")
                       else "This pack is already signed off.")
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), {"k": f"check:{pack_id}"})
    live = db.scalar(scoped(AITask, me.tenant.id).where(AITask.pack_id == pack_id, AITask.kind == "claimcheck",
                                                        AITask.status.in_(("queued", "running"))))
    if live is not None:
        return task_out(live)
    if not _check.to_check(db, me.tenant.id, pack_id, None):
        raise AppError(409, "nothing_to_check", "Every answer has been checked, or nothing has been drafted yet.")
    task = AITask(tenant_id=me.tenant.id, pack_id=pack_id, kind="claimcheck")
    db.add(task)
    pack.status = "checking"
    db.commit()
    return task_out(task)


@router.get("/packs/{pack_id}/export-check")
def export_check(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """The gate's verdict for the pack as it is now. The export route calls the same function on the server."""
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    allowed, reasons = _check.export_check(db, me.tenant.id, pack_id)
    return {"allowed": allowed, "reasons": reasons}


@router.get("/requirements/{req_id}/claims")
def get_claims(req_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    _question(db, me, req_id)
    d = db.scalar(scoped(Draft, me.tenant.id).where(Draft.requirement_id == req_id).order_by(Draft.version.desc()).limit(1))
    rows = [] if d is None else list(db.scalars(scoped(_Claim, me.tenant.id).where(_Claim.draft_id == d.id).order_by(_Claim.seq)))
    return {"draft_version": d.version if d else None, "checked": bool(d and d.check_sha256 == d.text_sha256),
            "claims": [{"seq": c.seq, "span": c.span, "kind": c.kind, "cited_ids": list(c.cited_ids), "verdict": c.verdict,
                        "evidence_quote": c.evidence_quote, "reason": c.reason, "decided_by": c.decided_by} for c in rows]}


# ---------- screens: one pack, cited passages, coverage and sign-off (S7) ----------
class SignoffIn(BaseModel):
    reviewer_name: StrippedLine = Field(min_length=1, max_length=120)
    accept_statement: bool = False
    statement_version: str = Field(default="", max_length=20)


@router.get("/packs/{pack_id}")
def get_pack(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    return pack_out(get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack"))


@router.get("/evidence/passages")
def evidence_passages(ids: str = Query(min_length=1, max_length=400), me: Current = Depends(current),
                      db: Session = Depends(get_db)):
    """The passages a draft cites, by E-number, with their document and page; soft-deleted ones are listed as removed
    without their text."""
    try:
        numbers = sorted({int(x) for x in ids.split(",") if x.strip()})[:100]
    except ValueError:
        raise AppError(422, "invalid_input", "ids must be numbers separated by commas.")
    rows = db.execute(select(EvidenceItem, SourceDocument.filename, SourceDocument.deleted_at).join(
        SourceDocument, (SourceDocument.tenant_id == EvidenceItem.tenant_id) & (SourceDocument.id == EvidenceItem.document_id))
        .where(EvidenceItem.tenant_id == me.tenant.id, EvidenceItem.display_no.in_(numbers))).all()
    out = []
    for e, filename, doc_deleted in rows:
        removed = e.deleted_at is not None or doc_deleted is not None
        out.append({"display_no": e.display_no, "label": f"E-{e.display_no}", "document": filename, "page_from": e.page_from,
                    "page_to": e.page_to, "heading": e.heading, "removed": removed, "text": "" if removed else e.text})
    return {"passages": sorted(out, key=lambda p: p["display_no"])}


@router.get("/packs/{pack_id}/coverage")
def coverage(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """One row per confirmed requirement, the gate's verdict and the sign-off state. It is a checklist, not a statement that
    the bid is compliant."""
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    reqs = list(db.scalars(scoped(Requirement, me.tenant.id).where(Requirement.pack_id == pack_id, Requirement.status == "confirmed")
                           .order_by(Requirement.seq)))
    rows = []
    for r in reqs:
        d = db.scalar(scoped(Draft, me.tenant.id).where(Draft.requirement_id == r.id).order_by(Draft.version.desc()).limit(1))
        verdicts: dict[str, int] = {}
        if d is not None:
            for v, n in db.execute(select(_Claim.verdict, func.count()).where(
                    _Claim.tenant_id == me.tenant.id, _Claim.draft_id == d.id).group_by(_Claim.verdict)):
                verdicts[v] = n
        question = r.kind == "question"
        words = d.word_count if d else None
        rows.append({"requirement_id": str(r.id), "seq": r.seq, "ref": r.ref, "kind": r.kind, "text": r.text,
                     "answered": (d is not None) if question else None, "words": words, "word_limit": r.word_limit,
                     "within_limit": None if words is None or r.word_limit is None else words <= r.word_limit,
                     "gaps": d.gap_count if d else 0, "checked": bool(d and d.check_sha256 == d.text_sha256),
                     "claims": verdicts, "covered": (d is not None) if question else True})
    allowed, reasons = _check.export_check(db, me.tenant.id, pack_id)
    so = db.scalar(scoped(_Signoff, me.tenant.id).where(_Signoff.pack_id == pack_id, _Signoff.voided_at.is_(None)).order_by(_Signoff.signed_at.desc()).limit(1))
    return {"pack": pack_out(pack), "rows": rows, "export": {"allowed": allowed, "reasons": reasons},
            "statement": {"version": gate.STATEMENT_VERSION, "text": gate.STATEMENT_TEXT},
            "signoff": None if so is None else {"reviewer_name": so.reviewer_name, "statement_version": so.statement_version,
                                                "signed_at": so.signed_at.isoformat()},
            "notice": "This is a checklist of what is answered and checked. It does not say the bid is compliant."}


@router.post("/packs/{pack_id}/signoff", status_code=201)
def sign_off(pack_id: uuid.UUID, body: SignoffIn, me: Current = Depends(current), db: Session = Depends(get_db)):
    """Record a named sign-off on a digest of the answers. The gate is re-run here on the server with the sign-off the
    request would create; if anything else blocks export, no sign-off is stored (T-201)."""
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    pack = db.scalar(scoped(TenderPack, me.tenant.id).where(TenderPack.id == pack_id).with_for_update()
                     .execution_options(populate_existing=True))  # T-201 item 8: a concurrent edit or check waits or is seen
    if not body.accept_statement or body.statement_version != gate.STATEMENT_VERSION:
        raise AppError(422, "statement_required", "Tick the responsibility statement as shown to sign off.")
    if pack.status in ("signed", "exported"):
        raise AppError(409, "already_signed", "This pack is already signed off.")
    if pack.status != "ready":
        raise AppError(409, "not_ready", "Every answer must be checked and clear before sign-off.")
    gpack, reqs, drafts, claims, _, live = _check.load_gate_inputs(db, me.tenant.id, pack_id)
    digest = gate.drafts_digest(reqs, drafts)
    allowed, reasons = gate.export_allowed(gpack, reqs, drafts, claims, gate.GateSignoff(gate.STATEMENT_VERSION, digest), live,
                                           gate.STATEMENT_VERSION)
    if not allowed:
        raise AppError(409, "export_blocked", "Sign-off is not possible yet: " + "; ".join(reasons))
    row = _Signoff(tenant_id=me.tenant.id, pack_id=pack_id, reviewer_user_id=me.user.id, reviewer_name=body.reviewer_name,
                   statement_version=gate.STATEMENT_VERSION, drafts_digest=digest)
    db.add(row)
    pack.status = "signed"
    db.commit()
    log.info("pack signed off", extra={"pack_id": str(pack_id)})
    return {"reviewer_name": row.reviewer_name, "statement_version": row.statement_version,
            "signed_at": row.signed_at.isoformat(), "pack": pack_out(pack)}


@router.get("/packs/{pack_id}/export")
def export_docx(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """The Word file, only if the gate passes on the rows as they are now (and the pack is signed, the sign-off valid and
    its digest current). The pack row is held FOR UPDATE (it is written below: signed becomes exported), so a reopen, an edit
    or a second export waits until the file and its record commit. GET on purpose (a plain browser download): it writes an
    audit row, but the session cookie is SameSite=Lax, so a cross-site request carries no session, and the frontend also
    sends X-Requested-With. Re-downloading from `exported` is allowed."""
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    pack = _lock_pack(db, me.tenant.id, pack_id)
    try:
        data, rows = _export.build(db, me.tenant.id, pack_id)
    except _export.ExportRefused as e:
        db.rollback()
        raise AppError(409, "export_blocked", "Export is blocked: " + "; ".join(e.reasons))
    db.add(ExportRecord(tenant_id=me.tenant.id, pack_id=pack_id, signoff_id=rows.signoff.id,
                        docx_sha256=_export.sha256(data), created_by=me.user.id))
    pack.status = "exported"
    db.commit()
    log.info("pack exported", extra={"pack_id": str(pack_id)})
    return Response(content=data, media_type=_export.DOCX_TYPE, headers={
        "Content-Disposition": f'attachment; filename="{_export.safe_filename(rows.pack.title)}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/packs/{pack_id}/reopen")
def reopen_signed_pack(pack_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    """Void the sign-off so the answers can be edited again. The sign-off row is kept (voided_at) for audit; the pack goes
    back to `ready`, and export is refused until it is signed again."""
    get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    pack = _lock_pack(db, me.tenant.id, pack_id)
    if pack.status not in ("signed", "exported"):
        raise AppError(409, "not_signed", "Only a signed-off pack can be reopened.")
    db.execute(update(_Signoff).where(_Signoff.tenant_id == me.tenant.id, _Signoff.pack_id == pack_id,
                                      _Signoff.voided_at.is_(None)).values(voided_at=datetime.now(timezone.utc)))
    # S8: not blindly `ready`: if a passage was removed meanwhile, or a claim is blocked, the pack goes to `drafting` (the
    # same test the end of a claim check uses), so the screens do not show "ready" for a pack the gate would block.
    db.flush()
    pack.status = "ready" if _check.pack_checked(db, me.tenant.id, pack_id) else "drafting"
    db.commit()
    log.info("pack reopened", extra={"pack_id": str(pack_id)})
    return {"pack": pack_out(pack)}
