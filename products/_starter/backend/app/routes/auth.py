"""Sign-up, sign-in, sign-out, the current user, and password reset."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from pydantic import AfterValidator, BaseModel, Field, field_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..billing import PLANS
from ..db import get_db
from ..deps import Current, current, session_cookie, subscription_of
from ..errors import AppError
from ..logs import bind
from ..models import AuthSession, EmailVerification, PasswordReset, Subscription, Tenant, User
from ..ratelimit import client_ip, email_key, off_loop
from ..textsafe import LINE_BAD, StrippedLine, is_blank
from ..security import (hash_capacity_after, hash_password, needs_rehash, new_token, password_problem, token_hash,
                        verify_password)

log = logging.getLogger("app.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


def _email(value: str) -> str:
    value = value.strip().lower()
    if not value.isascii():  # policy: ASCII-only addresses (no IDN or lookalike forms; Unicode variants would be separate accounts)
        raise ValueError("Use an email address with only standard (ASCII) characters.")
    if len(value) > 254 or not EMAIL.match(value) or LINE_BAD.search(value):
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
        value = " ".join(LINE_BAD.sub(" ", value).split())  # no control characters or newlines
        if not value or is_blank(value):
            raise ValueError("Enter your company name.")
        return value


class SignIn(BaseModel):
    email: StrippedLine = Field(max_length=254)
    password: str = Field(max_length=256)


class ResetRequest(BaseModel):
    email: StrippedLine = Field(max_length=254)


class VerifyIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


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
    response.set_cookie(session_cookie(settings), token, max_age=settings.session_days * 86400, httponly=True,
                        secure=settings.cookie_secure, samesite="lax", path="/")


def send_verification(request: Request, db: Session, user: User) -> None:
    """Email a fresh verification link; older unused links stop working."""
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)
    db.execute(update(EmailVerification).where(EmailVerification.user_id == user.id, EmailVerification.used_at.is_(None))
               .values(used_at=now))
    token = new_token()
    db.add(EmailVerification(user_id=user.id, token_hash=token_hash(token),
                             expires_at=now + timedelta(hours=settings.verify_hours)))
    db.commit()
    link = f"{settings.app_base_url.rstrip('/')}/verify-email?token={token}"
    request.app.state.email.send(user.email, "Confirm your email address",
                                 f"Confirm this address for your account (valid for {settings.verify_hours} hours): {link}")


def me_payload(db: Session, user: User, tenant: Tenant, request: Request) -> dict:
    sub = subscription_of(db, tenant.id)
    return {
        "user": {"id": str(user.id), "email": user.email, "role": user.role,
                 "email_verified": user.email_verified_at is not None,
                 # The server's gate (deps.verified_owner), so the UI can match it instead of guessing.
                 "email_verification_required": bool(request.app.state.settings.require_email_verification)},
        "tenant": {"id": str(tenant.id), "name": tenant.name},
        "subscription": {"plan": sub.plan, "status": sub.status, "offer": sub.offer,
                         "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                         "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None},
    }


# With Redis limits the gate body does network I/O, so `off_loop` runs it in a worker thread; with the in-memory
# limiter it runs inline (no thread). Cheap gates (rate limits, input checks) run BEFORE a hash slot is taken, so a rejected request never queues.
def _signup_checks(data: SignUp, request: Request) -> None:
    settings = request.app.state.settings
    _limit(request, f"signup:{client_ip(request)}")
    request.app.state.limiter.check(f"signup-day:{client_ip(request)}", settings.signups_per_ip_per_day, 86400)
    problem = password_problem(data.password)
    if problem:
        raise AppError(422, "weak_password", problem)


async def _signup_gate(data: SignUp, request: Request) -> None:
    await off_loop(request, lambda: _signup_checks(data, request))


async def _login_gate(data: SignIn, request: Request) -> None:
    await off_loop(request, lambda: _limit(request, f"login-ip:{client_ip(request)}",
                                           f"login-email:{email_key(data.email)}"))


def _reset_checks(data: ResetConfirm, request: Request) -> None:
    _limit(request, f"reset-confirm:{client_ip(request)}")
    problem = password_problem(data.new_password)
    if problem:
        raise AppError(422, "weak_password", problem)


async def _reset_gate(data: ResetConfirm, request: Request) -> None:
    await off_loop(request, lambda: _reset_checks(data, request))


@router.post("/signup", status_code=201, dependencies=[Depends(hash_capacity_after(_signup_gate))])
def signup(data: SignUp, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = request.app.state.settings
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if db.scalar(select(func.count()).select_from(Tenant).where(Tenant.created_at >= today)) >= settings.new_trials_per_day:
        raise AppError(429, "signups_paused", "We're not taking more sign-ups today. Please try again tomorrow.")
    db.commit()  # end the read transaction before hashing
    password_hash = hash_password(data.password)  # before any transaction opens
    tenant = Tenant(name=data.company_name)
    db.add(tenant)
    db.flush()
    user = User(tenant_id=tenant.id, email=data.email, password_hash=password_hash, role="owner",
                last_sign_in_at=datetime.now(timezone.utc))
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
    bind(tenant_id=str(tenant.id), user_id=str(user.id))
    log.info("signed up")
    send_verification(request, db, user)
    return me_payload(db, user, tenant, request)


@router.post("/login", dependencies=[Depends(hash_capacity_after(_login_gate))])
def login(data: SignIn, request: Request, response: Response, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    db.commit()  # no transaction (or pooled connection) held while the password is checked
    if not verify_password(user.password_hash if user else None, data.password):
        raise AppError(401, "invalid_credentials", "That email and password don't match.")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    user = db.merge(user)  # back into the new transaction after the commit above
    user.last_sign_in_at = datetime.now(timezone.utc)
    _start_session(request, response, db, user)
    db.commit()
    tenant = db.get(Tenant, user.tenant_id)
    bind(tenant_id=str(tenant.id), user_id=str(user.id))
    log.info("signed in")
    return me_payload(db, user, tenant, request)


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    token = request.cookies.get(session_cookie(request.app.state.settings))
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        db.commit()
    response = Response(status_code=204)
    response.delete_cookie(session_cookie(request.app.state.settings), path="/", secure=request.app.state.settings.cookie_secure,
                           httponly=True, samesite="lax")
    return response


@router.get("/me")
def me(request: Request, me: Current = Depends(current), db: Session = Depends(get_db)):
    return me_payload(db, me.user, me.tenant, request)


def _send_reset(app, user_id) -> None:
    """Runs after the response, so a known and an unknown email take the same time to answer."""
    settings = app.state.settings
    with app.state.db.sessions() as db:
        user = db.get(User, user_id)
        if user is None:
            return
        now = datetime.now(timezone.utc)
        db.execute(update(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
                   .values(used_at=now))  # only the newest link works
        token = new_token()
        db.add(PasswordReset(user_id=user.id, token_hash=token_hash(token),
                             expires_at=now + timedelta(minutes=settings.reset_token_minutes)))
        db.commit()
        link = f"{settings.app_base_url.rstrip('/')}/reset-password?token={token}"
        app.state.email.send(
            user.email, "Reset your password",
            f"Someone asked to reset the password for this account.\n\nReset it here (valid for "
            f"{settings.reset_token_minutes} minutes): {link}\n\nIf this wasn't you, ignore this email.")
        log.info("password reset requested", extra={"user_id": str(user.id)})


@router.post("/password-reset/request", status_code=202)
def reset_request(data: ResetRequest, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Always 202, whether or not the email has an account, so it can't be used to probe addresses."""
    settings = request.app.state.settings
    email = data.email.strip().lower()
    _limit(request, f"reset-ip:{client_ip(request)}")
    request.app.state.limiter.check(f"reset-email:{email_key(email)}", settings.reset_requests_per_hour, 3600)  # no inbox bombing
    user_id = db.scalar(select(User.id).where(User.email == email))
    db.commit()
    if user_id is not None:
        background.add_task(_send_reset, request.app, user_id)
    return {"status": "If that email has an account, we've sent a reset link."}


