# Review: p/_starter/T-174-team (commit 5545dbc)

Reviewer: reviewer agent, 2026-11-27. Scope: `git diff origin/main...origin/p/_starter/T-174-team`. The diff touches `backend/app/routes/team.py` (+14/-6), `backend/tests/test_team.py` (+111/-8) and the README test count. It addresses S1 to S4 of `reviews/T-173-team-review.md`.

## Verdict: PASS

All four intended changes are in, and each one is guarded by a test that fails when its fix is removed. I checked that by mutating the code. The deadlock catch is correct. It rolls back before deciding what to do, so no partial write survives. It re-raises every OperationalError that is not 40P01. Its 409 body is the same as the existing `email_taken` answer in `accept`. I found no blocking issues.

## Evidence

- Full backend suite in the worktree (Postgres 16 and Redis, `python -m pytest -p no:warnings -q -o addopts=`): **774 passed, 1 skipped in 95.40s**.
- `tests/test_team.py` run 5 times in a row: **23/23 passed each time**, with no flakes.
- Mutations. Each was applied to `app/routes/team.py` in the worktree, the tests were run, and the file was then restored. `git status` is clean.

| # | Mutant | Result |
|---|---|---|
| M1 | drop the tenant lock in `invite` (`team.py:74`) | **killed**: `test_concurrent_resends_leave_one_live_link` fails with "the resends did not both queue behind the tenant lock". `test_invites_for_one_tenant_are_serialised` is also killed. (This was S1: vacuous before, real now.) |
| M3 | tenant lock as a plain `with_for_update()` | **killed**: `test_tenant_lock_is_no_key_update...` gets `assert 409 == 201`. The accept is the deadlock victim and now surfaces as a 409. (S3) |
| M4 | remove the `except OperationalError` branch | **killed** on 3/3 runs: the cross-tenant test fails with `[201, 500] == [201, 409]`, and the injected test fails with `500 == 409`. (S2) |
| M5 | keep the catch, but move the B7 `UPDATE` back outside the `try` | **survived 5/5** (see S1 below) |

## Checks requested

- **Session state after 40P01.** `db.rollback()` runs before the sqlstate test, on both branches. The failed transaction is therefore ended, and the pending `User` is expunged. The `accepted_at` change and the invitation row lock are both discarded. Nothing is committed, and the cross-tenant test asserts exactly one `users` row.
- **No swallowing.** `getattr(exc.orig, "sqlstate", None) != "40P01"` re-raises statement timeouts, connection loss and other errors unchanged, so they give the same 500 as before. `psycopg.errors.DeadlockDetected.sqlstate` is a class attribute, so the injected test exercises the real comparison.
- **409 shape.** It is identical to the IntegrityError branch: `AppError(409, "email_taken", "That email already has an account. Try signing in.")`.
- **Moving the B7 update into the `try` is right.** In the A/B cross-tenant cycle, Postgres may abort either side. When the victim is the transaction running the UPDATE, the catch now covers it, and the survivor revokes the victim's still-pending invite. So the outcome is always one 201 and one 409.
- **The pg_stat_activity filter** uses `datname = current_database()`. conftest gives every pytest run its own database (`<db>_t<epoch>_<pid>_<rand>`), so concurrent runs cannot inflate the count. My full suite ran while another reviewer may have been running theirs, and it passed. One caveat is in S3.
- **Polling vs sleep.** All three former `sleep(0.7)` sites now poll and assert the result, so a slow argon2 hash can no longer give a false pass. The timeout is 8 s, below the 15 s idle-in-transaction timeout that would kill the side connection.

## Critical issues

None.

## Suggestions

- **S1. The real cross-tenant test only ever exercises the flush-side victim.** M5 survives because the transaction waiting on the unique index starts its wait first, so its `deadlock_timeout` fires first, and it is always the one aborted. The UPDATE-side victim path (`team.py:161-162` inside the `try`) is correct by inspection, but no test covers it. An injected test that raises `DeadlockDetected` from `Session.execute` for the `UPDATE invitations` statement would close this.
- **S2. Any 40P01 in `accept` now reads as "email taken".** Today that is true: the only known cycle is the cross-tenant double accept. But M3 shows that a future regression which caused an invite/accept deadlock would also show up as a misleading 409, not a 500 that someone would notice. Consider `log.warning("accept deadlock", ...)` in that branch so it stays visible in the logs.
- **S3. Under `TEST_DATABASE_SHARED=1`** two runs share one database, and `_wait_for_lock_waiters` could count the other run's waiters. The resulting false pass would need both runs to be inside race tests at the same moment. Low risk; a one-line note in the helper's docstring is enough.
- **S4. No test that a non-40P01 OperationalError is re-raised** (for example, an injected `QueryCanceled` should return 500 and not 409). This is cheap to add next to the injected deadlock test.
- Nit: in `test_concurrent_resends_leave_one_live_link`, a thread that raised fails with `KeyError: 'r'` rather than showing the captured exception. The newer tests assert `"error" not in box` first. Use the same pattern here for a clearer failure message.
