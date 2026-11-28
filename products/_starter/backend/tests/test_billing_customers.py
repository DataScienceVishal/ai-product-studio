"""T-181 (T-179 M1): one provider customer per tenant, and account deletion removes every customer the tenant had."""
from __future__ import annotations

import json
import time
import uuid
from urllib.parse import parse_qs

import httpx
from sqlalchemy import func, select, update

from app.billing import PLANS, MockBilling, StripeBilling, sign
from app.errors import AppError
from app.models import BillingCustomer, Subscription, Tenant
from app.routes.billing import apply_update
from tests.conftest import PASSWORD, sign_up, verify_email

SECRET = "whsec_test_customers"
DELETE = {"password": PASSWORD, "confirm": "DELETE"}


def _stripe(handler) -> StripeBilling:
    return StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))


def _tenant(client) -> str:
    return client.get("/api/auth/me").json()["tenant"]["id"]


def _apply(database, billing, tenant, eid, sub_id, customer, created):
    """A paid Stripe checkout event naming `customer`, applied the way the webhook route does."""
    obj = {"client_reference_id": tenant, "subscription": sub_id, "customer": customer, "payment_status": "paid",
           "metadata": {"tenant_id": tenant, "plan": "starter"}}
    payload = json.dumps({"id": eid, "type": "checkout.session.completed", "created": created, "livemode": False,
                          "data": {"object": obj}}).encode()
    update_ = _stripe(lambda r: httpx.Response(200, json={})).parse_webhook(payload, sign(payload, SECRET))
    with database.sessions() as db:
        return apply_update(db, update_, billing.name, billing)


def _customers(database, tenant=None):
    with database.sessions() as db:
        q = select(BillingCustomer.customer_ref).order_by(BillingCustomer.created_at)
        if tenant:
            q = q.where(BillingCustomer.tenant_id == uuid.UUID(tenant))
        return list(db.scalars(q))


def _form(request: httpx.Request) -> dict:
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


def test_stripe_checkout_sends_the_existing_customer_and_no_email():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(_form(request))
        return httpx.Response(200, json={"id": "cs_1", "url": "https://checkout.test/cs_1"})

    _stripe(handler).create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no",
                                     customer_ref="cus_A")
    assert seen["customer"] == "cus_A" and "customer_email" not in seen


def test_stripe_checkout_without_a_known_customer_sends_none():
    seen = {}

    def handler(request: httpx.Request):
        seen.update(_form(request))
        return httpx.Response(200, json={"id": "cs_1", "url": "https://checkout.test/cs_1"})

    _stripe(handler).create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no")
    assert "customer" not in seen and "customer_email" not in seen


def test_checkout_route_reuses_the_stored_customer(app, owner, database):
    client, _ = owner
    passed = []
    real = app.state.billing.create_checkout

    def spy(*args, **kwargs):
        passed.append(kwargs.get("customer_ref"))
        return real(*args, **kwargs)

    app.state.billing.create_checkout = spy
    assert client.post("/api/billing/checkout", json={"plan": "starter"}).status_code == 200
    with database.sessions() as db:
        db.execute(update(Subscription).values(provider_customer="cus_A", provider="mock", status="canceled"))
        db.commit()
    assert client.post("/api/billing/checkout", json={"plan": "starter"}).status_code == 200
    assert passed == [None, "cus_A"]


def test_checkout_ignores_a_customer_that_belongs_to_another_provider(app, owner, database):
    client, _ = owner
    passed = []
    real = app.state.billing.create_checkout

    def spy(*args, **kwargs):
        passed.append(kwargs.get("customer_ref"))
        return real(*args, **kwargs)

    app.state.billing.create_checkout = spy
    with database.sessions() as db:
        db.execute(update(Subscription).values(provider_customer="cus_A", provider="stripe"))
        db.commit()
    assert client.post("/api/billing/checkout", json={"plan": "starter"}).status_code == 200
    assert passed == [None]


