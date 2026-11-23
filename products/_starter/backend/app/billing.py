"""Billing adapter: plans, a free trial and an early-customer offer, behind one interface.

- MockBilling: default. No network, no money. Signs its webhooks the same way Stripe does.
- StripeBilling: Stripe TEST MODE only. Live keys are refused outright; nothing in the starter
  may take a real payment before Vishal sends `unlock selling` and a product ADR changes this.
Both share the contract tests in tests/test_billing_contract.py.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

import httpx

from .errors import AppError


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_pence: int
    ai_monthly_tokens: int
    currency: str = "gbp"
    interval: str = "month"


@dataclass(frozen=True)
class Offer:
    code: str
    percent_off: int
    months: int
    description: str


# Placeholder prices. Each product sets its own in its SPEC.md (strategist) and here.
PLANS: dict[str, Plan] = {
    "trial": Plan("trial", "Free trial", 0, ai_monthly_tokens=100_000),
    "starter": Plan("starter", "Starter", 2900, ai_monthly_tokens=500_000),
    "pro": Plan("pro", "Pro", 7900, ai_monthly_tokens=2_000_000),
}
OFFERS: dict[str, Offer] = {
    "EARLY50": Offer("EARLY50", 50, 3, "Early customers: 50% off for the first 3 months"),
}
ACTIVE_STATUSES = {"active", "trialing"}


@dataclass(frozen=True)
class Checkout:
    id: str
    url: str


@dataclass(frozen=True)
class BillingUpdate:
    """A provider event, reduced to what the app stores."""
    event_id: str
    tenant_id: uuid.UUID
    status: str  # active | past_due | canceled
    plan: str | None = None
    offer: str | None = None
    provider_ref: str | None = None
    current_period_end: datetime | None = None


class InvalidSignature(AppError):
    def __init__(self):
        super().__init__(400, "invalid_signature", "Webhook signature check failed.")


class BillingProvider(Protocol):
    name: str

    def create_checkout(self, tenant_id: uuid.UUID, plan: Plan, offer: Offer | None,
                        success_url: str, cancel_url: str) -> Checkout: ...

    def parse_webhook(self, payload: bytes, signature: str) -> BillingUpdate | None: ...


def sign(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Stripe-style signature header: t=<unix>,v1=<hex hmac-sha256 of "t.payload">."""
    ts = int(time.time()) if timestamp is None else timestamp
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def verify(payload: bytes, header: str, secret: str, tolerance: int = 300) -> None:
    parts = [p.split("=", 1) for p in (header or "").split(",") if "=" in p]
    timestamps = [v for k, v in parts if k == "t"]
    signatures = [v for k, v in parts if k == "v1"]
    if not timestamps or not signatures or not timestamps[0].isdigit():
        raise InvalidSignature()
    ts = int(timestamps[0])
    if abs(time.time() - ts) > tolerance:
        raise InvalidSignature()
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in signatures):
        raise InvalidSignature()


