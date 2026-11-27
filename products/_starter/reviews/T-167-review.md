# T-167 review: retry a failed model-guard trip save (T-165 L1) and the N1 log wording

- Branch `p/_starter/T-167`, commit 34fdfa1, diff `git diff main...origin/p/_starter/T-167` (4 files: `backend/app/ai.py`,
  `backend/app/models.py`, `backend/tests/test_ai.py`, `README.md`).
- Reviewer: reviewer agent, 2026-11-27. Read CLAUDE.md, `playbooks/engineering.md`, `reviews/T-165-security.md`,
  `reviews/T-163-review.md` and `reviews/T-163-review-2.md` (pool starvation). I changed no product code. The probes
  below ran in a throwaway worktree and were deleted.

## Verdict: PASS

The fix does what T-165 L1 asked. A failed trip save sets `trip_unsaved`. `ensure_ai_enabled` retries it at most once
per 30 s and only while the provider is off. One thread retries at a time. A success clears the flag. Nothing in the
retry path can set `disabled` back to False, and the 503 is raised whatever the retry does. N1 is fixed in the log line
(`ai.py:395`) and in the `AIGuardTrip` docstring. There are no blocking issues. There are two lows and two nits, below.

## Tests

- Full backend suite on the branch tree (local Postgres 16, `backend/.venv`): **729 passed, 1 skipped in 98 s**. This
  matches the README count.
- Mutation checks, run against `tests/test_ai.py`:

| Mutation in `app/ai.py` | Result |
|---|---|
| M1 `ensure_ai_enabled` never calls `retry(db)` (:105) | caught (`test_failed_trip_save_is_retried_into_the_real_table` and others) |
| M2 drop the 30 s clock check in `retry_unsaved_trip` | caught |
| M3 drop the pending-writes check (:444) | caught (`test_trip_save_retry_uses_the_callers_session_and_skips_one_with_pending_writes`) |
| M4 a successful save does not clear `trip_unsaved` | caught (5 tests) |
| M5 a successful retry sets `disabled = False` (re-enables the AI) | caught (3 tests) |
| M6 `_save_trip` ignores the caller's `db` and opens its own session | caught |
| M7 drop `not self.disabled` from the retry guard | not caught. This is equivalent today: the only caller runs it only when `disabled` is True. Fine. |

- Probes on real Postgres:
  - P1: an unsaved trip on a session that already ran a raw `INSERT` that was flushed but not committed. The caller's
    row **was committed** by the retry (count 1). This confirms builder risk 1.
  - P2: a retry whose write fails on the caller's session leaves that session in an aborted transaction. The next
    `SELECT 1` raises `InternalError`.
  - P3: tiny pool (`db_pool_size=1, db_max_overflow=0`), first save fails, retry runs through the route 31 s later:
    `200, 503, 503`, the row is saved, in 0.14 s. There is no nested checkout, so the T-163 pool starvation does not
    come back.

## Builder risks: my judgement

1. **Committing the caller's session: acceptable for now. A redesign is not needed, but harden it (L1 below).**
   The only caller that passes `db` is `routes/notes.py:113`. Everything before it on that session is a read (`current`
   commits its read transaction, then `_get` and `subscription_of` only select), so nothing extra can be committed
   today. The alternatives are worse or no better:
   - Always use a short own session. That brings back the nested checkout T-163 removed. It is bounded (one thread, once
     per 30 s), but on a starved pool that one request would block for `pool_timeout` 10 s.
   - Use a SAVEPOINT. It does not help: releasing a savepoint is not durable, so the outer commit is still needed and
     still includes the caller's writes.
   - Use a separate connection. That is the own-session option again.

   The weak spot is that `new/dirty/deleted` does not see flushed work. Because of autoflush, any ORM add followed by a
   query is already flushed by the time `ensure_ai_enabled` runs, so the check protects less than its comment
   suggests. P1 shows this. Because the template copies this helper into every product, write the contract into the
   public function, not only into `TripStore.record`.
