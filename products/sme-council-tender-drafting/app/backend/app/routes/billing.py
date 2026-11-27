"""Plans, checkout and the payment provider's webhook. Test mode only (see app/billing.py)."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..billing import LIMITED_PROVIDERS, OFFERS, PLANS, BillingUpdate, MockBilling, has_access, sign
from ..db import get_db
from ..deps import Current, owner, subscription_of, verified_owner
from ..errors import AppError
from ..models import BillingEvent, PendingCancel, Subscription

log = logging.getLogger("app.billing")
router = APIRouter(prefix="/api/billing", tags=["billing"])

# T-176: pending provider cancels. The webhook retries only rows that failed fewer times than this (each attempt can
# take about 17 s, and a provider outage must not push the webhook past the provider's timeout); the sweep does the rest.
INLINE_RETRY_MAX_ATTEMPTS = 3
# The sweep skips a row whose last attempt is more recent than min(2**attempts minutes, this).
SWEEP_BACKOFF_CAP = timedelta(hours=24)
# When a row's attempts reach this, log one CRITICAL line (the transition only); later failures log at WARNING.
ESCALATE_AT = 10


def cancel_backoff(attempts: int) -> timedelta:
    """How long the sweep leaves a row alone after its last attempt: 2**attempts minutes, at most a day."""
    return min(timedelta(minutes=2 ** min(max(attempts, 0), 12)), SWEEP_BACKOFF_CAP)


class CheckoutIn(BaseModel):
    plan: str = Field(max_length=40)
    offer_code: str | None = Field(default=None, max_length=40)


@router.get("/plans")
def plans(request: Request):
    trial = PLANS["trial"]
    return {
        "plans": [{"id": p.id, "name": p.name, "price_pence": p.price_pence, "currency": p.currency,
                   "interval": p.interval, "ai_monthly_tokens": p.ai_monthly_tokens}
                  for p in PLANS.values() if p.id != "trial"],
        "offers": [{"code": o.code, "description": o.description} for o in OFFERS.values()],
        # T-94: while the provider is in LIMITED_PROVIDERS every plan's AI use is capped at the trial allowance
        # (the AI routes), so the page must not promise the plan's own allowance yet.
        "ai_allowance": {"trial_sized": request.app.state.settings.billing_provider in LIMITED_PROVIDERS,
                         "monthly_tokens": trial.ai_monthly_tokens, "daily_tokens": trial.ai_daily_tokens},
    }


@router.post("/checkout")
def checkout(data: CheckoutIn, request: Request, me: Current = Depends(verified_owner), db: Session = Depends(get_db)):
    request.app.state.limiter.check(f"checkout:{me.tenant.id}", 10)
    sub = subscription_of(db, me.tenant.id)
    db.commit()  # don't hold a transaction while the payment provider is called
    if (sub.status == "active" and sub.provider_ref and sub.provider == request.app.state.billing.name
            and has_access(sub.status, sub.trial_ends_at, current_period_end=sub.current_period_end)):
        # (An "active" subscription past its grace period has no access, so a new checkout is allowed.)
        raise AppError(409, "already_subscribed", "You already have an active plan. To change it, contact support.")
    if sub.status == "past_due" and sub.provider_ref and sub.provider == request.app.state.billing.name:
        # A second checkout would start a new subscription next to the unpaid one: the customer pays twice.
        raise AppError(409, "subscription_past_due",
                       "Your last payment failed, so a new checkout would charge you twice. "
                       "Use \"Manage billing\" on the Billing page to update your card, or contact support.")
    plan = PLANS.get(data.plan)
    if plan is None or plan.id == "trial":
        raise AppError(422, "unknown_plan", "Choose one of the listed plans.")
    offer = None
    if data.offer_code:
        offer = OFFERS.get(data.offer_code.strip().upper())
        if offer is None:
            raise AppError(422, "unknown_offer", "That offer code isn't valid.")
    base = request.app.state.settings.app_base_url.rstrip("/")
    session = request.app.state.billing.create_checkout(me.tenant.id, plan, offer,
                                                        f"{base}/billing/done", f"{base}/billing")
    return {"checkout_id": session.id, "url": session.url}


@router.post("/portal")
def portal(request: Request, me: Current = Depends(verified_owner), db: Session = Depends(get_db)):
    """A provider-hosted page where the customer updates their card or manages the subscription."""
    request.app.state.limiter.check(f"portal:{me.tenant.id}", 10)
    sub = subscription_of(db, me.tenant.id)
    db.commit()  # don't hold a transaction while the payment provider is called
    billing = request.app.state.billing
    if not sub.provider_customer or sub.provider != billing.name:
        raise AppError(409, "no_billing_customer", "There is no payment account to manage yet. Choose a plan first.")
    base = request.app.state.settings.app_base_url.rstrip("/")
    return {"url": billing.portal_session(sub.provider_customer, f"{base}/billing")}


def _check_fields(update: BillingUpdate) -> None:
    """Refuse fields the columns cannot hold (wrong type, too long) with a 400, before the event id is recorded."""
    if not isinstance(update.event_id, str) or not 0 < len(update.event_id) <= 255:  # BillingEvent.id is String(255)
        log.warning("billing event has an unreadable id")
        raise AppError(400, "bad_event", "The event could not be read.")
    for name, limit in (("plan", 40), ("offer", 40), ("provider_ref", 255), ("customer_ref", 255)):
        value = getattr(update, name)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            log.warning("billing event has an unreadable field", extra={"field": name})
            raise AppError(400, "bad_event", "The event could not be read.")


def apply_update(db: Session, update: BillingUpdate, provider: str, billing=None) -> bool:
    """Apply one provider event (see `_apply_update`), then retry this tenant's pending provider cancels (T-175)."""
    applied = _apply_update(db, update, provider, billing)
    if billing is not None and isinstance(update.tenant_id, uuid.UUID):
        try:
            retry_pending_cancels(db, update.tenant_id, provider, billing)
        except Exception:  # the event is already applied; a retry problem must not fail the webhook
            db.rollback()
            log.error("could not retry pending cancels", extra={"tenant_id": str(update.tenant_id)}, exc_info=True)
    return applied


