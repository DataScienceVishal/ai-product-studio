# Review: p/_starter/T-15-pool-s3 (head 9ce035a)

Verdict: **PASS**

## Summary
Implements S3-S6 of T-15-pool-followups and items 1-3 of T-15-coupon-narrow. The main change is in
`backend/app/ratelimit.py` `run_blocking`: if `shutdown(cancel_futures=True)` drops a queued gate job, the request
now gets an in-memory answer instead of a stray `CancelledError`. If the current task is itself being cancelled
(`Task.cancelling() > 0`), the cancellation propagates. The fallback code is moved into `_answer_in_memory`. Other
changes are comments, a stronger assertion (`len(calls) == 1`), removal of a pointless `active_count` assertion, and
a 429 case added to the coupon-outage test.

## Evidence
- Full backend suite (separate worktree, Python 3.11): 491 passed, 1 skipped, 66s.
- tests/test_ratelimit_redis.py run 4 times: 35 passed each time (7.5 to 8.3s). No flakes.
- Mutation probes:
  - M1, remove the `fut.cancelled()` branch: killed (1 failure).
  - M2, always fall back, ignoring `cancelling()`: killed (1 failure; the monkeypatched test).
  - M3, fallback without `_skip_redis`: killed (2 failures).
  - M4, fallback mutating the caller's context: killed (1 failure).
  - M5, also dropping the coupon on `billing_unavailable`: killed (2 failures, the 503 and 429 params).
  - M6, moving the incomplete-reply check inside the `try` (so it drops the coupon): **survived** (36 passed). See S1.

## Correctness and security analysis of the S3 fallback
- **Can it hide a real cancellation?** Not in practice. A `task.cancel()` that arrives while the task is suspended
  in `asyncio.wait` is raised there, and the `except CancelledError` path (withdraw plus re-raise) handles it. A
  cancel that arrives after the waiter completes but before the task resumes sets `_must_cancel`, so it is also
  raised inside `wait`. The new branch is only reached with `cancelling()==0` when the future really was dropped by
  the pool and nothing asked to cancel the task. There are no other `fut.cancel()` callers that fall through: both
  of our own cancel paths return or raise first. A future that is already running cannot be cancelled, so the
  timed-out-but-started path still falls through to `await fut`, as before.
- **The `cancelling()>0` branch** is only reachable if an earlier cancellation was swallowed without `uncancel()`.
  In that case `await fut` raises `CancelledError`. That fails closed: the gate raises, so the request is not let
  through. This is the right side to err on.
- **Rate-limit bypass?** No. The fallback runs the same per-process in-memory limiter that the open breaker and the
  queue timeout already use (`_skip_redis` is set in a copied context, and M3/M4 confirm this is tested). The only
  weakening is the known one: during the short shutdown window, limits are per worker instead of global. Requests
  are still counted and limited, not waved through. The fallback does not trip the breaker. That is correct,
  because Redis is not at fault.
- **Is the monkeypatched `asyncio.wait` test meaningful?** Yes, it is acceptable. It is artificial, since it calls
  `cancel()` on itself after `wait` returns, but that is the one way to reach `cancelling()>0` at that line
  deterministically. It is the only test that kills M2, so it pins the "propagate when cancelling" contract. Keep it.
  Its docstring could say it simulates a cancellation that was swallowed earlier (S3 below).
- The comment on the shutdown race (an orphan pool is harmless) is accurate. Idle `ThreadPoolExecutor` workers exit
  when the executor is collected or when the interpreter exits.

## Critical issues
None.

## Suggestions (non-blocking)
- S1 `tests/test_billing.py`: no test pins the new comment in `billing.py` (around line 289) that an incomplete 2xx
  reply keeps the coupon cached. Mutant M6, which moves the check inside the `try`, survives. Add a test where
  checkout returns `200 {}`, then assert the coupon is still in `stripe._coupons` and the next checkout makes no
  coupon call.
- S2 `billing.py` comment: "an unparseable 2xx" drops the coupon (raised in `_call`), but an "incomplete 2xx" keeps
  it. The difference is defensible, but it is subtle. One clause explaining why the two differ would help.
- S3 The docstring of `test_cancelled_request_task_still_gets_cancelled_error_when_future_is_cancelled`: say that
  the monkeypatch simulates an earlier cancellation the code swallowed, which is the only real way to reach that
  branch.
- S4 `task is None` cannot happen inside a coroutine running on an asyncio loop. Harmless, but optional to drop.
