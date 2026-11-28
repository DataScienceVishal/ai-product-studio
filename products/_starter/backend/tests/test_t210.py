"""T-210: follow-ups from the T-182 review (S1, S2, S3, S6)."""
from __future__ import annotations

import logging
import time

import pytest

from sqlalchemy import func, select

from app import billing as billing_module
from app.billing import NoPaidInvoice
from app.errors import AppError
from app.models import BillingEvent

from .test_billing import _sub_event
from .test_t182 import _duplicate


def _owed(caplog):
    return [r for r in caplog.records if "refund_owed" in r.getMessage()]


def _event_stored(database, eid):
    with database.sessions() as s:
        return s.scalar(select(func.count()).select_from(BillingEvent).where(BillingEvent.id == eid)) == 1


# ---- S1: the event id is stored only after the cancel and the refund succeeded --------------------------------
def test_crash_after_the_cancel_leaves_no_event_id_and_the_redelivery_refunds(owner, app, database):
    client, _ = owner
    billing = app.state.billing
    real = billing.refund_latest_invoice

    def crash(ref, key):
        raise RuntimeError("worker killed")

    billing.refund_latest_invoice = crash
    try:
        r = _duplicate(client, app)
        assert r.status_code >= 500
    except RuntimeError:  # the test client may re-raise the crash instead of answering 500
        pass
    assert billing.cancelled == ["s2"] and billing.refunds == []
    assert not _event_stored(database, "d2")
    billing.refund_latest_invoice = real
    r = _sub_event(client, app, "d2", "checkout.completed", int(time.time()), "s2", plan="pro")
    assert r.status_code == 200
    assert [ref for ref, _k in billing.refunds] == ["s2"] and _event_stored(database, "d2")
    again = _sub_event(client, app, "d2", "checkout.completed", int(time.time()), "s2", plan="pro")
    assert again.status_code == 200 and again.json()["applied"] is False
    assert len(billing.refunds) == 1


def test_event_stored_after_success_and_a_concurrent_insert_counts_as_handled(owner, app, database):
    client, _ = owner
    billing = app.state.billing
    real = billing.refund_latest_invoice

    def other_worker_stores_it_first(ref, key):  # a second delivery finished while this one was refunding
        with database.sessions() as s:
            s.add(BillingEvent(id="d2"))
            s.commit()
        return real(ref, key)

    billing.refund_latest_invoice = other_worker_stores_it_first
    assert _duplicate(client, app).status_code == 200
    assert _event_stored(database, "d2")


# ---- S2: no paid invoice on a paid plan --------------------------------------------------------------------
def test_no_paid_invoice_logs_refund_owed_answers_503_then_redelivery_refunds(owner, app, database, caplog):
    client, _ = owner
    billing = app.state.billing
    real = billing.refund_latest_invoice

    def none_yet(ref, key):
        raise NoPaidInvoice()

    billing.refund_latest_invoice = none_yet
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        assert _duplicate(client, app).status_code == 503
    owed = _owed(caplog)
    assert len(owed) == 1 and owed[0].extra_subscription == "s2" and owed[0].reason == "no_paid_invoice"
    assert str(owed[0].tenant_id)
    assert not _event_stored(database, "d2")
    billing.refund_latest_invoice = real  # the invoice got paid meanwhile
    r = _sub_event(client, app, "d2", "checkout.completed", int(time.time()), "s2", plan="pro")
    assert r.status_code == 200 and [ref for ref, _k in billing.refunds] == ["s2"]


def test_no_paid_invoice_for_an_event_over_24h_old_stops_retrying(owner, app, database, caplog):
    client, _ = owner
    billing = app.state.billing

    def none_yet(ref, key):
        raise NoPaidInvoice()

    billing.refund_latest_invoice = none_yet
    now = int(time.time())
    assert _sub_event(client, app, "d1", "checkout.completed", now - 200000, "s1").status_code == 200
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        r = _sub_event(client, app, "d2", "checkout.completed", now - 25 * 3600, "s2", plan="pro")
    assert r.status_code == 200
    assert len(_owed(caplog)) == 1 and _event_stored(database, "d2")


def test_free_invoice_is_info_and_acknowledged(owner, app, caplog):
    client, _ = owner
    app.state.billing.refund_latest_invoice = lambda ref, key: False
    with caplog.at_level(logging.INFO, logger="app.billing"):
        assert _duplicate(client, app).status_code == 200
    assert not _owed(caplog)


