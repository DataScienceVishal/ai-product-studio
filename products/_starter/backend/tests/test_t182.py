"""T-182: follow-ups from the T-179 security review (M3, L1, N1, N4) and the T-180 review (S1, S2)."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import func, select

from app import billing as billing_module
from app.billing import CANCEL_WORST_CASE_SECONDS, CHECKOUT_TTL, OFFERS, PLANS, MockBilling, StripeBilling
from app.errors import AppError
from app.models import PendingCancel, Tenant
from app.routes.billing import retry_pending_cancels
from tests.conftest import PASSWORD

from .test_billing import SECRET, _sub_event, _tenant_id

DELETE = {"password": PASSWORD, "confirm": "DELETE"}


def _stripe(handler) -> StripeBilling:
    return StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))


# ---- M3: refund the extra subscription's latest paid invoice -------------------------------------------------

def test_mock_refund_is_recorded_once_per_key():
    mock = MockBilling("x", "https://app.test")
    assert mock.refund_latest_invoice("sub_2", "k1") is True
    assert mock.refund_latest_invoice("sub_2", "k1") is True  # same key: no second refund
    assert mock.refunds == [("sub_2", "k1")]


def _refund_handler(invoice, payments=None, calls=None, refund_status=200, refund_body=None):
    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path, dict(request.url.params), request.headers.get("idempotency-key"),
                      parse_qs(request.content.decode())))
        if request.url.path == "/v1/invoices":
            return httpx.Response(200, json={"data": [invoice] if invoice else []})
        if request.url.path == "/v1/invoice_payments":
            return httpx.Response(200, json={"data": payments or []})
        if request.url.path == "/v1/refunds":
            return httpx.Response(refund_status, json=refund_body or {"id": "re_1"})
        return httpx.Response(404, json={})
    return handler


def test_stripe_refund_old_api_shape_uses_the_invoice_payment_intent():
    calls = []
    stripe = _stripe(_refund_handler({"id": "in_1", "amount_paid": 7900, "payment_intent": "pi_1"}, calls=calls))
    assert stripe.refund_latest_invoice("sub_2", "refund-k") is True
    method, path, params, _key, _form = calls[0]
    assert (method, path, params["subscription"], params["status"], params["limit"]) == (
        "GET", "/v1/invoices", "sub_2", "paid", "1")
    method, path, _p, key, form = calls[-1]
    assert (method, path, key, form) == ("POST", "/v1/refunds", "refund-k", {"payment_intent": ["pi_1"]})


def test_stripe_refund_new_api_shape_uses_invoice_payments():
    """API versions from 2025-03-31 (basil) dropped `invoice.payment_intent`: the payment comes from /v1/invoice_payments.
    https://docs.stripe.com/api/invoice-payment/list"""
    calls = []
    payments = [{"id": "inpay_1", "status": "paid", "payment": {"type": "payment_intent", "payment_intent": "pi_9"}}]
    stripe = _stripe(_refund_handler({"id": "in_1", "amount_paid": 7900}, payments, calls))
    assert stripe.refund_latest_invoice("sub_2", "refund-k") is True
    assert [c[1] for c in calls] == ["/v1/invoices", "/v1/invoice_payments", "/v1/refunds"]
    assert calls[1][2]["invoice"] == "in_1" and calls[1][2]["status"] == "paid"
    assert calls[2][4] == {"payment_intent": ["pi_9"]}


def test_stripe_refund_without_a_paid_invoice_does_nothing():
    for invoice in (None, {"id": "in_0", "amount_paid": 0, "payment_intent": None}):
        calls = []
        assert _stripe(_refund_handler(invoice, calls=calls)).refund_latest_invoice("sub_2", "k") is False
        assert all(c[1] != "/v1/refunds" for c in calls)


def test_stripe_refund_already_refunded_counts_as_done():
    body = {"error": {"code": "charge_already_refunded", "message": "secret provider text"}}
    stripe = _stripe(_refund_handler({"id": "in_1", "amount_paid": 100, "payment_intent": "pi_1"},
                                     calls=[], refund_status=400, refund_body=body))
    assert stripe.refund_latest_invoice("sub_2", "k") is True


def test_stripe_refund_failure_raises():
    stripe = _stripe(_refund_handler({"id": "in_1", "amount_paid": 100, "payment_intent": "pi_1"}, calls=[],
                                     refund_status=402, refund_body={"error": {"code": "x"}}))
    with pytest.raises(AppError):
        stripe.refund_latest_invoice("sub_2", "k")


def _duplicate(client, app, first="s1", second="s2", eid="d2"):
    now = int(time.time())
    assert _sub_event(client, app, "d1", "checkout.completed", now - 100, first).status_code == 200
    return _sub_event(client, app, eid, "checkout.completed", now, second, plan="pro")


