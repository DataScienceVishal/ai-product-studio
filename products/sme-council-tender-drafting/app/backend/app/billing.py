"""Billing adapter: plans, a free trial and an early-customer offer, behind one interface.

- MockBilling: default. No network, no money. Signs its webhooks the same way Stripe does.
- StripeBilling: Stripe TEST MODE only. Live keys are refused outright; nothing in the starter
  may take a real payment before Vishal sends `unlock selling` and a product ADR changes this.
Both share the contract tests in tests/test_billing.py.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
import uuid
from urllib.parse import quote
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
    ai_daily_tokens: int | None = None  # extra daily cap, used for free trials
    currency: str = "gbp"
    interval: str = "month"


@dataclass(frozen=True)
class Offer:
    code: str
    percent_off: int
    months: int
    description: str

    @property
    def coupon_id(self) -> str:
        """Deterministic Stripe coupon id. The terms are in the id, so changing percent or months makes a NEW coupon
        (a Stripe coupon cannot be edited); bump the trailing version if the way coupons are made ever changes."""
        return f"studio-{self.code.lower()}-{self.percent_off}pc-{self.months}m-v1"


# Placeholder prices. Each product sets its own in its SPEC.md (strategist) and here.
PLANS: dict[str, Plan] = {
    "trial": Plan("trial", "Free trial", 0, ai_monthly_tokens=100_000, ai_daily_tokens=30_000),
    "starter": Plan("starter", "Starter", 2900, ai_monthly_tokens=500_000),
    "pro": Plan("pro", "Pro", 7900, ai_monthly_tokens=2_000_000),
}

# Providers whose plans get the free-trial AI allowance, whatever plan was bought: mock is a demo and Stripe is
# test-mode only until `unlock selling`, so neither plan has been paid for yet. Remove "stripe" in the same change
# that allows live keys (a selling ADR). Used by the AI cap (app/ai.py callers) and the plans list (routes/billing.py).
LIMITED_PROVIDERS = {"mock", "stripe"}

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
    customer_ref: str | None = None
    current_period_end: datetime | None = None
    occurred_at: datetime | None = None  # when the provider created the event, to ignore stale ones
    # True only for events that begin a subscription (checkout completed, subscription created). Only those may
    # replace the tenant's current provider_ref; an update for another id (an old subscription recovering) may not.
    starts_subscription: bool = False
    # True for a Stripe subscription event that says `active` without proof the first payment succeeded. With delayed
    # payment methods (Bacs, SEPA) Stripe reports `active` while the PaymentIntent is still `processing`. Such an event
    # may update the subscription we already track as paid, but never starts or replaces one: that waits for
    # checkout.session.completed (payment_status paid) or checkout.session.async_payment_succeeded.
    needs_paid_confirmation: bool = False


class InvalidSignature(AppError):
    def __init__(self):
        super().__init__(400, "invalid_signature", "Webhook signature check failed.")


class BillingProvider(Protocol):
    name: str

    def create_checkout(self, tenant_id: uuid.UUID, plan: Plan, offer: Offer | None,
                        success_url: str, cancel_url: str) -> Checkout: ...

    def portal_session(self, customer_ref: str, return_url: str) -> str:
        """URL of a provider-hosted page where the customer manages their payment method and subscription."""
        ...

    def parse_webhook(self, payload: bytes, signature: str) -> BillingUpdate | None: ...

    def close(self, customer_ref: str | None, subscription_ref: str | None) -> None:
        """Stop billing and remove the customer at the provider (account deletion). Raises on failure."""
        ...

    def cancel_subscription(self, subscription_ref: str) -> None:
        """Cancel one subscription (a duplicate the tenant bought twice). Raises on failure."""
        ...


def sign(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Stripe-style signature header: t=<unix>,v1=<hex hmac-sha256 of "t.payload">."""
    ts = int(time.time()) if timestamp is None else timestamp
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def verify(payload: bytes, header: str, secret: str, tolerance: int = 300) -> None:
    if not secret:
        raise InvalidSignature()  # an empty secret would let anyone sign
    parts = [p.split("=", 1) for p in (header or "").split(",") if "=" in p]
    timestamps = [v for k, v in parts if k == "t"]
    signatures = [v for k, v in parts if k == "v1"]
    if not timestamps or not signatures or not re.fullmatch(r"[0-9]{1,12}", timestamps[0]):  # ASCII digits only
        raise InvalidSignature()
    ts = int(timestamps[0])
    if abs(time.time() - ts) > tolerance:
        raise InvalidSignature()
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in signatures):
        raise InvalidSignature()


