"""Tender packs, document upload and the evidence library (DESIGN 4.1, 4.2, 5). Everything is scoped to the caller's
tenant through app.scoped; another tenant's row is a 404 like a missing one."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
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
from ..tender import extract as _extract  # noqa: F401  (registers the extract handler)
from ..tender_models import AITask, DocumentPage, EvidenceItem, Requirement, SourceDocument, TenderPack
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
    rows = db.scalars(scoped(SourceDocument, me.tenant.id).where(SourceDocument.kind == "evidence")
                      .order_by(SourceDocument.created_at)).all()
    return {"documents": [doc_out(d) for d in rows]}


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: uuid.UUID, me: Current = Depends(current), db: Session = Depends(get_db)):
    delete_row(db, get_scoped(db, SourceDocument, me.tenant.id, document_id, "document"))
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
    if db.scalar(scoped(SourceDocument, tenant_id).where(SourceDocument.sha256 == sha)) is not None:
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
    if db.scalar(scoped(SourceDocument, tenant_id).where(SourceDocument.sha256 == sha)) is not None:
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


@router.post("/packs/{pack_id}/requirements", status_code=201)
def add_requirement(pack_id: uuid.UUID, body: RequirementIn, me: Current = Depends(current), db: Session = Depends(get_db)):
    pack = get_scoped(db, TenderPack, me.tenant.id, pack_id, "tender pack")
    if pack.status in ("signed", "exported"):
        raise AppError(409, "pack_locked", "This pack is already signed off.")
    seq = (db.scalar(select(func.coalesce(func.max(Requirement.seq), 0)).where(
        Requirement.tenant_id == me.tenant.id, Requirement.pack_id == pack_id)) or 0) + 1
    r = Requirement(tenant_id=me.tenant.id, pack_id=pack_id, seq=seq, origin="user", status="proposed", edited_by=me.user.id,
                    **body.model_dump())
    db.add(r)
    db.commit()
    return req_out(r)


@router.patch("/requirements/{req_id}")
def edit_requirement(req_id: uuid.UUID, body: RequirementPatch, me: Current = Depends(current), db: Session = Depends(get_db)):
    """The model's original item stays in model_json; the row keeps origin=model and records who edited it."""
    r = get_scoped(db, Requirement, me.tenant.id, req_id, "requirement")
    pack = get_scoped(db, TenderPack, me.tenant.id, r.pack_id, "tender pack")
    if pack.status in ("signed", "exported"):
        raise AppError(409, "pack_locked", "This pack is already signed off.")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        if v is None and k in ("text", "kind", "status", "pass_fail", "ref"):
            raise AppError(422, "invalid_input", f"{k} cannot be empty.")
        setattr(r, k, v)
    if set(changes) - {"status"}:
        r.edited_by = me.user.id
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
