"""T-175: a failed takeover cancel is a durable to-do (pending_cancels), retried; dead-marker collisions keep dedup."""
import time
import uuid

import httpx
import pytest
from sqlalchemy import select

from app.billing import MockBilling, StripeBilling
from app.errors import AppError
from app.models import BillingEvent, PendingCancel
from app.maintenance import sweep_pending_cancels
from app.routes.billing import _dead_marker, retry_pending_cancels

from .test_billing import SECRET, _stripe_apply, _stripe_sub, _tenant_id


def _down(ref):
    raise AppError(503, "billing_unavailable", "down")


def _rows(database):
    with database.sessions() as db:
        return [(r.provider, r.ref, r.attempts, r.last_error) for r in db.scalars(select(PendingCancel))]


def _takeover(client, database, provider, prefix="a"):
    """sub_1 goes past_due, then a paid checkout for sub_2 replaces it (the old one must be cancelled)."""
    t, now = _tenant_id(client), int(time.time())
    _stripe_apply(database, t, f"{prefix}1", "checkout.session.completed", now - 300, "sub_1")
    _stripe_apply(database, t, f"{prefix}2", "customer.subscription.updated", now - 250, "sub_1", "past_due")
    _stripe_apply(database, t, f"{prefix}3", "checkout.session.completed", now - 200, "sub_2", plan="pro",
                  billing=provider)
    return t, now


def test_failed_takeover_cancel_is_recorded_and_logged_at_error(owner, database, caplog):
    client, _ = owner
    provider = MockBilling("x", "https://app.test")
    provider.cancel_subscription = _down
    with caplog.at_level("ERROR", logger="app.billing"):
        t, _now = _takeover(client, database, provider)
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")
    rows = _rows(database)
    assert len(rows) == 1 and rows[0][:3] == ("stripe", "sub_1", 1) and rows[0][3] == "AppError: down"
    assert any(r.levelname == "ERROR" and "cancel" in r.getMessage() for r in caplog.records)


def test_successful_takeover_cancel_leaves_no_todo(owner, database):
    client, _ = owner
    provider = MockBilling("x", "https://app.test")
    _takeover(client, database, provider)
    assert provider.cancelled == ["sub_1"] and _rows(database) == []


def test_todo_survives_a_crash_between_commit_and_cancel(owner, database):
    client, _ = owner
    provider = MockBilling("x", "https://app.test")

    def crash(ref):
        raise SystemExit("process killed")  # not an Exception: nothing after the commit runs

    provider.cancel_subscription = crash
    with pytest.raises(SystemExit):
        _takeover(client, database, provider)
    assert _rows(database) == [("stripe", "sub_1", 0, None)]
    good = MockBilling("x", "https://app.test")
    with database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": good}) == {"cancelled": 1, "failed": 0}
    assert good.cancelled == ["sub_1"] and _rows(database) == []


def test_next_event_for_the_tenant_retries_the_cancel(owner, database):
    client, _ = owner
    broken = MockBilling("x", "https://app.test")
    broken.cancel_subscription = _down
    t, now = _takeover(client, database, broken)
    assert len(_rows(database)) == 1
    good = MockBilling("x", "https://app.test")
    _stripe_apply(database, t, "a4", "customer.subscription.updated", now - 100, "sub_2", "active", plan="pro",
                  billing=good)
    assert good.cancelled == ["sub_1"] and _rows(database) == []


def test_a_retry_that_fails_again_counts_attempts_and_keeps_the_todo(owner, database, caplog):
    client, _ = owner
    broken = MockBilling("x", "https://app.test")
    broken.cancel_subscription = _down
    _takeover(client, database, broken)
    with caplog.at_level("ERROR", logger="app.billing"), database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": broken}) == {"cancelled": 0, "failed": 1}
    assert _rows(database)[0][:3] == ("stripe", "sub_1", 2)
    assert any(r.levelname == "ERROR" for r in caplog.records)


@pytest.mark.parametrize("delete_reply", [httpx.Response(404, json={"error": {"code": "resource_missing"}}),
                                          httpx.Response(400, json={"error": {"code": "resource_missing"}})])
def test_sweep_treats_an_already_cancelled_subscription_as_done(owner, database, delete_reply):
    client, _ = owner
    broken = MockBilling("x", "https://app.test")
    broken.cancel_subscription = _down
    _takeover(client, database, broken)

    def handler(request):  # DELETE says gone/rejected; a GET shows the subscription is already canceled
        if request.method == "GET":
            return httpx.Response(200, json={"id": "sub_1", "status": "canceled"})
        return delete_reply

    stripe = StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(handler)))
    with database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": stripe}) == {"cancelled": 1, "failed": 0}
    assert _rows(database) == []


def test_sweep_leaves_a_provider_it_has_no_client_for(owner, database):
    client, _ = owner
    with database.sessions() as db:
        db.add(PendingCancel(tenant_id=uuid.UUID(_tenant_id(client)), provider="other", ref="x"))
        db.commit()
        assert sweep_pending_cancels(db, {"stripe": MockBilling("x", "https://app.test")}) == {
            "cancelled": 0, "failed": 0}
    assert _rows(database) == [("other", "x", 0, None)]


def test_a_ref_has_one_todo_only(owner, database):
    client, _ = owner
    broken = MockBilling("x", "https://app.test")
    broken.cancel_subscription = _down
    t, _now = _takeover(client, database, broken)
    with database.sessions() as db:
        retry_pending_cancels(db, uuid.UUID(t), "stripe", broken)  # fails again: still one row
    assert len(_rows(database)) == 1
    with database.sessions() as db:
        db.add(PendingCancel(tenant_id=uuid.UUID(t), provider="stripe", ref="sub_1"))
        with pytest.raises(Exception):
            db.commit()


def test_dead_marker_collision_keeps_the_second_events_id(owner, database):
    """incomplete_expired then deleted for one never-activated ref: the second event's own dedup row must survive."""
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    assert _stripe_apply(database, t, "d1", "customer.subscription.updated", now - 50, "sub_9", "incomplete_expired")
    assert _stripe_apply(database, t, "d2", "customer.subscription.deleted", now - 40, "sub_9", "canceled")
    with database.sessions() as db:
        assert db.get(BillingEvent, "d2") is not None
        assert db.get(BillingEvent, _dead_marker("stripe", "sub_9")) is not None
    assert _stripe_apply(database, t, "d2", "customer.subscription.deleted", now - 40, "sub_9", "canceled") is False
