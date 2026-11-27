# Review: p/_starter/T-175-team (commit 21ce939)

Reviewer: reviewer agent, 2026-11-27. Scope: `git diff main...p/_starter/T-175-team`. The diff touches `backend/app/routes/team.py` (+5), `backend/tests/test_team.py` (+90) and the README test count. It follows up S1, S2 and S4 from `reviews/T-174-team-review.md`.

## Verdict: PASS

All three follow-ups are in. Each new test fails when the behaviour it guards is removed; I checked that by mutating the code. The new WARNING contains ids only. The rollback still runs before the sqlstate check, so the session is clean on every branch. I found no blocking issues.

## Evidence

- Full backend suite in the worktree (Postgres 16 and Redis, `.venv/bin/python -m pytest -p no:warnings -q -o addopts=`): **789 passed, 1 skipped in 104.04s**. That matches the README.
- `tests/test_team.py` run 3 more times in a row: **27/27 passed each time**, with no flakes.
- The WARNING as the JSON formatter emits it (captured with `-s`):
  `{"level": "WARNING", "logger": "app.team", "msg": "accept deadlock (40P01), answered as email_taken", "request_id": "...", "tenant_id": "<uuid>", "invitation_id": "<uuid>"}`.
  It has no email, token or password. The request path is `/api/invitations/accept`, and the token travels in the body, not the URL.
- Mutations. Each was applied to `app/routes/team.py` and the tests were run; the file was then restored. `git status` is clean.

| # | Mutant | Result |
|---|---|---|
| M1 | delete the `log.warning` (`team.py:176-177`) | **killed**: `test_a_deadlock_in_accept_is_logged_without_personal_data` |
| M2 | log at INFO, not WARNING | **killed**: the same test |
| M3 | add `email=user.email` to the log's `extra` | **killed**: the same test (PII assertion) |
| M4 | move the revoke `UPDATE` (`team.py:162`) back outside the `try` | **killed**: `test_a_deadlock_on_the_revoke_update_is_a_409_email_taken` gets a 500. This closes the gap that T-174 M5 left. |
| M5 | drop the `!= "40P01": raise` (swallow every OperationalError) | **killed**: `test_a_non_deadlock_operational_error_is_not_swallowed_as_409`, both `[flush]` and `[revoke]` |
| M6 | `db.commit()` in place of `db.rollback()` in the deadlock branch | **killed**: the real cross-tenant race test fails with `PendingRollbackError` |
| M7 | delete `db.rollback()` (`team.py:171`) | **survived** (see S1) |
| M8 | read `invitation.tenant_id` / `invitation.id` in the except, after the rollback, instead of capturing them early | **survived** (see S2; harmless) |

## Checks requested

- **Correctness.** The catch, the 409 body and the re-raise are unchanged from T-174. The only change in behaviour is the WARNING. Its message is fixed text and its `extra` holds two UUID strings captured before the flush.
- **Session state after rollback.** `db.rollback()` (`team.py:171`) runs before the sqlstate test, on both branches. The pending `User` is expunged, the change to `accepted_at` is discarded and the row lock is released. The revoke test checks the database from a separate connection: no `users` row, and `accepted_at IS NULL`. The non-40P01 test checks that no account is left behind, for both injection points.
- **The tests really fail without the fix.** Yes: M1 to M5 above.
- **The 500 path.** The non-40P01 test uses its own `TestClient(raise_server_exceptions=False)`, so it checks the real 500 response the app returns, not a re-raised exception. The app's unhandled-error log masks the details (`database error (sqlstate 57014); details hidden`).

## Critical issues

None.

## Suggestions

- **S1. The injected tests cannot tell whether the explicit `db.rollback()` runs (M7 survives).** The fake error is raised from the patched `Session.flush` or `Session.execute`, before any SQL reaches Postgres. The transaction is therefore never in the aborted state a real 40P01 leaves it in. `get_db`'s `db.close()` then rolls back anyway, so the "nothing survives" assertions pass with or without line 171. The rollback is still right, and M6 shows that the real race test needs the session to be usable. A cheap way to pin it: in the revoke test, also assert `db.in_transaction()` is false, or spy on `Session.rollback`. Optional.
- **S2. The comment at `team.py:156` slightly overstates the risk.** It says the ids are "unreadable once a flush fails". They are unreadable between the failed flush and the rollback (`PendingRollbackError`). After `db.rollback()` they reload with a fresh SELECT, which is why M8 survives. Capturing them early is still the better choice, because it avoids a round trip on a connection that has just deadlocked. Consider rewording the comment to "read before the flush so the except needs no reload".
- Nit: the `TestClient` built in `test_a_non_deadlock_operational_error_is_not_swallowed_as_409` (`test_team.py:459`) is never closed. Use `with TestClient(...) as client:`, or add a `raise_server_exceptions` option to the `new_client` factory so the fixture closes it.
- Nit: `_inject_on_accept` patches the whole `Session` class through `monkeypatch`, so every session in the test is affected, including the setup sessions. That is fine today, because the patch is installed after `_invite`. A short note in the docstring ("install after setup") would stop a future test from placing it earlier.
- T-174 S3 (a docstring note on `_wait_for_lock_waiters` about `TEST_DATABASE_SHARED=1`) was not in scope here and is still open.
