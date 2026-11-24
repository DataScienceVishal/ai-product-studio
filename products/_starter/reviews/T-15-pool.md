# Review: p/_starter/T-15-pool (head c793fb0)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff origin/main...HEAD` (9 files, +127/-5). Context: the
non-blocking follow-up in `reviews/T-15-redis.md` (Redis gates shared AnyIO's 40-token threadpool with sync routes).

## Summary

Redis-backed rate-limit gates now run on the limiter's own `ThreadPoolExecutor` (`ratelimit-redis`, setting
`RATE_LIMIT_REDIS_THREADS`, default 8, `Field(ge=1)` plus a constructor check). The context is copied explicitly with
`copy_context().run`. The in-memory limiter creates no pool and stays inline. `RateLimiter.shutdown()` (pool shut down
with `cancel_futures=True`, Redis client closed, idempotent) runs in the app lifespan before `db.dispose()`. Frontend
`engines.node` is `>=22.22.2 <23`, and the lock root entry matches (5 changed lines, nothing else in the lock moved).
The change does what the earlier review asked for. A slow Redis can now hold at most N threads of its own and none of
the shared worker threads.

## Test evidence (worktree at c793fb0)

- Backend: `.venv/bin/python -m pytest -q -o addopts=""` -> **363 passed, 1 skipped** in 52 s (Postgres local).
- Frontend: `npx vitest run` -> **5 files, 111 passed**.
- `tests/test_ratelimit_redis.py`: 24 passed (6 new).
- Mutation checks (run on a scratch copy of the backend, not the branch):

| Mutation | Result |
|---|---|
| `off_loop` back to `anyio.to_thread.run_sync` | 1 fail (`..._own_pool`) |
| executor bypassed (`run_in_executor(None, ...)`) | 5 fail |
| `max_workers=20` instead of the setting | 1 fail (`test_pool_is_bounded`) |
| drop `limiter.shutdown()` from lifespan | 1 fail |
| drop `ctx.run` (no context copy) | **0 fail** |
| `cancel_futures=False` | **0 fail** |
| drop `self._redis.close()` | **0 fail** |

- Behaviour probes (scratch script, real `RateLimiter` plus fakeredis):
  - contextvars: `request_id_var` set on the loop is visible in the pool thread (`['rid-123']`), so the
    "rate limit store unreachable" warning keeps its request id.
  - Saturation: 40 gates of 100 ms on 2 threads finish at 0.10 s to 2.01 s, with no error. **A full pool queues
    without a bound and never fails fast** (`ThreadPoolExecutor` has an unbounded work queue). This matches the
    `CapacityLimiter` the earlier review suggested, which also queues waiters.
  - Shutdown with 1 running and 2 queued: running -> `ok`, queued -> `CancelledError`. A new check after shutdown ->
    `RuntimeError: cannot schedule new futures after shutdown`.
  - A queued gate whose awaiting task is cancelled is removed from the queue and never runs. Good.

## Checks