def _apply_update(db: Session, update: BillingUpdate, provider: str, billing=None) -> bool:
    """Apply a provider event once, in order. Returns False if this event id was already applied.
    An event older than the last one applied is recorded as seen but changes nothing.
    `billing` is the provider, used to cancel a duplicate subscription (see below)."""
    _check_fields(update)
    if update.status == "active" and update.plan is not None and (update.plan not in PLANS or update.plan == "trial"):
        # Wrong provider metadata would otherwise activate the subscription on whatever plan the tenant had
        # (a free upgrade). Refuse before recording the event id, so a redelivery works once the catalogue or
        # the metadata is fixed. The webhook answers 400, like any event we cannot read.
        log.error("billing event names an unknown plan", extra={"plan": str(update.plan)[:40]})
        raise AppError(400, "unknown_plan", "The event names a plan that does not exist.")
    db.add(BillingEvent(id=update.event_id))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return False
    # Lock the row, so two webhooks delivered at once apply one after the other and the order check holds.
    sub = db.scalar(select(Subscription).where(Subscription.tenant_id == update.tenant_id).with_for_update())
    if sub is None:  # the tenant deleted their account; keep the event id, change nothing
        db.commit()
        return True
    # Stripe timestamps are whole seconds, so two events can share one. Tie-break: on equal timestamps a
    # cancellation already applied wins over any later non-cancel event (we can't know their true order, and
    # wrongly reactivating a cancelled customer costs money while a wrongly kept cancellation is fixed by the
    # customer's next, strictly newer, event). Cancel arriving after an activation at the same second still applies.
    # A different subscription id means a different subscription: never the "reactivation" of the cancelled one.
    other_sub = bool(update.provider_ref and sub.provider_ref and update.provider_ref != sub.provider_ref)
    if update.needs_paid_confirmation and update.provider_ref != sub.provider_ref:
        # T-173 S5: `active` without proof of payment (a delayed payment method may still be processing) cannot start
        # or replace a subscription; the paid checkout event does that. An update for the one we track is fine.
        db.commit()
        log.info("unconfirmed active subscription event ignored until the payment is confirmed")
        return True
    tombstone = _dead_marker(provider, update.provider_ref)
    if update.starts_subscription and tombstone and db.get(BillingEvent, tombstone) is not None:
        # T-174 B1/B2: this subscription was already seen cancelled before it was ever activated, so a late paid-looking
        # start event for the same ref must not grant access. Other refs are unaffected.
        db.commit()
        log.warning("start event for a subscription already cancelled is ignored",
                    extra={"tenant_id": str(update.tenant_id), "subscription": update.provider_ref})
        return True
    if update.provider_ref and update.status != "active" and sub.status == "trialing" and not sub.provider_ref:
        # T-174 (T-173 S-3): a failed first payment (past_due, incomplete_expired, deleted) for a subscription we never
        # activated must not end the free trial early. The trial runs to its end; only a paid checkout changes it.
        if update.status == "canceled" and tombstone:
            # remember this ref is dead (no migration: reuses the events table). A second cancel event for the same
            # ref finds the marker already there; never roll back the session for that, or this event's own dedup
            # row (flushed above) would go with it. The savepoint covers a concurrent insert of the marker.
            if db.get(BillingEvent, tombstone) is None:
                try:
                    with db.begin_nested():
                        db.add(BillingEvent(id=tombstone))
                except IntegrityError:
                    pass
        db.commit()
        log.info("event for a never-activated subscription ignored: the trial keeps running")
        return True
    if other_sub and not update.starts_subscription:
        # Only an event that starts a subscription may replace the current one. Anything else about another id
        # (cancel, past_due, or an old subscription becoming active again) must not touch the current subscription.
        db.commit()
        log.info("event for a different subscription ignored")
        return True
    duplicate = (other_sub and update.starts_subscription and update.status == "active" and sub.status == "active"
                 and sub.provider == provider
                 and has_access(sub.status, sub.trial_ends_at, current_period_end=sub.current_period_end))
    if duplicate:
        # T-172 B1: the tenant already pays for a working subscription. A second one must not silently replace it
        # (the first would keep billing, untracked). Keep the first, cancel the extra one at the provider.
        db.commit()
        log.warning("duplicate subscription for a tenant with an active one: cancelling the extra",
                    extra={"tenant_id": str(update.tenant_id), "extra_subscription": update.provider_ref})
        if billing is not None:
            try:
                billing.cancel_subscription(update.provider_ref)
            except Exception as error:
                # T-173 S1: nothing else changed for the tenant, so forget the event id and answer 5xx. Stripe
                # redelivers for days and the cancel is tried again. Until it works the customer is still charged
                # for the extra subscription, so the error stays in the log too.
                log.error("could not cancel the duplicate subscription (will be retried on redelivery)",
                          extra={"tenant_id": str(update.tenant_id), "extra_subscription": update.provider_ref},
                          exc_info=True)
                db.execute(delete(BillingEvent).where(BillingEvent.id == update.event_id))
                db.commit()
                raise AppError(503, "cancel_failed", "Could not cancel the extra subscription yet. Try again.") from error
        return True
    tie_after_cancel = (update.occurred_at is not None and update.occurred_at == sub.last_event_at
                        and sub.status == "canceled" and update.status != "canceled" and not other_sub)
    if update.occurred_at and sub.last_event_at and (update.occurred_at < sub.last_event_at or tie_after_cancel):
        db.commit()  # stale (arrived out of order): keep the event id, ignore its content
        log.info("stale billing event ignored")
        return True
    old_ref, old_provider = (sub.provider_ref, sub.provider) if (
        other_sub and update.starts_subscription and update.status == "active" and sub.status != "canceled") else (None, None)
    sub.status = update.status
    if update.plan in PLANS:
        sub.plan = update.plan
    if update.offer:
        sub.offer = update.offer
    if update.provider_ref:
        sub.provider_ref = update.provider_ref
    if update.customer_ref:
        sub.provider_customer = update.customer_ref
    if update.occurred_at:
        sub.last_event_at = update.occurred_at
    if update.current_period_end:
        sub.current_period_end = update.current_period_end
    sub.provider = provider
    if update.provider_ref and update.starts_subscription:
        # A ref that becomes current is no longer a to-do (it may have a row from an earlier takeover): cancelling it
        # would cancel what the customer just paid for.
        db.execute(delete(PendingCancel).where(PendingCancel.provider == provider,
                                               PendingCancel.ref == update.provider_ref))
    if old_ref and old_provider == provider:
        # T-175: write the to-do in the same transaction as the takeover, so a crash after the commit cannot lose it.
        # apply_update retries it right after this event (and again on the tenant's next event, or by the sweep).
        _record_pending_cancel(db, update.tenant_id, provider, old_ref)
    db.commit()
    log.info("subscription updated", extra={"status": update.status, "plan": sub.plan})
    if old_ref and old_provider != provider:
        log.warning("replaced subscription belongs to another provider: cancel it by hand there",
                    extra={"tenant_id": str(update.tenant_id), "old_subscription": old_ref,
                           "old_provider": old_provider})
    _fill_period_end(db, update, billing)
    return True


