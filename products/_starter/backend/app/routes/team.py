"""Team: owners invite members by email link; members can use the product but not billing,
export or account deletion. Invitations and members are always looked up within the caller's tenant."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Current, current, owner, verified_owner
from ..errors import AppError
from ..logs import bind
from ..models import Invitation, Tenant, User
from ..ratelimit import client_ip
from ..security import hash_capacity_after, hash_password, new_token, password_problem, token_hash
from .auth import Email, _start_session, me_payload

log = logging.getLogger("app.team")
router = APIRouter(prefix="/api/team", tags=["team"])
public = APIRouter(prefix="/api/invitations", tags=["team"])


class InviteIn(BaseModel):
    email: Email


class AcceptIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(max_length=256)


def email_safe(name: str) -> str:
    """A tenant name as it may appear in an email: no control characters, no links, short."""
    name = re.sub(r"[\x00-\x1f\x7f]", " ", name)
    name = re.sub(r"(?i)(?:[a-z][a-z0-9+.-]*://|www\.)\S*", "", name)
    name = re.sub(r"(?i)\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}(?:/\S*)?", "", name)  # bare domains too
    return " ".join(name.split())[:60] or "A team"


def _pending(now: datetime):
    return (Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None), Invitation.expires_at > now)


@router.get("")
def team(me: Current = Depends(current), db: Session = Depends(get_db)):
    members = db.scalars(select(User).where(User.tenant_id == me.tenant.id).order_by(User.created_at)).all()
    body = {"members": [{"id": str(u.id), "email": u.email, "role": u.role, "created_at": u.created_at.isoformat()}
                        for u in members]}
    if me.user.role == "owner":
        invites = db.scalars(select(Invitation).where(Invitation.tenant_id == me.tenant.id,
                                                      *_pending(datetime.now(timezone.utc)))
                             .order_by(Invitation.created_at)).all()
        body["invitations"] = [{"id": str(i.id), "email": i.email, "expires_at": i.expires_at.isoformat()}
                               for i in invites]
    return body


@router.post("/invitations", status_code=201)
def invite(data: InviteIn, request: Request, me: Current = Depends(verified_owner), db: Session = Depends(get_db)):
    settings = request.app.state.settings
    request.app.state.limiter.check(f"invite:{me.tenant.id}", 20)
    now = datetime.now(timezone.utc)
    sent_today = db.scalar(select(func.count()).select_from(Invitation)
                           .where(Invitation.tenant_id == me.tenant.id, Invitation.created_at > now - timedelta(days=1)))
    if sent_today >= settings.invites_per_day:
        raise AppError(429, "invite_limit", "You've sent a lot of invitations today. Try again tomorrow.")
    pending = db.scalar(select(func.count()).select_from(Invitation)
                        .where(Invitation.tenant_id == me.tenant.id, *_pending(now)))
    if pending >= settings.max_pending_invites:
        raise AppError(409, "too_many_pending", "Cancel some unanswered invitations before sending more.")
    if db.scalar(select(User.id).where(User.email == data.email)) is not None:
        raise AppError(409, "email_taken", "That email already has an account.")
    db.execute(update(Invitation).where(Invitation.tenant_id == me.tenant.id, Invitation.email == data.email,
                                        *_pending(now)).values(revoked_at=now))  # only the newest link works
    token = new_token()
    invitation = Invitation(tenant_id=me.tenant.id, email=data.email, role="member", token_hash=token_hash(token),
                            invited_by=me.user.id, expires_at=now + timedelta(days=settings.invite_days))
    db.add(invitation)
    db.commit()
    link = f"{settings.app_base_url.rstrip('/')}/accept-invite?token={token}"
    team_name = email_safe(me.tenant.name)
    request.app.state.email.send(
        data.email, f"You're invited to {team_name}",
        f"{team_name} has invited you to join their account.\n\nAccept within {settings.invite_days} days: {link}")
    log.info("member invited", extra={"invitation_id": str(invitation.id)})
    return {"id": str(invitation.id), "email": invitation.email, "expires_at": invitation.expires_at.isoformat()}


@router.delete("/invitations/{invitation_id}", status_code=204)
def revoke(invitation_id: uuid.UUID, me: Current = Depends(owner), db: Session = Depends(get_db)) -> Response:
    invitation = db.scalar(select(Invitation).where(Invitation.id == invitation_id, Invitation.tenant_id == me.tenant.id))
    if invitation is None:
        raise AppError(404, "not_found", "That invitation doesn't exist.")
    invitation.revoked_at = invitation.revoked_at or datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@router.delete("/members/{user_id}", status_code=204)
def remove_member(user_id: uuid.UUID, me: Current = Depends(owner), db: Session = Depends(get_db)) -> Response:
    if user_id == me.user.id:
        raise AppError(422, "cannot_remove_self", "You can't remove yourself. Delete the account from Settings instead.")
    member = db.scalar(select(User).where(User.id == user_id, User.tenant_id == me.tenant.id))
    if member is None:
        raise AppError(404, "not_found", "That person isn't in your team.")
    db.execute(delete(Invitation).where(Invitation.tenant_id == me.tenant.id, Invitation.email == member.email))
    db.delete(member)  # their sessions go with them (ON DELETE CASCADE); their invitation rows too (above)
    db.commit()
    log.info("member removed", extra={"removed_user_id": str(user_id)})
    return Response(status_code=204)


async def _accept_gate(data: AcceptIn, request: Request) -> None:
    """Cheap checks, run before a hash slot is taken."""
    request.app.state.limiter.check(f"accept:{client_ip(request)}", request.app.state.settings.auth_rate_limit_per_minute)
    problem = password_problem(data.password)
    if problem:
        raise AppError(422, "weak_password", problem)


@public.post("/accept", status_code=201, dependencies=[Depends(hash_capacity_after(_accept_gate))])
def accept(data: AcceptIn, request: Request, response: Response, db: Session = Depends(get_db)):
    password_hash = hash_password(data.password)  # before any transaction opens
    now = datetime.now(timezone.utc)
    invitation = db.scalar(select(Invitation).where(Invitation.token_hash == token_hash(data.token), *_pending(now)))
    if invitation is None:
        raise AppError(400, "invalid_invitation", "This invitation has expired or was already used. Ask for a new one.")
    user = User(tenant_id=invitation.tenant_id, email=invitation.email, password_hash=password_hash,
                role=invitation.role, email_verified_at=now, last_sign_in_at=now)  # the link proved the inbox
    db.add(user)
    invitation.accepted_at = now
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "email_taken", "That email already has an account. Try signing in.")
    _start_session(request, response, db, user)
    db.commit()
    tenant = db.get(Tenant, user.tenant_id)
    bind(tenant_id=str(tenant.id), user_id=str(user.id))
    log.info("invitation accepted", extra={"invitation_id": str(invitation.id)})
    return me_payload(db, user, tenant)
