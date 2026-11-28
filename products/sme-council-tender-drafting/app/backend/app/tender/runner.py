"""The ai_tasks job runner (DESIGN 4.6).

A worker claims a row with SELECT ... FOR UPDATE SKIP LOCKED, sets a lease, and runs the task's handler with no
transaction open. The handler calls `heartbeat()` before every model call, which extends the lease. A worker that
dies leaves status `running` with an expired lease; the next poll takes it over. A task that may already have been
billed is retried at most once (`attempts` caps at MAX_ATTEMPTS); after that it is failed, never looped.
"""
from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_, select, update
from sqlalchemy.orm import sessionmaker

from ..errors import AppError
from ..tender_models import AITask

log = logging.getLogger("app.tender.runner")
MAX_ATTEMPTS = 2


class LeaseLost(Exception):
    """This worker no longer owns the task (its lease expired and another worker took it over). Stop quietly."""


# kind -> handler(sessions, task, heartbeat, provider) -> (input_tokens, output_tokens). Slices S4 to S6 register theirs.
# `provider` is the worker provider the Runner built (180 s limits); a handler never builds its own.
Handler = Callable[[sessionmaker, AITask, Callable[[], None], object], tuple[int, int]]

HANDLERS: dict[str, Handler] = {}
# kind -> hook(sessions, task), run when a task is failed as attempts_exhausted (the handler never got to clean up).
FAILURE_HOOKS: dict[str, Callable[[sessionmaker, AITask], None]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def claim_next(sessions: sessionmaker, lease: timedelta, now: datetime | None = None) -> AITask | None:
    """Take the oldest queued task, or a running one whose lease has expired. Returns a detached row or None."""
    now = now or _now()
    with sessions() as db:
        while True:
            task = db.scalar(select(AITask).where(or_(AITask.status == "queued",
                                                      (AITask.status == "running") & (AITask.lease_until < now)))
                             .order_by(AITask.created_at).limit(1).with_for_update(skip_locked=True))
            if task is None:
                db.rollback()
                return None
            if task.attempts >= MAX_ATTEMPTS:  # a possibly-billed task is retried once, then stops
                task.status, task.error_code, task.lease_until = "failed", "attempts_exhausted", None
                db.commit()
                db.expunge(task)
                _run_failure_hook(sessions, task)
                continue
            task.status, task.lease_until, task.attempts = "running", now + lease, task.attempts + 1
            db.commit()
            db.refresh(task)
            db.expunge(task)
            return task


def _run_failure_hook(sessions: sessionmaker, task: AITask) -> None:
    hook = FAILURE_HOOKS.get(task.kind)
    if hook is None:
        return
    try:
        hook(sessions, task)
    except Exception:
        log.error("ai task failure hook crashed", extra={"task": str(task.id), "kind": task.kind}, exc_info=True)


def _owned(task: AITask):
    """Fence: only the attempt that claimed the row may touch it. A takeover bumps `attempts`."""
    return (AITask.tenant_id == task.tenant_id, AITask.id == task.id, AITask.attempts == task.attempts,
            AITask.status == "running")


def extend_lease(sessions: sessionmaker, task: AITask, lease: timedelta) -> None:
    with sessions() as db:
        result = db.execute(update(AITask).where(*_owned(task)).values(lease_until=_now() + lease))
        db.commit()
    if result.rowcount == 0:
        raise LeaseLost(str(task.id))


def _finish(sessions: sessionmaker, task: AITask, status: str, code: str | None, tin: int, tout: int) -> bool:
    with sessions() as db:
        result = db.execute(update(AITask).where(*_owned(task))
                            .values(status=status, error_code=code, lease_until=None,
                                    input_tokens=AITask.input_tokens + tin, output_tokens=AITask.output_tokens + tout))
        db.commit()
    if result.rowcount == 0:
        log.warning("ai task result dropped: lease lost", extra={"task": str(task.id)})
        return False
    return True


def run_one(sessions: sessionmaker, lease: timedelta, handlers: dict[str, Handler] | None = None,
            now: datetime | None = None, provider=None) -> bool:
    """Claim and run one task. Returns False when there was nothing to do."""
    task = claim_next(sessions, lease, now)
    if task is None:
        return False
    handler = (handlers if handlers is not None else HANDLERS).get(task.kind)
    if handler is None:
        _finish(sessions, task, "failed", "no_handler", 0, 0)
        return True
    try:
        tin, tout = handler(sessions, task, lambda: extend_lease(sessions, task, lease), provider)
    except LeaseLost:
        log.warning("ai task lease lost; another worker owns it", extra={"task": str(task.id)})
    except AppError as error:  # budget refusals, truncation, invalid output: fixed codes, no document text
        tin, tout = getattr(error, "task_tokens", (0, 0))  # a handler may report what it used before it stopped
        _finish(sessions, task, "failed", error.code[:40], tin, tout)
    except Exception:
        log.error("ai task crashed", extra={"task": str(task.id), "kind": task.kind}, exc_info=True)
        _finish(sessions, task, "failed", "internal", 0, 0)
    else:
        _finish(sessions, task, "done", None, tin, tout)
    return True


class Runner:
    """`threads` workers polling the queue. threads=0 starts nothing (tests drive run_one directly)."""

    def __init__(self, sessions: sessionmaker, threads: int, lease_seconds: int, poll_seconds: float = 2.0,
                 handlers: dict[str, Handler] | None = None, provider=None):
        self.provider = provider
        self.sessions, self.lease, self.poll = sessions, timedelta(seconds=lease_seconds), poll_seconds
        self.handlers, self.stop_event = handlers, threading.Event()
        self.threads = [threading.Thread(target=self._loop, name=f"ai-worker-{i}", daemon=True) for i in range(threads)]

    def start(self) -> None:
        for thread in self.threads:
            thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=5)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                busy = run_one(self.sessions, self.lease, self.handlers, provider=self.provider)
            except Exception:
                log.error("ai worker loop error", exc_info=True)
                busy = False
            if not busy:
                self.stop_event.wait(self.poll)
