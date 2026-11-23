"""Billing: API behaviour plus a contract every provider (mock and Stripe test mode) must meet."""
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.billing import (OFFERS, PLANS, InvalidSignature, MockBilling, StripeBilling, has_access, sign,
                         verify)

SECRET = "whsec_test_contract"


# --- API -------------------------------------------------------------------------------------

def test_plans_are_public_and_exclude_trial(new_client):
    body = new_client().get("/api/billing/plans").json()
    assert {p["id"] for p in body["plans"]} == {"starter", "pro"}
    assert body["offers"][0]["code"] == "EARLY50"


def test_checkout_then_mock_payment_activates_plan_with_offer(owner):
    client, _ = owner
    checkout = client.post("/api/billing/checkout", json={"plan": "pro", "offer_code": "early50"})
    assert checkout.status_code == 200
    session_id = checkout.json()["checkout_id"]
    done = client.post(f"/api/billing/mock/complete/{session_id}").json()
    assert done == {"plan": "pro", "status": "active", "offer": "EARLY50"}
    assert client.get("/api/auth/me").json()["subscription"]["status"] == "active"


def test_checkout_validation(owner):
    client, _ = owner
    assert client.post("/api/billing/checkout", json={"plan": "trial"}).json()["error"] == "unknown_plan"
    assert client.post("/api/billing/checkout", json={"plan": "pro", "offer_code": "FREE100"}).json()["error"] == "unknown_offer"


def test_another_tenant_cannot_complete_my_checkout(owner, new_client):
    from .conftest import sign_up
    client, _ = owner
    session_id = client.post("/api/billing/checkout", json={"plan": "starter"}).json()["checkout_id"]
    other = new_client()
    sign_up(other, email="other@beta.test", company="Beta")
    assert other.post(f"/api/billing/mock/complete/{session_id}").status_code == 404


def test_webhook_is_signed_and_idempotent(app, owner):
    client, me = owner
    billing: MockBilling = app.state.billing
    session_id = client.post("/api/billing/checkout", json={"plan": "starter"}).json()["checkout_id"]
    payload = billing.completion_event(session_id)
    bad = client.post("/api/billing/webhook", content=payload, headers={"x-billing-signature": "t=1,v1=00"})
    assert bad.status_code == 400 and bad.json()["error"] == "invalid_signature"
    headers = {"x-billing-signature": sign(payload, billing.secret)}
    first = client.post("/api/billing/webhook", content=payload, headers=headers).json()
    second = client.post("/api/billing/webhook", content=payload, headers=headers).json()
    assert first["applied"] is True and second["applied"] is False
    assert client.get("/api/auth/me").json()["subscription"]["plan"] == "starter"


def test_webhook_needs_no_csrf_header_but_other_writes_do(new_client, app):
    browser = new_client(csrf=False)
    payload = json.dumps({"id": "evt_x", "type": "unknown", "data": {}}).encode()
    response = browser.post("/api/billing/webhook", content=payload,
                            headers={"x-billing-signature": sign(payload, app.state.billing.secret)})
    assert response.status_code == 200 and response.json()["applied"] is False


# --- Provider contract -------------------------------------------------------------------------

def stripe_provider() -> StripeBilling:
    def handler(request: httpx.Request):
        assert request.url.path == "/v1/checkout/sessions"
        form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
        assert form["mode"] == "subscription" and "client_reference_id" in form
        return httpx.Response(200, json={"id": "cs_test_123", "url": "https://checkout.stripe.com/c/cs_test_123"})

    return StripeBilling("sk_test_contract", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))


def stripe_completion(tenant: uuid.UUID, _session_id: str) -> bytes:
    return json.dumps({"id": f"evt_{uuid.uuid4().hex}", "type": "checkout.session.completed",
                       "data": {"object": {"client_reference_id": str(tenant), "subscription": "sub_test_1"}}}).encode()


def mock_completion(provider: MockBilling, session_id: str) -> bytes:
    return provider.completion_event(session_id)


PROVIDERS = {
    "mock": (lambda: MockBilling(SECRET, "https://app.test"), lambda p, t, s: mock_completion(p, s)),
    "stripe": (stripe_provider, lambda p, t, s: stripe_completion(t, s)),
}


@pytest.mark.parametrize("name", PROVIDERS)
def test_contract_checkout_and_completion(name):
    make, completion = PROVIDERS[name]
    provider = make()
    tenant = uuid.uuid4()
    checkout = provider.create_checkout(tenant, PLANS["starter"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    assert checkout.id and checkout.url.startswith("https://")
    payload = completion(provider, tenant, checkout.id)
    update = provider.parse_webhook(payload, sign(payload, SECRET))
    assert update.tenant_id == tenant and update.status == "active" and update.event_id


@pytest.mark.parametrize("name", PROVIDERS)
def test_contract_rejects_bad_signatures(name):
    make, _ = PROVIDERS[name]
    provider = make()
    payload = b'{"id": "evt_1", "type": "checkout.completed", "data": {}}'
    with pytest.raises(InvalidSignature):
        provider.parse_webhook(payload, sign(payload, "wrong-secret"))
    with pytest.raises(InvalidSignature):
        provider.parse_webhook(payload, sign(payload, SECRET, timestamp=int(time.time()) - 3600))
    with pytest.raises(InvalidSignature):
        provider.parse_webhook(payload, "")


@pytest.mark.parametrize("name", PROVIDERS)
def test_contract_ignores_unknown_events(name):
    make, _ = PROVIDERS[name]
    payload = b'{"id": "evt_2", "type": "invoice.created", "data": {}}'
    assert make().parse_webhook(payload, sign(payload, SECRET)) is None


def test_stripe_subscription_cancellation_maps_to_canceled():
    tenant = uuid.uuid4()
    payload = json.dumps({"id": "evt_3", "type": "customer.subscription.deleted",
                          "data": {"object": {"id": "sub_1", "status": "canceled",
                                              "metadata": {"tenant_id": str(tenant), "plan": "pro"}}}}).encode()
    update = stripe_provider().parse_webhook(payload, sign(payload, SECRET))
    assert update.status == "canceled" and update.plan == "pro"


def test_stripe_live_keys_are_refused():
    for key in ("sk_live_abc", "rk_live_abc", "", "pk_test_abc"):
        with pytest.raises(ValueError, match="test-mode"):
            StripeBilling(key, SECRET)


def test_signature_round_trip_and_tolerance():
    payload = b"{}"
    verify(payload, sign(payload, SECRET), SECRET)
    with pytest.raises(InvalidSignature):
        verify(payload, sign(payload, SECRET, timestamp=int(time.time()) + 600), SECRET)


def test_access_rules():
    now = datetime.now(timezone.utc)
    assert has_access("active", None, now)
    assert has_access("trialing", now + timedelta(days=1), now)
    assert not has_access("trialing", now - timedelta(seconds=1), now)
    assert not has_access("past_due", None, now) and not has_access("canceled", None, now)


def test_oversized_webhook_is_refused_without_reading_it_all(new_client):
    client = new_client(csrf=False)
    response = client.post("/api/billing/webhook", content=b"x" * 300_000, headers={"x-billing-signature": "t=1,v1=0"})
    assert response.status_code == 413 and response.json()["error"] == "too_large"

    def chunks():  # no content-length: the streaming check has to catch it
        for _ in range(40):
            yield b"y" * 10_000

    streamed = client.post("/api/billing/webhook", content=chunks(), headers={"x-billing-signature": "t=1,v1=0"})
    assert streamed.status_code == 413
