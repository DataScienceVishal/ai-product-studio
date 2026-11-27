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
from ..tender_models import DocumentPage, EvidenceItem, SourceDocument, TenderPack
from ..textsafe import StrippedLine

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
