# Review: p/_starter/T-15-redis (head 0e087ec)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff main...p/_starter/T-15-redis` (11 files, +327/-9).

## Summary

Adds an optional Redis backend to `RateLimiter` (`RATE_LIMIT_REDIS_URL`): one Lua sliding-window script per hit on a
sorted set `rl:<key>`, scored by Redis `TIME`; 200 ms connect/read timeouts; on any error a fallback to the in-process
limiter with a 5 s skip and a warning at most every 30 s (exception class only). Default (unset) behaviour is
unchanged. Docs (README, `.env.example`, ADR 0002) are accurate and honest that no Azure Redis is provisioned.

The core is good: the Lua window matches the in-memory semantics, it is atomic, keys expire, secrets are not logged,
and failures never 500. Two cheap things must change before this goes into the starter that every product copies.

## Test evidence (branch tree, worktree at 0e087ec)

- Backend: `python3.13 -m pytest -q -o addopts=""` -> **348 passed, 1 skipped** in 62 s.
- Frontend: `npx vitest run` -> **5 files, 111 passed**.
- New file `tests/test_ratelimit_redis.py`: 12 passed.
- Mutation checks on `app/ratelimit.py` (each reverted after):
  - remove the 5 s backoff -> 3 fail; remove `PEXPIRE` -> 1 fail; `>=` to `>` in Lua -> 5 fail;
    log `exc` instead of class name -> 1 fail; window ms x0.1 -> 1 fail. Good: the tests test behaviour.
  - Not caught: Retry-After replaced by a constant `window` (test asserts `8 < wait <= 10` right after the first hit,
    so a constant passes); boundary `now - window - 1` (sub-ms, acceptable).
- Real redis-py 8.2.0 against a local socket that accepts and never replies (hung Redis, with password):
  `TimeoutError` after **0.209 s**, one connection, no client retries. The "hung Redis bounded at ~200 ms" claim holds.

## Checks

| Area | Result |
|---|---|
| Lua vs in-memory | Same: both drop hits with `t <= now - window` (`ZREMRANGEBYSCORE -inf now-window` is inclusive, matching `now - hits[0] >= window`), refused hits are not recorded, wait = window - (now - oldest). Lua clamps to >= 1 ms. |
| Atomicity | One script = atomic on the server; two replicas cannot both take the last slot. `TIME` before writes is fine on Redis 5+ (effects replication). Single key, so cluster-safe. |
| Key expiry / memory | `PEXPIRE window` on every accepted hit; all members are <= now, so the key outlives its last member by exactly the window. ZCARD <= limit per key. Bounded. |
| Secret hygiene | Only `type(exc).__name__` logged, no `exc_info`; test asserts `secret`/`redis://` absent. `from_url` errors on bad schemes do not echo the URL. OK. |
| Fallback safety | Broad `except Exception` -> in-process limiter, still enforces per replica; 5 s skip means one timeout per 5 s, not per request. AuthenticationError (wrong password) also falls back. Auth never 500s because of Redis. |
| Dependencies | `redis==8.2.0` in `requirements.txt` with hashes (Dockerfile uses `--require-hashes`); `fakeredis 2.41.0`, `lupa 2.8`, `sortedcontainers 2.4.0` only in `requirements-dev.txt`; `redis>=5.0,<9` in pyproject. Consistent. |

## Critical issues (blocking)

1. **Sync Redis call on the event loop in the login/signup/reset gates.**
   `backend/app/routes/auth.py:115-131` - `_signup_gate`, `_login_gate`, `_reset_gate` are `async def` and call
   `limiter.check` (`ratelimit.py:72-92`) directly, so the blocking socket round trip runs on the event loop. Login
   makes two calls (ip + email). Healthy Redis (~1 ms) is fine, and a hung Redis costs one 200 ms stall per 5 s.
   But a Redis that is **slow but answering** (failover, CPU-bound cache, cross-region by mistake: 50-190 ms) never
   trips the breaker. Then every login freezes the whole process, including `/health` probes and every other tenant's
   requests, for up to 2 x 190 ms. That is exactly the multi-replica production case the feature exists for. It also
   happens on a cold connection's DNS lookup, which `socket_connect_timeout` does not bound.
   **Fix (small):** make the three gates plain `def`. FastAPI runs sync dependencies in the threadpool, and
   `hash_capacity_after` only does `Depends(gate)`, so nothing else changes. Or wrap the call in
   `await anyio.to_thread.run_sync(...)`. Add a test that a slow limiter (script that sleeps 150 ms) does not block a
   concurrent `/health` request, or at least assert the gates are not coroutine functions.

