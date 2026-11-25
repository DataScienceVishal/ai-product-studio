"""Billing: API behaviour plus a contract every provider (mock and Stripe test mode) must meet."""
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import httpx
import pytest

from app.billing import (OFFERS, Offer, PLANS, InvalidSignature, MockBilling, StripeBilling, has_access, sign,
                         verify)
from app.errors import AppError

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
        if request.url.path == "/v1/coupons":  # the offer's coupon is ensured before the session
            return httpx.Response(200, json={"id": OFFERS["EARLY50"].coupon_id})
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


# --- Early-customer offer as a server-side Stripe coupon -------------------------------------------

def coupon_stripe(coupon_reply=None):
    """A StripeBilling on a recording MockTransport. coupon_reply(request) answers POST/GET /v1/coupons."""
    calls = []

    def handler(request: httpx.Request):
        form = {k: v[0] for k, v in parse_qs(request.content.decode(), keep_blank_values=True).items()}
        calls.append((request.method, request.url.path, form, request.headers.get("idempotency-key")))
        if request.url.path.startswith("/v1/coupons"):
            return coupon_reply(request) if coupon_reply else httpx.Response(200, json={"id": form.get("id")})
        return httpx.Response(200, json={"id": "cs_test_1", "url": "https://checkout.stripe.com/c/cs_test_1"})

    return StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler))), calls


def checkout_form(calls):
    return next(c[2] for c in calls if c[1] == "/v1/checkout/sessions")


