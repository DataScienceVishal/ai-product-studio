"""Small in-process sliding-window rate limiter.

By default per instance only: with several replicas each keeps its own counts, so the real limit is
N times higher. Fine for one replica. Set RATE_LIMIT_REDIS_URL to share the counts through Redis (ADR 0001, 0002).

Redis mode uses the same sliding window (one sorted set per key, scored by Redis server time, so replica clock
skew cannot matter) checked and updated by one Lua script, so concurrent replicas cannot both take the last slot.

Failure policy (fail safe, never fail closed): if Redis errors or exceeds the short timeout, the call is answered by
this process's own in-memory limiter, a warning is logged (at most one per 30 s, and never with the URL or password),
and Redis is not tried again for RETRY_AFTER_FAILURE seconds, so a hung Redis costs one timeout, not one per login.
Auth routes therefore never 500 and never stall because of Redis; during an outage the limit is per replica again.

Async gates run Redis checks on the limiter's own bounded thread pool. The wait in that pool's queue is bounded too
(RATE_LIMIT_REDIS_QUEUE_TIMEOUT): a gate that waits longer is answered by the in-memory check on the spot and counts as
a Redis failure, so the breaker trips on "slow" as well as "down" and later gates skip the pool until Redis recovers.
"""
from __future__ import annotations

import asyncio
import contextvars
import hashlib
import logging
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from fastapi import Request

from .errors import AppError

log = logging.getLogger("app.ratelimit")

REDIS_TIMEOUT_SECONDS = 0.2
DEFAULT_QUEUE_TIMEOUT = 1.0  # max seconds a gate waits for a free Redis pool thread before using the in-memory check
RETRY_AFTER_FAILURE = 5.0  # seconds to go straight to the in-memory limiter after a Redis failure
WARN_EVERY = 30.0

# KEYS[1] = counter key; ARGV = limit, window in ms, unique member. Returns 0 if allowed, else ms until allowed.
_SLIDING_WINDOW_LUA = """
local t = redis.call('TIME')
local now = t[1] * 1000 + math.floor(t[2] / 1000)
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
if redis.call('ZCARD', KEYS[1]) >= limit then
  local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
  return math.max(1, window - (now - tonumber(oldest[2])))
end
redis.call('ZADD', KEYS[1], now, ARGV[3])
redis.call('PEXPIRE', KEYS[1], window)
return 0
"""


def build_redis_client(url: str):
    """A client with short timeouts and no retries. rediss:// gives TLS. The URL is never logged."""
    import redis
    return redis.Redis.from_url(url, socket_timeout=REDIS_TIMEOUT_SECONDS,
                                socket_connect_timeout=REDIS_TIMEOUT_SECONDS, retry_on_timeout=False,
                                health_check_interval=0, decode_responses=False)


_FALLBACK = object()
# Set only around the inline in-memory answer for a gate that timed out in the pool queue: hit() then skips Redis.
_skip_redis: contextvars.ContextVar[bool] = contextvars.ContextVar("ratelimit_skip_redis", default=False)


