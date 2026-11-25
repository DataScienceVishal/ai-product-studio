"""Data model. Every customer-owned table carries tenant_id and is deleted with its tenant."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, false, text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def _tenant() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True, nullable=False)


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = _id()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = _created()


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)  # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="owner", nullable=False)  # owner | member
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sign_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # protects live accounts from purges
    created_at: Mapped[datetime] = _created()


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True,
                                               nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # sha256, never the token
    created_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True,
                                               nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), unique=True,
                                                 nullable=False)
    plan: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # trialing | active | past_due | canceled
    offer: Mapped[str | None] = mapped_column(String(40))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(255))  # the provider's subscription id
    provider_customer: Mapped[str | None] = mapped_column(String(255))  # the provider's customer id
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # ignore older events
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow,
                                                 nullable=False)


class BillingEvent(Base):
    """Webhook events already applied, so a repeated delivery is a no-op."""
    __tablename__ = "billing_events"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    received_at: Mapped[datetime] = _created()


class AIUsage(Base):
    """Token use per call. Rows outlive their tenant (tenant_id is cleared on deletion), because the global
    daily budget must still count what deleted accounts spent; they hold no personal data."""
    __tablename__ = "ai_usage"
    __table_args__ = (Index("ix_ai_usage_tenant_created", "tenant_id", "created_at"),
                      Index("ix_ai_usage_created", "created_at"),
                      # The abandoned-reservation sweep (ai.release_stale_reservations) and the in-flight count
                      # only look at pending rows, which are few and short-lived.
                      Index("ix_ai_usage_pending", "tenant_id", "created_at",
                            postgresql_where=text("model = 'pending'")))
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()
    feature: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    trial: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)


class Note(Base):
    """Example tenant-owned record. Products replace this with their own core objects."""
    __tablename__ = "notes"
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow,
                                                 nullable=False)


class Invitation(Base):
    """An owner's invite for a new member. Only the token's hash is stored; the link is the secret."""
    __tablename__ = "invitations"
    id: Mapped[uuid.UUID] = _id()
    tenant_id: Mapped[uuid.UUID] = _tenant()
    email: Mapped[str] = mapped_column(String(254), nullable=False)  # lower-case
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id: Mapped[uuid.UUID] = _id()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True,
                                               nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = _created()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

