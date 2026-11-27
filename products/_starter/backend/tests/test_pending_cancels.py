"""T-175: a failed takeover cancel is a durable to-do (pending_cancels), retried; dead-marker collisions keep dedup."""
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import select

from app.billing import MockBilling, StripeBilling, sign
from app.errors import AppError
from app.models import BillingEvent, PendingCancel
from app.maintenance import sweep_pending_cancels
from app.routes.billing import _dead_marker, retry_pending_cancels

from .test_billing import SECRET, _stripe_apply, _stripe_sub, _tenant_id


_LATER = datetime.now(timezone.utc) + timedelta(days=2)  # past any backoff after an attempt made during the test


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
        assert sweep_pending_cancels(db, {"stripe": broken}, now=_LATER) == {"cancelled": 0, "failed": 1}
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
        assert sweep_pending_cancels(db, {"stripe": stripe}, now=_LATER) == {"cancelled": 1, "failed": 0}
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


def test_b1_a_pending_cancel_never_cancels_the_tenants_current_subscription(owner, database):
    """Reviewer's sequence: sub_1 comes back as the current subscription while it still has a to-do."""
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    provider = MockBilling("x", "https://app.test")
    real = provider.cancel_subscription
    provider.cancel_subscription = _down
    _stripe_apply(database, t, "p1", "checkout.session.completed", now - 300, "sub_1")
    _stripe_apply(database, t, "p2", "customer.subscription.updated", now - 250, "sub_1", "past_due")
    _stripe_apply(database, t, "p3", "checkout.session.completed", now - 200, "sub_2", plan="pro", billing=provider)
    _stripe_apply(database, t, "p4", "customer.subscription.updated", now - 150, "sub_2", "past_due", plan="pro",
                  billing=provider)
    _stripe_apply(database, t, "p5", "checkout.session.async_payment_succeeded", now - 100, "sub_1", billing=provider)
    assert _stripe_sub(database, t)[2] == "sub_1"
    assert [r[1] for r in _rows(database)] == ["sub_2"]  # sub_1 is current, so its to-do is gone
    provider.cancel_subscription = real  # the provider is back up
    _stripe_apply(database, t, "p6", "customer.subscription.updated", now - 50, "sub_1", "active", billing=provider)
    assert provider.cancelled == ["sub_2"]
    assert _stripe_sub(database, t) == ("active", "starter", "sub_1") and _rows(database) == []


def test_b1_the_retry_and_the_sweep_skip_and_drop_a_row_for_the_current_ref(owner, database):
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    _stripe_apply(database, t, "q1", "checkout.session.completed", now - 100, "sub_1")
    with database.sessions() as db:
        db.add(PendingCancel(tenant_id=uuid.UUID(t), provider="stripe", ref="sub_1"))
        db.commit()
    provider = MockBilling("x", "https://app.test")
    with database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": provider}) == {"cancelled": 0, "failed": 0}
    assert provider.cancelled == [] and _rows(database) == []


def test_b1_one_bad_row_does_not_stop_the_sweep(owner, database, monkeypatch):
    import app.routes.billing as routes
    client, _ = owner
    with database.sessions() as db:
        for ref in ("old_1", "old_2"):
            db.add(PendingCancel(tenant_id=uuid.UUID(_tenant_id(client)), provider="stripe", ref=ref))
        db.commit()
    real, seen = routes.attempt_pending_cancel, []

    def flaky(db, row_id, billing):
        ref = db.scalar(select(PendingCancel.ref).where(PendingCancel.id == row_id))
        seen.append(ref)
        if ref == "old_1":
            raise RuntimeError("stale data")
        return real(db, row_id, billing)

    monkeypatch.setattr(routes, "attempt_pending_cancel", flaky)
    provider = MockBilling("x", "https://app.test")
    with database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": provider}) == {"cancelled": 1, "failed": 1}
    assert seen == ["old_1", "old_2"] and provider.cancelled == ["old_2"]


