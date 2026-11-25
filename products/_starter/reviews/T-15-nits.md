# Review: p/_starter/T-15-nits

- Branch tip reviewed: 9c85a5db54f75aba167d8373c8671e91ebe7dc12 (one commit on top of origin/main 406168a)
- Reviewer: reviewer agent, 2026-11-25
- Context: `reviews/T-15-coupon-narrow.md`, `reviews/T-15-pool-s3.md` (S4: `task is None` is optional to drop)

## Summary

This commit makes four small changes in `products/_starter/backend`:

1. `app/ratelimit.py:172-173`: drops the `task is None` guard before `asyncio.current_task().cancelling()`.
2. `app/billing.py:283, 289-291`: rewords the comments to separate an unparseable 2xx (`_call` raises `billing_rejected` inside the try, so the coupon is dropped) from a readable but incomplete 2xx (raised outside the try, so the coupon is kept).
3. `tests/test_billing.py:338-361`: adds the new test `test_incomplete_200_reply_keeps_the_cached_coupon`.
4. `tests/test_ratelimit_redis.py:491-494`: expands the docstring of the S3 cancellation test.

No behaviour changes except in the unreachable case (see below). Verdict: **PASS**.

## Evidence

### Test suite (run the way CI runs it)

Setup: Python 3.12.3 in a fresh venv, `pip install --require-hashes -r requirements-dev.txt`, local Postgres 16 on localhost:5432 (studio/studio, `starter_test`), and a local `redis-server` is available.

- `alembic upgrade head && alembic check && alembic downgrade base`: clean, with "No new upgrade operations detected."
- `REQUIRE_PG=1 bash ../infra/test-db-setup.sh`: `passed: 33  failed: 0`
- `python -m pytest -q` (counts from junitxml): **493 collected, 492 passed, 1 skipped, 0 failed, 0 errors**, 59.8 s.
  - The one skip is `tests/test_spa.py:103: frontend not built`. The CI backend job doesn't build the frontend either, so CI skips it too.
- `pip-audit` was not run (it needs network access to the vulnerability DB). This commit doesn't change any dependencies.

### Mutation testing of the new billing test

| Mutation in `app/billing.py` | Result |
|---|---|
| Add `self._coupons.discard(coupon_id)` before the incomplete-reply `raise` | `test_incomplete_200_reply_keeps_the_cached_coupon` FAILS (the only test in the file that fails) |
| Move the incomplete-reply check inside the `try` (the realistic regression the comment warns about) | `test_incomplete_200_reply_keeps_the_cached_coupon` FAILS (again the only one) |

The test catches both regressions, and it is the only test that pins this contract. Both mutations were reverted, and the worktree was clean afterwards.

### Ratelimit change: can `current_task()` be None?

No, not in any reachable call path:

- The only production caller is `off_loop` (`app/ratelimit.py:250`), an `async def` that FastAPI awaits inside a request task.
- `run_blocking` calls `asyncio.get_running_loop()` (line 155) before the changed line. That raises RuntimeError outside a running loop, so sync contexts never reach line 173.
- Line 173 is reached only after `await asyncio.wait(...)` has suspended and resumed. Resuming needs a Task driving the coroutine.
- `loop.run_until_complete(coro)` and `asyncio.run(coro)` both wrap a bare coroutine in a Task. I checked this: `current_task()` is not None in both cases. Tests use both `asyncio.run(limiter.run_blocking(...))` (line 264) and `await` inside `asyncio.run` (line 452).
- Eager task factories (3.12) also set the current task.
- The only way to get None is to drive the coroutine by hand with `coro.send()` from a loop callback. That is not a supported use.

If that ever did happen, the failure would now be an AttributeError instead of a silent fallback. That is louder, which is acceptable. The new comment at line 172 is accurate.

### Comment accuracy

- `billing.py:283`: "a 2xx whose body _call could not parse" matches `_call`: `response.json()` raises ValueError, which becomes `billing_rejected` inside the try, so the coupon is discarded. Accurate.
- `billing.py:289-291`: accurate. The reasoning (an unreadable body tells us nothing; a readable body without id/url means Stripe accepted the request, discount included) is sound.
- `test_ratelimit_redis.py:491-494`: mostly accurate (see suggestion 2).

## Critical issues

None.

## Suggestions (non-blocking)

1. `app/billing.py:283` is 143 characters, longer than the file's usual ~120-character width (lines 248-249 already run long too). Consider wrapping it the next time this file is touched.
2. `tests/test_ratelimit_redis.py:491-493`: the patched `wait` calls `current_task().cancel()` on the running task. That makes a cancellation request pending (`_must_cancel`, `cancelling() == 1`). It does not swallow an earlier CancelledError. Both mechanisms leave `cancelling() > 0`, and both are real (the other is code that cancels its own task synchronously), so "the only real way" is slightly overstated. Something like "simulates a cancellation that is pending or was swallowed without uncancel()" would be exact. This is cosmetic.
3. In `test_incomplete_200_reply_keeps_the_cached_coupon`, the final `calls.count(("POST", "/v1/coupons")) == 1` check duplicates the `in stripe._coupons` check. That is harmless, and it pins the observable effect (no extra Stripe call), so it's worth keeping.

## Verdict

**PASS.** The tests are green (492 passed, 1 skipped, 0 failed), the new test catches both mutations, the removed guard is unreachable, and the comments are accurate.