# ---- S3: permanent refund rejection is acknowledged, a transient failure is retried ---------------------------
def test_permanent_refund_rejection_logs_refund_owed_with_code_and_acknowledges(owner, app, database, caplog):
    client, _ = owner

    def rejected(ref, key):
        raise AppError(502, "billing_rejected", "provider said: charge_disputed for card 4242", provider_status=400)

    app.state.billing.refund_latest_invoice = rejected
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        assert _duplicate(client, app).status_code == 200
    owed = _owed(caplog)
    assert len(owed) == 1 and owed[0].error == "billing_rejected"
    assert "4242" not in caplog.text and _event_stored(database, "d2")


def test_transient_refund_failure_answers_503_and_stores_no_event(owner, app, database, caplog):
    client, _ = owner

    def down(ref, key):
        raise AppError(503, "billing_unavailable", "x")

    app.state.billing.refund_latest_invoice = down
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        assert _duplicate(client, app).status_code == 503
    assert len(_owed(caplog)) == 1 and not _event_stored(database, "d2")


def test_stripe_no_paid_invoice_raises_but_a_free_invoice_returns_false():
    from .test_t182 import _refund_handler, _stripe
    try:
        _stripe(_refund_handler(None, calls=[])).refund_latest_invoice("sub_2", "k")
        raise AssertionError("expected NoPaidInvoice")
    except NoPaidInvoice:
        pass
    free = {"id": "in_0", "amount_paid": 0, "payment_intent": None}
    assert _stripe(_refund_handler(free, calls=[])).refund_latest_invoice("sub_2", "k") is False


# ---- T-211: only 400/402 are permanent; an event without a timestamp is expired --------------------------------
def _rejecting(status):
    def rejected(ref, key):
        raise AppError(502, "billing_rejected", "provider text 4242", provider_status=status)
    return rejected


def test_409_refund_rejection_is_transient_and_the_redelivery_refunds_once(owner, app, database, caplog):
    client, _ = owner
    billing = app.state.billing
    real = billing.refund_latest_invoice
    billing.refund_latest_invoice = _rejecting(409)
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        assert _duplicate(client, app).status_code == 503
    assert not _event_stored(database, "d2") and "4242" not in caplog.text
    billing.refund_latest_invoice = real
    assert _duplicate(client, app).status_code == 200
    assert len(billing.refunds) == 1 and _event_stored(database, "d2")


def test_400_and_402_refund_rejections_are_acknowledged_as_refund_owed(owner, app, database, caplog):
    client, _ = owner
    app.state.billing.refund_latest_invoice = _rejecting(402)
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        assert _duplicate(client, app).status_code == 200
    assert len(_owed(caplog)) == 1 and _event_stored(database, "d2")


def test_403_refund_rejection_is_transient(owner, app, database):
    client, _ = owner
    app.state.billing.refund_latest_invoice = _rejecting(403)
    assert _duplicate(client, app).status_code == 503
    assert not _event_stored(database, "d2")


def test_stripe_adapter_carries_the_provider_status():
    from .test_t182 import _stripe
    import httpx
    stripe = _stripe(lambda request: httpx.Response(409, json={"error": {"code": "idempotency_key_in_use"}}))
    with pytest.raises(AppError) as error:
        stripe._call("POST", "/refunds", {"a": "b"}, attempts=1)
    assert error.value.provider_status == 409 and "idempotency" not in error.value.message


def test_no_paid_invoice_without_a_timestamp_is_treated_as_expired(owner, app, database, caplog):
    client, _ = owner

    def none_yet(ref, key):
        raise NoPaidInvoice()

    app.state.billing.refund_latest_invoice = none_yet
    import uuid
    from app.billing import BillingUpdate
    from app.routes import billing as route
    update = BillingUpdate(event_id="x1", tenant_id=uuid.uuid4(), status="active", provider_ref="s9", occurred_at=None)
    with caplog.at_level(logging.ERROR, logger="app.billing"):
        route._cancel_and_refund_duplicate(update, app.state.billing)  # returns: acknowledged, no 503
    owed = _owed(caplog)
    assert len(owed) == 1 and owed[0].will_retry is False
