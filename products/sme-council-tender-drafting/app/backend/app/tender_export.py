"""Account export (R7): every customer-content table of the tender product, for one tenant. `ai_tasks` and `ai_cache`
are operational data and left out."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from .scoped import scoped
from .tender_models import (Claim, Draft, DocumentPage, EvidenceItem, ExportRecord, Requirement, Signoff,
                            SourceDocument, TenderPack)

# export key -> (model, columns left out). Original file bytes are never stored, so there are none to export.
_TABLES = {"packs": TenderPack, "source_documents": SourceDocument, "document_pages": DocumentPage,
           "requirements": Requirement, "evidence_items": EvidenceItem, "drafts": Draft, "claims": Claim,
           "signoffs": Signoff, "export_records": ExportRecord}
_SKIP = {"tsv"}  # generated search column


def _value(v):
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def tender_export(db: Session, tenant_id: uuid.UUID) -> dict:
    out = {}
    for key, model in _TABLES.items():
        cols = [c.key for c in inspect(model).column_attrs if c.key not in _SKIP]
        out[key] = [{c: _value(getattr(r, c)) for c in cols} for r in db.scalars(scoped(model, tenant_id)).all()]
    return out