def test_s4_a_concurrent_dead_marker_insert_keeps_the_events_dedup_row(owner, database):
    """Another transaction inserts the marker and commits while this event waits on it: the savepoint path."""
    import threading
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    other = database.sessions().__enter__()
    other.add(BillingEvent(id=_dead_marker("stripe", "sub_9")))
    other.flush()  # held uncommitted
    result = {}
    worker = threading.Thread(target=lambda: result.update(
        applied=_stripe_apply(database, t, "c1", "customer.subscription.deleted", now - 40, "sub_9", "canceled")))
    worker.start()
    time.sleep(1.0)
    assert worker.is_alive()  # blocked on the other transaction's unique key
    other.commit()
    other.close()
    worker.join(10)
    assert result == {"applied": True}
    with database.sessions() as db:
        assert db.get(BillingEvent, "c1") is not None
    assert _stripe_apply(database, t, "c1", "customer.subscription.deleted", now - 40, "sub_9", "canceled") is False


# --- T-176 ------------------------------------------------------------------------------------

def _seed(database, tenant, ref, attempts=0, last_attempt_at=None):
    with database.sessions() as db:
        db.add(PendingCancel(tenant_id=uuid.UUID(tenant), provider="stripe", ref=ref, attempts=attempts,
                             last_attempt_at=last_attempt_at))
        db.commit()


def _row(database, ref):
    with database.sessions() as db:
        return db.scalar(select(PendingCancel).where(PendingCancel.ref == ref))


def test_s3_a_failing_retry_does_not_change_the_webhooks_answer(app, owner, database, monkeypatch):
    """The retry runs after the event is committed: whatever it raises, the webhook still answers 200 applied."""
    import app.routes.billing as routes
    from sqlalchemy.orm.exc import StaleDataError
    from app.models import Subscription
    client, _ = owner
    tenant = _tenant_id(client)
    billing = app.state.billing
    with database.sessions() as db:  # a to-do for the mock provider, so the retry has something to do
        db.add(PendingCancel(tenant_id=uuid.UUID(tenant), provider=billing.name, ref="old_x"))
        db.commit()

    def boom(*args, **kwargs):
        raise StaleDataError("row vanished")

    monkeypatch.setattr(routes, "retry_pending_cancels", boom)
    session_id = client.post("/api/billing/checkout", json={"plan": "starter"}).json()["checkout_id"]
    payload = billing.completion_event(session_id)
    event_id = json.loads(payload)["id"]
    response = client.post("/api/billing/webhook", content=payload,
                           headers={"x-billing-signature": sign(payload, billing.secret)})
    assert response.status_code == 200 and response.json() == {"received": True, "applied": True}
    with database.sessions() as db:
        assert db.get(BillingEvent, event_id) is not None
        assert db.scalar(select(Subscription.status).where(Subscription.tenant_id == uuid.UUID(tenant))) == "active"


def test_note1_the_takeover_deletes_the_new_refs_todo_on_its_own(owner, database):
    """No retry runs (billing=None), so only the takeover's own delete can remove the row for the new ref."""
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    _stripe_apply(database, t, "n1", "checkout.session.completed", now - 300, "sub_1")
    _stripe_apply(database, t, "n2", "customer.subscription.updated", now - 250, "sub_1", "past_due")
    _seed(database, t, "sub_2")  # a stale to-do for the ref that is about to become current
    _stripe_apply(database, t, "n3", "checkout.session.completed", now - 200, "sub_2", plan="pro", billing=None)
    assert _stripe_sub(database, t) == ("active", "pro", "sub_2")
    assert [r[1] for r in _rows(database)] == ["sub_1"]  # sub_2's row is gone; the replaced sub_1 is the to-do


def test_note2_a_row_locked_by_another_session_is_skipped_without_calling_the_provider(owner, database):
    from app.routes.billing import attempt_pending_cancel
    client, _ = owner
    t = _tenant_id(client)
    _seed(database, t, "old_1")
    row_id = _row(database, "old_1").id
    provider = MockBilling("x", "https://app.test")
    with database.sessions() as holder, database.sessions() as db:
        holder.scalar(select(PendingCancel).where(PendingCancel.id == row_id).with_for_update())  # committed row, held
        assert attempt_pending_cancel(db, row_id, provider) is None
        assert provider.cancelled == []
        holder.rollback()
    assert _row(database, "old_1") is not None  # untouched, still a to-do


def test_s7_every_failed_attempt_stamps_last_attempt_at(owner, database):
    from datetime import datetime, timedelta, timezone
    client, _ = owner
    broken = MockBilling("x", "https://app.test")
    broken.cancel_subscription = _down
    before = datetime.now(timezone.utc)
    _takeover(client, database, broken)
    first = _row(database, "sub_1").last_attempt_at
    assert first is not None and before - timedelta(seconds=5) <= first <= datetime.now(timezone.utc)
    with database.sessions() as db:
        sweep_pending_cancels(db, {"stripe": broken}, now=datetime.now(timezone.utc) + timedelta(days=2))
    second = _row(database, "sub_1")
    assert second.attempts == 2 and second.last_attempt_at > first


