"""Retention: delete what the starter no longer needs. Run daily, for example as a Container Apps job:

    python -m app.maintenance purge

Rules (also in DATA.md):
  - sessions: when expired
  - password-reset and email-verification links: 7 days after they were used or expired
  - invitations: 30 days after they were accepted, cancelled or expired
  - billing events (idempotency records): after 400 days
  - AI usage rows: after 400 days (13 months covers a full year of billing questions). They outlive deleted
    tenants (unlinked), because the studio-wide daily AI budget must count them.
  - AI reservations still "pending" after 15 minutes (the process died mid-call): zeroed, so they stop counting
  - accounts whose owner never verified their email, never signed in for 30 days, and has no payment-provider
    customer: after 30 days, only when verification is required AND real email is sent (with the outbox nobody
    can verify, so nothing is purged)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from .ai import release_stale_reservations
from .config import Settings
from .db import Database
from .models import (AIUsage, AuthSession, BillingEvent, EmailVerification, Invitation, PasswordReset, Subscription,
                     Tenant, User)


def purge(db: Session, now: datetime | None = None, unverified_after_days: int | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    week, month, year = now - timedelta(days=7), now - timedelta(days=30), now - timedelta(days=400)
    statements = {
        "sessions": delete(AuthSession).where(AuthSession.expires_at <= now),
        "password_resets": delete(PasswordReset).where(PasswordReset.created_at < week,
                                                       or_(PasswordReset.used_at.is_not(None), PasswordReset.expires_at <= now)),
        "email_verifications": delete(EmailVerification).where(
            EmailVerification.created_at < week,
            or_(EmailVerification.used_at.is_not(None), EmailVerification.expires_at <= now)),
        "invitations": delete(Invitation).where(Invitation.created_at < month, or_(
            Invitation.accepted_at.is_not(None), Invitation.revoked_at.is_not(None), Invitation.expires_at <= now)),
        "billing_events": delete(BillingEvent).where(BillingEvent.received_at < year),
        "ai_usage": delete(AIUsage).where(AIUsage.created_at < year),
    }
    if unverified_after_days is not None:
        cutoff = now - timedelta(days=unverified_after_days)
        paying = select(Subscription.tenant_id).where(Subscription.provider_customer.is_not(None))
        abandoned = select(User.tenant_id).where(
            User.role == "owner", User.email_verified_at.is_(None), User.created_at < cutoff,
            or_(User.last_sign_in_at.is_(None), User.last_sign_in_at < cutoff))
        statements["unverified_accounts"] = delete(Tenant).where(Tenant.id.in_(abandoned), Tenant.id.not_in(paying))
    counts = {name: db.execute(statement).rowcount for name, statement in statements.items()}
    counts["abandoned_ai_reservations"] = release_stale_reservations(db)  # killed calls: stop counting their estimate
    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["purge"])
    parser.parse_args()
    settings = Settings()
    database = Database(settings.database_url, settings.db_statement_timeout_ms, db_auth=settings.db_auth,
                        client_id=settings.azure_client_id)
    try:
        with database.sessions() as db:
            # Only when people can actually verify: verification required AND real email (not the outbox).
            days = 30 if settings.require_email_verification and settings.email_provider != "outbox" else None
            print(json.dumps({"purged": purge(db, unverified_after_days=days)}))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