def test_mock_checkout_carries_the_customer_it_was_given(app):
    billing = app.state.billing
    session = billing.create_checkout(uuid.uuid4(), PLANS["starter"], None, "u", "u", customer_ref="cus_A")
    assert billing.sessions[session.id]["customer"] == "cus_A"


def test_webhook_events_record_each_customer_once(app, owner, database):
    client, _ = owner
    t, now = _tenant(client), int(time.time())
    _apply(database, app.state.billing, t, "e1", "sub_1", "cus_A", now - 100)
    _apply(database, app.state.billing, t, "e2", "sub_1", "cus_A", now - 50)
    assert _customers(database, t) == ["cus_A"]


def test_takeover_and_duplicate_customers_are_recorded(app, owner, database):
    client, _ = owner
    t, now = _tenant(client), int(time.time())
    billing = app.state.billing
    _apply(database, billing, t, "e1", "sub_1", "cus_A", now - 300)
    with database.sessions() as db:  # sub_1 went past_due: a new checkout takes over (cus_B)
        db.execute(update(Subscription).values(status="past_due"))
        db.commit()
    _apply(database, billing, t, "e2", "sub_2", "cus_B", now - 200)
    assert _customers(database, t) == ["cus_A", "cus_B"]
    _apply(database, billing, t, "e3", "sub_3", "cus_C", now - 100)  # a duplicate while sub_2 is active
    assert _customers(database, t) == ["cus_A", "cus_B", "cus_C"]


def test_deletion_deletes_every_customer_of_the_tenant(app, owner, database):
    client, _ = owner
    t, now = _tenant(client), int(time.time())
    billing = app.state.billing
    _apply(database, billing, t, "e1", "sub_1", "cus_A", now - 300)
    with database.sessions() as db:
        db.execute(update(Subscription).values(status="past_due"))
        db.commit()
    _apply(database, billing, t, "e2", "sub_2", "cus_B", now - 200)
    _apply(database, billing, t, "e3", "sub_3", "cus_C", now - 100)  # duplicate
    assert client.request("DELETE", "/api/account", json=DELETE).status_code == 204
    assert sorted(c for c, _ in billing.closed) == ["cus_A", "cus_B", "cus_C"]
    assert ("cus_B", "sub_2") in billing.closed
    assert _customers(database) == []  # the rows go with the tenant


def test_deletion_never_touches_another_tenants_customer(app, owner, new_client, outbox, database):
    client, _ = owner
    other = new_client()
    sign_up(other, email="other@acme.test", company="Other Ltd")
    verify_email(other, outbox)
    t, o, now = _tenant(client), _tenant(other), int(time.time())
    billing = app.state.billing
    _apply(database, billing, t, "e1", "sub_1", "cus_MINE", now - 100)
    _apply(database, billing, o, "e2", "sub_9", "cus_OTHER", now - 100)
    # a customer id already recorded for the other tenant is never re-assigned to this one
    _apply(database, billing, t, "e3", "sub_1", "cus_OTHER", now - 50)
    assert client.request("DELETE", "/api/account", json=DELETE).status_code == 204
    assert [c for c, _ in billing.closed] == ["cus_MINE"]
    assert _customers(database, o) == ["cus_OTHER"]


def test_a_failing_customer_delete_keeps_the_account_and_the_list_and_a_retry_finishes(app, owner, database):
    client, _ = owner
    t, now = _tenant(client), int(time.time())
    billing = app.state.billing
    _apply(database, billing, t, "e1", "sub_1", "cus_A", now - 300)
    with database.sessions() as db:
        db.execute(update(Subscription).values(status="past_due"))
        db.commit()
    _apply(database, billing, t, "e2", "sub_2", "cus_B", now - 200)
    real_close = billing.close

    def flaky(customer, subscription):
        if customer == "cus_A":  # the replaced (older) customer's delete fails
            raise AppError(503, "billing_unavailable", "down")
        real_close(customer, subscription)

    billing.close = flaky
    response = client.request("DELETE", "/api/account", json=DELETE)
    assert response.status_code == 503 and response.json()["error"] == "billing_unavailable"
    with database.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Tenant)) == 1
    assert _customers(database, t) == ["cus_A", "cus_B"]  # the to-do is not lost
    billing.close = real_close
    assert client.request("DELETE", "/api/account", json=DELETE).status_code == 204
    assert {"cus_A", "cus_B"} <= {c for c, _ in billing.closed}


