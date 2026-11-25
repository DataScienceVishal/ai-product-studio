"""Redis-backed rate limits (T-15): shared across replicas, same window semantics, safe when Redis fails."""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import CancelledError
from types import SimpleNamespace
from unittest import mock

import fakeredis
import pytest
import redis

from app import ratelimit
from app.errors import AppError
from app.ratelimit import RateLimiter, build_redis_client


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def _replica(server) -> RateLimiter:
    return RateLimiter(redis_client=fakeredis.FakeRedis(server=server))


def test_limit_is_shared_by_two_replicas(server):
    a, b = _replica(server), _replica(server)
    assert a.hit("login-ip:1", 3) is None
    assert b.hit("login-ip:1", 3) is None
    assert a.hit("login-ip:1", 3) is None
    wait = b.hit("login-ip:1", 3)  # the 4th hit anywhere is refused, whichever replica gets it
    assert wait is not None and 0 < wait <= 60
    assert a.hit("login-ip:1", 3) is not None
    assert a.hit("login-ip:2", 3) is None  # other keys are independent


def test_in_memory_default_is_per_instance_and_unchanged():
    a, b = RateLimiter(), RateLimiter()
    for _ in range(3):
        assert a.hit("k", 3) is None
    assert a.hit("k", 3) is not None
    assert b.hit("k", 3) is None


def test_window_expires_and_keys_get_a_ttl(server):
    a = _replica(server)
    assert a.hit("k", 1, 0.3) is None
    assert a.hit("k", 1, 0.3) is not None
    assert fakeredis.FakeRedis(server=server).pttl("rl:k") > 0
    time.sleep(0.4)
    assert a.hit("k", 1, 0.3) is None


def test_retry_after_counts_down_from_the_oldest_hit(server):
    a = _replica(server)
    a.hit("k", 1, 2)
    first = a.hit("k", 1, 2)
    assert 1.5 < first <= 2
    time.sleep(0.4)
    later = a.hit("k", 1, 2)
    assert 0 < later < first - 0.3  # it counts down; a constant window would fail


def test_check_raises_429_with_retry_after(server):
    a = _replica(server)
    a.check("k", 1)
    with pytest.raises(AppError) as err:
        a.check("k", 1)
    assert err.value.status == 429 and "Retry-After" in err.value.headers


class _Broken:
    def __init__(self, exc):
        self.calls = 0
        self.exc = exc

    def register_script(self, _src):
        def run(**_kw):
            self.calls += 1
            raise self.exc
        return run


@pytest.mark.parametrize("exc", [redis.ConnectionError("boom redis://u:secret@host"), redis.TimeoutError("slow"),
                                 redis.ResponseError("OOM")])
def test_redis_failure_falls_back_to_in_process_limits(exc, caplog):
    broken = _Broken(exc)
    limiter = RateLimiter(redis_client=broken)
    with caplog.at_level(logging.WARNING, logger="app.ratelimit"):
        assert limiter.hit("k", 2) is None
        assert limiter.hit("k", 2) is None
        assert limiter.hit("k", 2) is not None  # still enforced, in this process
    assert broken.calls == 1  # backed off after the first failure: no timeout per request
    assert len(caplog.records) == 1
    assert "secret" not in caplog.text and "redis://" not in caplog.text  # never the URL or password


def test_warnings_are_rate_limited_and_redis_is_retried_after_backoff(monkeypatch, server, caplog):
    broken = _Broken(redis.ConnectionError("x"))
    limiter = RateLimiter(redis_client=broken)
    clock = [1000.0]
    monkeypatch.setattr(ratelimit.time, "monotonic", lambda: clock[0])
    with caplog.at_level(logging.WARNING, logger="app.ratelimit"):
        limiter.hit("a", 100)
        clock[0] += ratelimit.RETRY_AFTER_FAILURE + 1
        limiter.hit("a", 100)  # retried, fails again, but within WARN_EVERY: one warning only
        assert broken.calls == 2 and len(caplog.records) == 1
        clock[0] += ratelimit.WARN_EVERY
        limiter.hit("a", 100)
        assert len(caplog.records) == 2
    # Redis comes back: it is used again
    limiter._redis_script = fakeredis.FakeRedis(server=server).register_script(ratelimit._SLIDING_WINDOW_LUA)
    clock[0] += ratelimit.RETRY_AFTER_FAILURE + 1
    assert limiter.hit("b", 1) is None and limiter.hit("b", 1) is not None


