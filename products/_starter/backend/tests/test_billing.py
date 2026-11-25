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


# --- T-71 regression tests: malformed webhooks and same-second ordering ---

def _hook(client, app, event, raw: bytes | None = None):
    payload = raw if raw is not None else json.dumps(event).encode()
    return client.post("/api/billing/webhook", content=payload,
                       headers={"x-billing-signature": sign(payload, app.state.settings.billing_webhook_secret)})


def _tenant_id(client) -> str:
    return client.get("/api/auth/me").json()["tenant"]["id"]


@pytest.mark.parametrize("event", [
    [],
    "str",
    {"type": "checkout.completed", "created": 1, "data": {"tenant_id": str(uuid.uuid4())}},  # no id
    {"id": "e", "type": "checkout.completed", "data": {"tenant_id": str(uuid.uuid4()), "current_period_end": 10**18}},
], ids=["array", "string", "no-id", "period-end-out-of-range"])
def test_signed_but_malformed_webhook_is_a_400_not_a_500(owner, app, event):
    client, _ = owner
    if isinstance(event, dict) and "tenant_id" in event.get("data", {}):
        event["data"]["tenant_id"] = _tenant_id(client)
    response = _hook(client, app, event)
    assert response.status_code == 400
    assert response.json()["error"] == "bad_event"


def test_webhook_with_out_of_range_created_is_a_400(owner, app):
    client, _ = owner
    event = {"id": "e_big", "type": "checkout.completed", "created": 10**18, "data": {"tenant_id": _tenant_id(client)}}
    assert _hook(client, app, event).status_code == 400


def test_webhook_invalid_json_is_a_400_and_bad_signature_is_rejected(owner, app):
    client, _ = owner
    assert _hook(client, app, None, raw=b"{not json").status_code == 400
    assert client.post("/api/billing/webhook", content=b"{}", headers={"x-billing-signature": "t=1,v1=00"}
                       ).json()["error"] == "invalid_signature"


def _status(client) -> str:
    return client.get("/api/auth/me").json()["subscription"]["status"]


def _flow(client, app, order):
    tid, now = _tenant_id(client), int(time.time())
    events = {
        "activate": {"id": "evt_act", "type": "checkout.completed", "created": now - 100,
                     "data": {"tenant_id": tid, "plan": "starter", "subscription": "s1"}},
        "cancel": {"id": "evt_can", "type": "subscription.canceled", "created": now, "data": {"tenant_id": tid}},
        "checkout": {"id": "evt_chk", "type": "checkout.completed", "created": now,
                     "data": {"tenant_id": tid, "plan": "starter", "subscription": "s1"}},
    }
    for name in order:
        assert _hook(client, app, events[name]).status_code == 200
    return _status(client)


def test_same_second_checkout_after_cancel_does_not_reactivate(owner, app):
    client, _ = owner
    assert _flow(client, app, ["activate", "cancel", "checkout"]) == "canceled"


def test_same_second_cancel_after_checkout_cancels(owner, app):
    client, _ = owner
    assert _flow(client, app, ["activate", "checkout", "cancel"]) == "canceled"


# --- T-72: events for an old subscription must not touch the current one ---

def _sub_event(client, app, eid, kind, created, ref, plan="starter"):
    return _hook(client, app, {"id": eid, "type": kind, "created": created,
                               "data": {"tenant_id": _tenant_id(client), "plan": plan, "subscription": ref}})


def _plan(client) -> str:
    return client.get("/api/auth/me").json()["subscription"]["plan"]