def _dead_marker(provider: str, ref: str | None) -> str | None:
    """Id of the BillingEvent row that marks `ref` as cancelled. Hashed so it always fits String(255)."""
    return f"dead:{provider}:{hashlib.sha256(ref.encode()).hexdigest()}" if ref else None


def _record_pending_cancel(db: Session, tenant_id: uuid.UUID, provider: str, ref: str) -> None:
    """Remember that `ref` must be cancelled at the provider. One row per (provider, ref)."""
    if db.scalar(select(PendingCancel.id).where(PendingCancel.provider == provider, PendingCancel.ref == ref)) is None:
        db.add(PendingCancel(tenant_id=tenant_id, provider=provider, ref=ref))


def _record_failed_attempt(db: Session, row: PendingCancel, error: Exception) -> int | None:
    """Count a failed cancel and return the new attempts value (None: the row is gone).
    T-180 (T-179 M2): if the commit fails (Postgres ended the idle transaction while the provider hung, 25P03, or the
    connection dropped), the lock is gone too. Roll back, open a fresh transaction, re-read the row and count the attempt
    there, so the backoff and the CRITICAL escalation keep working. A second failure propagates (the sweep logs it)."""
    row_id, message = row.id, f"{type(error).__name__}: {error}"[:500]
    try:
        row.attempts = (row.attempts or 0) + 1
        row.last_error = message
        row.last_attempt_at = datetime.now(timezone.utc)
        db.commit()
        return row.attempts
    except Exception:
        log.warning("could not record a failed cancel in the locked transaction; recording it in a new one",
                    exc_info=True)
        db.rollback()
    fresh = db.scalar(select(PendingCancel).where(PendingCancel.id == row_id).with_for_update()
                      .execution_options(populate_existing=True))
    if fresh is None:
        db.rollback()
        return None
    fresh.attempts = (fresh.attempts or 0) + 1
    fresh.last_error = message
    fresh.last_attempt_at = datetime.now(timezone.utc)
    db.commit()
    return fresh.attempts