def test_duplicate_subscription_is_cancelled_and_refunded(owner, app):
    client, _ = owner
    assert _duplicate(client, app).status_code == 200
    billing = app.state.billing
    assert billing.cancelled == ["s2"]
    assert [ref for ref, _k in billing.refunds] == ["s2"]
    assert billing.refunds[0][1].startswith("refund-") and len(billing.refunds[0][1]) <= 255


def test_duplicate_without_a_paid_invoice_is_cancelled_with_an_info_log(owner, app, caplog):
    client, _ = owner
    app.state.billing.refund_latest_invoice = lambda ref, key: False
    with caplog.at_level(logging.INFO, logger="app.billing"):
        assert _duplicate(client, app).status_code == 200
    assert app.state.billing.cancelled == ["s2"]
    assert any(r.levelno == logging.INFO and "no paid invoice" in r.getMessage() for r in caplog.records)


def test_failed_refund_logs_refund_owed_answers_503_and_the_redelivery_refunds(owner, app, caplog):
    client, _ = owner
    billing = app.state.billing
    real = billing.refund_latest_invoice

    def boom(ref, key):
        raise AppError(502, "billing_rejected", "provider said: card 4242 something")

    billing.refund_latest_invoice = boom
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        r = _duplicate(client, app)
    assert r.status_code == 503
    owed = [rec for rec in caplog.records if "refund_owed" in rec.getMessage()]
    assert len(owed) == 1 and owed[0].extra_subscription == "s2"
    assert "4242" not in caplog.text and "provider said" not in caplog.text
    billing.refund_latest_invoice = real
    now = int(time.time())
    r = _sub_event(client, app, "d2", "checkout.completed", now, "s2", plan="pro")  # same event id: redelivery
    assert r.status_code == 200 and r.json()["applied"] is True
    assert [ref for ref, _k in billing.refunds] == ["s2"] and billing.cancelled == ["s2"]


def test_the_refund_idempotency_key_is_stable_for_one_event_id(owner, app):
    client, _ = owner
    billing = app.state.billing
    keys = []
    real = billing.refund_latest_invoice
    billing.refund_latest_invoice = lambda ref, key: (keys.append(key), real(ref, key))[1]
    _duplicate(client, app)
    other = MockBilling("x", "https://a")
    assert keys and keys[0] == billing_module.refund_key("d2") != billing_module.refund_key("d3")
    assert other.refund_latest_invoice("s", keys[0]) is True


# ---- M3 prevention: every Checkout Session expires -----------------------------------------------------------

def test_stripe_checkout_session_expires_in_about_half_an_hour():
    seen = []

    def handler(request: httpx.Request):
        if request.url.path == "/v1/coupons":
            return httpx.Response(200, json={"id": "c"})
        seen.append(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"id": "cs_1", "url": "https://checkout.stripe.com/c/1"})

    before = int(time.time())
    _stripe(handler).create_checkout(uuid.uuid4(), PLANS["starter"], None, "https://a/ok", "https://a/no")
    expires = int(seen[0]["expires_at"][0])
    assert CHECKOUT_TTL >= timedelta(minutes=30)  # Stripe's minimum
    assert before + 30 * 60 <= expires <= int(time.time()) + int(CHECKOUT_TTL.total_seconds())


def test_mock_checkout_session_expires_and_an_expired_one_cannot_complete():
    mock = MockBilling("x", "https://app.test")
    tenant = uuid.uuid4()
    checkout = mock.create_checkout(tenant, PLANS["starter"], None, "https://a/ok", "https://a/no")
    expires = mock.sessions[checkout.id]["expires_at"]
    assert abs(expires - (time.time() + CHECKOUT_TTL.total_seconds())) < 5
    mock.sessions[checkout.id]["expires_at"] = time.time() - 1
    with pytest.raises(AppError):
        mock.completion_event(checkout.id)


# ---- L1: account deletion tries the tenant's pending cancels --------------------------------------------------

def _pending(database, tenant, ref="sub_old", **kw):
    with database.sessions() as db:
        db.add(PendingCancel(tenant_id=uuid.UUID(tenant), provider="mock", ref=ref, **kw))
        db.commit()


def _tenants(database):
    with database.sessions() as db:
        return db.scalar(select(func.count()).select_from(Tenant))


def test_account_deletion_cancels_pending_cancels_first(owner, app, database):
    client, _ = owner
    _pending(database, _tenant_id(client), attempts=12)  # escalated rows too
    assert client.request("DELETE", "/api/account", json=DELETE).status_code == 204
    assert app.state.billing.cancelled == ["sub_old"]
    with database.sessions() as db:
        assert db.scalar(select(func.count()).select_from(PendingCancel)) == 0


