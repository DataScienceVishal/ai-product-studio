# Review: p/_starter/T-15-leftovers (head 9f27a16)

Reviewer gate, 2026-11-25. Diff: `git diff origin/main...origin/p/_starter/T-15-leftovers` (4 files, +73 / -7).
This branch closes leftovers from `reviews/T-15-coupon.md` (items 2 to 5 and the 40-character nit) and
`reviews/T-15-pool-followups.md` S2.

**Verdict: PASS**

## Summary

- `app/billing.py:274-285`: `create_checkout` stores the coupon id it attached. If the checkout POST raises `AppError`,
  it removes that id from `self._coupons` and re-raises. The next offer checkout then runs `ensure_coupon` again, which
  re-creates a deleted coupon, or re-checks an existing one with the GET and terms check. This was review item 2.
- `tests/test_billing.py`: the imports are now in sorted order (item 5, first half). There are three new tests:
  - the cache is dropped after a failed checkout and re-filled on the next one;
  - a failed checkout with no offer leaves the cache alone;
  - the coupon name is capped at 40 characters (item 3).
- `tests/test_spa.py:597-600`: the F1 assertion message now names the known false positive, a comma inside a quoted
  string (item 4).
- `tests/test_ratelimit_redis.py`: the `_skip_redis` leak assertions read the ContextVar inside the coroutine, in the
  caller's own context, after `run_blocking`/`off_loop`. They cover both the breaker-open path and the queue-timeout path
  (pool-followups S2).

## Evidence

- Full backend suite on this branch (git worktree at 9f27a16, local Postgres 16, `/tmp/claude-0/venv`):
  `python -m pytest -o addopts="" -q` gives **487 passed, 1 skipped, 0 failed** in 69.5s. That is 484 + 3 new tests. The
  skip is the existing `test_spa.py` check that needs a built frontend.
- Mutation probes. Each mutation was applied on its own, the named test file was run, then the file was restored with
  `git checkout`. The worktree was clean afterwards.

| # | Mutation | Result | Test that caught it |
|---|---|---|---|
| M1 | `self._coupons.discard(coupon_id)` replaced with `pass` | KILLED | `test_failed_checkout_drops_the_cached_coupon_so_the_next_one_rechecks_it` |
| M2 | `self._coupons.clear()` on any checkout failure (over-eager) | KILLED | `test_failed_checkout_without_offer_leaves_the_coupon_cache_alone` |
| M3 | `[:40]` removed from the coupon name | KILLED | `test_coupon_name_is_capped_at_stripes_40_characters` |
| M4 | `[:40]` changed to `[:39]` | KILLED | same |
| M5 | `except AppError` changed to `except ValueError` | KILLED | drop-cache test |
| M6 | `ratelimit.py:136` breaker path: `_skip_redis.set(True)` in the caller's context instead of `ctx.run(...)` | KILLED (it **survives** with main's test file) | `test_open_breaker_skips_the_pool` |
| M7 | `ratelimit.py:166` timeout path: `_skip_redis.set(True)` in the caller's context instead of `fallback.run(...)` | KILLED (main's file also catches it, indirectly) | `test_queue_wait_is_bounded_and_late_waiters_use_the_memory_check` |

M6 is the one S2 asked for. Before this branch nothing caught it, and now the breaker-path test does. The variant where
`if coupon_id:` is removed is equivalent (`discard(None)` does nothing), so it can't be killed and needs no test.

## Correctness questions asked

- **Could dropping the id on a transient 503 cause harm?** No. The only effect is that the next offer checkout makes
  one or two extra calls: POST /coupons, then `resource_already_exists`, then GET. If Stripe is still down, that call
  fails with the same `billing_unavailable` the checkout would have given, so the customer sees the same result. The
  coupon is never re-created with different terms, because the id is deterministic and the GET checks percent, duration,
  months and `valid`. Worst case on a flaky Stripe is some extra latency from `_call`'s 1s and 2s back-off.
- **Is it safe under concurrency?** Yes. `/api/billing/checkout` is a sync route, so FastAPI runs it in its threadpool,
  and all threads share one `StripeBilling`. `set.add` and `set.discard` are atomic under the GIL. If one thread
  discards while another has just ensured the coupon, the other thread re-ensures it next time: redundant calls, never a
  wrong discount and never a missing one. Stripe's dedupe of `resource_already_exists` already handles concurrent
  ensures.
- **Is there a path where the coupon is attached but not dropped?**
  - The "incomplete reply" 502 (no `id` or `url`) is raised after the `try`, so the id stays cached. That reply means
    Stripe accepted the request, so the coupon is not the cause. That is correct.
  - Non-`AppError` exceptions from `client.request` (for example `httpx.InvalidURL`) also bypass the drop. They are
    unrelated to the coupon. Fine.
  - If `ensure_coupon` itself fails, nothing was added to the cache. Fine.
- **Is the catch too broad?** It drops the id on any checkout failure, including ones unrelated to the coupon (for
  example a bad `success_url`). The cost is one re-check. That is an acceptable trade, and the code comment says so.

## Critical issues

None.

## Suggestions (non-blocking)

1. Optional: drop the id only on `billing_rejected` (a 4xx answer), not on `billing_unavailable`. A coupon that is
   deleted or invalid comes back as a 400. A 503 says nothing about the coupon, and skipping the drop saves the
   re-check during an outage. The current behaviour is safe, so this is a small efficiency gain only.
2. Item 5, second half, is still open: the `stripe_provider()` handler at `tests/test_billing.py:78` still answers
   coupons with `{"id": "studio-coupon"}`. It is harmless (the code ignores the POST reply's id) and cosmetic only.
3. `test_coupon_name_is_capped_at_stripes_40_characters` repeats the name format string from `billing.py`, in two
   places. If the wording changes, the test has to change too. The `len(name) == 40` check alone would be enough to
   catch M3 and M4.

## Security and performance

- No endpoint, authorization or tenancy changes. No secrets. The test-mode key lock is untouched.
- Cost: at most two extra Stripe calls after a failed offer checkout. No new queries.