@router.post("/password-reset/confirm", status_code=204, dependencies=[Depends(hash_capacity_after(_reset_gate))])
def reset_confirm(data: ResetConfirm, request: Request, db: Session = Depends(get_db)) -> Response:
    new_hash = hash_password(data.new_password)  # before the transaction
    now = datetime.now(timezone.utc)
    # Consume the link in one statement, so two simultaneous clicks can't both use it.
    user_id = db.scalar(update(PasswordReset)
                        .where(PasswordReset.token_hash == token_hash(data.token), PasswordReset.used_at.is_(None),
                               PasswordReset.expires_at > now)
                        .values(used_at=now).returning(PasswordReset.user_id))
    if user_id is None:
        db.rollback()
        raise AppError(400, "invalid_reset_link", "This reset link has expired or was already used. Ask for a new one.")
    user = db.get(User, user_id)
    user.password_hash = new_hash
    user.email_verified_at = user.email_verified_at or now  # the link proved they control the inbox
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))  # sign out everywhere
    db.commit()
    log.info("password reset", extra={"user_id": str(user.id)})
    return Response(status_code=204)


@router.post("/verify-email", status_code=204)
def verify_email(data: VerifyIn, request: Request, me: Current = Depends(current), db: Session = Depends(get_db)) -> Response:
    """The person must be signed in as the account the link was sent to. Otherwise someone who signed up
    with your address could have you verify *their* account just by clicking an unexpected email."""
    _limit(request, f"verify:{client_ip(request)}")
    now = datetime.now(timezone.utc)
    used = db.scalar(update(EmailVerification)
                     .where(EmailVerification.token_hash == token_hash(data.token), EmailVerification.used_at.is_(None),
                            EmailVerification.expires_at > now, EmailVerification.user_id == me.user.id)
                     .values(used_at=now).returning(EmailVerification.id))
    if used is None:
        db.rollback()
        raise AppError(400, "invalid_verification_link",
                       "This link has expired, was already used, or belongs to a different account.")
    user = db.get(User, me.user.id)
    user.email_verified_at = user.email_verified_at or now
    db.commit()
    log.info("email verified", extra={"user_id": str(user.id)})
    return Response(status_code=204)


@router.post("/verify-email/resend", status_code=202)
def resend_verification(request: Request, me: Current = Depends(current), db: Session = Depends(get_db)):
    request.app.state.limiter.check(f"verify-resend:{me.user.id}", 3, 3600)  # 3 an hour
    if me.user.email_verified_at is not None:
        return {"status": "Your email is already verified."}
    send_verification(request, db, me.user)
    return {"status": "We've sent a new link. It works for 48 hours."}