def _tenant(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class MockBilling:
    name = "mock"

    def __init__(self, webhook_secret: str, base_url: str):
        self.secret, self.base_url = webhook_secret, base_url.rstrip("/")
        self.sessions: dict[str, dict] = {}

    def create_checkout(self, tenant_id, plan, offer, success_url, cancel_url) -> Checkout:
        session_id = f"mock_cs_{uuid.uuid4().hex}"
        self.sessions[session_id] = {"tenant_id": str(tenant_id), "plan": plan.id,
                                     "offer": offer.code if offer else None}
        return Checkout(session_id, f"{self.base_url}/billing/mock-checkout?session={session_id}")

    def completion_event(self, session_id: str) -> bytes:
        """What the mock 'provider' would post when the customer pays. Used by the dev endpoint and tests."""
        session = self.sessions.get(session_id)
        if session is None:
            raise AppError(404, "not_found", "Unknown checkout session.")
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
        event = {"id": f"mock_evt_{uuid.uuid4().hex}", "type": "checkout.completed",
                 "data": {**session, "subscription": f"mock_sub_{session_id[8:20]}",
                          "current_period_end": int(period_end.timestamp())}}
        return json.dumps(event).encode()

    def parse_webhook(self, payload: bytes, signature: str) -> BillingUpdate | None:
        verify(payload, signature, self.secret)
        event = json.loads(payload)
        data = event.get("data") or {}
        tenant = _tenant(data.get("tenant_id"))
        if tenant is None:
            return None
        status = {"checkout.completed": "active", "subscription.past_due": "past_due",
                  "subscription.canceled": "canceled"}.get(event.get("type"))
        if status is None:
            return None
        end = data.get("current_period_end")
        return BillingUpdate(event_id=str(event["id"]), tenant_id=tenant, status=status, plan=data.get("plan"),
                             offer=data.get("offer"), provider_ref=data.get("subscription"),
                             current_period_end=datetime.fromtimestamp(end, timezone.utc) if end else None)


class StripeBilling:
    """Stripe test mode via its REST API. Not exercised against Stripe until test keys exist."""
    name = "stripe"
    API = "https://api.stripe.com/v1"

    def __init__(self, secret_key: str, webhook_secret: str, client: httpx.Client | None = None):
        if not secret_key.startswith(("sk_test_", "rk_test_")):
            raise ValueError("Only Stripe test-mode keys are allowed (sk_test_/rk_test_). Live mode is locked.")
        self.key, self.secret = secret_key, webhook_secret
        self.client = client or httpx.Client(timeout=20.0)

    def create_checkout(self, tenant_id, plan, offer, success_url, cancel_url) -> Checkout:
        form = {
            "mode": "subscription", "success_url": success_url, "cancel_url": cancel_url,
            "client_reference_id": str(tenant_id),
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": plan.currency,
            "line_items[0][price_data][unit_amount]": str(plan.price_pence),
            "line_items[0][price_data][recurring][interval]": plan.interval,
            "line_items[0][price_data][product_data][name]": plan.name,
            "subscription_data[metadata][tenant_id]": str(tenant_id),
            "subscription_data[metadata][plan]": plan.id,
            "allow_promotion_codes": "true",  # the early-customer offer is a Stripe promotion code
        }
        if offer:
            form["subscription_data[metadata][offer]"] = offer.code
        for attempt in range(3):
            try:
                response = self.client.post(f"{self.API}/checkout/sessions", data=form,
                                            auth=(self.key, ""), headers={"Idempotency-Key": f"{tenant_id}-{plan.id}-{int(time.time() // 60)}"})
            except httpx.TransportError as error:
                if attempt == 2:
                    raise AppError(503, "billing_unavailable", "Payments are unavailable. Try again shortly.") from error
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    raise AppError(503, "billing_unavailable", "Payments are unavailable. Try again shortly.")
                time.sleep(2 ** attempt)
                continue
            if response.status_code >= 400:
                raise AppError(502, "billing_rejected", "The payment provider rejected the checkout.")
            body = response.json()
            return Checkout(body["id"], body["url"])
        raise AppError(503, "billing_unavailable", "Payments are unavailable. Try again shortly.")

    def parse_webhook(self, payload: bytes, signature: str) -> BillingUpdate | None:
        verify(payload, signature, self.secret)
        event = json.loads(payload)
        obj = (event.get("data") or {}).get("object") or {}
        kind = event.get("type")
        if kind == "checkout.session.completed":
            tenant = _tenant(obj.get("client_reference_id"))
            return tenant and BillingUpdate(str(event["id"]), tenant, "active", provider_ref=obj.get("subscription"))
        if kind in ("customer.subscription.updated", "customer.subscription.deleted"):
            meta = obj.get("metadata") or {}
            tenant = _tenant(meta.get("tenant_id"))
            status = "canceled" if kind.endswith("deleted") else {
                "active": "active", "trialing": "active", "past_due": "past_due", "unpaid": "past_due",
                "canceled": "canceled", "incomplete_expired": "canceled"}.get(obj.get("status"))
            end = obj.get("current_period_end")
            if tenant is None or status is None:
                return None
            return BillingUpdate(str(event["id"]), tenant, status, plan=meta.get("plan"), offer=meta.get("offer"),
                                 provider_ref=obj.get("id"),
                                 current_period_end=datetime.fromtimestamp(end, timezone.utc) if end else None)
        return None


def build_billing(settings) -> BillingProvider:
    if settings.billing_provider == "stripe":
        return StripeBilling(settings.stripe_secret_key, settings.billing_webhook_secret)
    return MockBilling(settings.billing_webhook_secret, settings.app_base_url)


def has_access(status: str, trial_ends_at: datetime | None, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if status == "active":
        return True
    return status == "trialing" and trial_ends_at is not None and trial_ends_at > now