def test_s5_the_webhook_retries_only_rows_below_the_attempt_limit(owner, database):
    from app.routes import billing as routes
    client, _ = owner
    t, now = _tenant_id(client), int(time.time())
    _seed(database, t, "fresh", attempts=routes.INLINE_RETRY_MAX_ATTEMPTS - 1)
    _seed(database, t, "worn", attempts=routes.INLINE_RETRY_MAX_ATTEMPTS)
    good = MockBilling("x", "https://app.test")
    _stripe_apply(database, t, "s5", "checkout.session.completed", now - 100, "sub_1", billing=good)
    assert good.cancelled == ["fresh"]
    assert [r[1] for r in _rows(database)] == ["worn"]  # left to the sweep
    with database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": good}) == {"cancelled": 1, "failed": 0}
    assert good.cancelled == ["fresh", "worn"]


@pytest.mark.parametrize("attempts,age,tried", [
    (0, None, True),                                  # never tried
    (2, timedelta(minutes=3), False),                 # backoff 2**2 = 4 min
    (2, timedelta(minutes=5), True),
    (3, timedelta(minutes=5), False),                 # 8 min
    (3, timedelta(minutes=9), True),
    (20, timedelta(hours=23), False),                 # capped at 24 h
    (20, timedelta(hours=25), True),
])
def test_s6_the_sweep_backs_off_by_attempts_up_to_a_day(owner, database, attempts, age, tried):
    client, _ = owner
    now = datetime.now(timezone.utc)
    _seed(database, _tenant_id(client), "old_1", attempts=attempts, last_attempt_at=now - age if age else None)
    provider = MockBilling("x", "https://app.test")
    with database.sessions() as db:
        result = sweep_pending_cancels(db, {"stripe": provider}, now=now)
    assert (provider.cancelled == ["old_1"]) is tried
    assert result == ({"cancelled": 1, "failed": 0} if tried else {"cancelled": 0, "failed": 0})


def test_s6_a_row_with_attempts_but_no_timestamp_is_tried(owner, database):
    """Rows written before last_attempt_at existed have attempts > 0 and no timestamp: do not back off forever."""
    client, _ = owner
    _seed(database, _tenant_id(client), "old_1", attempts=4, last_attempt_at=None)
    provider = MockBilling("x", "https://app.test")
    with database.sessions() as db:
        assert sweep_pending_cancels(db, {"stripe": provider}) == {"cancelled": 1, "failed": 0}


def test_s6_the_tenth_failure_logs_one_critical_line_with_ids_only_then_warnings(owner, database, caplog):
    from app.routes import billing as routes
    client, _ = owner
    t = _tenant_id(client)
    _seed(database, t, "old_1", attempts=routes.ESCALATE_AT - 2)
    broken = MockBilling("x", "https://app.test")
    broken.cancel_subscription = _down
    far = datetime.now(timezone.utc)

    def run():
        caplog.clear()
        far_now = far + timedelta(days=run.n)
        run.n += 2
        with caplog.at_level("DEBUG", logger="app.billing"), database.sessions() as db:
            sweep_pending_cancels(db, {"stripe": broken}, now=far_now)
        return [(r.levelname, r.getMessage()) for r in caplog.records if "cancel" in r.getMessage()], caplog.records
    run.n = 1
    lines, _ = run()          # attempts 8 -> 9: ERROR
    assert [lvl for lvl, _m in lines] == ["ERROR"]
    lines, records = run()    # 9 -> 10: the transition
    assert [lvl for lvl, _m in lines] == ["CRITICAL"] and lines[0][1] == "pending cancel needs operator"
    critical = [r for r in records if r.levelname == "CRITICAL"][0]
    assert critical.old_subscription == "old_1" and critical.tenant_id == t and critical.attempts == 10
    assert not critical.exc_info
    lines, _ = run()          # 10 -> 11: WARNING, never ERROR or CRITICAL again
    assert [lvl for lvl, _m in lines] == ["WARNING"]
    lines, _ = run()
    assert [lvl for lvl, _m in lines] == ["WARNING"]
    assert _row(database, "old_1").attempts == 12
