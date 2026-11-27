"""Checks shared by the tender routes: document deletes and the requirement-to-document link."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import AppError
from ..scoped import get_scoped, scoped
from ..tender_models import SourceDocument, TenderPack

log = logging.getLogger("app.tender")
IN_USE = ("Some requirements still cite this document. Remove or reassign those requirements first, "
          "then delete it.")


def ensure_requirement_document(db: Session, tenant_id: uuid.UUID, pack_id: uuid.UUID,
                                document_id: uuid.UUID | None) -> SourceDocument | None:
    """A requirement may cite only a tender document of its own pack. Called by every requirement write path
    (the schema's composite FK checks the tenant, not the pack). Another tenant's or another pack's document is
    refused with the same 422, so ids are not probed across tenants."""
    if document_id is None:
        return None
    doc = db.scalar(scoped(SourceDocument, tenant_id).where(SourceDocument.id == document_id,
                                                            SourceDocument.kind == "tender",
                                                            SourceDocument.pack_id == pack_id))
    if doc is None:
        raise AppError(422, "document_not_in_pack", "A requirement can only cite a document of its own tender pack.")
    return doc


def delete_row(db: Session, row) -> None:
    """Delete a pack or document. fk_requirements_document refuses (NO ACTION) while requirements still cite a
    document; that becomes a 409 with a message, never a 500."""
    try:
        db.delete(row)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "fk_requirements_document" in str(exc.orig) or "fk_requirements_document" in str(exc):
            raise AppError(409, "document_in_use", IN_USE)
        raise
