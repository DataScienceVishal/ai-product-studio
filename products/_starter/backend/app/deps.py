"""Request dependencies: the signed-in user, CSRF protection, roles and the tenant's subscription."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .errors import AppError
from .logs import bind
from .models import AuthSession, Subscription, Tenant, User
from .security import token_hash

SESSION_COOKIE = "session"
CSRF_HEADER = "x-requested-with"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}


def require_csrf_header(request: Request) -> None:
    """Cookie-authenticated writes must carry a custom header. Browsers can't add one cross-site
    without a CORS preflight, which our CORS policy refuses, so forged form posts fail."""
    if request.method in UNSAFE and not request.headers.get(CSRF_HEADER):
        raise AppError(403, "csrf_check_failed", "Missing request header. Please reload the page and try again.")


@dataclass
class Current:
    user: User
    tenant: Tenant
    session: AuthSession


def current(request: Request, db: Session = Depends(get_db)) -> Current:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AppError(401, "not_signed_in", "Please sign in.")
    row = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token)))
    if row is None or row.expires_at <= datetime.now(timezone.utc):
        raise AppError(401, "not_signed_in", "Your session has ended. Please sign in again.")
    user = db.get(User, row.user_id)
    tenant = db.get(Tenant, user.tenant_id) if user else None
    if user is None or tenant is None:
        raise AppError(401, "not_signed_in", "Please sign in.")
    bind(tenant_id=str(tenant.id), user_id=str(user.id))
    db.commit()  # end the read transaction; with expire_on_commit=False the objects stay usable
    return Current(user=user, tenant=tenant, session=row)


def owner(me: Current = Depends(current)) -> Current:
    if me.user.role != "owner":
        raise AppError(403, "forbidden", "Only the account owner can do that.")
    return me


def verified_owner(request: Request, me: Current = Depends(owner)) -> Current:
    """Owner actions that send email or take payment need a verified address (stops invite spam)."""
    if request.app.state.settings.require_email_verification and me.user.email_verified_at is None:
        raise AppError(403, "email_not_verified", "Please verify your email address first. Check your inbox, or resend the link.")
    return me


def subscription_of(db: Session, tenant_id) -> Subscription:
    sub = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id))
    if sub is None:  # every tenant gets one at sign-up; this guards against bad data
        raise AppError(402, "no_subscription", "Choose a plan to continue.")
    return sub
