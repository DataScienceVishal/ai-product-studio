"""T-15: hashing capacity is taken on the event loop, before a worker thread is assigned.

Before: every waiting login sat in a worker thread for up to HASH_WAIT_SECONDS, so a burst filled the
threadpool and /healthz queued behind it (measured 5.7 s). After: waiters cost nothing but a coroutine.
"""
import asyncio
import inspect
import time

import anyio
import httpx
from fastapi.routing import APIRoute

import app.security as security

BURST = 60  # more than the 40 default worker threads, so a thread-per-waiter design cannot hide


class SlowHasher:
    """Stands in for argon2: every check takes 0.4 s and never matches."""

    def hash(self, password):
        time.sleep(0.4)
        return "$fake$"

    def verify(self, stored, password):
        time.sleep(0.4)
        return False

    def check_needs_rehash(self, stored):
        return False


async def _burst(app, paths_during=("/livez", "/healthz")):
    transport = httpx.ASGITransport(app=app)
    headers = {"X-Requested-With": "test"}
    async with httpx.AsyncClient(transport=transport, base_url="https://testserver", headers=headers) as client:
        peak = 0
        done = asyncio.Event()

        async def watch_threads():
            nonlocal peak
            limiter = anyio.to_thread.current_default_thread_limiter()
            while not done.is_set():
                peak = max(peak, limiter.borrowed_tokens)
                await asyncio.sleep(0.005)

        async def login(i):
            started = time.perf_counter()
            r = await client.post("/api/auth/login", json={"email": f"u{i}@x.test", "password": "whatever pass"})
            return r, time.perf_counter() - started

        watcher = asyncio.create_task(watch_threads())
        logins = [asyncio.create_task(login(i)) for i in range(BURST)]
        await asyncio.sleep(0.3)  # the burst is in flight
        probes = {}
        for path in paths_during:
            started = time.perf_counter()
            r = await client.get(path)
            probes[path] = (r.status_code, time.perf_counter() - started)
        results = await asyncio.gather(*logins)
        done.set()
        await watcher
        return probes, results, peak


def test_a_login_burst_does_not_hold_worker_threads_or_delay_health_probes(app, monkeypatch):
    monkeypatch.setattr(security, "_hasher", SlowHasher())
    monkeypatch.setattr(security, "HASH_WAIT_SECONDS", 1.5)
    probes, results, peak_threads = asyncio.run(_burst(app))
    for path, (status, seconds) in probes.items():
        assert status == 200 and seconds < 1.0, f"{path} took {seconds:.2f}s during the burst"
    assert peak_threads <= security.HASH_SLOTS + 2, f"{peak_threads} worker threads were in use"
    statuses = [r.status_code for r, _ in results]
    assert set(statuses) <= {401, 503}
    assert statuses.count(503) > 0 and statuses.count(401) > 0  # some got a slot, the rest were told to retry
    for r, _ in results:
        if r.status_code == 503:
            assert r.headers["retry-after"] == "5" and r.json()["error"] == "busy"


def test_excess_logins_get_503_quickly_when_every_slot_is_busy(app, monkeypatch):
    monkeypatch.setattr(security, "HASH_WAIT_SECONDS", 0.5)

    async def scenario():
        limiter = security._limiter()
        holders = [object() for _ in range(security.HASH_SLOTS)]
        for holder in holders:
            await limiter.acquire_on_behalf_of(holder)
        try:
            return await _burst(app)
        finally:
            for holder in holders:
                limiter.release_on_behalf_of(holder)

    probes, results, peak_threads = asyncio.run(scenario())
    assert all(r.status_code == 503 for r, _ in results)
    assert all(seconds < 1.5 for _, seconds in results)
    assert peak_threads <= 2
    assert all(status == 200 and seconds < 1.0 for status, seconds in probes.values())


def test_every_route_that_hashes_or_verifies_takes_capacity_first():
    """Guards new callers: a route calling hash_password/verify_password needs the hash_capacity dependency."""
    hashing = []
    from app.routes import account, auth, billing, notes, team
    routers = [getattr(module, name) for module in (account, auth, billing, notes, team)
               for name in ("router", "public") if hasattr(module, name)]
    for route in (r for router in routers for r in router.routes):
        if not isinstance(route, APIRoute):
            continue
        source = inspect.getsource(route.endpoint)
        if "hash_password(" in source or "verify_password(" in source:
            hashing.append(route)
            calls = [d.call for d in route.dependant.dependencies]
            capacity = [c for c in calls if getattr(c, "is_hash_capacity", False)]
            assert capacity, f"{route.path} hashes but does not take hash_capacity_after(gate)"
            # route-level dependencies run first, and the slot dependency runs only after its gate (a sub-dependency)
            assert calls.index(capacity[0]) == 0, f"{route.path}: the capacity dependency must come first"
            sub = next(d for d in route.dependant.dependencies if d.call is capacity[0])
            assert [d.call for d in sub.dependencies] == [capacity[0].gate], f"{route.path}: the gate must precede the slot"
    assert {r.path for r in hashing} >= {"/api/auth/signup", "/api/auth/login", "/api/auth/password-reset/confirm",
                                          "/api/invitations/accept", "/api/account", "/api/account/me"}


def test_the_limiter_is_per_event_loop():
    async def get():
        return security._limiter()

    first, second = asyncio.run(get()), asyncio.run(get())
    assert first is not second and first.total_tokens == security.HASH_SLOTS
