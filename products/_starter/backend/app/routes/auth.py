"""Sign-up, sign-in, sign-out, the current user, and password reset."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import AfterValidator, BaseModel, Field, field_validator
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..billing import PLANS
from ..db import get_db
from ..deps import SESSION_COOKIE, Current, current, require_csrf_header, subscription_of
from ..errors import AppError
from ..models import AuthSession, PasswordReset, Subscription, Tenant, User
from ..ratelimit import client_ip
from ..security import (hash_password, needs_rehash, new_token, password_problem, token_hash,
                        verify_password)

log = logging.getLogger("app.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(require_csrf_header)])
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def _email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


Email = Annotated[str, AfterValidator(_email)]


class SignUp(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    email: Email
    password: str = Field(max_length=256)

    @field_validator("company_name")
    @classmethod
    def _company(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Enter your company name.")
        return value


class SignIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


class ResetRequest(BaseModel):
    email: str = Field(max_length=254)


class ResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(max_length=256)


def _limit(request: Request, *keys: str) -> None:
    settings = request.app.state.settings
    for key in keys:
        request.app.state.limiter.check(key, settings.auth_rate_limit_per_minute)


def _start_session(request: Request, response: Response, db: Session, user: User) -> None:
    settings = request.app.state.settings
    token = new_token()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    db.add(AuthSession(user_id=user.id, token_hash=token_hash(token), expires_at=expires))
    response.set_cookie(SESSION_COOKIE, token, max_age=settings.session_days * 86400, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/")


def me_payload(db: Session, user: User, tenant: Tenant) -> dict:
    sub = subscription_of(db, tenant.id)
    return {
        "user": {"id": str(user.id), "email": user.email, "role": user.role},
        "tenant": {"id": str(tenant.id), "name": tenant.name},
        "subscription": {"plan": sub.plan, "status": sub.status, "offer": sub.offer,
                         "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                         "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None},
    }


@router.post("/signup", status_code=201)
def signup(data: SignUp, request: Request, response: Response, db: Session = Depends(get_db)):
    _limit(request, f"signup:{client_ip(request)}")
    problem = password_problem(data.password)
    if problem:
        raise AppError(422, "weak_password", problem)
    settings = request.app.state.settings
    tenant = Tenant(name=data.company_name)
    db.add(tenant)
    db.flush()
    user = User(tenant_id=tenant.id, email=data.email, password_hash=hash_password(data.password), role="owner")
    db.add(user)
    db.add(Subscription(tenant_id=tenant.id, plan=PLANS["trial"].id, status="trialing", provider="none",
                        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=settings.trial_days)))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Reveals that the address has an account. Accepted for a B2B sign-up form; rate limited above.
        raise AppError(409, "email_taken", "An account with this email already exists. Try signing in.")
    _start_session(request, response, db, user)
    db.commit()
    log.info("signed up", extra={"user_id": str(user.id)})
    return me_payload(db, user, tenant)


@router.post("/login")
def login(data: SignIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    _limit(request, f"login-ip:{client_ip(request)}", f"login-email:{email}")
    user = db.scalar(select(User).where(User.email == email))
    if not verify_password(user.password_hash if user else None, data.password):
        raise AppError(401, "invalid_credentials", "That email and password don't match.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    _start_session(request, response, db, user)
    db.commit()
    tenant = db.get(Tenant, user.tenant_id)
    log.info("signed in", extra={"user_id": str(user.id)})
    return me_payload(db, user, tenant)


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        db.commit()
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=request.app.state.settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response


@router.get("/me")
def me(me: Current = Depends(current), db: Session = Depends(get_db)):
    return me_payload(db, me.user, me.tenant)


@router.post("/password-reset/request", status_code=202)
def reset_request(data: ResetRequest, request: Request, db: Session = Depends(get_db)):
    """Always 202, whether or not the email has an account, so it can't be used to probe addresses."""
    email = data.email.strip().lower()
    _limit(request, f"reset-ip:{client_ip(request)}", f"reset-email:{email}")
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        settings = request.app.state.settings
        db.execute(update(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
                   .values(used_at=datetime.now(timezone.utc)))  # only the newest link works
        token = new_token()
        db.add(PasswordReset(user_id=user.id, token_hash=token_hash(token),
                             expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_minutes)))
        db.commit()
        link = f"{settings.app_base_url.rstrip('/')}/reset-password?token={token}"
        request.app.state.email.send(
            user.email, "Reset your password",
            f"Someone asked to reset the password for this account.\n\nReset it here (valid for "
            f"{settings.reset_token_minutes} minutes): {link}\n\nIf this wasn't you, ignore this email.")
        log.info("password reset requested", extra={"user_id": str(user.id)})
    return {"status": "If that email has an account, we've sent a reset link."}


@router.post("/password-reset/confirm", status_code=204)
def reset_confirm(data: ResetConfirm, request: Request, db: Session = Depends(get_db)) -> Response:
    _limit(request, f"reset-confirm:{client_ip(request)}")
    now = datetime.now(timezone.utc)
    row = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == token_hash(data.token)))
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise AppError(400, "invalid_reset_link", "This reset link has expired or was already used. Ask for a new one.")
    problem = password_problem(data.new_password)
    if problem:
        raise AppError(422, "weak_password", problem)
    user = db.get(User, row.user_id)
    user.password_hash = hash_password(data.new_password)
    row.used_at = now
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))  # sign out everywhere
    db.commit()
    log.info("password reset", extra={"user_id": str(user.id)})
    return Response(status_code=204)