def test_unreachable_redis_with_real_client_is_fast_and_does_not_raise():
    limiter = RateLimiter(redis_client=build_redis_client("redis://:pw@127.0.0.1:1/0"))
    started = time.monotonic()
    assert limiter.hit("k", 1) is None
    assert limiter.hit("k", 1) is not None
    assert time.monotonic() - started < 1.0


def test_client_uses_short_timeouts_and_tls_for_rediss():
    client = build_redis_client("rediss://:pw@cache.example.net:6380/0")
    kwargs = client.connection_pool.connection_kwargs
    assert kwargs["socket_timeout"] <= 0.2 and kwargs["socket_connect_timeout"] <= 0.2
    assert client.connection_pool.connection_class is redis.SSLConnection


def test_app_uses_redis_only_when_configured(app):
    from app.main import create_app
    assert app.state.limiter._redis is None  # default settings: in-memory
    settings = app.state.settings.model_copy(update={"rate_limit_redis_url": "redis://127.0.0.1:1/0"})
    assert create_app(settings).state.limiter._redis is not None


def test_redis_key_prefix_separates_products_and_environments(app, server):
    from app.main import create_app
    other = app.state.settings.model_copy(update={"app_name": "other-product"})
    a, b = create_app(app.state.settings), create_app(other)
    assert a.state.limiter._redis_prefix != b.state.limiter._redis_prefix
    assert a.state.limiter._redis_prefix == f"rl:{app.state.settings.app_name}:{app.state.settings.env}:"
    ra, rb = (RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_prefix=x.state.limiter._redis_prefix)
              for x in (a, b))
    assert ra.hit("login-email:x", 1) is None
    assert rb.hit("login-email:x", 1) is None  # product B is not locked out by product A


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_below_one_is_rejected_without_touching_redis(limit, server):
    limiter = _replica(server)
    with pytest.raises(ValueError):
        limiter.hit("k", limit)
    assert limiter._redis_down_until == 0.0
    with pytest.raises(ValueError):
        RateLimiter().hit("k", limit)


def test_settings_reject_non_positive_limits():
    from pydantic import ValidationError
    from app.config import Settings
    with pytest.raises(ValidationError):
        Settings(auth_rate_limit_per_minute=0)


def test_email_key_is_a_hash_of_the_normalised_address():
    key = ratelimit.email_key("  Bob@Acme.TEST ")
    assert key == ratelimit.email_key("bob@acme.test") and "bob" not in key and "@" not in key


def test_slow_limiter_does_not_block_the_event_loop(app):
    """A slow rate-limit store (blocking call) must not freeze other requests: the gates run in the threadpool."""
    import asyncio
    import httpx

    class Slow(RateLimiter):
        blocking = True  # as a Redis-backed limiter is

        def hit(self, key, limit, window_seconds=60.0):
            time.sleep(0.4)
            return None

    app.state.limiter = Slow()

    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="https://testserver",
                                     headers={"X-Requested-With": "test"}) as client:
            async def login():
                await client.post("/api/auth/login", json={"email": "a@b.test", "password": "x" * 12})
                return time.monotonic()

            async def health():
                await asyncio.sleep(0.05)
                await client.get("/livez")
                return time.monotonic()

            login_done, health_done = await asyncio.gather(login(), health())
            return login_done, health_done

    login_done, health_done = asyncio.run(run())
    assert health_done < login_done - 0.2  # /livez answered while the login's limiter calls were still sleeping


# ---- own bounded pool for Redis checks (T-15 pool) ----

def _req(limiter):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(limiter=limiter)))


def test_redis_checks_run_on_the_limiters_own_pool(server):
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_threads=2)
    seen = []
    asyncio.run(ratelimit.off_loop(_req(limiter), lambda: seen.append(threading.current_thread().name)))
    assert seen[0].startswith("ratelimit-redis")
    limiter.shutdown()


def test_pool_is_bounded(server):
    # Counts thread names: it would also pass on one shared pool with a single name, which the `..._own_pool`
    # test above rules out.
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_threads=3)
    names = set()
    lock = threading.Lock()

    def gate():
        with lock:
            names.add(threading.current_thread().name)
        time.sleep(0.05)

    async def go():
        await asyncio.gather(*[ratelimit.off_loop(_req(limiter), gate) for _ in range(20)])

    asyncio.run(go())
    assert 1 <= len(names) <= 3
    limiter.shutdown()