# ---- T-208: follow-ups from the T-181 review (S1, S3, S4, nits) ----

def _orphan_event(database, billing, tenant, eid, sub_id, customer):
    return _apply(database, billing, tenant, eid, sub_id, customer, int(time.time()) - 10)


def _delete_account(client):
    return client.request("DELETE", "/api/account", json=DELETE)


def test_payment_after_the_account_was_deleted_closes_the_new_customer(app, owner, database):
    from app.models import BillingEvent
    client, _ = owner
    t, billing = _tenant(client), app.state.billing
    assert _delete_account(client).status_code == 204
    assert _orphan_event(database, billing, t, "e_late", "sub_late", "cus_LATE") is True
    assert billing.closed == [("cus_LATE", "sub_late")]
    with database.sessions() as db:
        assert db.get(BillingEvent, "e_late") is not None  # kept: a redelivery is a no-op
    assert _orphan_event(database, billing, t, "e_late", "sub_late", "cus_LATE") is False
    assert billing.closed == [("cus_LATE", "sub_late")]


def test_payment_for_a_deleted_tenant_never_closes_a_customer_a_live_tenant_owns(app, owner, new_client, outbox, database):
    client, _ = owner
    other = new_client()
    sign_up(other, email="other@acme.test", company="Other Ltd")
    verify_email(other, outbox)
    t, o, billing = _tenant(client), _tenant(other), app.state.billing
    _apply(database, billing, o, "e_o", "sub_o", "cus_OTHER", int(time.time()) - 100)
    assert _delete_account(client).status_code == 204
    billing.closed.clear()
    _orphan_event(database, billing, t, "e_x", "sub_x", "cus_OTHER")  # names the other tenant's customer
    assert billing.closed == []
    assert _customers(database, o) == ["cus_OTHER"]


def test_a_failing_close_for_a_deleted_tenant_answers_503_and_the_redelivery_closes_it(app, owner, database):
    from app.models import BillingEvent
    client, _ = owner
    t, billing = _tenant(client), app.state.billing
    assert _delete_account(client).status_code == 204
    real_close = billing.close

    def down(customer, subscription):
        raise AppError(503, "billing_unavailable", "down")

    billing.close = down
    try:
        _orphan_event(database, billing, t, "e_late", "sub_late", "cus_LATE")
        raise AssertionError("expected a 503")
    except AppError as error:
        assert error.status == 503
    with database.sessions() as db:
        assert db.get(BillingEvent, "e_late") is None  # not stored, so Stripe's redelivery is processed again
    billing.close = real_close
    assert _orphan_event(database, billing, t, "e_late", "sub_late", "cus_LATE") is True
    assert billing.closed[-1] == ("cus_LATE", "sub_late")


def test_webhook_route_answers_503_when_closing_an_orphan_fails(app, owner, database):
    client, _ = owner
    t, billing = _tenant(client), app.state.billing
    assert _delete_account(client).status_code == 204
    billing.close = lambda c, s: (_ for _ in ()).throw(AppError(503, "billing_unavailable", "down"))
    session = {"tenant_id": t, "plan": "starter", "offer": None, "customer": "cus_LATE"}
    billing.sessions["mock_cs_late"] = session
    payload = billing.completion_event("mock_cs_late")
    response = client.post("/api/billing/webhook", content=payload, headers={"x-billing-signature": sign(payload, billing.secret)})
    assert response.status_code == 503


