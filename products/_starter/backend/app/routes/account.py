"""Data export and the delete-my-data path (UK GDPR and India DPDP basics)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..ai import tokens_this_month
from ..db import get_db
from ..deps import Current, current, owner, session_cookie, subscription_of
from ..errors import AppError
from ..models import BillingCustomer, Invitation, Note, Tenant, User
from ..security import hash_capacity_after, verify_password

log = logging.getLogger("app.account")
router = APIRouter(prefix="/api/account", tags=["account"])


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


def _delete_account_gate(data: DeleteIn, request: Request, me: Current = Depends(owner)) -> Current:
    """Session, role, rate limit and confirmation, all before a hash slot is taken."""
    request.app.state.limiter.check(f"delete-account:{me.user.id}", 5)
    if data.confirm != "DELETE":
        raise AppError(422, "confirm_required", 'Type DELETE to confirm.')
    return me


@router.delete("", status_code=204, dependencies=[Depends(hash_capacity_after(_delete_account_gate))])
def delete_account(data: DeleteIn, request: Request, me: Current = Depends(_delete_account_gate),
                   db: Session = Depends(get_db)) -> Response:
    """Deletes the tenant and, by cascade, every user, session, note and usage row it owns."""
    if not verify_password(me.user.password_hash, data.password):
        raise AppError(401, "invalid_credentials", "That password isn't right.")
    tenant_id = str(me.tenant.id)
    sub = subscription_of(db, me.tenant.id)
    customer, subscription = sub.provider_customer, sub.provider_ref
    billing = request.app.state.billing
    # T-181 (T-179 M1): every customer this tenant ever had at the provider, not only the current one. The stored one
    # goes first (with the subscription); the rest are duplicates or customers a takeover replaced.
    others = [c for c in db.scalars(select(BillingCustomer.customer_ref).where(
        BillingCustomer.tenant_id == me.tenant.id, BillingCustomer.provider == billing.name)
        .order_by(BillingCustomer.created_at)) if c != customer]
    db.commit()  # no transaction open while the payment provider is called
    calls = ([(customer, subscription)] if customer or subscription else []) + [(c, None) for c in others]
    if calls:
        try:  # stop billing and remove their details at the provider first; if any fails, delete nothing. The rows
            # that list the customers stay, so the owner retries (deleting a customer is idempotent at the provider).
            for call_customer, call_subscription in calls:
                billing.close(call_customer, call_subscription)
        except AppError:
            log.error("could not delete a payment-provider customer; account kept", extra={"tenant_id": tenant_id})
            raise AppError(503, "billing_unavailable", "We couldn't cancel your subscription with the payment "
                           "provider, so nothing was deleted. Please try again in a few minutes.") from None
    db.delete(db.get(Tenant, me.tenant.id))  # rows cascade: users, sessions, notes, usage, invitations
    db.commit()
    log.info("tenant deleted", extra={"deleted_tenant_id": tenant_id})
    response = Response(status_code=204)
    response.delete_cookie(session_cookie(request.app.state.settings), path="/", secure=request.app.state.settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response


@router.get("/me/export")
def export_me(me: Current = Depends(current), db: Session = Depends(get_db)):
    """Any user's own data (UK GDPR access request): their profile and the notes they wrote."""
    notes = db.scalars(select(Note).where(Note.tenant_id == me.tenant.id, Note.created_by == me.user.id)
                       .order_by(Note.created_at)).all()
    return {"user": {"id": str(me.user.id), "email": me.user.email, "role": me.user.role,
                     "created_at": me.user.created_at.isoformat()},
            "tenant": {"id": str(me.tenant.id), "name": me.tenant.name},
            "notes_written": [{"id": str(n.id), "title": n.title, "body": n.body, "created_at": n.created_at.isoformat()}
                              for n in notes]}


def _delete_me_gate(data: DeleteIn, request: Request, me: Current = Depends(current)) -> Current:
    """Session, rate limit, role and confirmation, all before a hash slot is taken."""
    request.app.state.limiter.check(f"delete-me:{me.user.id}", 5)
    if me.user.role == "owner":
        raise AppError(422, "owner_cannot_leave", "As the owner, delete the whole account in Settings instead.")
    if data.confirm != "DELETE":
        raise AppError(422, "confirm_required", "Type DELETE to confirm.")
    return me


@router.delete("/me", status_code=204, dependencies=[Depends(hash_capacity_after(_delete_me_gate))])
def delete_me(data: DeleteIn, request: Request, me: Current = Depends(_delete_me_gate),
              db: Session = Depends(get_db)) -> Response:
    """A member removes themselves and their sign-in. Notes they wrote stay with the company (author cleared)."""
    if not verify_password(me.user.password_hash, data.password):
        raise AppError(401, "invalid_credentials", "That password isn't right.")
    db.execute(delete(Invitation).where(Invitation.tenant_id == me.tenant.id, Invitation.email == me.user.email))
    db.delete(db.get(User, me.user.id))
    db.commit()
    log.info("member left", extra={"left_user_id": str(me.user.id)})
    response = Response(status_code=204)
    response.delete_cookie(session_cookie(request.app.state.settings), path="/", secure=request.app.state.settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response

