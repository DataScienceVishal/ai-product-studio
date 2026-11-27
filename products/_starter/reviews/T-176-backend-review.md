# Review: p/_starter/T-176 (backend)

Reviewer gate, 2026-11-27. Scope: `git diff main...p/_starter/T-176` (commits a832705, 9e4bd5a). It addresses T-175-billing-review S3, S5, S6, S7 and re-review notes 1-2, plus T-175-team-review S1.

**Verdict: PASS**

## Summary

- The change adds `pending_cancels.last_attempt_at` (migration 0011, nullable `timestamptz`, clean downgrade). Every failed attempt now stamps it.
- The webhook retries only rows with `attempts < 3`.
- The sweep skips a row while `now - last_attempt_at < min(2^attempts min, 24 h)`. A row with a NULL timestamp is always tried.
- At exactly 10 attempts the code logs one CRITICAL line ("pending cancel needs operator"). The line carries ids only and no `exc_info`. Later failures log at WARNING.
- The new tests cover the webhook wrapper's `except`, the takeover delete on its own, a committed row held by another session (SKIP LOCKED), and team rollback through a spy.

## Evidence

- Full backend suite: `.venv/bin/python -m pytest` gave **819 passed, 1 skipped in 150.70s**, which matches the README.
- Mutations: 13 run, 12 killed, each by the intended test. The tree was restored with `git checkout` and is clean.

| # | Mutation | Result |
|---|---|---|
| M1 | inline filter `<` to `<=` | killed: test_s5 |
| M2 | escalate `==` to `>=` | killed: tenth_failure |
| M3 | sweep backoff `<` to `<=` | **survived** (see S1) |
| M4 | backoff check removed | killed: 3 backoff cases |
| M5 | 24 h cap changed to 48 h | killed: `[20-25h-True]` |
| M6 | NULL timestamp with attempts > 0 skipped | killed: no_timestamp, s5, tenth_failure |
| M7 | `last_attempt_at` stamp removed | killed: s7 |
| M8 | takeover's `delete(PendingCancel)` removed | killed: note1 |
| M9 | `skip_locked` changed to `nowait` | killed: note2 |
| M10 | webhook wrapper's `except` removed | killed: s3 |
| M11 | `exc_info=True` added to the CRITICAL line | killed: tenth_failure |
| M12 | escalated WARNING changed to ERROR | killed: tenth_failure |
| M13 | `team.py` OperationalError `db.rollback()` changed to `pass` | killed: 4 tests in test_team |

## Correctness checks

- **Escalates exactly once.** `attempt_pending_cancel` re-reads the row `FOR UPDATE SKIP LOCKED` with `populate_existing`, so increments are serialized. The session factory uses `expire_on_commit=False` (`app/db.py:45`), so `row.attempts` after the commit is this worker's own value, not a refresh that a concurrent worker could have changed. Only one worker can produce the value 10. The webhook cannot reach 10 because it only touches rows below 3.
- **Thresholds.** The webhook retries attempts 0, 1 and 2, and leaves 3 to the sweep (tested at 2 and 3). Backoff is skipped when the elapsed time is less than the backoff and tried when it is equal or more. Equality is untested (S1). `2 ** min(attempts, 12)` cannot overflow, and the cap applies from 2^11 minutes.
- **Timezones.** The default `now` is UTC-aware. The column is `timestamptz`, which psycopg returns as aware. The tests pass aware datetimes.
- **NULL `last_attempt_at`.** Rows from before 0011 that have `attempts > 0` are tried at once and then stamped. This is tested.
- **Migration.** The upgrade and downgrade test also runs `command.check`.
- **Logging.** The CRITICAL line carries `tenant_id`, `old_subscription`, `old_provider` and `attempts` only, with no exception text (asserted). The ERROR and WARNING lines keep `exc_info` as T-175 did.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. Exact backoff boundary is untested.** `app/maintenance.py` line 85 (`now - last_attempt_at < ...`). Mutant M3 (`<=`) survives. Add a parametrize case `(2, timedelta(minutes=4), True)` to fix the boundary.
- **S2. The backoff check reads an unlocked snapshot.** The sweep decides from the list it read at the start and does not re-check under the lock. Two overlapping sweeps, or a webhook retry while a sweep runs, can therefore attempt the same row twice in quick succession. This is harmless (the cancel is idempotent and attempts are still counted once each), but it bypasses the backoff for that row. To fix it, re-check `cancel_backoff` inside `attempt_pending_cancel` after the locked read, or add a `where` on `last_attempt_at` to the locked select.
- **S3. The CRITICAL line is at most once, not exactly once.** It is logged after the commit. If the process dies between the commit and the log, the row sits at 10+ attempts and is never escalated. Document an operator query (`SELECT id, ref, attempts FROM pending_cancels WHERE attempts >= 10`) in the README next to the alert, so the table, not only the log, is the source of truth.
- **S4. DATA.md is slightly inaccurate.** The "Deleted by" column still says "the tenant's next billing event" without saying this only applies to rows with fewer than 3 failures. The README says it correctly.
- **S5. The test message claims an order it does not check.** In `tests/test_team.py`, the spy asserts that a rollback happened, not that it happened "before it logs" as the message says. Either reword the message or record the order next to the log handler. The IntegrityError branch's `db.rollback()` has no spy (out of S1's scope).
- **S6. Mixed import styles in the tests.** `test_s7` re-imports `datetime` locally although the module already imports it at the top. This is cosmetic.