def test_old_subscription_cancel_after_new_checkout_keeps_customer_active(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "e1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "e2", "checkout.completed", now - 50, "s2", plan="pro")
    # s1's deletion arrives late and is strictly newer than s2's checkout
    assert _sub_event(client, app, "e3", "subscription.canceled", now, "s1").status_code == 200
    assert _status(client) == "active" and _plan(client) == "pro"


def test_old_subscription_past_due_does_not_downgrade_current(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "e1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "e2", "checkout.completed", now - 50, "s2")
    _sub_event(client, app, "e3", "subscription.past_due", now, "s1")
    assert _status(client) == "active"


def test_same_second_old_cancel_then_new_activation_ends_active(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "e1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "e2", "subscription.canceled", now, "s1")  # applies: s1 is current
    assert _status(client) == "canceled"
    _sub_event(client, app, "e3", "checkout.completed", now, "s2", plan="pro")  # a new subscription, same second
    assert _status(client) == "active" and _plan(client) == "pro"


def test_same_second_new_activation_then_old_cancel_ends_active(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "e1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "e2", "checkout.completed", now, "s2")
    _sub_event(client, app, "e3", "subscription.canceled", now, "s1")
    assert _status(client) == "active"


def test_cancel_of_the_current_subscription_still_works(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "e1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "e2", "checkout.completed", now - 50, "s2")
    _sub_event(client, app, "e3", "subscription.canceled", now, "s2")
    assert _status(client) == "canceled"


# --- T-72: an active event with an unknown plan is refused, not applied to the old plan ---

def test_active_event_with_unknown_plan_is_refused_and_can_be_redelivered(owner, app):
    client, _ = owner
    now = int(time.time())
    response = _sub_event(client, app, "e_plan", "checkout.completed", now, "s1", plan="enterprise-free")
    assert response.status_code == 400 and response.json()["error"] == "unknown_plan"
    assert _status(client) == "trialing"
    # the event id was not consumed, so a corrected redelivery with the same id applies
    assert _sub_event(client, app, "e_plan", "checkout.completed", now, "s1", plan="pro").json()["applied"] is True
    assert _status(client) == "active" and _plan(client) == "pro"


def test_cancel_with_unknown_plan_still_cancels(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "e1", "checkout.completed", now - 10, "s1")
    assert _sub_event(client, app, "e2", "subscription.canceled", now, "s1", plan="legacy").status_code == 200
    assert _status(client) == "canceled"


# --- T-72 review fixes: only an event that starts a subscription may replace the current one ---

def _stripe_apply(database, tenant_id, eid, kind, created, sub_id, status="active", plan="starter"):
    """A real-shaped Stripe event, parsed by StripeBilling and applied the way the webhook route does."""
    from app.routes.billing import apply_update
    if kind == "checkout.session.completed":
        obj = {"client_reference_id": tenant_id, "subscription": sub_id, "customer": "cus_1",
               "metadata": {"tenant_id": tenant_id, "plan": plan}}
    else:
        obj = {"id": sub_id, "status": status, "customer": "cus_1", "metadata": {"tenant_id": tenant_id, "plan": plan}}
    payload = json.dumps({"id": eid, "type": kind, "created": created, "livemode": False,
                          "data": {"object": obj}}).encode()
    update = stripe_provider().parse_webhook(payload, sign(payload, SECRET))
    with database.sessions() as db:
        return apply_update(db, update, "stripe")


def _stripe_sub(database, tenant_id):
    from sqlalchemy import select
    from app.models import Subscription
    with database.sessions() as db:
        sub = db.scalar(select(Subscription).where(Subscription.tenant_id == uuid.UUID(tenant_id)))
        return sub.status, sub.plan, sub.provider_ref


def test_old_subscription_recovering_does_not_take_over_then_cancel_the_customer(owner, database):
    """Reviewer's scenario: s1 past_due, customer buys s2 (pro), s1's retry succeeds (updated/active), s1 deleted."""
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    _stripe_apply(database, t, "e1", "checkout.session.completed", now - 500, "sub_1", plan="starter")
    _stripe_apply(database, t, "e2", "customer.subscription.updated", now - 400, "sub_1", "past_due")
    _stripe_apply(database, t, "e3", "checkout.session.completed", now - 300, "sub_2", plan="pro")
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")
    assert _stripe_apply(database, t, "e4", "customer.subscription.updated", now - 200, "sub_1", "active") is True
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")  # ref and plan unchanged
    _stripe_apply(database, t, "e5", "customer.subscription.deleted", now - 100, "sub_1", "canceled")
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")


def test_stripe_old_subscription_deleted_after_new_checkout_keeps_customer(owner, database):
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    _stripe_apply(database, t, "e1", "checkout.session.completed", now - 300, "sub_1")
    _stripe_apply(database, t, "e2", "checkout.session.completed", now - 200, "sub_2", plan="pro")
    assert _stripe_apply(database, t, "e3", "customer.subscription.deleted", now, "sub_1", "canceled") is True
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")
    # redelivery of the ignored event is an idempotent no-op
    assert _stripe_apply(database, t, "e3", "customer.subscription.deleted", now, "sub_1", "canceled") is False
    # the current subscription's own deletion still cancels
    _stripe_apply(database, t, "e4", "customer.subscription.deleted", now + 1, "sub_2", "canceled")
    assert _stripe_sub(database, t)[0] == "canceled"


def test_subscription_created_for_a_new_id_does_take_over(owner, database):
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    _stripe_apply(database, t, "e1", "checkout.session.completed", now - 300, "sub_1")
    _stripe_apply(database, t, "e2", "customer.subscription.created", now - 200, "sub_2", plan="pro")
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")


def test_webhook_refuses_the_trial_plan_on_an_active_event(owner, app):
    client, _ = owner
    r = _sub_event(client, app, "e_trial", "checkout.completed", int(time.time()), "s1", plan="trial")
    assert r.status_code == 400 and r.json()["error"] == "unknown_plan"


# --- T-73: no new checkout while the subscription is past_due ---

def test_checkout_refused_while_past_due(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "p1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "p2", "subscription.past_due", now, "s1")
    assert _status(client) == "past_due"
    r = client.post("/api/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 409 and r.json()["error"] == "subscription_past_due"


def test_checkout_allowed_after_cancel(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "c1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "c2", "subscription.canceled", now, "s1")
    assert _status(client) == "canceled"
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 200


def test_checkout_allowed_on_trial(owner):
    client, _ = owner
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 200


# --- T-74: past_due follow-ups (T-73 review S1 and S3) and the billing portal (S2) ---

def test_past_due_refusal_creates_no_checkout_session(owner, app):
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "n1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "n2", "subscription.past_due", now, "s1")
    sessions_before = dict(app.state.billing.sessions)
    r = client.post("/api/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 409 and r.json()["error"] == "subscription_past_due"
    assert app.state.billing.sessions == sessions_before  # the provider was never called


def test_past_due_from_another_provider_does_not_block_checkout(owner, app):
    """S1: a tenant left past_due by the mock provider must be able to buy once the app uses another provider."""
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "m1", "checkout.completed", now - 100, "s1")
    _sub_event(client, app, "m2", "subscription.past_due", now, "s1")
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 409
    app.state.billing.name = "stripe"  # the app now runs another provider than the one that owns the subscription
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 200


def test_stripe_unpaid_blocks_checkout(owner, database):
    """S3b: Stripe's `unpaid` maps to past_due, so the refusal applies to a real-shaped Stripe event."""
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    app_billing = client.app.state.billing
    _stripe_apply(database, t, "u1", "checkout.session.completed", now - 100, "sub_1")
    _stripe_apply(database, t, "u2", "customer.subscription.updated", now, "sub_1", "unpaid")
    assert _stripe_sub(database, t)[0] == "past_due"
    app_billing.name = "stripe"  # the subscription is Stripe's, so the app must be running Stripe
    r = client.post("/api/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 409 and r.json()["error"] == "subscription_past_due"


def test_past_due_then_active_on_same_ref_is_already_subscribed(owner, app):
    """S3c: recovery moves the refusal from subscription_past_due to already_subscribed."""
    client, _ = owner
    now = int(time.time())
    _sub_event(client, app, "r1", "checkout.completed", now - 300, "s1")
    _sub_event(client, app, "r2", "subscription.past_due", now - 200, "s1")
    assert client.post("/api/billing/checkout", json={"plan": "pro"}).json()["error"] == "subscription_past_due"
    # the same subscription recovers: a later activation event on the same ref
    _sub_event(client, app, "r3", "checkout.completed", now - 100, "s1")
    assert _status(client) == "active"
    r = client.post("/api/billing/checkout", json={"plan": "pro"})
    assert r.status_code == 409 and r.json()["error"] == "already_subscribed"


def _set_customer(database, client, customer="cus_1", provider="mock"):
    from sqlalchemy import select
    from app.models import Subscription
    with database.sessions() as db:
        sub = db.scalar(select(Subscription).where(Subscription.tenant_id == uuid.UUID(_tenant_id(client))))
        sub.provider_customer, sub.provider = customer, provider
        db.commit()


def test_portal_without_a_customer_is_409(owner):
    client, _ = owner
    r = client.post("/api/billing/portal")
    assert r.status_code == 409 and r.json()["error"] == "no_billing_customer"


def test_portal_customer_of_another_provider_is_409(owner, database):
    client, _ = owner
    _set_customer(database, client, "cus_1", provider="stripe")  # the app runs the mock provider
    assert client.post("/api/billing/portal").status_code == 409


def test_portal_mock_success(owner, database):
    client, _ = owner
    _set_customer(database, client)
    r = client.post("/api/billing/portal")
    assert r.status_code == 200
    assert r.json()["url"] == "https://app.test/billing/mock-portal?customer=cus_1"


def test_portal_is_owner_only(owner, new_client, outbox, database):
    from .conftest import link_token
    client, _ = owner
    _set_customer(database, client)
    client.post("/api/team/invitations", json={"email": "member@acme.test"})
    member = new_client()
    assert member.post("/api/invitations/accept", json={"token": link_token(outbox, "accept-invite"),
                                                        "password": "correct horse battery 2"}).status_code == 201
    assert member.post("/api/billing/portal").status_code == 403
    assert new_client().post("/api/billing/portal").status_code == 401


def test_portal_never_shows_another_tenants_customer(owner, new_client, outbox, database):
    from .conftest import sign_up, verify_email
    client, _ = owner
    _set_customer(database, client, "cus_acme")
    other = new_client()
    sign_up(other, email="other@beta.test", company="Beta")
    verify_email(other, outbox)
    assert other.post("/api/billing/portal").status_code == 409  # Beta has no customer; it never sees cus_acme


def test_portal_is_rate_limited(owner, database):
    client, _ = owner
    _set_customer(database, client)
    codes = [client.post("/api/billing/portal").status_code for _ in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def _portal_stripe(reply=None):
    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path, parse_qs(request.content.decode()),
                      request.headers.get("idempotency-key")))
        return reply(request) if reply else httpx.Response(200, json={"url": "https://billing.stripe.com/p/session/x"})

    return StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler))), calls


def test_stripe_portal_session_call_parameters():
    stripe, calls = _portal_stripe()
    url = stripe.portal_session("cus_42", "https://app.test/billing")
    assert url == "https://billing.stripe.com/p/session/x"
    (method, path, form, key), = calls
    assert (method, path) == ("POST", "/v1/billing_portal/sessions")
    assert form == {"customer": ["cus_42"], "return_url": ["https://app.test/billing"]} and key


def test_stripe_portal_incomplete_reply_and_rejection():
    stripe, _ = _portal_stripe(lambda r: httpx.Response(200, json={}))
    with pytest.raises(AppError) as error:
        stripe.portal_session("cus_1", "https://a/b")
    assert error.value.code == "billing_rejected"
    stripe, _ = _portal_stripe(lambda r: httpx.Response(400, json={"error": {"code": "x"}}))
    with pytest.raises(AppError):
        stripe.portal_session("cus_1", "https://a/b")


def test_portal_route_builds_return_url_from_settings_not_headers(owner, database, app, monkeypatch):
    client, _ = owner
    _set_customer(database, client, "cus_9", provider="stripe")
    stripe, calls = _portal_stripe()
    stripe.name = "stripe"
    monkeypatch.setattr(app.state, "billing", stripe)
    r = client.post("/api/billing/portal", headers={"Host": "evil.test", "Origin": "https://evil.test"})
    assert r.status_code == 200
    assert calls[0][2]["return_url"] == ["https://app.test/billing"] and calls[0][2]["customer"] == ["cus_9"]