def attempt_pending_cancel(db: Session, row_id: uuid.UUID, billing, *, backoff_now: datetime | None = None) -> bool | None:
    """Cancel one pending subscription at the provider. True: cancelled (row deleted). False: failed (attempt counted,
    error kept, ERROR logged: an unpaid-for duplicate may still be billing the customer). None: skipped, because the row
    is gone or locked by another worker, or its ref is the tenant's current subscription (the row is then dropped).
    The row is re-read FOR UPDATE SKIP LOCKED and stays locked until the commit after the cancel, so a takeover that
    makes this ref current waits for an in-flight cancel instead of racing it.
    backoff_now (the sweep passes it): after the locked read, also skip (None) a row whose backoff has not passed at that
    time, because another worker may have attempted it since the sweep listed it. The webhook retry leaves it unset and
    ignores the backoff on purpose (it only retries the first INLINE_RETRY_MAX_ATTEMPTS failures).
    A subscription the provider reports as already cancelled or gone counts as success (the adapter handles that)."""
    row = db.scalar(select(PendingCancel).where(PendingCancel.id == row_id).with_for_update(skip_locked=True)
                    .execution_options(populate_existing=True))
    if row is None:
        db.rollback()
        return None
    if (backoff_now is not None and row.last_attempt_at is not None
            and backoff_now - row.last_attempt_at < cancel_backoff(row.attempts or 0)):
        db.rollback()  # not due any more: release the lock
        return None
    todo = {"tenant_id": str(row.tenant_id), "old_subscription": row.ref, "old_provider": row.provider}
    sub = db.scalar(select(Subscription).where(Subscription.tenant_id == row.tenant_id)
                    .execution_options(populate_existing=True)) if row.tenant_id else None
    if sub is not None and sub.provider == row.provider and sub.provider_ref == row.ref:
        db.delete(row)
        db.commit()
        log.warning("pending cancel dropped: that subscription is the tenant's current one", extra=todo)
        return None
    try:
        billing.cancel_subscription(row.ref)
    except Exception as error:
        attempts = _record_failed_attempt(db, row, error)
        if attempts is None:  # the row vanished meanwhile (cancelled by another worker, or dropped)
            return False
        extra = {**todo, "attempts": attempts}
        if attempts == ESCALATE_AT:  # once, on the transition: the one line an operator should act on (ids only)
            log.critical("pending cancel needs operator", extra=extra)
        elif attempts > ESCALATE_AT:  # already escalated: keep the log quiet, the row stays visible in the table
            log.warning("could not cancel the replaced subscription (already escalated)", extra=extra, exc_info=True)
        else:
            log.error("could not cancel the replaced subscription: it is kept as a to-do and retried; cancel it by "
                      "hand at the provider if this repeats", extra=extra, exc_info=True)
        return False
    db.delete(row)
    db.commit()
    log.info("replaced subscription cancelled", extra=todo)
    return True


