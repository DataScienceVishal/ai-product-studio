# Review: p/_starter/T-15-pool-followups (head b100c3a)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff origin/main...origin/p/_starter/T-15-pool-followups`
(7 files, +284/-26: `app/ratelimit.py`, `app/config.py`, `app/main.py`, `tests/test_ratelimit_redis.py`, README,
`.env.example`, NEXT.md). Scope: suggestions S1-S7 from `reviews/T-15-pool.md`.

## Verdict: PASS

The change does what S1-S7 asked for, and I found nothing blocking. The withdraw protocol is race-free, nothing is
counted twice, `_skip_redis` does not leak, lazy pool creation is thread-safe, and the breaker semantics match the
docs. Suggestions below are non-blocking.

## Test evidence

- Backend, full suite: `.venv/bin/python -m pytest -q -o addopts=""` gives **372 passed, 1 skipped** (47.8 s, local Postgres).
- `tests/test_ratelimit_redis.py` run 5 times in a row: 33 passed each time (6.3 to 7.2 s). The timing-based tests
  were not flaky here.
- Frontend: `npx vitest run` gives **5 files, 111 passed**.

### Mutation probes (on `app/ratelimit.py`, restored afterwards)

| Mutation | Result |
|---|---|
| M2 fallback sets `_skip_redis` in the caller's context instead of a copy | caught (queue-wait test) |
| M4 `shutdown()` does not clear `_executor` | caught (2: shutdown test, second-lifespan test) |
| M5 no breaker trip on queue timeout | caught |
| M7 `hit()` ignores `_skip_redis` | caught (only because the test's slow `_redis_hit` mock runs; see S6) |
| M8 no breaker-open fast path | caught |
| M1 job ignores the `withdrawn` flag | **survives** |
| M9 timeout path drops `fut.cancel()` | **survives** |
| M1 + M9 together | caught (2 fail) |
| M6 cancel path does not set `withdrawn` | **survives** (`fut.cancel()` covers it) |
| M3 breaker-open path sets `_skip_redis` in the caller's context | **survives** |

### Behaviour probes (scratch script, not committed)

- `_skip_redis.get()` in the caller after `run_blocking` returns: False on both the breaker-open path and the
  queue-timeout path. No leak.
- 16 threads racing `_pool()` behind a barrier get one executor.
- Shutdown while a gate is queued: the running gate returns normally. The queued gate's request task gets
  `CancelledError` even though the task itself was never cancelled (see S3; main behaves the same way).

## Correctness analysis

- **Withdrawal vs job start race.** `job()` checks `withdrawn` and sets `started` under one lock. The waiter sets
  `withdrawn` only when `not started`, under the same lock. Exactly one side wins, so a withdrawn job never runs `fn`,
  and a started job is awaited instead of being answered twice. `state["withdrawn"]` is read outside the lock
  afterwards, which is fine because only the waiter writes it. `fut.cancel()` on the `run_in_executor` wrapper
  cancels the concurrent future synchronously (`_chain_future`, source loop is None). So the flag and the cancel
  are two independent guards for the same thing, which is why M1 and M9 each survive alone.
- **Double counting.** A gate's hits all run either in the job or inline, never split. Queued jobs whose waiters
  have not timed out yet run after the trip, and `_redis_hit` sends them to memory. Each hit is counted once.
  `test_withdrawn_job_does_not_double_count` checks this across Redis and memory.
- **Contextvars.** The fallback uses a fresh `copy_context()` rather than `ctx`, which is correct: it avoids
  re-entering a context the job might hold, and the caller's context is never touched. Request id propagation
  (S1) is tested.
- **Lazy pool.** `_pool()` and `shutdown()` both hold `_executor_lock`, and `shutdown()` swaps the executor out
  before shutting it down. Thread-safe.
- **Breaker.** A queue timeout trips it for `RETRY_AFTER_FAILURE` (5 s). While it is open, gates run inline
  without a thread (cheap: in-memory only), and sync-route `hit()` callers skip Redis too. This is documented in
  the module docstring and README ("slow counts as down"). `_trip_breaker` is called from both the loop and pool
  threads without a lock. The only race is a possible duplicate warning, which is harmless.
- **Exceptions.** A 429 `AppError` from `fn` propagates on all three paths: inline, fallback, and `await fut`.
- **After shutdown.** A later `run_blocking` builds a fresh pool, and the redis-py client reconnects after
  `close()` (pool `disconnect()` is reusable). The second lifespan returns 401, not 500, and is tested (M4 caught).

## Security / performance

- No new endpoints or inputs. The new setting is validated (`0 < x <= 30`) in both `Settings` and the constructor.
- The warning logs only the literal reason `queue timeout`, with no URL or secret.
- An attacker could force per-replica limits for 5 s by saturating the pool's queue. With healthy Redis (about
  1 ms per check, 8 threads) that takes thousands of concurrent auth requests, and per-replica limits still apply.
  Acceptable; it is the same failure mode as a slow Redis.
- Cost of the bound: at most `redis_queue_timeout` (default 1 s) plus, once a job has started, up to 2 x 0.2 s
  per Redis call. NEXT.md states this.

## Suggestions (non-blocking)

- **S1 Pin each guard with its own test.** M1, M6 and M9 each survive alone because the flag and `fut.cancel()`
  overlap. Extracting the job/withdraw pair into a small helper would let a test drive the race deterministically:
  set `started` first, then time out, and assert the waiter awaits rather than falls back; set `withdrawn` first and
  assert the job is a no-op.
- **S2 Leak test for `_skip_redis`.** M3 survives. Add an assertion that `_skip_redis.get()` is False in the caller
  after `run_blocking` on both the breaker-open and queue-timeout paths. Two lines; the probe above shows it holds today.
- **S3 Shutdown with queued gates.** `cancel_futures=True` turns a queued gate into `CancelledError` inside a request
  task that was not cancelled (`ratelimit.py`, `await fut` and the `done` branch). This predates this branch, and
  uvicorn drains requests before lifespan shutdown, so it is rare. A cheap hardening: if `fut.cancelled()` and the
  current task is not cancelling, answer with the in-memory fallback.
- **S4 Pool after shutdown.** A `run_blocking` racing with `shutdown()` creates a fresh pool that nothing shuts down.
  Its idle workers exit when the executor is collected or at interpreter exit, so this is benign. It is the price
  of S3 from the earlier review; a one-line comment would help.
- **S5 Test tidy-ups.** In `test_second_lifespan_on_the_same_app_works`, `assert threading.active_count() >= 1` is
  vacuous; drop it. In the queue-wait test, `calls == ["k0"] or len(calls) == 1` reduces to `len(calls) == 1`.
- **S6 `_skip_redis` on the timeout path.** It is defence in depth: the breaker is tripped just before, so `_redis_hit`
  would return `_FALLBACK` anyway. It matters only if the breaker window ended between the check and the call. M7 is
  caught only because the test mock sleeps before the breaker check. A comment saying so would stop someone
  "simplifying" it away.
