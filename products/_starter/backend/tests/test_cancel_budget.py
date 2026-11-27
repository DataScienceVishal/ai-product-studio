"""T-180 (T-179 M2): the provider cancel runs inside the row lock, so it must finish well before Postgres ends an idle
transaction, and a failure must still be counted when the transaction was killed anyway."""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.billing import CANCEL_WORST_CASE_SECONDS, StripeBilling
from app.config import Settings
from app.db import Database
from app.maintenance import sweep_pending_cancels
from app.models import PendingCancel
from app.routes.billing import ESCALATE_AT

from .test_billing import SECRET, _tenant_id


def _idle_default_seconds():
    return Settings.model_fields["db_idle_in_transaction_timeout_ms"].default / 1000


def test_cancel_budget_is_clearly_under_the_idle_transaction_timeout():
    assert CANCEL_WORST_CASE_SECONDS <= 10
    assert CANCEL_WORST_CASE_SECONDS <= _idle_default_seconds() * 2 / 3
    # the Database default (used by maintenance, which does not override it) must agree
    import inspect
    db_default = inspect.signature(Database).parameters["idle_in_transaction_timeout_ms"].default / 1000
    assert CANCEL_WORST_CASE_SECONDS <= db_default * 2 / 3


def test_worst_case_cancel_measured_with_a_fake_clock(monkeypatch):
    """Every request times out; the adapter's own timeouts and sleeps add up to the stated budget, DELETE then GET."""
    spent = []
    monkeypatch.setattr("app.billing.time.sleep", lambda s: spent.append(s))

    def slow(request: httpx.Request):
        spent.append(request.extensions["timeout"]["read"])
        raise httpx.ReadTimeout("slow")

    try:
        StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(slow))).cancel_subscription("s")
    except Exception:
        pass
    assert sum(spent) <= CANCEL_WORST_CASE_SECONDS

    # a slow first DELETE, then a fast 4xx, then a slow GET check: the other long path
    spent.clear()
    calls = []

    def mixed(request: httpx.Request):
        calls.append(request.method)
        spent.append(request.extensions["timeout"]["read"] if request.method == "GET" or len(calls) == 1 else 0)
        if request.method == "DELETE" and len(calls) == 1:
            raise httpx.ReadTimeout("slow")
        if request.method == "DELETE":
            return httpx.Response(403, json={"error": {"message": "no"}})
        raise httpx.ReadTimeout("slow")

    try:
        StripeBilling("sk_test_x", SECRET, client=httpx.Client(transport=httpx.MockTransport(mixed))).cancel_subscription("s")
    except Exception:
        pass
    assert calls == ["DELETE", "DELETE", "GET"] and sum(spent) <= CANCEL_WORST_CASE_SECONDS


class _SlowDown:
    name = "stripe"

    def __init__(self, seconds):
        self.seconds = seconds

    def cancel_subscription(self, ref):
        time.sleep(self.seconds)
        raise TimeoutError("provider hung")


def test_a_cancel_slower_than_the_idle_timeout_still_counts_each_attempt_and_escalates(owner, database, caplog):
    """The reviewer's probe: the idle timeout (0.3 s here, 15 s in production) kills the locked transaction during the
    call. Each sweep must still increment attempts and last_attempt_at, and the CRITICAL line fires at ESCALATE_AT."""
    client, _ = owner
    tenant = uuid.UUID(_tenant_id(client))
    with database.sessions() as db:
        row_id = PendingCancel(tenant_id=tenant, provider="stripe", ref="sub_slow")
        db.add(row_id)
        db.commit()
        row_id = row_id.id
    small = Database(database.engine.url.render_as_string(hide_password=False), idle_in_transaction_timeout_ms=300)
    try:
        clients, seen, base = {"stripe": _SlowDown(0.6)}, [], datetime.now(timezone.utc)
        with caplog.at_level(logging.WARNING, logger="app.billing"):
            for i in range(ESCALATE_AT):
                with small.sessions() as db:
                    result = sweep_pending_cancels(db, clients, now=base + timedelta(days=2 * (i + 1)))
                assert result == {"cancelled": 0, "failed": 1}, (i, result)
                with database.sessions() as db:
                    row = db.get(PendingCancel, row_id)
                    seen.append((row.attempts, row.last_attempt_at))
                    if i == 0:
                        assert row.last_error and "TimeoutError" in row.last_error
        assert [a for a, _t in seen] == list(range(1, ESCALATE_AT + 1))
        assert len({t for _a, t in seen}) == ESCALATE_AT and all(t is not None for _a, t in seen)
        critical = [r for r in caplog.records if r.levelno == logging.CRITICAL]
        assert len(critical) == 1 and "operator" in critical[0].getMessage()
    finally:
        small.dispose()
        with database.sessions() as db:
            db.query(PendingCancel).filter(PendingCancel.ref == "sub_slow").delete()
            db.commit()
