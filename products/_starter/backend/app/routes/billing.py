"""Plans, checkout and the payment provider's webhook. Test mode only (see app/billing.py)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..billing import OFFERS, PLANS, BillingUpdate, MockBilling, sign
from ..db import get_db
from ..deps import Current, owner, require_csrf_header, subscription_of
from ..errors import AppError
from ..models import BillingEvent, Subscription

log = logging.getLogger("app.billing")
router = APIRouter(prefix="/api/billing", tags=["billing"])


class CheckoutIn(BaseModel):
    plan: str = Field(max_length=40)
    offer_code: str | None = Field(default=None, max_length=40)


@router.get("/plans")
def plans():
    return {
        "plans": [{"id": p.id, "name": p.name, "price_pence": p.price_pence, "currency": p.currency,
                   "interval": p.interval, "ai_monthly_tokens": p.ai_monthly_tokens}
                  for p in PLANS.values() if p.id != "trial"],
        "offers": [{"code": o.code, "description": o.description} for o in OFFERS.values()],
    }


@router.post("/checkout", dependencies=[Depends(require_csrf_header)])
def checkout(data: CheckoutIn, request: Request, me: Current = Depends(owner)):
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


def apply_update(db: Session, update: BillingUpdate, provider: str) -> bool:
    """Apply a provider event once. Returns False if this event id was already applied."""
    db.add(BillingEvent(id=update.event_id))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return False
    sub = db.scalar(select(Subscription).where(Subscription.tenant_id == update.tenant_id))
    if sub is None:  # the tenant deleted their account; keep the event id, change nothing
        db.commit()
        return True
    sub.status = update.status
    if update.plan in PLANS:
        sub.plan = update.plan
    if update.offer:
        sub.offer = update.offer
    if update.provider_ref:
        sub.provider_ref = update.provider_ref
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
    update = request.app.state.billing.parse_webhook(payload, signature)
    if update is None:
        return {"received": True, "applied": False}
    applied = await run_in_threadpool(apply_update, db, update, request.app.state.billing.name)
    return {"received": True, "applied": applied}


@router.post("/mock/complete/{session_id}", dependencies=[Depends(require_csrf_header)])
def mock_complete(session_id: str, request: Request, me: Current = Depends(owner), db: Session = Depends(get_db)):
    """Dev and demo only: pretend the customer paid. Goes through the same signed webhook path."""
    billing = request.app.state.billing
    if not isinstance(billing, MockBilling) or request.app.state.settings.env == "prod":
        raise AppError(404, "not_found", "Not available.")
    session = billing.sessions.get(session_id)
    if session is None or session["tenant_id"] != str(me.tenant.id):
        raise AppError(404, "not_found", "Unknown checkout session.")
    payload = billing.completion_event(session_id)
    update = billing.parse_webhook(payload, sign(payload, billing.secret))
    apply_update(db, update, billing.name)
    sub = subscription_of(db, me.tenant.id)
    return {"plan": sub.plan, "status": sub.status, "offer": sub.offer}