2. **First retry no sooner than 30 s after the failure: acceptable.** During that window another replica or a cold start
   could make about one expensive call (around $1.10), which is the exposure T-165 already rated low. The global daily
   cap still bounds the total. Retrying straight away on the next call would usually hit the same database blip. Waiting
   is the sensible default.
3. **A trip that no later call follows stays unsaved: acceptable.** With scale-to-zero, the process dies and the next
   process pays at most one more call before it saves the row itself. That is no worse than main, and it is strictly
   better whenever there is any follow-up traffic. A background timer is not worth the extra complexity. The optional
   T-165 suggestion of `ai: "disabled"` on `/api/health` would make this visible, and that can wait for a later task.

## Findings

### L1 (low, data integrity, latent): the retry can commit a caller's flushed writes, and the contract is not on the public helper
- Where: `backend/app/ai.py:93-105` (the `ensure_ai_enabled` docstring does not mention the commit),
  `:124-131` (`record` commits `db`), and `:444` (the check cannot see flushed work).
- Scenario: a future product route writes row A, runs a query (autoflush), then calls `ensure_ai_enabled(ai, db)` while
  a trip is unsaved. The retry commits A, and the request returns 503. A was supposed to commit only together with B,
  so the database is left half-written. Probe P1 reproduces this.
- Fix (small, no redesign needed):
  - In the `ensure_ai_enabled` docstring, say "with `db`, the call may commit that session: call it before the route
    writes anything".
  - Optionally, also skip when `db.in_transaction()` holds writes. One cheap proxy is
    `db.info.get("wrote")` set by an `after_flush` session event. Another is not to pass `db` from routes that write
    first.
  - A test that pins "the route's session is clean when `ensure_ai_enabled` runs" would catch a regression in
    `notes.py`.

### L2 (low, robustness): a failed retry on the caller's session leaves it unusable
- Where: `backend/app/ai.py:421-432` (`_save_trip`'s `except` does not roll back the passed session).
- Scenario: the retry's `INSERT` or commit fails on the request session. `ensure_ai_enabled` raises 503 straight away
  and `get_db` closes the session, so today nothing breaks. But a future caller that catches the 503 to degrade
  gracefully would get `InternalError` / `PendingRollbackError` on its next query (probe P2).
- Fix: in `_save_trip`'s `except`, call `db.rollback()` inside a `try` when `db` is not None, or do it in `record`.

### N1 (nit): the success path leaves `_trip_retry_at` stale
- Where: `ai.py:433`. This is harmless, because `trip_unsaved` gates everything. Mentioned only for tidiness.

### N2 (nit): the real-table test does not check a fresh process
- Where: `tests/test_ai.py:1587`. Its docstring says "a fresh process sees it", but the test only counts rows. Adding
  `_summaries_again(_store_app(...))` with zero model calls would pin the T-165 acceptance criterion exactly: process B
  refuses with 0 calls.

## Checked and fine
- Logs record only `type(exc).__name__`. The test asserts that the exception text (`SECRET-PROMPT`) is not logged.
- Thread safety: the lock is non-blocking, so concurrent callers never wait on it. The state is re-checked under the
  lock. `trip_unsaved` and `_trip_retry_at` are written without the lock in `_save_trip` from the trip path, but that
  runs once per process and the race is benign: at worst there is one extra retry.
- `complete()` calls `ensure_ai_enabled(self)` without `db`. That uses one short own session inside `AISlots` after
  `reserve` has released the request connection, and only once per 30 s. That is within the T-163 pool reasoning.
- A trip loaded from the database (`check_persisted_trip`) never sets `trip_unsaved`, so a loaded trip triggers no
  writes.
- `INSERT ... ON CONFLICT DO NOTHING` makes a retry after a save that actually succeeded (for example a lost commit
  acknowledgement) idempotent.
- There is no migration, no new dependency and no new secret.