def test_account_deletion_fails_closed_while_a_pending_cancel_is_still_live(owner, app, database):
    client, _ = owner
    _pending(database, _tenant_id(client))
    billing = app.state.billing
    real = billing.cancel_subscription

    def down(ref):
        raise AppError(503, "billing_unavailable", "down")

    billing.cancel_subscription = down
    r = client.request("DELETE", "/api/account", json=DELETE)
    assert r.status_code == 503 and r.json()["error"] == "billing_unavailable"
    assert _tenants(database) == 1
    with database.sessions() as db:
        assert db.scalar(select(PendingCancel.attempts)) == 1
    billing.cancel_subscription = real
    assert client.request("DELETE", "/api/account", json=DELETE).status_code == 204


def test_account_deletion_ignores_another_tenants_pending_cancels(owner, app, database):
    client, _ = owner
    with database.sessions() as db:
        db.add(PendingCancel(tenant_id=None, provider="mock", ref="sub_orphan"))
        db.commit()
    assert client.request("DELETE", "/api/account", json=DELETE).status_code == 204
    assert app.state.billing.cancelled == []


# ---- N1: pending-cancel delete is tenant-scoped ---------------------------------------------------------------

def test_a_start_event_never_drops_another_tenants_pending_cancel(owner, app, database):
    client, _ = owner
    other = uuid.uuid4()
    with database.sessions() as db:
        from app.models import Tenant as T
        db.add(T(id=other, name="Other"))
        db.flush()
        db.add(PendingCancel(tenant_id=other, provider="mock", ref="s_shared"))
        db.add(PendingCancel(tenant_id=None, provider="mock", ref="s_null"))
        db.commit()
    now = int(time.time())
    _sub_event(client, app, "n1", "checkout.completed", now - 10, "s_shared")
    _sub_event(client, app, "n1c", "subscription.canceled", now - 8, "s_shared")  # lapsed: a new start may replace it
    _sub_event(client, app, "n2", "checkout.completed", now - 5, "s_null")
    with database.sessions() as db:
        refs = set(db.scalars(select(PendingCancel.ref)))
    assert refs == {"s_shared"}  # NULL-tenant rows may be dropped (ref became current), another tenant's may not


# ---- N4: last_error holds a code or a class name, never provider text ------------------------------------------

@pytest.mark.parametrize("error,expected", [
    (AppError(502, "billing_rejected", "card 4242 declined"), "billing_rejected"),
    (RuntimeError("customer jane@example.com"), "RuntimeError"),
])
def test_last_error_never_stores_message_text(owner, app, database, error, expected):
    client, _ = owner
    _pending(database, _tenant_id(client))

    def boom(ref):
        raise error

    app.state.billing.cancel_subscription = boom
    with database.sessions() as db:
        retry_pending_cancels(db, uuid.UUID(_tenant_id(client)), "mock", app.state.billing)
    with database.sessions() as db:
        assert db.scalar(select(PendingCancel.last_error)) == expected


# ---- S1: one wall-clock deadline for the whole cancel ----------------------------------------------------------

def test_both_cancel_tries_share_one_deadline(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(billing_module, "_clock", lambda: clock[0])
    monkeypatch.setattr(billing_module.time, "sleep", lambda s: clock.__setitem__(0, clock[0] + s))
    reads = []

    def trickle(request: httpx.Request):
        timeout = request.extensions["timeout"]["read"]
        reads.append(timeout)
        clock[0] += 7 if len(reads) == 1 else timeout  # the first try dribbles for 7 s, then fails
        raise httpx.ReadTimeout("slow")

    with pytest.raises(AppError):
        _stripe(trickle).cancel_subscription("sub_x")
    assert clock[0] <= CANCEL_WORST_CASE_SECONDS, (clock[0], reads)


# ---- S2: the inline retry in the webhook has a total budget ----------------------------------------------------

def test_inline_retry_stops_starting_rows_once_the_budget_is_spent(owner, app, database, monkeypatch):
    client, _ = owner
    t = _tenant_id(client)
    for i in range(3):
        _pending(database, t, ref=f"sub_{i}")
    clock = [0.0]
    monkeypatch.setattr("app.routes.billing._clock", lambda: clock[0])
    tried = []

    def slow(ref):
        tried.append(ref)
        clock[0] += 3  # each attempt takes 3 s of the 5 s budget
        raise AppError(503, "billing_unavailable", "down")

    app.state.billing.cancel_subscription = slow
    with database.sessions() as db:
        retry_pending_cancels(db, uuid.UUID(t), "mock", app.state.billing)
    assert len(tried) == 2  # the third waits for the sweep