def test_checkout_with_offer_applies_the_coupon_server_side():
    stripe, calls = coupon_stripe()
    stripe.create_checkout(uuid.uuid4(), PLANS["starter"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    form = checkout_form(calls)
    assert form["discounts[0][coupon]"] == OFFERS["EARLY50"].coupon_id
    assert "allow_promotion_codes" not in form  # Stripe rejects both together
    assert form["metadata[offer]"] == "EARLY50"
    assert calls[0][:2] == ("POST", "/v1/coupons")  # the coupon exists before the session refers to it
    assert calls[0][2] == {"id": OFFERS["EARLY50"].coupon_id, "percent_off": "50", "duration": "repeating",
                           "duration_in_months": "3", "name": "EARLY50 50% off for 3 months"}
    assert calls[0][3].startswith(f"coupon-{OFFERS['EARLY50'].coupon_id}-")  # Idempotency-Key, fresh per call
    assert len(calls[0][3]) == len(f"coupon-{OFFERS['EARLY50'].coupon_id}-") + 32


def test_checkout_without_offer_has_no_discount_and_no_promotion_codes():
    stripe, calls = coupon_stripe()
    stripe.create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no")
    form = checkout_form(calls)
    assert not any(k.startswith("discounts") for k in form) and "allow_promotion_codes" not in form
    assert form["metadata[offer]"] == ""
    assert [c[1] for c in calls] == ["/v1/checkout/sessions"]  # no coupon call


def test_coupon_is_created_once_then_cached():
    stripe, calls = coupon_stripe()
    for _ in range(3):
        stripe.create_checkout(uuid.uuid4(), PLANS["pro"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    assert [c[1] for c in calls].count("/v1/coupons") == 1


def already_exists(terms):
    def reply(request: httpx.Request):
        if request.method == "POST":
            return httpx.Response(400, json={"error": {"code": "resource_already_exists", "type": "invalid_request_error"}})
        return httpx.Response(200, json=terms)
    return reply


def test_coupon_already_exists_is_accepted_when_it_matches():
    same = {"id": OFFERS["EARLY50"].coupon_id, "percent_off": 50, "duration": "repeating", "duration_in_months": 3, "valid": True}
    stripe, calls = coupon_stripe(already_exists(same))
    stripe.create_checkout(uuid.uuid4(), PLANS["starter"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    assert checkout_form(calls)["discounts[0][coupon]"] == OFFERS["EARLY50"].coupon_id
    assert ("GET", f"/v1/coupons/{OFFERS['EARLY50'].coupon_id}") == calls[1][:2]


@pytest.mark.parametrize("change", [{"percent_off": 90}, {"duration_in_months": 12}, {"duration": "forever"}, {"valid": False}])
def test_existing_coupon_with_other_terms_is_refused(change):
    terms = {"percent_off": 50, "duration": "repeating", "duration_in_months": 3, "valid": True, **change}
    stripe, calls = coupon_stripe(already_exists(terms))
    with pytest.raises(AppError) as error:
        stripe.create_checkout(uuid.uuid4(), PLANS["starter"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    assert error.value.code == "billing_rejected"
    assert not any(c[1] == "/v1/checkout/sessions" for c in calls)


@pytest.mark.parametrize("body", [{"error": {"code": "parameter_invalid_integer"}}, {"error": {"code": "resource_missing"}}, {}, None])
def test_other_400s_on_the_coupon_are_billing_rejected(body):
    stripe, calls = coupon_stripe(lambda r: httpx.Response(400, json=body) if body is not None else httpx.Response(400, text="no"))
    with pytest.raises(AppError) as error:
        stripe.create_checkout(uuid.uuid4(), PLANS["starter"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    assert error.value.code == "billing_rejected"
    assert not any(c[1] == "/v1/checkout/sessions" for c in calls)


def test_checkout_400_stays_billing_rejected_even_with_already_exists_code():
    """Only the coupon call tolerates resource_already_exists; a checkout session 400 must still fail."""
    def handler(request):
        return httpx.Response(400, json={"error": {"code": "resource_already_exists"}})
    stripe = StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AppError) as error:
        stripe.create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no")
    assert error.value.code == "billing_rejected"


def test_coupon_id_changes_with_the_offer_terms():
    base = Offer("EARLY50", 50, 3, "d")
    ids = {base.coupon_id, Offer("EARLY50", 40, 3, "d").coupon_id, Offer("EARLY50", 50, 6, "d").coupon_id,
           Offer("LAUNCH", 50, 3, "d").coupon_id}
    assert len(ids) == 4
    assert base.coupon_id == Offer("EARLY50", 50, 3, "other text").coupon_id  # wording does not matter
    assert OFFERS["EARLY50"].coupon_id == "studio-early50-50pc-3m-v1"


def test_failed_checkout_drops_the_cached_coupon_so_the_next_one_rechecks_it():
    """A coupon deleted in Stripe after it was cached: the checkout 400s, the id is forgotten, the next call re-ensures it."""
    state = {"fail": False}
    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path))
        if request.url.path.startswith("/v1/coupons"):
            return httpx.Response(200, json={"id": "c"})
        if state["fail"]:
            return httpx.Response(400, json={"error": {"code": "resource_missing", "param": "discounts[0][coupon]"}})
        return httpx.Response(200, json={"id": "cs_test_1", "url": "https://checkout.stripe.com/c/cs_test_1"})

    stripe = StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))
    args = (uuid.uuid4(), PLANS["pro"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    stripe.create_checkout(*args)
    stripe.create_checkout(*args)  # success keeps the cache
    assert calls.count(("POST", "/v1/coupons")) == 1
    state["fail"] = True
    with pytest.raises(AppError) as failed:
        stripe.create_checkout(*args)
    assert failed.value.code == "billing_rejected"
    assert OFFERS["EARLY50"].coupon_id not in stripe._coupons
    state["fail"] = False
    stripe.create_checkout(*args)
    assert calls.count(("POST", "/v1/coupons")) == 2  # ensure_coupon ran again
    assert OFFERS["EARLY50"].coupon_id in stripe._coupons


@pytest.mark.parametrize("status", [503, 429])
def test_checkout_outage_keeps_the_cached_coupon(monkeypatch, status):
    """A 503 or 429 says nothing about the coupon: it stays cached and the next checkout makes no coupon call."""
    monkeypatch.setattr("app.billing.time.sleep", lambda _s: None)
    state = {"down": False}
    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path))
        if request.url.path.startswith("/v1/coupons"):
            return httpx.Response(200, json={"id": "c"})
        if state["down"]:
            return httpx.Response(status)
        return httpx.Response(200, json={"id": "cs_test_1", "url": "https://checkout.stripe.com/c/cs_test_1"})

    stripe = StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))
    args = (uuid.uuid4(), PLANS["pro"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    stripe.create_checkout(*args)
    state["down"] = True
    with pytest.raises(AppError) as failed:
        stripe.create_checkout(*args)
    assert failed.value.code == "billing_unavailable"
    assert OFFERS["EARLY50"].coupon_id in stripe._coupons
    state["down"] = False
    stripe.create_checkout(*args)
    assert calls.count(("POST", "/v1/coupons")) == 1  # no extra coupon call


def test_incomplete_200_reply_keeps_the_cached_coupon():
    """A 200 with an empty body is rejected as incomplete, but the request succeeded, so the coupon stays cached."""
    state = {"empty": False}
    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path))
        if request.url.path.startswith("/v1/coupons"):
            return httpx.Response(200, json={"id": "c"})
        if state["empty"]:
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"id": "cs_test_1", "url": "https://checkout.stripe.com/c/cs_test_1"})

    stripe = StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))
    args = (uuid.uuid4(), PLANS["pro"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    stripe.create_checkout(*args)
    state["empty"] = True
    with pytest.raises(AppError) as failed:
        stripe.create_checkout(*args)
    assert failed.value.code == "billing_rejected"
    assert OFFERS["EARLY50"].coupon_id in stripe._coupons
    state["empty"] = False
    stripe.create_checkout(*args)
    assert calls.count(("POST", "/v1/coupons")) == 1  # no extra coupon call


def test_failed_checkout_without_offer_leaves_the_coupon_cache_alone():
    stripe, _ = coupon_stripe()
    stripe.create_checkout(uuid.uuid4(), PLANS["pro"], OFFERS["EARLY50"], "https://a/ok", "https://a/no")
    stripe.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(400, json={})))
    with pytest.raises(AppError):
        stripe.create_checkout(uuid.uuid4(), PLANS["pro"], None, "https://a/ok", "https://a/no")
    assert OFFERS["EARLY50"].coupon_id in stripe._coupons


def test_coupon_name_is_capped_at_stripes_40_characters():
    long_offer = Offer("A-VERY-LONG-EARLY-CUSTOMER-OFFER-CODE", 50, 3, "d")
    assert len(f"{long_offer.code} {long_offer.percent_off}% off for {long_offer.months} months") > 40
    stripe, calls = coupon_stripe()
    stripe.create_checkout(uuid.uuid4(), PLANS["pro"], long_offer, "https://a/ok", "https://a/no")
    name = calls[0][2]["name"]
    assert calls[0][:2] == ("POST", "/v1/coupons") and len(name) == 40
    assert name == "A-VERY-LONG-EARLY-CUSTOMER-OFFER-CODE 50% off for 3 months"[:40]
