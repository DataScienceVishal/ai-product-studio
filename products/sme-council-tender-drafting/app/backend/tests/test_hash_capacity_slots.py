"""T-15 review C1 and C2.

C1: cheap rejects (rate limit, no session, weak password, wrong confirmation) never take a hash slot.
C2: every path out of a request (200, 401, 409, 422, 429, 503, 500) returns its slot. Each TestClient request
runs on its own event loop, so a leaked slot would vanish with the loop; these tests run everything on ONE loop.
"""
import asyncio
import time

import httpx

import app.security as security
from tests.test_async_hash_capacity import SlowHasher

HEADERS = {"X-Requested-With": "test"}


def _run(app, scenario):
    async def main():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="https://testserver", headers=HEADERS) as client:
            return await scenario(client)

    return asyncio.run(main())


async def _hold_all_slots():
    limiter = security._limiter()
    holders = [object() for _ in range(security.HASH_SLOTS)]
    for holder in holders:
        await limiter.acquire_on_behalf_of(holder)
    return limiter, holders


def _release(limiter, holders):
    for holder in holders:
        limiter.release_on_behalf_of(holder)


def test_every_exit_path_returns_its_slot_on_one_loop(app, monkeypatch):
    monkeypatch.setattr(security, "HASH_WAIT_SECONDS", 0.3)
    app.state.settings.auth_rate_limit_per_minute = 8

    async def scenario(client):
        limiter = security._limiter()
        seen = {}

        async def step(name, request_coro):
            r = await request_coro
            seen[name] = r.status_code
            assert limiter.borrowed_tokens == 0, f"slot leaked after {name} ({r.status_code})"
            return r

        good = {"email": "a@x.test", "password": "a long enough pass", "company_name": "Acme"}
        await step("signup 201", client.post("/api/auth/signup", json=good))
        await step("signup 409", client.post("/api/auth/signup", json=good))
        await step("signup 422", client.post("/api/auth/signup", json={**good, "password": "short"}))
        await step("login 200", client.post("/api/auth/login", json={"email": "a@x.test", "password": good["password"]}))
        await step("login 401", client.post("/api/auth/login", json={"email": "a@x.test", "password": "wrong password"}))
        await step("login 422 body", client.post("/api/auth/login", json={"email": "not-an-email"}))
        await step("delete 422", client.request("DELETE", "/api/account", json={"password": good["password"], "confirm": "no"}))
        await step("delete 401", client.request("DELETE", "/api/account", json={"password": "wrong password", "confirm": "DELETE"}))
        # 503: every slot busy, the request times out waiting
        limiter, holders = await _hold_all_slots()
        try:
            r = await client.post("/api/auth/login", json={"email": "a@x.test", "password": "x" * 12})
            assert r.status_code == 503 and limiter.borrowed_tokens == security.HASH_SLOTS
            assert limiter.statistics().tasks_waiting == 0
        finally:
            _release(limiter, holders)
        assert limiter.borrowed_tokens == 0, "slot leaked after 503"
        # 429: over the per-minute limit (rejected by the gate)
        statuses = [(await client.post("/api/auth/login", json={"email": "b@x.test", "password": "x" * 12})).status_code
                    for _ in range(app.state.settings.auth_rate_limit_per_minute + 2)]
        assert statuses[-1] == 429
        assert limiter.borrowed_tokens == 0, "slot leaked after 429"
        app.state.limiter._hits.clear()  # a fresh window for the next step
        # 500: the endpoint blows up after the slot is taken
        monkeypatch.setattr("app.routes.auth.verify_password", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")))
        await step("login 500", client.post("/api/auth/login", json={"email": "c@x.test", "password": "x" * 12}))
        assert seen["login 500"] == 500
        return seen

    seen = _run(app, scenario)
    assert seen["signup 201"] == 201 and seen["signup 409"] == 409 and seen["signup 422"] == 422
    assert seen["login 200"] == 200 and seen["login 401"] == 401 and seen["login 422 body"] == 422
    assert seen["delete 422"] == 422 and seen["delete 401"] == 401


def test_cheap_rejects_never_take_or_wait_for_a_slot(app, monkeypatch):
    """With every slot busy, requests that the gate rejects still get their own answer, instantly (not a 503)."""
    monkeypatch.setattr(security, "HASH_WAIT_SECONDS", 2.0)
    app.state.settings.auth_rate_limit_per_minute = 3

    async def scenario(client):
        limiter, holders = await _hold_all_slots()
        try:
            started = time.perf_counter()
            results = {}
            limit = app.state.settings.auth_rate_limit_per_minute
            for _ in range(limit):  # use up this address's allowance without touching the hasher
                app.state.limiter.hit("login-ip:127.0.0.1", limit)
            over = [await client.post("/api/auth/login", json={"email": "z@x.test", "password": "x" * 12})]
            results["over-limit login"] = over[-1].status_code
            results["no-cookie delete account"] = (await client.request(
                "DELETE", "/api/account", json={"password": "x" * 12, "confirm": "DELETE"})).status_code
            results["no-cookie delete me"] = (await client.request(
                "DELETE", "/api/account/me", json={"password": "x" * 12, "confirm": "DELETE"})).status_code
            results["weak signup"] = (await client.post(
                "/api/auth/signup", json={"email": "w@x.test", "password": "short", "company_name": "W"})).status_code
            results["weak reset"] = (await client.post(
                "/api/auth/password-reset/confirm", json={"token": "t" * 20, "new_password": "short"})).status_code
            elapsed = time.perf_counter() - started
            assert limiter.borrowed_tokens == security.HASH_SLOTS  # only the test's own holders
            assert limiter.statistics().tasks_waiting == 0
            return results, elapsed
        finally:
            _release(limiter, holders)

    results, elapsed = _run(app, scenario)
    assert results == {"over-limit login": 429, "no-cookie delete account": 401, "no-cookie delete me": 401,
                       "weak signup": 422, "weak reset": 422}
    assert elapsed < 2.0, f"cheap rejects waited for a slot ({elapsed:.2f}s)"


def test_a_flood_of_unauthenticated_deletes_does_not_turn_away_real_logins(app, monkeypatch):
    """Review probe: cookieless DELETE /api/account used to take slots and make real sign-ins return 503."""
    monkeypatch.setattr(security, "_hasher", SlowHasher())
    monkeypatch.setattr(security, "HASH_WAIT_SECONDS", 1.0)

    async def scenario(client):
        flood = [asyncio.create_task(client.request("DELETE", "/api/account",
                                                    json={"password": "x" * 12, "confirm": "DELETE"}))
                 for _ in range(300)]
        await asyncio.sleep(0.05)
        real = [asyncio.create_task(client.post("/api/auth/login", json={"email": f"r{i}@x.test", "password": "x" * 12}))
                for i in range(2)]  # 2 x 0.4 s fits inside the 1.0 s wait with 2 slots
        real_codes = [r.status_code for r in await asyncio.gather(*real)]
        flood_codes = {r.status_code for r in await asyncio.gather(*flood)}
        assert security._limiter().borrowed_tokens == 0
        return real_codes, flood_codes

    real_codes, flood_codes = _run(app, scenario)
    assert real_codes == [401, 401]  # wrong credentials, not "busy"
    assert flood_codes == {401}
