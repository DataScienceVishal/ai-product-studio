"""Retention: delete what the starter no longer needs. Run daily, for example as a Container Apps job:

    python -m app.maintenance purge

and, every few minutes or hourly (T-175, retries subscription cancels that failed after a checkout replaced a
lapsed subscription; prints the counts, exits 0 even when some still fail, they are logged at ERROR; a row is skipped until min(2**attempts minutes, 24 h)
have passed since its last attempt, and its 10th failure logs one CRITICAL "pending cancel needs operator" line):

    python -m app.maintenance cancels

Rules (also in DATA.md):
  - sessions: when expired
  - password-reset and email-verification links: 7 days after they were used or expired
  - invitations: 30 days after they were accepted, cancelled or expired
  - billing events (idempotency records): after 400 days
  - AI usage rows: after 400 days (13 months covers a full year of billing questions). They outlive deleted
    tenants (unlinked), because the studio-wide daily AI budget must count them.
  - AI cache rows (ai_cache, customer content derived from uploads): 90 days after creation
  - soft-deleted evidence documents (and their passages): 90 days after deleted_at, unless a pack with an exports row
    has a draft citing one of their passages (the audit keeps it)
  - AI reservations still "pending" after 15 minutes (the process died mid-call): zeroed, so they stop counting
  - accounts whose owner never verified their email, never signed in for 30 days, and has no payment-provider
    customer: after 30 days, only when verification is required AND real email is sent (with the outbox nobody
    can verify, so nothing is purged)
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import any_, delete, exists, or_, select
from sqlalchemy.orm import Session

from .ai import release_stale_reservations
from .billing import build_billing
from .config import Settings
from .db import Database
from .tender_models import AICache, Draft, EvidenceItem, ExportRecord, Requirement, SourceDocument
from .models import (AIUsage, AuthSession, BillingEvent, EmailVerification, Invitation, PasswordReset, PendingCancel, Subscription,
                     Tenant, User)


log = logging.getLogger("app.billing")
AI_CACHE_DAYS = 90
EVIDENCE_PURGE_DAYS = 90  # soft-deleted evidence documents (T-201 item 10)


def _purgeable_evidence(now: datetime):
    """Soft-deleted evidence documents past the horizon, unless an exported pack's drafts cite one of their passages
    (an exports row is the audit; the appendix text it was built from stays while any export may cite it)."""
    cited_by_export = exists().where(
        EvidenceItem.document_id == SourceDocument.id, EvidenceItem.tenant_id == SourceDocument.tenant_id,
        Draft.tenant_id == EvidenceItem.tenant_id, EvidenceItem.display_no == any_(Draft.cited_ids),
        Requirement.tenant_id == Draft.tenant_id, Requirement.id == Draft.requirement_id,
        exists().where(ExportRecord.tenant_id == Requirement.tenant_id, ExportRecord.pack_id == Requirement.pack_id))
    return (SourceDocument.kind == "evidence", SourceDocument.deleted_at.is_not(None),
            SourceDocument.deleted_at < now - timedelta(days=EVIDENCE_PURGE_DAYS), ~cited_by_export)


def purge(db: Session, now: datetime | None = None, unverified_after_days: int | None = None) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    week, month, year = now - timedelta(days=7), now - timedelta(days=30), now - timedelta(days=400)
    statements = {
        # Age only: the row's own created_at decides, no tenant content is read, and no other table is touched.
        "ai_cache": delete(AICache).where(AICache.created_at < now - timedelta(days=AI_CACHE_DAYS)),
        # The document row goes and its passages and pages cascade. Age and the exports audit decide; no text is read.
        "soft_deleted_evidence": delete(SourceDocument).where(*_purgeable_evidence(now)),
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


def sweep_pending_cancels(db: Session, clients: dict, now: datetime | None = None) -> dict[str, int]:
    """T-175: retry every pending subscription cancel (see routes/billing.py). `clients` maps provider name to its
    client; a row for a provider with no client is left alone. Safe to run often: a cancel is idempotent.
    T-176: a row is left alone until min(2**attempts minutes, 24 h) have passed since its last attempt. The check is
    repeated under the row lock with this run's start time (`now`): a row that another worker attempted meanwhile is
    skipped, and so is one whose backoff ends during a long run (it waits for the next run)."""
    from .routes import billing as routes
    now = now or datetime.now(timezone.utc)
    done = failed = 0
    todo = db.execute(select(PendingCancel.id, PendingCancel.provider, PendingCancel.ref, PendingCancel.attempts,
                             PendingCancel.last_attempt_at).order_by(PendingCancel.created_at)).all()
    for row_id, row_provider, ref, attempts, last_attempt_at in todo:
        client = clients.get(row_provider)
        if client is None:
            continue
        if last_attempt_at is not None and now - last_attempt_at < routes.cancel_backoff(attempts or 0):
            continue
        try:
            result = routes.attempt_pending_cancel(db, row_id, client, backoff_now=now)
        except Exception:  # one bad row (a stale or deleted one, a database error) must not stop the run
            db.rollback()
            log.error("pending cancel could not be processed", extra={"old_subscription": ref}, exc_info=True)
            failed += 1
            continue
        if result is True:
            done += 1
        elif result is False:
            failed += 1
    return {"cancelled": done, "failed": failed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["purge", "cancels"])
    args = parser.parse_args()
    settings = Settings()
    database = Database(settings.database_url, settings.db_statement_timeout_ms, db_auth=settings.db_auth,
                        client_id=settings.azure_client_id)
    try:
        with database.sessions() as db:
            if args.command == "cancels":
                provider = build_billing(settings)
                print(json.dumps({"pending_cancels": sweep_pending_cancels(db, {provider.name: provider})}))
                return
            # Only when people can actually verify: verification required AND real email (not the outbox).
            days = 30 if settings.require_email_verification and settings.email_provider != "outbox" else None
            print(json.dumps({"purged": purge(db, unverified_after_days=days)}))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
