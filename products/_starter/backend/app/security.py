"""Password hashing (argon2id) and opaque tokens. Only token hashes are ever stored."""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import threading
import weakref
from collections.abc import AsyncIterator, Callable

from fastapi import Depends

import anyio

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

HASH_SLOTS = 2
_hasher = PasswordHasher()  # argon2id with the library's current recommended parameters
# Each hash or check uses about 64 MiB. Bounding concurrency bounds memory: extra requests wait their turn.
_hash_slots = threading.BoundedSemaphore(HASH_SLOTS)  # each argon2 run uses 4 lanes; 2 x 4 suits a 0.5-1 vCPU container
HASH_WAIT_SECONDS = 3.0  # then a 503 with Retry-After, instead of queueing request threads
# Verified against when the email is unknown, so a miss takes as long as a wrong password.
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")

MIN_PASSWORD = 10
MAX_PASSWORD = 128  # bounds hashing cost per request


def password_problem(password: str) -> str | None:
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return f"Use at most {MAX_PASSWORD} characters."
    if not password.strip():
        return "The password can't be only spaces."
    return None


def _busy():
    from .errors import AppError
    return AppError(503, "busy", "We're busy right now. Please try again in a moment.", headers={"Retry-After": "5"})


# Hashing capacity is taken in async code, before the request is given a worker thread, so a login burst
# waits on the event loop (cheap) instead of parking up to 40 threadpool threads and starving /healthz.
# One limiter per event loop (a limiter belongs to the loop it is first used on).
_limiters: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, anyio.CapacityLimiter]" = weakref.WeakKeyDictionary()


def _limiter() -> anyio.CapacityLimiter:
    loop = asyncio.get_running_loop()  # the app runs on asyncio (uvicorn)
    limiter = _limiters.get(loop)
    if limiter is None:
        limiter = _limiters[loop] = anyio.CapacityLimiter(HASH_SLOTS)
    return limiter


def hash_capacity_after(gate: Callable) -> Callable:
    """Dependency factory for routes that hash or verify a password. `gate` holds every cheap check (rate
    limits, session/auth, input validation); FastAPI runs it first, so a request it rejects never takes a
    slot and never queues behind real sign-ins. Then waits at most HASH_WAIT_SECONDS for a slot and answers
    the friendly 503 without occupying a worker thread. The slot is held until the request is done."""

    async def hash_capacity(_gate=Depends(gate)) -> AsyncIterator[None]:
        limiter = _limiter()
        with anyio.move_on_after(HASH_WAIT_SECONDS) as scope:
            await limiter.acquire()
        if scope.cancelled_caught:
            raise _busy()
        try:
            yield
        finally:
            limiter.release()

    hash_capacity.is_hash_capacity = True  # type: ignore[attr-defined]
    hash_capacity.gate = gate  # type: ignore[attr-defined]
    return hash_capacity


class _Slot:
    """Backstop for callers that did not take hash_capacity first: a hashing slot, or a friendly 503 if none frees up soon (so waiting requests don't pile up)."""

    def __enter__(self):
        if not _hash_slots.acquire(timeout=HASH_WAIT_SECONDS):
            raise _busy()

    def __exit__(self, *exc):
        _hash_slots.release()


def hash_password(password: str) -> str:
    """Call outside any database transaction: hashing takes about 0.1 s and 64 MiB."""
    with _Slot():
        return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    try:
        with _Slot():
            return _hasher.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
