"""Tenant-scoped query helpers usable by routes and background workers (no request object needed).
Another tenant's row looks exactly like a missing one: both raise the same 404."""
from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from .errors import AppError

T = TypeVar("T")


def scoped(model: type[T], tenant_id: uuid.UUID) -> Select:
    return select(model).where(model.tenant_id == tenant_id)  # type: ignore[attr-defined]


def get_scoped(db: Session, model: type[T], tenant_id: uuid.UUID, obj_id: uuid.UUID, what: str = "item") -> T:
    row = db.scalar(scoped(model, tenant_id).where(model.id == obj_id))  # type: ignore[attr-defined]
    if row is None:
        raise AppError(404, "not_found", f"That {what} doesn't exist.")
    return row