2. **Key prefix is a fixed `"rl:"`, shared by every product and environment.**
   `backend/app/ratelimit.py:61` and `backend/app/main.py:177`. Every product is copied from this starter. With the
   $80 budget, one Azure Cache shared by several products (or by staging and prod) is the likely deployment. Then
   `rl:login-email:<email>`, `rl:signup-day:<ip>` and `rl:accept:<ip>` collide across products: failed logins on
   product A lock the same email out of product B, and one office IP's signups count against another product's daily
   cap. That is a cross-product lockout and a data leak of attempt counts.
   **Fix (one line):** in `create_app`, pass `redis_prefix=f"rl:{settings.app_name}:{settings.env}:"`, and add a test
   that two limiters with different prefixes on one `FakeServer` do not share counts.

## Suggestions (non-blocking)

- `limit <= 0` (for example a setting set to 0 to "disable" a limit): the Lua script raises on `oldest[2]` being nil,
  which logs a misleading "store unreachable" warning and **turns Redis off for all keys for 5 s**. The in-memory
  path then raises `IndexError` (a 500), which is a pre-existing bug. Validate limits as `>= 1` in `Settings`, or handle
  `limit <= 0` in `hit()`. Similarly, consider not tripping the global backoff on `ResponseError` raised by the script
  itself, since that is a bug and not an outage.
- Strengthen `test_retry_after_counts_down_from_the_oldest_hit`: sleep about 0.3 s (or use a 1 s window) between hits
  and assert the wait drops, so a constant `window` return fails.
- `_redis_down_until` and `_last_warn` are written without the lock. The race is benign (at worst an extra warning or
  an extra Redis attempt). Add a one-line comment saying so.
- The login-email key stores the raw email in Redis for up to 60 s. That is acceptable, but hashing it
  (`login-email:<sha256>`) keeps personal data out of the cache, which costs nothing.
- `build_redis_client` errors on a malformed URL raise at startup. That is good (fail fast), but worth a sentence in
  the README.

## Verdict

**CHANGES**: two small fixes, items 1 and 2 above. Everything else is solid, and the tests are behavioural and
catch real regressions. Re-review should only need the two diffs and their tests.

## Re-review (head e7bba21, fixes on top of aa3d177)

Tests on e7bba21: backend `python3.13 -m pytest -q -o addopts=""` -> **354 passed, 1 skipped**; frontend `npx vitest run`
-> **5 files, 111 passed**; `tests/test_ratelimit_redis.py` 18 passed.

1. **Event loop: fixed.** `off_loop` (`app/ratelimit.py`) runs the gate body in `anyio.to_thread` when
   `limiter.blocking` (Redis is configured), and inline for the in-memory limiter, so the existing async-login slot
   tests are unchanged. All four async gates use it: signup, login and reset-confirm in `routes/auth.py`, and accept in
   `routes/team.py`. Every other limiter caller is a sync route, so it already runs in the threadpool.
   `test_slow_limiter_does_not_block_the_event_loop` is a real guard: I forced `off_loop` to always run inline, and
   that test failed (1 failed, 17 passed); it passes again once reverted.
   Cheap rejects still happen before any hash slot. `hash_capacity(_gate=Depends(gate))` (`security.py:65`) resolves
   the gate before `limiter.acquire()`. The gate is still the same async callable, now awaiting a thread, and an
   `AppError` raised in the thread comes back through `run_sync`, so a 429 or 422 never takes a slot.
2. **Prefix: fixed.** `create_app` passes `rl:<app_name>:<env>:`. A test on one shared FakeServer shows product B is
   not locked out by product A.

Earlier suggestions also addressed: limit settings are `Field(ge=1)` and `hit()` raises `ValueError` for `limit < 1`
without touching Redis or its backoff; email keys are a sha256 prefix (`email_key`) for login and reset-request; the
Retry-After test now checks the countdown.

Remaining (non-blocking, follow-up when Redis is actually provisioned): the Redis-backed gates share AnyIO's default
40-token threadpool with every sync route. With healthy Redis each gate holds a thread for about 1 ms. A burst of
auth requests against a slow Redis (up to 200 ms per call, and login makes 2 calls) can queue sync routes behind them
until the 5 s backoff starts. A dedicated `anyio.CapacityLimiter` (for example 8) passed to `run_sync` in `off_loop`
would cap that. Log it in NEXT.md as a precondition for raising `maxReplicas`.

**Verdict: PASS.**
