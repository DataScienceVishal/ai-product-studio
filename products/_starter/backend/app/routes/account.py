"""Data export and the delete-my-data path (UK GDPR and India DPDP basics)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import tokens_this_month
from ..db import get_db
from ..deps import SESSION_COOKIE, Current, current, owner, require_csrf_header, subscription_of
from ..errors import AppError
from ..models import Note, User
from ..security import verify_password

log = logging.getLogger("app.account")
router = APIRouter(prefix="/api/account", tags=["account"], dependencies=[Depends(require_csrf_header)])


class DeleteIn(BaseModel):
    password: str = Field(max_length=256)
    confirm: str = Field(max_length=40)


@router.get("/export")
def export(me: Current = Depends(owner), db: Session = Depends(get_db)):
    sub = subscription_of(db, me.tenant.id)
    users = db.scalars(select(User).where(User.tenant_id == me.tenant.id)).all()
    notes = db.scalars(select(Note).where(Note.tenant_id == me.tenant.id).order_by(Note.created_at)).all()
    return {
        "tenant": {"id": str(me.tenant.id), "name": me.tenant.name, "created_at": me.tenant.created_at.isoformat()},
        "users": [{"id": str(u.id), "email": u.email, "role": u.role, "created_at": u.created_at.isoformat()}
                  for u in users],
        "subscription": {"plan": sub.plan, "status": sub.status, "offer": sub.offer},
        "notes": [{"id": str(n.id), "title": n.title, "body": n.body, "summary": n.summary,
                   "created_at": n.created_at.isoformat()} for n in notes],
        "ai_tokens_this_month": tokens_this_month(db, me.tenant.id),
    }


@router.get("/usage")
def usage(me: Current = Depends(current), db: Session = Depends(get_db)):
    return {"ai_tokens_this_month": tokens_this_month(db, me.tenant.id)}


@router.delete("", status_code=204)
def delete_account(data: DeleteIn, request: Request, me: Current = Depends(owner),
                   db: Session = Depends(get_db)) -> Response:
    """Deletes the tenant and, by cascade, every user, session, note and usage row it owns."""
    if data.confirm != "DELETE":
        raise AppError(422, "confirm_required", 'Type DELETE to confirm.')
    if not verify_password(me.user.password_hash, data.password):
        raise AppError(401, "invalid_credentials", "That password isn't right.")
    tenant_id = str(me.tenant.id)
    db.delete(me.tenant)  # same session as `owner` (FastAPI caches get_db per request)
    db.commit()
    log.info("tenant deleted", extra={"deleted_tenant_id": tenant_id})
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=request.app.state.settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response