def _when(timestamp) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(timestamp), timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _tenant(value) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


class MockBilling:
    name = "mock"

    MAX_SESSIONS = 1000  # in memory, so keep only the newest

    def __init__(self, webhook_secret: str, base_url: str):
        self.secret, self.base_url = webhook_secret, base_url.rstrip("/")
        self.sessions: dict[str, dict] = {}
        self.closed: list[tuple[str | None, str | None]] = []
        self.cancelled: list[str] = []

    def create_checkout(self, tenant_id, plan, offer, success_url, cancel_url) -> Checkout:
        session_id = f"mock_cs_{uuid.uuid4().hex}"
        while len(self.sessions) >= self.MAX_SESSIONS:
            self.sessions.pop(next(iter(self.sessions)))
        self.sessions[session_id] = {"tenant_id": str(tenant_id), "plan": plan.id,
                                     "offer": offer.code if offer else None}
        return Checkout(session_id, f"{self.base_url}/billing/mock-checkout?session={session_id}")

    def portal_session(self, customer_ref, return_url) -> str:
        return f"{self.base_url}/billing/mock-portal?customer={quote(customer_ref, safe='')}"

    def completion_event(self, session_id: str) -> bytes:
        """What the mock 'provider' would post when the customer pays. Used by the dev endpoint and tests."""
        session = self.sessions.get(session_id)
        if session is None:
            raise AppError(404, "not_found", "Unknown checkout session.")
        period_end = datetime.now(timezone.utc) + timedelta(days=30)
        event = {"id": f"mock_evt_{uuid.uuid4().hex}", "type": "checkout.completed", "created": int(time.time()),
                 "data": {**session, "subscription": f"mock_sub_{session_id[8:20]}",
                          "customer": f"mock_cus_{session['tenant_id'].replace('-', '')}",
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
        occurred_at = _when(event.get("created"))
        if occurred_at is None:  # without a timestamp the ordering check cannot protect a newer state
            raise ValueError("billing event has no usable created timestamp")
        end = data.get("current_period_end")
        return BillingUpdate(event_id=event["id"], tenant_id=tenant, status=status, plan=data.get("plan"),
                             offer=data.get("offer"), provider_ref=data.get("subscription"),
                             customer_ref=data.get("customer"),
                             current_period_end=datetime.fromtimestamp(end, timezone.utc) if end else None,
                             occurred_at=occurred_at,
                             starts_subscription=event.get("type") == "checkout.completed")

    def close(self, customer_ref, subscription_ref) -> None:
        self.closed.append((customer_ref, subscription_ref))

    def subscription_period_end(self, subscription_ref) -> datetime | None:
        return None  # mock completion events already carry the period end

    def cancel_subscription(self, subscription_ref) -> None:
        if subscription_ref not in self.cancelled:  # cancelling twice is a no-op, like a canceled Stripe subscription
            self.cancelled.append(subscription_ref)


# T-180 (T-179 M2): the cancel budget. DELETE gets 2 tries (4 s each, 1 s backoff between), the "is it already canceled?"
# GET after a rejected DELETE gets 1. The worst case is a slow DELETE (4 + 1 + 4 = 9 s), or a slow first try, a fast
# rejection, then a slow GET (4 + 1 + 0 + 4 = 9 s). Keep it well under the idle-in-transaction timeout (15 s by
# default, app/config.py and app/db.py), because the pending-cancel path makes this call inside an open transaction.
CANCEL_REQUEST_TIMEOUT = 4.0
CANCEL_DELETE_ATTEMPTS = 2
CANCEL_CHECK_ATTEMPTS = 1
_CANCEL_BACKOFF = 1.0  # _call sleeps 2**attempt: 1 s after a first failed try


def _cancel_worst_case() -> float:
    delete = CANCEL_DELETE_ATTEMPTS * CANCEL_REQUEST_TIMEOUT + (CANCEL_DELETE_ATTEMPTS - 1) * _CANCEL_BACKOFF
    check = CANCEL_CHECK_ATTEMPTS * CANCEL_REQUEST_TIMEOUT + (CANCEL_CHECK_ATTEMPTS - 1) * _CANCEL_BACKOFF
    rejected_then_check = (CANCEL_DELETE_ATTEMPTS - 1) * (CANCEL_REQUEST_TIMEOUT + _CANCEL_BACKOFF) + check
    return max(delete, rejected_then_check)


CANCEL_WORST_CASE_SECONDS = _cancel_worst_case()
assert CANCEL_WORST_CASE_SECONDS <= 10, "the cancel call runs inside a row lock: keep it under the idle-in-transaction timeout"


class StripeBilling:
    """Stripe test mode via its REST API. Not exercised against Stripe until test keys exist."""
    name = "stripe"
    API = "https://api.stripe.com/v1"
    CANCEL_TIMEOUT = CANCEL_REQUEST_TIMEOUT  # seconds, for calls made while a webhook waits (cancel, period end lookup)

    def __init__(self, secret_key: str, webhook_secret: str, client: httpx.Client | None = None, api_version: str = ""):
        if not secret_key.startswith(("sk_test_", "rk_test_")):
            raise ValueError("Only Stripe test-mode keys are allowed (sk_test_/rk_test_). Live mode is locked.")
        self.key, self.secret = secret_key, webhook_secret
        self.client = client or httpx.Client(timeout=20.0)
        self.headers = {"Stripe-Version": api_version} if api_version else {}
        self._coupons: set[str] = set()  # coupon ids already ensured (and checked) in this process

    def _call(self, method: str, path: str, form: dict | None = None, idempotency_key: str | None = None,
              accept_error_codes: frozenset[str] = frozenset(), timeout: float | None = None,
              attempts: int = 3) -> dict:
        """accept_error_codes: Stripe error codes on a 400 that the caller treats as an answer, not a failure.
        The reply body is then returned (read `error.code`). Any other 4xx still raises billing_rejected.
        timeout/attempts: per-request timeout (default: the client's) and the number of tries for a transport error,
        429 or 5xx. A 4xx is never retried."""
        last = attempts - 1
        extra = {} if timeout is None else {"timeout": timeout}
        headers = dict(self.headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key  # one key per logical request, reused across retries
        for attempt in range(attempts):
            try:
                response = self.client.request(method, f"{self.API}{path}", data=form, auth=(self.key, ""), headers=headers,
                                               **extra)
            except httpx.TransportError as error:
                if attempt == last:
                    raise AppError(503, "billing_unavailable", "Payments are unavailable. Try again shortly.") from error
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == last:
                    raise AppError(503, "billing_unavailable", "Payments are unavailable. Try again shortly.")
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 404 and method == "DELETE":
                return {}  # already gone
            if response.status_code == 400 and accept_error_codes:
                try:
                    error = (response.json().get("error") or {})
                except (ValueError, AttributeError):
                    error = {}
                if error.get("code") in accept_error_codes:
                    return {"error": error}
            if response.status_code >= 400:
                raise AppError(502, "billing_rejected", "The payment provider rejected the request.")
            try:
                return response.json()
            except ValueError:
                raise AppError(502, "billing_rejected", "The payment provider sent an unreadable reply.") from None
        raise AppError(503, "billing_unavailable", "Payments are unavailable. Try again shortly.")

    def ensure_coupon(self, offer: Offer) -> str:
        """Make sure the offer's coupon exists in Stripe (test mode) and return its id. Safe to call repeatedly.

        POST /coupons with the deterministic id and an Idempotency-Key. If the coupon already exists (an earlier run,
        another instance) we GET it once and check it carries these exact terms; a mismatch is an error, never a
        silent discount of the wrong size. Only `resource_already_exists` is tolerated; other 400s raise."""
        coupon_id = offer.coupon_id
        if coupon_id in self._coupons:
            return coupon_id
        form = {"id": coupon_id, "percent_off": str(offer.percent_off), "duration": "repeating",
                "duration_in_months": str(offer.months), "name": f"{offer.code} {offer.percent_off}% off for {offer.months} months"[:40]}  # Stripe max 40
        body = self._call("POST", "/coupons", form, idempotency_key=f"coupon-{coupon_id}-{uuid.uuid4().hex}",  # fresh per call: a fixed key
                          # would 409 on concurrent first checkouts and replay stale results for 24 h
                          accept_error_codes=frozenset({"resource_already_exists"}))
        if (body.get("error") or {}).get("code") == "resource_already_exists":
            existing = self._call("GET", f"/coupons/{coupon_id}")
            if (existing.get("percent_off") != offer.percent_off or existing.get("duration") != "repeating"
                    or existing.get("duration_in_months") != offer.months or existing.get("valid") is False):
                raise AppError(502, "billing_rejected", "The payment provider's early-customer coupon does not match the offer.")
        self._coupons.add(coupon_id)
        return coupon_id

    def create_checkout(self, tenant_id, plan, offer, success_url, cancel_url) -> Checkout:
        meta = {"tenant_id": str(tenant_id), "plan": plan.id, "offer": offer.code if offer else ""}
        form = {
            "mode": "subscription", "success_url": success_url, "cancel_url": cancel_url,
            "client_reference_id": str(tenant_id),
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": plan.currency,
            "line_items[0][price_data][unit_amount]": str(plan.price_pence),
            "line_items[0][price_data][recurring][interval]": plan.interval,
            "line_items[0][price_data][product_data][name]": plan.name,
        }
        # Decision (T-15): only offers the app validated exist. The offer is applied here, server-side, as a coupon;
        # allow_promotion_codes is NOT sent (Stripe rejects it together with discounts, and it would let customers
        # type codes the app never checked or recorded).
        coupon_id = None
        if offer:
            coupon_id = form["discounts[0][coupon]"] = self.ensure_coupon(offer)
        for key, value in meta.items():  # on the session (read at checkout.session.completed) and the subscription
            form[f"metadata[{key}]"] = value
            form[f"subscription_data[metadata][{key}]"] = value
        try:
            body = self._call("POST", "/checkout/sessions", form, idempotency_key=f"checkout-{uuid.uuid4().hex}")
        except AppError as error:
            # billing_rejected (any non-429 4xx, or a 2xx whose body _call could not parse) may mean the cached coupon was deleted or archived:
            # re-check it next time.
            # An outage (billing_unavailable) says nothing about the coupon, so keep it cached.
            if coupon_id and error.code == "billing_rejected":
                self._coupons.discard(coupon_id)
            raise
        # Keep this outside the try: the request succeeded, so the coupon is fine and must stay cached. (This differs
        # from an unparseable 2xx, which _call itself rejects above and so does drop the coupon: a body we cannot
        # read tells us nothing, whereas a readable but incomplete one shows Stripe accepted the discount.)
        if not body.get("id") or not body.get("url"):
            raise AppError(502, "billing_rejected", "The payment provider sent an incomplete reply.")
        return Checkout(body["id"], body["url"])

    def portal_session(self, customer_ref, return_url) -> str:
        # The key is random per call on purpose. A portal session is a short-lived URL, so replaying a shared key
        # within Stripe's 24 h window would return a stale or expired URL. It only satisfies _call, which sends a key
        # on every POST; it gives no idempotency (and none is needed: creating a second session is harmless).
        body = self._call("POST", "/billing_portal/sessions", {"customer": customer_ref, "return_url": return_url},
                          idempotency_key=f"portal-{uuid.uuid4().hex}")
        if not body.get("url"):
            raise AppError(502, "billing_rejected", "The payment provider sent an incomplete reply.")
        return body["url"]

    def close(self, customer_ref, subscription_ref) -> None:
        if customer_ref:  # deleting the customer cancels their subscriptions and removes their details
            self._call("DELETE", f"/customers/{customer_ref}")
        elif subscription_ref:
            self._call("DELETE", f"/subscriptions/{subscription_ref}")

    def cancel_subscription(self, subscription_ref) -> None:
        """404 (already gone) counts as done. Stripe's docs do not say what DELETE answers for a subscription that is
        already canceled (a second extra-subscription event, a redelivery), so a rejected cancel is checked with a GET:
        a `canceled` status means the goal is met. Outages and a live subscription still raise."""
        # T-174 S2: this runs inside a webhook, which Stripe abandons after a few seconds of waiting, so use a short
        # timeout and one retry instead of the default 3 x 20 s. A failure answers 503 and Stripe redelivers (T-173 S1),
        # so the retry here only smooths over a blip.
        # T-180 (T-179 M2): the pending-cancel path calls this while holding a row lock in an open transaction, which
        # Postgres ends after idle_in_transaction_session_timeout (15 s). The budget is therefore CANCEL_WORST_CASE_SECONDS
        # (9 s), asserted below to stay under that timeout.
        path = f"/subscriptions/{quote(str(subscription_ref), safe='')}"
        try:
            self._call("DELETE", path, timeout=self.CANCEL_TIMEOUT, attempts=CANCEL_DELETE_ATTEMPTS)
        except AppError as error:
            if error.code != "billing_rejected":
                raise
            if self._call("GET", path, timeout=self.CANCEL_TIMEOUT, attempts=CANCEL_CHECK_ATTEMPTS).get("status") != "canceled":
                raise

    def subscription_period_end(self, subscription_ref) -> datetime | None:
        """When the current paid period ends (a checkout event does not carry it). Raises on failure."""
        path = f"/subscriptions/{quote(str(subscription_ref), safe='')}"
        return self._period_end(self._call("GET", path, timeout=self.CANCEL_TIMEOUT, attempts=2))

    @staticmethod
    def _period_end(obj: dict) -> datetime | None:
        end = obj.get("current_period_end")
        if end is None:  # newer API versions keep it on the subscription items
            items = ((obj.get("items") or {}).get("data") or [{}])
            end = (items[0] or {}).get("current_period_end")
        return datetime.fromtimestamp(end, timezone.utc) if end else None

    def parse_webhook(self, payload: bytes, signature: str) -> BillingUpdate | None:
        verify(payload, signature, self.secret)
        event = json.loads(payload)
        if event.get("livemode") is True:  # second guard for the selling lock: never act on live events
            return None
        obj = (event.get("data") or {}).get("object") or {}
        kind = event.get("type")
        meta = obj.get("metadata") or {}
        if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            # A delayed payment method (bank debit) completes the session while still unpaid: wait for
            # async_payment_succeeded. async_payment_failed changes nothing here: Stripe's subscription events
            # (incomplete_expired / unpaid) report the outcome.
            if obj.get("payment_status") not in ("paid", "no_payment_required"):
                return None
            tenant = _tenant(meta.get("tenant_id") or obj.get("client_reference_id"))
            if tenant is None:
                return None
            return BillingUpdate(event["id"], tenant, "active", plan=meta.get("plan") or None,
                                 offer=meta.get("offer") or None, provider_ref=obj.get("subscription"),
                                 customer_ref=obj.get("customer"), occurred_at=_when(event.get("created")),
                                 starts_subscription=True)
        if kind in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
            tenant = _tenant(meta.get("tenant_id"))
            status = "canceled" if kind.endswith("deleted") else {
                "active": "active", "trialing": "active", "past_due": "past_due", "unpaid": "past_due",
                "canceled": "canceled", "incomplete_expired": "canceled"}.get(obj.get("status"))
            if tenant is None or status is None:
                return None
            invoice = obj.get("latest_invoice")  # an id string unless the endpoint expands it
            paid_proof = isinstance(invoice, dict) and invoice.get("status") == "paid"
            return BillingUpdate(event["id"], tenant, status, plan=meta.get("plan") or None,
                                 offer=meta.get("offer") or None, provider_ref=obj.get("id"),
                                 customer_ref=obj.get("customer"), current_period_end=self._period_end(obj),
                                 occurred_at=_when(event.get("created")),
                                 starts_subscription=kind.endswith("created"),
                                 needs_paid_confirmation=status == "active" and not paid_proof)
        return None


def build_billing(settings) -> BillingProvider:
    if settings.billing_provider == "stripe":
        return StripeBilling(settings.stripe_secret_key, settings.billing_webhook_secret,
                             api_version=settings.stripe_api_version)
    return MockBilling(settings.billing_webhook_secret, settings.app_base_url)


GRACE = timedelta(days=3)  # a renewal webhook can arrive late


def has_access(status: str, trial_ends_at: datetime | None, now: datetime | None = None,
               current_period_end: datetime | None = None, billing_enabled: bool = True) -> bool:
    """With billing off there is no plan to buy, so a trial never lapses (the AI daily and monthly caps still apply)."""
    if not billing_enabled and status in ("trialing", "active"):
        return True
    now = now or datetime.now(timezone.utc)
    if status == "active":  # a paid period that ended (plus grace) without renewal no longer counts
        return current_period_end is None or current_period_end + GRACE > now
    return status == "trialing" and trial_ends_at is not None and trial_ends_at > now
