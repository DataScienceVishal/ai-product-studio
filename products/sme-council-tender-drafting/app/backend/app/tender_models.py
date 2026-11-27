"""Tender-drafting tables (DESIGN section 3). Every row carries tenant_id; every child links to its parent with a
composite foreign key (tenant_id, parent_id) -> parent(tenant_id, id), so the database refuses a cross-tenant link
even if application code has a bug. Each parent therefore has UNIQUE (tenant_id, id)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (ARRAY, BigInteger, Boolean, Computed, DateTime, ForeignKey, ForeignKeyConstraint, Index,
                        Integer, String, Text, UniqueConstraint, Uuid, text)
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .models import _created, _id, _tenant, utcnow


def _child(name: str, col: str, parent: str, ondelete: str = "CASCADE") -> ForeignKeyConstraint:
    """(tenant_id, col) -> parent(tenant_id, id), cascading with the parent unless told otherwise."""
    return ForeignKeyConstraint(["tenant_id", col], [f"{parent}.tenant_id", f"{parent}.id"], ondelete=ondelete,
                                name=name)


class TenderPack(Base):
    __tablename__ = "tender_packs"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_tender_packs_tenant_id"),)
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    buyer: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created()


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_source_documents_tenant_id"),
                      UniqueConstraint("tenant_id", "sha256", name="uq_source_documents_tenant_sha256"),
                      _child("fk_source_documents_pack", "pack_id", "tender_packs"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # tender | evidence
    pack_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)  # null for evidence
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(20))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_mode: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf_page | docx_break | docx_block
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="parsed")  # parsed | rejected
    reject_reason: Mapped[str | None] = mapped_column(String(40))
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_no", name="uq_document_pages_doc_page"),
                      _child("fk_document_pages_document", "document_id", "source_documents"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_requirements_tenant_id"),
                      _child("fk_requirements_pack", "pack_id", "tender_packs"),
                      # NO ACTION, not CASCADE: deleting a source document that requirements still cite is refused, so it cannot
                      # silently wipe drafts and claims. (NO ACTION, not RESTRICT: the check does not depend on cascade trigger order; see migration 0014.)
                      _child("fk_requirements_document", "source_document_id", "source_documents", "NO ACTION"),
                      Index("ix_requirements_tenant_source_document", "tenant_id", "source_document_id"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    pack_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    ref: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # question | mandatory | deadline | other
    text: Mapped[str] = mapped_column(Text, nullable=False)
    word_limit: Mapped[int | None] = mapped_column(Integer)
    page_limit: Mapped[int | None] = mapped_column(Integer)
    marks: Mapped[int | None] = mapped_column(Integer)
    weight_pct: Mapped[int | None] = mapped_column(Integer)
    pass_fail: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    source_page: Mapped[int | None] = mapped_column(Integer)
    source_quote: Mapped[str | None] = mapped_column(Text)
    quote_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    origin: Mapped[str] = mapped_column(String(10), nullable=False, default="model")  # model | user
    edited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="proposed")  # proposed|confirmed|removed
    model_json: Mapped[dict | None] = mapped_column(JSONB)  # the model's item exactly as returned; user edits never change it
    flags: Mapped[list[str]] = mapped_column(ARRAY(String(30)), nullable=False, default=list,
                                        server_default=sa_text("'{}'"))  # limit_mismatch ...


class EvidenceCounter(Base):
    """Per-tenant counter behind the E-n numbers (never reused); bumped under an advisory lock."""
    __tablename__ = "evidence_counters"
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    next_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_evidence_items_tenant_id"),
                      UniqueConstraint("tenant_id", "display_no", name="uq_evidence_items_tenant_display_no"),
                      _child("fk_evidence_items_document", "document_id", "source_documents"),
                      Index("ix_evidence_items_tsv", "tsv", postgresql_using="gin"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    display_no: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    page_from: Mapped[int] = mapped_column(Integer, nullable=False)
    page_to: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tsv: Mapped[str] = mapped_column(TSVECTOR, Computed(
        "to_tsvector('english'::regconfig, coalesce(heading, '') || ' ' || coalesce(text, ''))", persisted=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Draft(Base):
    __tablename__ = "drafts"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_drafts_tenant_id"),
                      UniqueConstraint("requirement_id", "version", name="uq_drafts_requirement_version"),
                      _child("fk_drafts_requirement", "requirement_id", "requirements"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    requirement_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    word_limit_snapshot: Mapped[int | None] = mapped_column(Integer)
    retrieved_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    cited_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    author: Mapped[str] = mapped_column(String(10), nullable=False, default="ai")  # ai | user
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="drafted")  # drafted|checked_ok|blocked
    outside_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list,
                                                   server_default=sa_text("'{}'"))  # [E-n] cited but not retrieved
    flags: Mapped[list[str]] = mapped_column(ARRAY(String(30)), nullable=False, default=list,
                                             server_default=sa_text("'{}'"))  # citation_outside_set | shortened | trimmed ...
    created_at: Mapped[datetime] = _created()


class Claim(Base):
    __tablename__ = "claims"
    __table_args__ = (_child("fk_claims_draft", "draft_id", "drafts"),
                      UniqueConstraint("draft_id", "seq", name="uq_claims_draft_seq"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    draft_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    span: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    cited_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    verdict: Mapped[str] = mapped_column(String(15), nullable=False, default="unchecked")
    evidence_quote: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[str] = mapped_column(String(10), nullable=False, default="rule")  # model | rule


class Signoff(Base):
    __tablename__ = "signoffs"
    __table_args__ = (UniqueConstraint("tenant_id", "id", name="uq_signoffs_tenant_id"),
                      _child("fk_signoffs_pack", "pack_id", "tender_packs"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    pack_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    statement_version: Mapped[str] = mapped_column(String(20), nullable=False)
    drafts_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExportRecord(Base):
    """Audit trail of generated files; the file itself is not stored."""
    __tablename__ = "exports"
    __table_args__ = (_child("fk_exports_pack", "pack_id", "tender_packs"),
                      _child("fk_exports_signoff", "signoff_id", "signoffs"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    pack_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    signoff_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    docx_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()


class AITask(Base):
    """The job queue: SELECT ... FOR UPDATE SKIP LOCKED."""
    __tablename__ = "ai_tasks"
    __table_args__ = (_child("fk_ai_tasks_pack", "pack_id", "tender_packs"),
                      Index("ix_ai_tasks_queue", "status", "lease_until"))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    pack_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)  # extract | draft | claimcheck
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="queued")
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(40))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow,
                                                 nullable=False)


class AICache(Base):
    """Per tenant, so one tenant's output is never served to another."""
    __tablename__ = "ai_cache"
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    output_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = _created()