class RateLimiter:
    def __init__(self, max_keys: int = 50_000, redis_client=None, redis_prefix: str = "rl:",
                 redis_threads: int = 8, redis_queue_timeout: float = DEFAULT_QUEUE_TIMEOUT):
        if redis_threads < 1:
            raise ValueError("redis_threads must be at least 1")
        if not redis_queue_timeout > 0:
            raise ValueError("redis_queue_timeout must be positive")
        # Redis checks get their own small pool so a slow Redis (200 ms timeout each) cannot use up the shared
        # worker threads that serve sync routes. Created on first use (so a second app lifespan on the same object
        # works after shutdown()); the in-memory limiter never creates one because it never leaves the loop.
        self._executor: ThreadPoolExecutor | None = None
        self._executor_lock = threading.Lock()
        self.redis_threads = redis_threads
        self.redis_queue_timeout = redis_queue_timeout
        self._redis = redis_client
        self._redis_script = redis_client.register_script(_SLIDING_WINDOW_LUA) if redis_client is not None else None
        self._redis_prefix = redis_prefix
        self._redis_down_until = 0.0  # these two are written without the lock: a race only costs an extra
        # warning or an extra Redis attempt, so it is benign
        self._last_warn = 0.0
        self._hits: dict[str, deque[float]] = {}
        self._windows: dict[str, float] = {}  # each key's own window, so eviction can't reset an hourly cap
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def hit(self, key: str, limit: int, window_seconds: float = 60.0) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until the next hit is allowed."""
        if limit < 1:  # a programming/config error, not an outage: never reaches Redis or trips its backoff
            raise ValueError("rate limit must be at least 1")
        if self._redis is not None and not _skip_redis.get():
            wait = self._redis_hit(key, limit, window_seconds)
            if wait is not _FALLBACK:
                return wait
        return self._local_hit(key, limit, window_seconds)

    @property
    def blocking(self) -> bool:
        """True when a hit does network I/O, so async callers must not run it on the event loop."""
        return self._redis is not None

    def _pool(self) -> ThreadPoolExecutor:
        with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=self.redis_threads,
                                                    thread_name_prefix="ratelimit-redis")
            return self._executor

    def _trip_breaker(self, reason: str) -> None:
        now = time.monotonic()
        self._redis_down_until = now + RETRY_AFTER_FAILURE
        if now - self._last_warn >= WARN_EVERY or self._last_warn == 0.0:
            self._last_warn = now
            log.warning("rate limit store unreachable, using in-process limits (%s)", reason)

    async def run_blocking(self, fn) -> None:
        """Run a sync gate off the event loop on the limiter's own bounded pool (the caller's context is kept).

        Always uses this limiter's pool (created on first use, recreated after shutdown()), never the loop's default
        executor, even when a subclass sets `blocking` without a Redis client. The wait for a free pool thread is
        bounded by `redis_queue_timeout`: on timeout the queued job is withdrawn (it can never run against Redis
        afterwards, so nothing is counted twice), the breaker trips as for a Redis failure, and the gate is answered
        by the in-memory check inline. While the breaker is open the pool is skipped altogether.
        """
        ctx = contextvars.copy_context()
        if time.monotonic() < self._redis_down_until:
            ctx.run(_skip_redis.set, True)  # Redis is known bad: a Redis-free answer needs no thread
            ctx.run(fn)
            return
        lock = threading.Lock()
        state = {"started": False, "withdrawn": False}

        def job():
            with lock:
                if state["withdrawn"]:
                    return
                state["started"] = True
            ctx.run(fn)

        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(self._pool(), job)
        try:
            done, _ = await asyncio.wait({fut}, timeout=self.redis_queue_timeout)
        except asyncio.CancelledError:
            with lock:
                state["withdrawn"] = True
            fut.cancel()
            raise
        if not done:
            with lock:
                if not state["started"]:
                    state["withdrawn"] = True
            if state["withdrawn"]:
                fut.cancel()
                self._trip_breaker("queue timeout")
                # Defence in depth: the breaker was just tripped, so _redis_hit would answer _FALLBACK anyway. This
                # only matters if the breaker window ended between the trip and the call. Do not "simplify" it away.
                self._answer_in_memory(fn)
                return
        if fut.cancelled():
            # shutdown(cancel_futures=True) dropped this queued job. If our own task is being cancelled, let that
            # propagate; otherwise the request is still alive and must get an answer, so use the in-memory check.
            # current_task() is never None here: this coroutine always runs inside a task on the loop.
            if asyncio.current_task().cancelling() == 0:
                self._answer_in_memory(fn)
                return
        await fut  # finished, or already running (bounded by the Redis socket timeouts)

    @staticmethod
    def _answer_in_memory(fn) -> None:
        """Run the gate inline in a fresh context copy with Redis skipped (the caller's context is never touched)."""
        fallback = contextvars.copy_context()
        fallback.run(_skip_redis.set, True)
        fallback.run(fn)

    def shutdown(self) -> None:
        """Stop the Redis pool (queued checks are dropped, running ones finish) and close the client. Idempotent.
        A later run_blocking creates a fresh pool, so the app object can be started again."""
        with self._executor_lock:
            executor, self._executor = self._executor, None
        if executor is not None:
            # A run_blocking racing with this call creates a fresh pool that nothing shuts down. That is benign: its
            # idle workers exit when the executor is collected or at interpreter exit.
            executor.shutdown(wait=False, cancel_futures=True)
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception:  # shutting down: nothing useful to do about it
                pass

    def _redis_hit(self, key: str, limit: int, window_seconds: float):
        now = time.monotonic()
        if now < self._redis_down_until:
            return _FALLBACK
        try:
            ms = int(self._redis_script(keys=[self._redis_prefix + key],
                                        args=[limit, int(window_seconds * 1000), uuid.uuid4().hex]))
        except Exception as exc:  # any Redis or network failure: fail safe to the in-process limiter
            self._trip_breaker(type(exc).__name__)
            return _FALLBACK
        return None if ms == 0 else ms / 1000.0

    def _local_hit(self, key: str, limit: int, window_seconds: float) -> float | None:
        now = time.monotonic()
        with self._lock:
            if key not in self._hits and len(self._hits) >= self._max_keys:
                self._evict(now, window_seconds)
            hits = self._hits.setdefault(key, deque())
            self._windows[key] = window_seconds
            while hits and now - hits[0] >= window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, window_seconds - (now - hits[0]))
            hits.append(now)
            return None

    def _evict(self, now: float, window_seconds: float) -> None:
        """Bound memory without unblocking anyone: drop keys with no recent hits, then the keys with the
        fewest hits. A flood of new keys has one hit each, so a blocked key (many hits) survives it."""
        idle = [k for k, hits in self._hits.items()
                if not hits or now - hits[-1] >= self._windows.get(k, window_seconds)]
        for key in idle:
            del self._hits[key]
            self._windows.pop(key, None)
        if len(self._hits) >= self._max_keys:
            ranked = sorted(self._hits.items(), key=lambda item: (len(item[1]), item[1][-1]))
            for key, _ in ranked[:len(self._hits) - int(self._max_keys * 0.9)]:
                del self._hits[key]
                self._windows.pop(key, None)

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        wait = self.hit(key, limit, window_seconds)
        if wait is not None:
            raise AppError(429, "rate_limited", "Too many attempts. Please wait a moment and try again.",
                           headers={"Retry-After": str(int(wait) + 1)})


async def off_loop(request: Request, fn) -> None:
    """Run a sync rate-limit gate: in a worker thread if the limiter does network I/O, else inline (it is cheap)."""
    if request.app.state.limiter.blocking:
        await request.app.state.limiter.run_blocking(fn)
    else:
        fn()


def email_key(email: str) -> str:
    """Rate-limit key part for an email: a hash, so addresses never sit in Redis."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]


def client_ip(request: Request) -> str:
    if request.app.state.settings.trust_proxy_headers:
        forwarded = ",".join(request.headers.getlist("x-forwarded-for"))  # every header line, in order
        if forwarded.strip(", "):
            return forwarded.split(",")[-1].strip()  # the hop our own ingress added
    return request.client.host if request.client else "unknown"
