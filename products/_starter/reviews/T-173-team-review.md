# Review: p/_starter/T-173-team (commit 6490473)

Reviewer: reviewer agent, 2026-11-27. Scope: `git diff origin/main...6490473`. The diff changes `backend/app/routes/team.py` (+14/-4), `backend/app/models.py` (index on `Invitation.email`), the new migration `migrations/versions/20261127_0009_invitations_email_index.py`, `backend/tests/test_team.py` (+84) and `NEXT.md`. It addresses the Races and Suggestions sections of `reviews/T-172-team-review.md`.

## Verdict: PASS

The per-tenant `FOR NO KEY UPDATE` lock in `invite` and the `FOR UPDATE` read in `accept` are both correct, and both are needed. The lock mode was chosen correctly: I showed that a plain `FOR UPDATE` deadlocks (evidence below). The migration is sound and the email lower-casing invariant holds on every write path. I found no must-fix issues. One race test is vacuous, and one pre-existing deadlock is still open. Both are listed under Suggestions.

## Evidence

- Full backend suite on the branch tree (6490473, local Postgres 16, `python -m pytest -q -o addopts=`): **762 passed, 1 skipped, 1 warning in 108.37s**.
- Mutation check. Each mutant was applied to a scratch copy of `backend/`, then `tests/test_team.py` was run. The worktree was not modified.

| # | Mutant | Result |
|---|---|---|
| M1 | drop the tenant lock in `invite` (`team.py:74`) | **killed** by `test_invites_for_one_tenant_are_serialised` |
| M1b | same mutant, `test_concurrent_resends_leave_one_live_link` only, run 5 times | **survived 5/5** (the test is vacuous, see S1) |
| M2 | drop `.with_for_update()` in `accept` (`team.py:148-149`) | **killed** by `test_accept_waits_for_a_concurrent_revoke_and_then_fails` |
| M3 | tenant lock as plain `FOR UPDATE` instead of `key_share=True` | **survived** the committed tests. My probe (below) shows that it deadlocks. |
| M4 | B7 back to `func.lower(Invitation.email) == ...` | survived (equivalent behaviour; only the plan changes) |

- Probe P1: accept is in flight and a resend of the same address arrives. A side connection holds the users unique-index slot, accept takes the invitation lock and waits on it, then the resend takes the tenant lock and waits on the invitation. With the branch as written: accept 201, resend 201, no deadlock. With M3: **`DeadlockDetected` (40P01), and one request returns 500**. This confirms the comment at `team.py:71-73`: `key_share=True` is load-bearing.
- Probe P2: one person accepts invites from two tenants at once. Both accepts lock their own invitation row and then queue on the users unique index. **Result: 201 and 500 (`DeadlockDetected`)**, the same on 3 of 3 runs. With M2 (main's behaviour) the result is the same 201/500, so this is **pre-existing and not introduced by this branch**. Data stays consistent: one account, and the other invite is revoked by the winner's B7 update. See S2.

## Checks requested

- **Lock ordering and deadlocks.** `invite` locks in this order: tenant (NO KEY UPDATE), then this tenant's invitation rows (resend UPDATE), then the new insert (KEY SHARE on the tenant, which it already holds, and on `users`). `accept` locks its invitation (FOR UPDATE), then inserts the user (KEY SHARE on the tenant, compatible with NO KEY UPDATE), then the B7 UPDATE on other tenants' pending rows. `revoke` takes one invitation row lock by primary key and nothing else. No invite/resend/revoke/accept pair forms a cycle. The only cycle I found is accept/accept across tenants for one address (P2, pre-existing).
- **Accept re-checks pending after the lock.** It does. The `_pending(now)` predicate sits in the same `SELECT ... FOR UPDATE`, so under READ COMMITTED Postgres re-evaluates it on the updated row version once the lock is granted. A row that was revoked or replaced in the meantime drops out, and accept returns `invalid_invitation`. M2 shows the test depends on this.
- **Lower-case emails on every write path.** `Invitation.email` is written in one place only, `team.py:93`, from `InviteIn.email: Email`. `_email` in `routes/auth.py:30-37` calls `.strip().lower()`. `User.email` is written at `auth.py:161` (signup, also from `Email`) and at `team.py:152` (copied from the invitation). No other writers exist (grep for `Invitation(`, `.email =` and `email=` under `app/`). Every invitation row has gone through `Email` since migration 0002, so no backfill is needed. Plain equality is safe.
- **Migration 0009.** `op.f('ix_invitations_email')` matches the model's `index=True` name. The downgrade drops the same index. `tests/test_migrations.py::test_pending_usage_partial_index_upgrades_and_downgrades` upgrades to head (which includes 0009), runs `command.check` (the models and migrations agree), and downgrades to base. It passes in the run above. The plain `CREATE INDEX` blocks writes to `invitations` for its duration, which is fine for a small table.
- **Do the race tests fail without the fix?** `test_invites_for_one_tenant_are_serialised` and `test_accept_waits_for_a_concurrent_revoke_and_then_fails` both fail without the fix (M1, M2). `test_concurrent_resends_leave_one_live_link` does not (S1).

## Critical issues

None.

## Suggestions

- **S1. `test_concurrent_resends_leave_one_live_link` (`tests/test_team.py`, the second new race test) does not test the race.** It passed 5 of 5 times with the tenant lock removed: the two TestClient requests never overlap inside the check-then-insert window. Either delete it (the serialisation test already guards the lock) or make it deterministic. For example, hold the tenant `FOR NO KEY UPDATE` in a side connection, start both resends, wait until `pg_stat_activity` shows 2 lock waiters, then release.
- **S2. Pre-existing: concurrent accepts of one address from two tenants deadlock, and the loser gets a 500** (P2). `accept` catches only `IntegrityError` at `team.py:156-160`. The narrowest fix: also catch `OperationalError` with `sqlstate == '40P01'` around the flush and the B7 update, roll back, and return 409 `email_taken`. The winner has created the account by then, so that is the true answer. Another option is to take the locks in a fixed order (for example, lock all pending invitations for the address `ORDER BY id FOR UPDATE` before the insert). This is rare (one person, two links, the same second), and nothing is corrupted.
- **S3. Guard `key_share=True` with a test.** M3 survives the committed suite. Probe P1 is a deterministic regression test for it: a side transaction inserts the user row uncommitted, the test waits for lock waiters through `pg_stat_activity`, then rolls back, and asserts both requests return 201. Someone "simplifying" to `with_for_update()` would then be caught.
- **S4. Replace `time.sleep(0.7)` with polling for a lock waiter** in the two new race tests. `accept` runs a real argon2 hash before its SELECT. On a slow CI runner that can take longer than 0.7 s, and then the side commits the revoke first and the test passes without exercising the lock (a false pass, not a flake). Polling `pg_stat_activity WHERE wait_event_type = 'Lock'` until it shows one waiter makes the tests truly deterministic.
- **S5. Known residual, unchanged:** a resend (or another tenant's invite) that runs while an accept is in flight still creates a pending invite for an address that now has an account. P1 ends with both requests returning 201. This is the "acceptable residual" from the T-172 review. Note that the tenant lock does not close it, because `accept` never conflicts with it. A sweep, or filtering `GET /api/team` invitations against `users`, would close it.
- Nits: the `test_invites_for_one_tenant_are_serialised` docstring's first line is about 190 characters and has a doubled parenthetical. The race-test imports sit mid-file with `noqa: E402`, and could move to the top. `test_invitation_email_is_indexed` checks the `create_all` schema, so it tests the model and not the migration. The migration is covered by `command.check` in `test_migrations.py`, so this is fine, but the name could say so.