def test_a_customer_recorded_during_account_deletion_is_closed_too(app, owner, database):
    client, _ = owner
    t, now, billing = _tenant(client), int(time.time()), app.state.billing
    _apply(database, billing, t, "e1", "sub_1", "cus_A", now - 300)
    real_close, raced = billing.close, []

    def close_and_race(customer, subscription):
        real_close(customer, subscription)
        if not raced:  # a webhook lands while the first provider call is running
            raced.append(1)
            with database.sessions() as db:
                db.execute(update(Subscription).values(status="past_due"))
                db.commit()
            _apply(database, billing, t, "e2", "sub_2", "cus_RACE", now - 100)

    billing.close = close_and_race
    assert _delete_account(client).status_code == 204
    assert {"cus_A", "cus_RACE"} <= {c for c, _ in billing.closed}
    assert _customers(database) == []


def test_a_failing_close_of_a_customer_recorded_during_deletion_keeps_the_account(app, owner, database):
    client, _ = owner
    t, now, billing = _tenant(client), int(time.time()), app.state.billing
    _apply(database, billing, t, "e1", "sub_1", "cus_A", now - 300)
    real_close, raced = billing.close, []

    def close_and_race(customer, subscription):
        if customer == "cus_RACE":
            raise AppError(503, "billing_unavailable", "down")
        real_close(customer, subscription)
        if not raced:
            raced.append(1)
            _apply(database, billing, t, "e2", "sub_1", "cus_RACE", now - 100)

    billing.close = close_and_race
    response = _delete_account(client)
    assert response.status_code == 503 and response.json()["error"] == "billing_unavailable"
    with database.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Tenant)) == 1
    assert "cus_RACE" in _customers(database, t)  # the to-do survives for the retry
    billing.close = real_close
    assert _delete_account(client).status_code == 204
    assert "cus_RACE" in {c for c, _ in billing.closed}


def test_stripe_close_uses_a_short_timeout_and_two_tries(monkeypatch):
    monkeypatch.setattr("app.billing.time.sleep", lambda s: None)
    seen = []

    def handler(request: httpx.Request):
        seen.append(request.extensions["timeout"]["read"])
        raise httpx.ConnectTimeout("slow", request=request)

    try:
        _stripe(handler).close("cus_A", "sub_1")
        raise AssertionError("expected a 503")
    except AppError as error:
        assert error.status == 503
    assert seen == [6.0, 6.0]


def test_checkout_retries_once_without_a_customer_that_is_missing_at_stripe():
    forms = []

    def handler(request: httpx.Request):
        forms.append(_form(request))
        if "customer" in forms[-1]:
            return httpx.Response(400, json={"error": {"code": "resource_missing", "param": "customer"}})
        return httpx.Response(200, json={"id": "cs_2", "url": "https://checkout.test/cs_2"})

    checkout = _stripe(handler).create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no",
                                                customer_ref="cus_GONE")
    assert checkout.id == "cs_2"
    assert len(forms) == 2 and forms[0]["customer"] == "cus_GONE" and "customer" not in forms[1]


def test_checkout_does_not_retry_when_something_else_is_missing():
    calls = []

    def handler(request: httpx.Request):
        calls.append(1)
        return httpx.Response(400, json={"error": {"code": "resource_missing", "param": "discounts[0][coupon]"}})

    try:
        _stripe(handler).create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no",
                                         customer_ref="cus_A")
        raise AssertionError("expected a rejection")
    except AppError as error:
        assert error.code == "billing_rejected"
    assert len(calls) == 1


def test_a_customer_inserted_concurrently_by_another_tenant_is_refused_at_the_insert(app, owner, new_client, outbox, database):
    from app.routes.billing import _record_customer
    client, _ = owner
    other = new_client()
    sign_up(other, email="other@acme.test", company="Other Ltd")
    verify_email(other, outbox)
    t, o = uuid.UUID(_tenant(client)), uuid.UUID(_tenant(other))
    with database.sessions() as db:
        db.add(BillingCustomer(tenant_id=o, provider="mock", customer_ref="cus_RACE"))
        db.commit()
    with database.sessions() as db:
        real = db.scalar
        db.scalar = lambda *a, **k: None  # the pre-check missed the other tenant's row (it committed just after)
        assert _record_customer(db, t, "mock", "cus_RACE") is False
        db.scalar = real
        assert db.scalar(select(func.count()).select_from(BillingCustomer)) == 1  # session still usable, no half row
