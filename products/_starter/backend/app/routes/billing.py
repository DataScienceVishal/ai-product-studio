"""Plans, checkout and the payment provider's webhook. Test mode only (see app/billing.py)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..billing import LIMITED_PROVIDERS, OFFERS, PLANS, BillingUpdate, MockBilling, has_access, sign
from ..db import get_db
from ..deps import Current, owner, subscription_of, verified_owner
from ..errors import AppError
from ..models import BillingEvent, Subscription

log = logging.getLogger("app.billing")
router = APIRouter(prefix="/api/billing", tags=["billing"])


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
        # (routes/notes.py), so the page must not promise the plan's own allowance yet.
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
    for name, limit in (("plan", 40), ("offer", 40), ("provider_ref", 255), ("customer_ref", 255)):
        value = getattr(update, name)
        if value is not None and (not isinstance(value, str) or len(value) > limit):
            log.warning("billing event has an unreadable field", extra={"field": name})
            raise AppError(400, "bad_event", "The event could not be read.")


def apply_update(db: Session, update: BillingUpdate, provider: str, billing=None) -> bool:
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
    if other_sub and not update.starts_subscription:
        # Only an event that starts a subscription may replace the current one. Anything else about another id
        # (cancel, past_due, or an old subscription becoming active again) must not touch the current subscription.
        db.commit()
        log.info("event for a different subscription ignored")
        return True
    tie_after_cancel = (update.occurred_at is not None and update.occurred_at == sub.last_event_at
                        and sub.status == "canceled" and update.status != "canceled" and not other_sub)
    if update.occurred_at and sub.last_event_at and (update.occurred_at < sub.last_event_at or tie_after_cancel):
        db.commit()  # stale (arrived out of order): keep the event id, ignore its content
        log.info("stale billing event ignored")
        return True
    duplicate = (other_sub and update.starts_subscription and update.status == "active" and sub.status == "active"
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
            except Exception:  # never fail the webhook (the event is recorded); the log line is the to-do
                log.error("could not cancel the duplicate subscription: cancel or refund it by hand",
                          extra={"tenant_id": str(update.tenant_id), "extra_subscription": update.provider_ref},
                          exc_info=True)
        return True
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
    db.commit()
    log.info("subscription updated", extra={"status": update.status, "plan": sub.plan})
    return True


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