| Area | Result |
|---|---|
| Hash-slot ordering | Kept. `hash_capacity(_gate=Depends(gate))` (`security.py:65`) still awaits the gate before `acquire()`, and route-level `dependencies` resolve before `db: Session = Depends(get_db)`. So a gate queued in the pool holds no hash slot and no DB connection. It only holds a coroutine. An `AppError` (429/422) raised in the pool thread comes back through the future, so rejects never take a slot (covered: the executor-bypass mutation breaks app-level tests). |
| contextvars | Correct. `run_in_executor` does not copy the context on its own, and the explicit `copy_context().run` does. Each call gets a fresh copy, so there is no cross-request leak. Untested (see S1). |
| Shutdown / in-flight logins | Safe under uvicorn 0.54. `Server.shutdown` waits for request tasks to finish (or cancels them after `timeout_graceful_shutdown`) **before** it sends lifespan shutdown. So when `limiter.shutdown()` runs, no login is in flight, and `cancel_futures=True` drops nothing in practice. If an ASGI server ran lifespan shutdown with requests still running, a queued login would get a `CancelledError` (connection dropped or 500) and a new one would get a `RuntimeError` (500). That cannot happen on our deploy path. |
| Pool saturation | It queues without a bound (see probe). With a slow but answering Redis (~190 ms per call, 2 calls per login) one replica serves about 21 logins/s through 8 threads. Above that, latency grows until the client or ingress times out, and the 5 s breaker never trips because no call fails. Sync routes and `/health` are unaffected, and that was the goal. Fail-fast is a suggestion (S2), not a blocker: Redis is not provisioned, and the old path queued the same way. |
| Config / docs | `Field(ge=1)` with a test; README row and `.env.example` added; NEXT.md status is accurate (363/1, 111). The `auth.py:114` comment ("in a worker thread") is still true. |
| Frontend engines | `<23` is consistent with `node:22-slim` and CI `node-version: "22"`. jsdom needs `^22.22.2 \|\| ^24.15.0 \|\| >=26`, so 23 really is unsupported. There is no `.npmrc` `engine-strict`, so the field is advisory (it warns and does not fail `npm ci`). Fine. |
| Security | No new endpoints, nothing new logged, the URL is still never logged. Thread names carry no data. |

## Critical issues (blocking)

None.

## Suggestions (non-blocking)

1. **S1: Pin the context copy with a test.** Removing `ctx.run` (`app/ratelimit.py:103`) passes every test, but the
   request id in the limiter's warning depends on it. Add a test that sets `request_id_var`, runs a gate through
   `off_loop` on a Redis limiter, and asserts the value seen in the thread.
2. **S2: Fail fast when the pool is saturated** (do this before raising `maxReplicas` or provisioning Redis). Give the
   queue wait a bound. For example, take an `asyncio.Semaphore(N * k)` (or a `move_on_after(1.0)`) before submitting.
   On a timeout, run the in-memory check inline (it is cheap and still enforces per replica) and count it as a Redis
   failure, so the breaker trips on "slow" as well as "down". Add a test: 1 thread, a slow gate, and N waiters, where
   the late ones are answered within the bound. Log it in NEXT.md "Left".
3. **S3: The lifespan is not symmetric.** The pool is created in `create_app` and shut down in the lifespan, so a
   second lifespan cycle on the same app object (two `with TestClient(app)` blocks, or a product test that re-enters)
   gets a 500 from the `RuntimeError` on every Redis-gated route. Either create the executor at lifespan startup or on
   first use, or have `run_blocking` fall back to the in-memory check after shutdown. Uvicorn never does this, which is
   why it is non-blocking.
4. **S4: Docstring precision.** When `blocking` is true but `_executor is None` (the `Slow` subclass in
   `test_slow_limiter_does_not_block_the_event_loop`), `run_in_executor(None, ...)` uses the loop's default executor,
   which is not this bounded pool. Either note it in the `run_blocking` docstring or assert the executor exists.
5. **S5: Untested shutdown details.** `cancel_futures=True` and `self._redis.close()` survive mutation. The probe
   above is a ready-made test for the first (1 thread: running -> ok, queued -> CancelledError). Use a mock client for
   `close()`.
6. **S6: Test-file tidiness.** `tests/test_ratelimit_redis.py:208-210` re-imports `asyncio`/`threading` mid-file (move
   them to the top). `test_app_shutdown_stops_pool` rebinds the `app` fixture name and only uses it for settings, so
   use the `settings` value directly. `test_pool_is_bounded` counts thread *names*, so it would also pass on a
   shared pool with one name (AnyIO's): the `..._own_pool` test covers that, and a one-line comment would help.
7. Setting `RATE_LIMIT_REDIS_THREADS` has no effect without `RATE_LIMIT_REDIS_URL`. Say so in the README row.

## Verdict

**PASS.** Correct, scoped, documented, and the tests catch the main regressions (pool used, bound respected,
lifespan shutdown). Nothing blocks the merge. S2 (fail fast on a saturated pool) is the item to schedule before Redis
is provisioned or `maxReplicas` is raised above 1.
