# Review: p/_starter/T-172-team (commit cdfd38b)

Reviewer: reviewer agent, 2026-11-27. Scope: `git diff origin/main...cdfd38b`, which touches `backend/app/routes/team.py` (+12/-2) and `backend/tests/test_team.py` (+30). It fixes bugs B6 and B7 from `reviews/T-172-bughunt.md`.

## Verdict: CHANGES

Both code changes are correct and do what the bug report asks. The suite is green. Two of the behaviours the task promises can regress without any test failing (mutation evidence below), and one of those is a tenant-isolation guard. Fixing this needs two small tests and no product code changes.

## Evidence

- Full backend suite in a worktree at cdfd38b on local Postgres 16: **737 passed, 1 skipped** (111.8 s).
- Mutation check. Each mutant was applied to `app/routes/team.py`, then `tests/test_team.py` and `tests/test_hardening.py` were run, then the file was restored (the worktree was clean afterwards).

| # | Mutant | Result |
|---|---|---|
| M1 | drop `and not is_resend` (B6 exemption) | killed |
| M2 | skip the B7 revoke UPDATE | killed |
| M3 | scope the B7 revoke to the accepting tenant only | killed |
| M7 | resend no longer revokes the old invite | killed |
| M5 | B7 uses `Invitation.email ==` instead of `func.lower(...)` | survived (equivalent: emails are stored lower-case by `_email`) |
| M4 | B7 UPDATE without `*_pending(now)` | survived |
| **M6** | daily quota ignores revoked rows (so resends stop counting) | **survived** |
| **M8** | `is_resend` lookup drops `Invitation.tenant_id == me.tenant.id` | **survived** |

## Critical issues (must fix)

1. **No test protects "daily quota still counts resends".** `app/routes/team.py:70-73` with the comment at `:74`. The task explicitly asks for this behaviour, and the new comment claims it is deliberate, but M6 survives. `test_invitation_caps` (`tests/test_hardening.py:497`) only uses distinct addresses. If someone later "fixes" the quota to skip revoked rows, an owner could send unlimited emails to one address. Fix: add a test that sets `invites_per_day=3`, invites a@ three times (201, 201, 201), then asserts the fourth send (to a@ or b@) returns 429.
2. **No test protects the tenant scope of `is_resend`.** `app/routes/team.py:78-79`. If the tenant filter is dropped (M8), tenant A at its pending cap can bypass the cap by inviting any address that tenant B has pending. A's revoke at `:84` is tenant-scoped, so nothing is replaced and A's pending count grows past the cap. Fix: add a test where tenant A is at `max_pending_invites=1`, tenant B has a pending invite for x@, A invites x@ and gets 409 `too_many_pending`, and B's invite is still listed and still acceptable.

## Correctness notes (checked, fine)

- B6: `is_resend` uses the same `_pending(now)` predicate and tenant filter as the revoke at `:84`, so "is a resend" and "will replace one" agree. The quota check runs first and is unchanged. A resend to an address that already has an account still gets `email_taken` from `:82`. The address is normalised by `_email`, so `A@acme.test` counts as a resend (the test covers this).
- B7: the revoke runs after `db.flush()` succeeds. If the insert fails, the IntegrityError path rolls back and nothing is revoked. The revoke commits atomically with the user, the accepted mark and the session. `Invitation.id != invitation.id` is redundant, because the row is already flushed as accepted and so no longer pending, but it is harmless.
- Tenant isolation: the B7 UPDATE is deliberately cross-tenant. It only touches pending rows whose email equals the address whose inbox the accepter just proved. It only sets `revoked_at` and returns nothing. Tenant B seeing the invite disappear reveals no more than the invite-time `email_taken` signal does already (an accepted risk in the bug hunt).

## Races (none introduced by this diff; all pre-existing, all low)

- **Two concurrent resends of the same address.** Both see `is_resend=True`. Both UPDATEs target the old row: the second blocks, then re-checks and skips it. Both INSERT. The result is two live links for one address and pending at cap+1. The revoke-then-insert race already existed before this diff.
- **Accept racing a resend or a manual revoke.** `accept` reads the invitation without a lock (`:140`), and the ORM sets `accepted_at` by primary key only. If a resend revokes the old row between the read and the flush, the old link still creates the account. The B7 UPDATE then revokes the new link, so the end state stays consistent: one member, no dangling pending invite. It is still worth closing: use `.with_for_update()` on the `:140` select, or a conditional `UPDATE ... WHERE accepted_at IS NULL AND revoked_at IS NULL RETURNING`.
- **Another tenant invites while an accept is in flight.** That tenant's `User` check sees no user yet, and its insert lands after the B7 UPDATE, so a dead pending invite can still appear in a narrow window. Resending to the same tenant while an accept is in flight behaves the same way. Acceptable residual. A periodic sweep, or filtering out addresses with an account in `GET /api/team`, would close it.
- Serialising invites per tenant would fix the first and last cases: `SELECT ... FROM tenants WHERE id = :t FOR UPDATE` at the top of `invite`.

## Suggestions

- **Performance:** the B7 UPDATE filters on `func.lower(Invitation.email)`, and `invitations.email` has no index (migration `20261123_0002` only indexes `tenant_id`). Every accept therefore seq-scans the whole invitations table across all tenants. Emails are already lower-case, so use plain `Invitation.email == invitation.email` and add an index on `invitations(email)` in a migration. Small now, linear in table size later.
- Assert in the B7 test that an already-revoked or expired invite in another tenant keeps its original `revoked_at`. This kills M4, which would otherwise silently rewrite audit timestamps.
- Move the B7 comment (`team.py:147-148`) down to the UPDATE it describes. It currently sits above the `try/flush`.
- The B6 test could also assert the daily-quota side (see issue 1) to keep both halves of the B6 contract in one place.