def retry_pending_cancels(db: Session, tenant_id: uuid.UUID, provider: str, billing) -> None:
    """T-175: try this tenant's pending cancels for `provider`. Runs after every billing event for the tenant.
    T-176: only rows with fewer than INLINE_RETRY_MAX_ATTEMPTS failures; the rest wait for the sweep."""
    ids = db.scalars(select(PendingCancel.id).where(PendingCancel.tenant_id == tenant_id,
                                                    PendingCancel.provider == provider,
                                                    PendingCancel.attempts < INLINE_RETRY_MAX_ATTEMPTS)
                     .order_by(PendingCancel.created_at)).all()
    for row_id in ids:
        attempt_pending_cancel(db, row_id, billing)


def _fill_period_end(db: Session, update: BillingUpdate, billing) -> None:
    """T-174 (T-173 S-2): a checkout event has no period end, so an active subscription would have no end date (open
    access) until its first renewal. Read it from the provider, outside any lock, and store it if still empty."""
    lookup = getattr(billing, "subscription_period_end", None)
    sub = db.scalar(select(Subscription).where(Subscription.tenant_id == update.tenant_id))
    if lookup is None or sub is None or sub.status != "active" or sub.current_period_end or not sub.provider_ref:
        return
    ref = sub.provider_ref
    db.commit()  # end the read transaction before the network call
    try:
        end = lookup(ref)
    except Exception:
        log.warning("could not read the subscription period end; the next renewal event will set it", exc_info=True)
        return
    if end:
        sub = db.scalar(select(Subscription).where(Subscription.tenant_id == update.tenant_id).with_for_update())
        if sub is not None and sub.provider_ref == ref and sub.current_period_end is None:
            sub.current_period_end = end
        db.commit()


MAX_WEBHOOK_BYTES = 256_000


async def _read_limited(request: Request, limit: int) -> bytes:
    """Read the body but stop as soon as it passes `limit`, so a huge request can't exhaust memory."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise AppError(413, "too_large", "Payload too large.")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise AppError(413, "too_large", "Payload too large.")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Called by the payment provider, not the browser: no cookie, no CSRF header, signature instead."""
    payload = await _read_limited(request, MAX_WEBHOOK_BYTES)
    signature = request.headers.get("stripe-signature") or request.headers.get("x-billing-signature", "")
    try:
        update = request.app.state.billing.parse_webhook(payload, signature)
    except AppError:  # bad signature and the like keep their own answer
        raise
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError, OSError):
        # Correctly signed but malformed (not an object, no id, timestamp out of range): a 400 is a clear, final
        # answer; a 500 would make the provider retry and fill the error log. OSError is here for
        # datetime.fromtimestamp on huge values: parse_webhook does no I/O, so keep this try block around
        # parsing only (never widen it around database or network calls).
        log.warning("malformed billing webhook rejected", exc_info=True)
        raise AppError(400, "bad_event", "The event could not be read.")
    if update is None:
        return {"received": True, "applied": False}
    applied = await run_in_threadpool(apply_update, db, update, request.app.state.billing.name,
                                      request.app.state.billing)
    return {"received": True, "applied": applied}


@router.post("/mock/complete/{session_id}")
def mock_complete(session_id: str, request: Request, me: Current = Depends(owner), db: Session = Depends(get_db)):
    """Dev and demo only: pretend the customer paid. Goes through the same signed webhook path."""
    billing = request.app.state.billing
    if not isinstance(billing, MockBilling) or not request.app.state.settings.mock_checkout_enabled:
        raise AppError(404, "not_found", "Not available.")
    session = billing.sessions.get(session_id)
    if session is None or session["tenant_id"] != str(me.tenant.id):
        raise AppError(404, "not_found", "Unknown checkout session.")
    payload = billing.completion_event(session_id)
    update = billing.parse_webhook(payload, sign(payload, billing.secret))
    apply_update(db, update, billing.name, billing)
    sub = subscription_of(db, me.tenant.id)
    return {"plan": sub.plan, "status": sub.status, "offer": sub.offer}