def test_in_memory_stays_inline_with_no_pool():
    limiter = RateLimiter()
    seen = []
    asyncio.run(ratelimit.off_loop(_req(limiter), lambda: seen.append(threading.current_thread())))
    assert seen[0] is threading.main_thread() and limiter._executor is None
    limiter.shutdown()  # harmless


def test_threads_setting_validated(server):
    from app.config import Settings
    with pytest.raises(ValueError):
        RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_threads=0)
    with pytest.raises(Exception):
        Settings(rate_limit_redis_threads=0, _env_file=None)


def test_shutdown_stops_pool_and_is_idempotent(server):
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server))
    assert limiter.redis_threads == 8
    asyncio.run(limiter.run_blocking(lambda: None))
    pool = limiter._executor
    assert pool is not None
    limiter.shutdown()
    limiter.shutdown()
    assert limiter._executor is None
    with pytest.raises(RuntimeError):
        pool.submit(lambda: None)


def test_app_shutdown_stops_pool(app, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    import app.main as main
    monkeypatch.setattr(main, "build_redis_client", lambda url: fakeredis.FakeRedis())
    new_app = create_app(app.state.settings.model_copy(
        update={"rate_limit_redis_url": "redis://x", "rate_limit_redis_threads": 4}))
    with TestClient(new_app) as c:
        assert c.app.state.limiter.redis_threads == 4
        c.post("/api/auth/login", json={"email": "a@b.test", "password": "x" * 12}, headers=HDRS)
        pool = c.app.state.limiter._executor
        assert pool is not None
    with pytest.raises(RuntimeError):
        pool.submit(lambda: None)


HDRS = {"X-Requested-With": "test"}


def test_second_lifespan_on_the_same_app_works(app, monkeypatch):
    """S3: two sequential `with TestClient(app)` blocks; the Redis-gated login must answer 401, not 500."""
    from fastapi.testclient import TestClient
    from app.main import create_app
    import app.main as main
    monkeypatch.setattr(main, "build_redis_client", lambda url: fakeredis.FakeRedis())
    new_app = create_app(app.state.settings.model_copy(update={"rate_limit_redis_url": "redis://x"}))
    for _ in range(2):
        with TestClient(new_app) as c:
            r = c.post("/api/auth/login", json={"email": "nobody@b.test", "password": "x" * 12}, headers=HDRS)
            assert r.status_code == 401, r.text
            assert threading.active_count() >= 1


def test_request_id_is_visible_inside_the_pool_thread(server):
    """S1: the context is copied into the pool thread (fails without ctx.run)."""
    from app.logs import request_id_var
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_threads=1)
    seen = []

    async def go():
        request_id_var.set("rid-123")
        await ratelimit.off_loop(_req(limiter), lambda: seen.append(request_id_var.get()))

    asyncio.run(go())
    assert seen == ["rid-123"]
    limiter.shutdown()


def test_shutdown_cancels_queued_checks_and_lets_running_finish(server):
    """S5: 1 thread: the running check finishes, the queued one is cancelled (fails with cancel_futures=False)."""
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_threads=1)
    release, started = threading.Event(), threading.Event()

    def running():
        started.set()
        release.wait(5)
        return "ok"

    pool = limiter._pool()
    f1 = pool.submit(running)
    assert started.wait(5)
    f2 = pool.submit(lambda: "queued")
    limiter.shutdown()
    release.set()
    assert f1.result(5) == "ok"
    with pytest.raises(CancelledError):
        f2.result(5)


def test_shutdown_closes_the_redis_client():
    client = mock.Mock()
    limiter = RateLimiter(redis_client=client)
    limiter.shutdown()
    client.close.assert_called_once_with()
    client.close.side_effect = RuntimeError("boom")
    limiter.shutdown()  # swallowed


def test_queue_timeout_setting_validated(server):
    from app.config import Settings
    assert Settings(_env_file=None).rate_limit_redis_queue_timeout == 1.0
    for bad in (0, -1, 31):
        with pytest.raises(Exception):
            Settings(rate_limit_redis_queue_timeout=bad, _env_file=None)
    for bad in (0, -0.5):
        with pytest.raises(ValueError):
            RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_queue_timeout=bad)


