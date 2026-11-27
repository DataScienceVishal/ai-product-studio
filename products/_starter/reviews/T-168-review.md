# T-168 review: trip-retry contract hardening (T-167 review L1, L2, N2)

- Branch `p/_starter/T-168`, commits 43f1d36 (code and tests) and 868abcb (hand-off note). Diff
  `git diff main...origin/p/_starter/T-168`: 4 files (`backend/app/ai.py`, `backend/tests/test_ai.py`, `README.md`,
  `NEXT-T-168.md`).
- Reviewer: reviewer agent, 2026-11-27. Read `reviews/T-167-review.md` (L1, L2, N2), `app/ai.py` (TripStore,
  `ensure_ai_enabled`, `_save_trip`, `retry_unsaved_trip`), `app/routes/notes.py` (summarize) and `app/main.py`. I
  changed no product code. Mutants ran in a throwaway worktree, which has been removed.

## Verdict: PASS

All three findings are fixed as the T-167 review asked:
- **L1:** the `ensure_ai_enabled` docstring now warns that the call may commit the session (`ai.py:98-101`). A route
  test pins the call order in `notes.py` (`test_ai.py:1731`).
- **L2:** `_save_trip` now rolls back the caller's session when the write fails. A failure of the rollback itself is
  caught, and only its exception type is logged (`ai.py:437-441`).
- **N2:** the real-table end-to-end test now starts a fresh provider and app on the same database. It checks that this
  process refuses with zero model calls (`test_ai.py:1613-1620`).

There are no blocking issues. There are three non-blocking suggestions below.

## Tests

- Full backend suite on the branch tree (local Postgres 16, a fresh venv from `requirements-dev.txt`,
  `python -m pytest`): **733 passed, 1 skipped in 87 s**. This matches the README count (729 before, plus 4 new tests).

## Mutation check

Each mutant was applied to the branch tree. I ran `tests/test_ai.py -k "rollback or no_writes or real_table or retry or trip"`
(21 tests), then reverted the change.

| # | Mutant | Result | Caught by |
|---|---|---|---|
| m1 | Remove `db.rollback()` in `_save_trip` (L2) | KILLED | `..._rolls_it_back_and_session_stays_usable` (InFailedSqlTransaction) and `..._logged_by_type_only` |
| m2 | Move `ensure_ai_enabled(ai, db)` after `reserve()` (which writes and commits) in `notes.py` (L1) | KILLED | `test_notes_route_calls_ensure_ai_enabled_on_a_session_with_no_writes`, plus 4 older trip tests |
| m3 | ORM write plus `db.flush()` before `ensure_ai_enabled` in `notes.py` (L1) | KILLED | `test_notes_route_calls_..._with_no_writes` only |
| m4 | Raw SQL `UPDATE notes ...` via `db.execute` before `ensure_ai_enabled` (L1) | SURVIVED | known blind spot that the builder declared (S1) |
| m5 | Remove the pending-writes guard in `retry_unsaved_trip` (the existing commit-safety) | KILLED | `test_trip_save_retry_uses_the_callers_session_and_skips_one_with_pending_writes` |
| m6 | `check_persisted_trip` never latches (`if tripped` becomes `if False`) | KILLED | 3 tests, including the real-table test |
| m7 | Rollback-failure log prints the exception text instead of its type | KILLED | `test_rollback_failure_..._logged_by_type_only` (SECRET-DSN reached the log) |
| m8 | Rollback exception not swallowed (`except ZeroDivisionError`) | KILLED | `test_rollback_failure_..._logged_by_type_only` |
| m9 | Drop the `if db is not None` guard, so `None.rollback()` is called | SURVIVED | nothing (S2) |
| m10 | The caller-session `record` writes the row under the wrong (reversed) fingerprint, so the row count stays 1 | KILLED | the **N2** lines only: `again.status_code` was 200, not 503 |
| m11 | `TripStore.tripped(fp, db)` always returns False on the request-session path | SURVIVED | all 35 `-k trip` tests pass (S3, older gap) |
| m12 | m10 with the N2 block removed | SURVIVED | shows N2 is the only test that catches m10 |

L1 and N2 are now mutation-checked: m2 and m3 for L1, and m10 against m12 for N2.

## Critical issues

None.

## Suggestions (non-blocking)

### S1 (low): the L1 test cannot see raw SQL writes (m4)
- Where: `tests/test_ai.py:1731-1763`. The spy only reads `session.new/dirty/deleted` and the `before_flush` event, so
  a `db.execute(insert/update/text(...))` before the call goes unnoticed. Today `notes.py` has no such write, and the
  builder declared this gap.
- Fix (optional): record DML on the request's connection. Use an `Engine` `before_cursor_execute` listener that marks
  `conn.info["wrote"]` for `INSERT|UPDATE|DELETE` statements. The spy then asserts that
  `db.connection().info.get("wrote")` is falsy, or uses `do_orm_execute` on the session. This covers ORM and raw SQL
  writes in one check.

### S2 (nit): the no-session test does not check that rollback is skipped (m9)
- Where: `tests/test_ai.py:1804`. Its name says that no rollback is needed, but without the `db is not None` guard,
  `None.rollback()` raises AttributeError. The `except` swallows it and logs a misleading "rollback of the caller's
  session failed (AttributeError)".
- Fix: add `caplog` and assert that no record contains "rollback".

### S3 (low, from before T-168): the per-request trip read on the request session is not checked for its result (m11)
- Where: `app/ai.py:120-123` and `routes/notes.py:113`. If the request-session read wrongly said "not tripped", a fresh
  process would still refuse with zero model calls. `complete()` calls `ensure_ai_enabled(self)` without `db` and
  re-reads the trip on its own session. But by then the route has already reserved budget (`reserve` commits), and the
  fallback needs the second pooled checkout that T-163 removed.
- Fix (optional, separate task): in the N2 block, or in a new test, assert that the refused request wrote no
  reservation or usage row. Or count connection checkouts during the refused request, as the tiny-pool test does.

## Checked and fine

- **Rollback semantics:** the retry only runs while `disabled` is set, and `ensure_ai_enabled` raises a 503 whatever
  the retry does. So losing the caller's uncommitted work on rollback cannot hide a partial write behind a 200. The
  docstring states this trade-off.
- **Rollback after a failed `commit()`:** `record` executes and then commits. If either step fails, the session needs
  a rollback, and the new code does that. Without a session, `record` uses its own `with self.sessions()` block,
  which cleans itself up.
- **Secrets:** both log lines record only `type(exc).__name__`. m7 shows that the test enforces this.
- **Concurrency:** no change. The rollback runs inside `_trip_retry_lock` on the caller's own session.
- **Tests test behaviour:** the L2 test uses a real Postgres aborted transaction, not a mock. N2 uses a real second
  app over the same database and counts HTTP calls to the mock model.
- **Docs:** the README count is updated to 733 passed, 1 skipped, which matches the run.

## Merge notes

- Delete `products/_starter/NEXT-T-168.md` in the merge, as the note itself says.
- Rerun the full backend suite on the merged tree.
