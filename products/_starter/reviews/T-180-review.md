# T-180 review: cancel budget and fresh-transaction failure count (T-179 M2)

Branch `p/_starter/T-180`, commit 629060a, diff `git diff main...origin/p/_starter/T-180`.
Reviewer: `reviewer` (opus). Separate worktree on the branch, real Postgres 16.

## Verdict: PASS

M2 is fixed. Every place that calls the provider while holding a `FOR UPDATE` lock now has a 9 s budget, which is under
the 15 s idle timeout. When the timeout fires anyway, the failed attempt is still counted, so backoff and the CRITICAL
alert work again. The tests fail without the fix. The T-173/T-174 webhook behaviour is unchanged. No blocking items.

## Evidence

- Full backend suite (README "Tests": `cd backend && .venv/bin/python -m pytest`, real Postgres, ephemeral DB):
  **828 passed, 1 skipped, 1 warning in 150.67 s**. The skip is `tests/test_spa.py:152` (frontend not built). This
  matches the build note.
- Mutation checks. Each change was made in the scratch worktree, run, and reverted; `git status` was clean afterwards:
  1. Fallback removed (the commit error is re-raised instead of handled with rollback and a re-read): the probe test
     `test_a_cancel_slower_than_the_idle_timeout_still_counts_each_attempt_and_escalates` **fails**. 1 failed, 2 passed.
  2. Old budget restored (8 s timeout, GET 2 tries, module assert disabled): `test_cancel_budget_is_clearly_under_...`
     and `test_worst_case_cancel_measured_with_a_fake_clock` **fail**. 2 failed, 1 passed.
  3. Constants left correct but the GET hard-coded back to `attempts=2`: the fake-clock test **fails**. So the test
     measures what the adapter actually does, not only the constants.

## Every path that holds or follows a lock

| Path | Lock held during provider call? | Worst case | Verdict |
|---|---|---|---|
| `attempt_pending_cancel` (sweep and webhook inline), `routes/billing.py:301-319` | yes, `PendingCancel` row `FOR UPDATE SKIP LOCKED` | 9 s (4 + 1 + 4, or 4 + 1 + 0 + 4) | under 15 s |
| Webhook inline retry, `retry_pending_cancels` `:339-347`, up to 3 rows | one row at a time: every `attempt_pending_cancel` ends with commit or rollback, so each row gets its own transaction. The time does **not** add up inside one transaction. | 9 s per transaction | under 15 s |
| Duplicate-subscription cancel, `:194-210` | no: `db.commit()` at `:194` comes before the call, and nothing in between touches the DB | 9 s, outside any transaction | fine. T-173 S1 is unchanged (503, event id forgotten, redelivered) |
| Period-end lookup, `_fill_period_end` `:350-368` | no: commit at `:358` comes before `lookup` (`expire_on_commit=False`, so reading `ref` does not reopen a transaction) | GET 2 x 4 s + 1 s = 9 s | fine |
| Fallback re-read, `_record_failed_attempt` `:279` | blocking `FOR UPDATE` (no SKIP LOCKED) | bounded by `statement_timeout` 10 s (`db.py`) | acceptable, see S3 |

T-174 S2 is kept: DELETE still gets 2 tries with a short timeout, and a 4xx is never retried and is checked once with
a GET. `test_s2_*` in `tests/test_billing.py:1164-1199` passes unchanged (`["DELETE","DELETE"]`, `["DELETE","GET"]`,
read timeout <= 10).

## Fresh-transaction fallback (`routes/billing.py:263-288`)

- **Another worker took the row.** Once the lock is lost, a sweep may lock the row and attempt it. The fallback's
  blocking `FOR UPDATE` waits for that worker's commit and then re-reads with `populate_existing`:
  - If the other worker cancelled the row or dropped it, the re-read finds nothing and returns None.
  - If the other worker failed too, the fallback counts its own failure on top. That is two real attempts, each
    counted once, and each value is assigned under the lock, so `== ESCALATE_AT` still fires exactly once.
  The fallback only writes attempts, the error and the time. It never deletes, cancels, or skips the current-sub check.
- **Double counting.** This happens only if the first COMMIT reached the server but the reply was lost (the
  connection dropped after the server committed). The fallback then adds one more. That brings backoff and escalation
  forward by one attempt, and nothing worse. Low, see S4.
- **Masking other errors.** `except Exception` covers only the commit, and the error is logged at WARNING with the
  traceback. If the fallback also fails, that error propagates (the sweep logs it; `apply_update` catches it and logs
  ERROR). The caller's `exc_info=True` ERROR line still shows the provider error, because Python restores the outer
  exception once the nested handler finishes.
- `expire_on_commit=False`, so reading `row.attempts` after the commit cannot trigger a refresh. `pool_pre_ping` plus
  the rollback handle the connection that 25P03 terminated, and the probe proves this end to end.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. "9 s" bounds each phase of a request, not the whole call.** `billing.py:231, 276`: `timeout=4.0` becomes
  `httpx.Timeout(4.0)`, a separate 4 s limit for connect, write, each read, and the pool. DNS (`getaddrinfo`) is not
  covered at all. A slow-trickling or slow-resolving provider can push one request past 4 s, and so the whole cancel
  past 15 s.
  - Failure path: the new fallback now covers this.
  - Success path: if the cancel succeeds after the lock was lost, the delete commit raises 25P03, nothing is counted,
    and the next sweep finds the subscription gone (404 or canceled) and deletes the row. That is safe but noisy.
  - Fix: wrap the call in a wall-clock deadline, for example one deadline shared by both tries. Or state in the
    comment that the bound is per phase.
- **S2. Webhook total latency.** One event can do the duplicate cancel or the period-end lookup (9 s), then 3 inline
  rows at 9 s each, which is about 36 s in total. That is down from about 68 s, but still longer than a provider
  usually waits. It causes no lock or data problem: the event is committed first and the redelivery is deduplicated.
  The cost is failed deliveries in Stripe's dashboard and, if this persists, endpoint-disable warnings. Fix: a total
  time budget for `retry_pending_cancels` (stop starting new rows after about 5 s), or retry only the oldest row
  inline.
- **S3. The fallback can wait up to 10 s on another worker's lock.** It then raises a statement timeout, which the
  sweep logs. That is acceptable. Using `SKIP LOCKED` and returning None there would be faster, but would drop this
  attempt's count. The current choice is defensible; a one-line comment would help.
- **S4. Silent `None` branch.** At `:321-322`, when the row vanished during the fallback, the function returns False
  and logs nothing. The sweep counts this as "failed" even though another worker may have cancelled the subscription.
  Fix: log an INFO line, and consider returning None ("skipped") to match the docstring's meaning of None.
- **S5. The `_cancel_worst_case` formula only holds for 2 tries or fewer.** It assumes a flat `_CANCEL_BACKOFF = 1.0`,
  while `_call` actually sleeps `2**attempt` (1, 2, 4, ...). The fake-clock test would still catch a change, but
  computing the sum from `2**i` would make the constant honest.
- **S6. Test gap.** The probe covers the sweep only. The webhook inline path uses the same function, but a single
  webhook-level test (slow cancel, small idle timeout, `attempts` reaches `INLINE_RETRY_MAX_ATTEMPTS` and inline
  retries stop) would pin the "`attempts < 3` bites again" claim from M2.
- **Nit.** The README test table still says "820 passed"; it is now 828.