def _slow_gate_limiter(server, calls, delay=0.5, timeout=0.2):
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server), redis_threads=1,
                          redis_queue_timeout=timeout)
    orig = limiter._redis_hit

    def slow_redis_hit(key, limit, window):
        calls.append(key)
        time.sleep(delay)
        return orig(key, limit, window)

    limiter._redis_hit = slow_redis_hit
    return limiter


def test_queue_wait_is_bounded_and_late_waiters_use_the_memory_check(server, caplog):
    """S2: 1 thread, a slow gate, N waiters: the late ones are answered within the bound, the breaker trips, and
    no withdrawn job runs against Redis afterwards."""
    calls: list[str] = []
    limiter = _slow_gate_limiter(server, calls, delay=0.5, timeout=0.2)
    n = 6
    finished: dict[int, float] = {}
    leaked: list[bool] = []

    async def go():
        t0 = time.monotonic()

        async def one(i):
            await ratelimit.off_loop(_req(limiter), lambda: limiter.check(f"k{i}", 5))
            finished[i] = time.monotonic() - t0
            leaked.append(ratelimit._skip_redis.get())  # in the waiter's own context, after the fallback ran

        await asyncio.gather(*[one(i) for i in range(n)])

    with caplog.at_level(logging.WARNING, logger="app.ratelimit"):
        asyncio.run(go())
    late = [finished[i] for i in range(1, n)]
    assert max(late) < 0.2 + 0.25, finished  # bound plus scheduling slack, far below 6 * 0.5 s
    assert limiter._redis_down_until > time.monotonic()  # breaker tripped on "slow"
    assert any("queue timeout" in r.getMessage() for r in caplog.records)
    assert leaked == [False] * n  # the fallback ran in a copied context; no caller's context is marked
    time.sleep(0.7)  # let the running job end; withdrawn ones must not run later
    assert calls == ["k0"] or len(calls) == 1, calls  # only the job that was already running touched Redis
    limiter.shutdown()


def test_withdrawn_job_does_not_double_count(server):
    """The timed-out gate is counted once (in memory); the queued Redis job is a no-op."""
    calls: list[str] = []
    limiter = _slow_gate_limiter(server, calls, delay=0.4, timeout=0.1)
    observer = fakeredis.FakeRedis(server=server)

    async def go():
        await asyncio.gather(ratelimit.off_loop(_req(limiter), lambda: limiter.check("a", 5)),
                             ratelimit.off_loop(_req(limiter), lambda: limiter.check("b", 5)))

    asyncio.run(go())
    time.sleep(0.6)
    assert observer.zcard("rl:b") == 0  # never reached Redis
    assert len(limiter._hits["b"]) == 1  # answered once, in memory
    # the running job finished after the breaker tripped, so it was answered in memory: counted exactly once
    assert observer.zcard("rl:a") + len(limiter._hits.get("a", ())) == 1
    limiter.shutdown()


def test_cancelled_waiter_is_withdrawn(server):
    calls: list[str] = []
    limiter = _slow_gate_limiter(server, calls, delay=0.4, timeout=5)

    async def go():
        first = asyncio.ensure_future(ratelimit.off_loop(_req(limiter), lambda: limiter.check("a", 5)))
        await asyncio.sleep(0.05)
        second = asyncio.ensure_future(ratelimit.off_loop(_req(limiter), lambda: limiter.check("b", 5)))
        await asyncio.sleep(0.05)
        second.cancel()
        with pytest.raises(asyncio.CancelledError):
            await second
        await first

    asyncio.run(go())
    time.sleep(0.2)
    assert calls == ["a"]
    limiter.shutdown()


def test_open_breaker_skips_the_pool(server):
    limiter = RateLimiter(redis_client=fakeredis.FakeRedis(server=server))
    limiter._redis_down_until = time.monotonic() + 60
    seen, leaked = [], []

    async def go():
        await limiter.run_blocking(lambda: seen.append(threading.current_thread()))
        leaked.append(ratelimit._skip_redis.get())  # read in the caller's own context, after run_blocking

    asyncio.run(go())
    assert seen == [threading.main_thread()] and limiter._executor is None
    assert leaked == [False]  # the caller's context is not left marked as "Redis is down"
