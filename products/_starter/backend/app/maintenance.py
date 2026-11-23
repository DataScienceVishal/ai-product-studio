"""Retention: delete what the starter no longer needs. Run daily, for example as a Container Apps job:

    python -m app.maintenance purge

Rules (also in DATA.md):
  - sessions: when expired
  - password-reset and email-verification links: 7 days after they were used or expired
  - invitations: 30 days after they were accepted, cancelled or expired
  - billing events (idempotency records): after 400 days
  - AI usage rows: after 400 days (13 months covers a full year of billing questions)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from .config import Settings
from .db import Database
from .models import AIUsage, AuthSession, BillingEvent, EmailVerification, Invitation, PasswordReset


def purge(db: Session, now: datetime | None = None) -> dict[str, int]:
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
    counts = {name: db.execute(statement).rowcount for name, statement in statements.items()}
    db.commit()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["purge"])
    parser.parse_args()
    settings = Settings()
    database = Database(settings.database_url, settings.db_statement_timeout_ms)
    try:
        with database.sessions() as db:
            print(json.dumps({"purged": purge(db)}))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
