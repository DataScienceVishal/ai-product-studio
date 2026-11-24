"""Redis-backed rate limits (T-15): shared across replicas, same window semantics, safe when Redis fails."""
from __future__ import annotations

import logging
import time

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
    a.hit("k", 1, 10)
    wait = a.hit("k", 1, 10)
    assert 8 < wait <= 10


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
