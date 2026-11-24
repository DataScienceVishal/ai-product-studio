# Review: p/_starter/T-18-sql (8b41dca), ADR 0003 build slice 3

Reviewer, 2026-11-24. Diff: `git diff origin/main...8b41dca` (db-setup.sql, db-grants.sql header, test-db-setup.sh,
_starter-ci.yml backend step, NEXT.md).

## Verdict: CHANGES (2 blocking, 7 non-blocking)

Both blocking items are small. The SQL itself is correct and does what ADR 0003 decision 3 says, steps 1 to 7.

## Summary

- **SQL and injection.** Every identifier goes through `:"var"` or `format('%I')`, every literal through `:'var'` or
  `%L`. The oid regex is anchored and lower-case only. The test's `'... OR 1=1 --'` oid is refused. I generated the
  real (non-stub) `SECURITY LABEL` text by hand with a role name containing `"` and it quoted correctly:
  `SECURITY LABEL FOR "pgaadauth" ON ROLE "We""ird" IS 'aadauth,oid=...,type=service'`. The format matches Learn
  (`aadauth,oid=<oid>,type=service`, no `admin`).
- **Idempotency.** The script runs twice in a row and a second product sets up beside the first. A changed oid re-maps.
- **Passwords.** `PASSWORD NULL` is set on every run for both roles. No other statement sets a password.
- **Tests.** I ran a copy renamed to `_t18v` (including `pgaadauth_stub_t18v`) against local PG16.15 as a non-superuser
  CREATEROLE admin: **passed 28, failed 0**.
- **Mutation results.**
  - Caught: removing the app's `CONNECTION LIMIT 12` (1 fail), removing `SET ROLE` (2 fails), removing
    `REVOKE ... FROM PUBLIC` (3 fails), disabling the other-admin check (1 fail).
  - **Survived** (28/28 still pass): removing `PASSWORD NULL` from either role; the migrator's oid check and its
    `isadmin = 0` check; the app's `isadmin = 0` and `principaltype` checks; dropping `isadmin = 0` from the stub upsert.
- **CI.** `ubuntu-latest` is 24.04, whose runner image ships the PostgreSQL 16 client (`/usr/bin/psql`). That matches
  this sandbox: Ubuntu 24.04 with psql 16.15. With `REQUIRE_PG=1`, a missing psql fails the job loudly instead of
  skipping. The backend job's `postgres:16` service has studio/studio on 5432 and the `working-directory` is
  `products/_starter/backend`, so `bash ../infra/test-db-setup.sh` resolves.

## Blocking

**B1. The test doesn't check the headline property: no role ever has a password.**
`test-db-setup.sh:89-90` asserts `rolpassword IS NULL`, but the roles are always created fresh with no password, so the
check passes even when `PASSWORD NULL` is deleted from `db-setup.sql:53-54` (mutation survived). The point of
`PASSWORD NULL` is to wipe a password that is already there (for example `studioadmin` setting one in phase 1, or a
manual `ALTER ROLE`).

Fix: before the second run, as superuser, run `ALTER ROLE p1_t18s_app PASSWORD 'x'` and
`ALTER ROLE p1_t18s_migrator PASSWORD 'x'`. Then run setup and assert `rolpassword IS NULL` for both.

**B2. `db-setup.sql` only refuses bad input if the caller remembers `-v ON_ERROR_STOP=1`.**
The script has no `ON_ERROR_STOP` of its own. Every guard (`app_oid is not set`, `not a lower-case UUID`, the mismatch
and other-admin checks) is a `RAISE`, and psql carries on past it. I ran it without `ON_ERROR_STOP` and with
`app_oid=bad`: both errors printed, then `CREATE ROLE` ran twice and `ALTER ROLE` ran twice. The deploy step that will
call it (slice 4) isn't written yet, so this is the cheapest moment to make the script safe on its own.

Fix: put `\set ON_ERROR_STOP on` as the first line after the header comment in `db-setup.sql`. It costs nothing when
the caller already passes it.

## Non-blocking

1. **Mismatch checks are only half tested** (`db-setup.sql:70-75`). Only the app's oid mismatch is exercised. Add
   skew triggers for: the migrator's oid, `isadmin = 1` on a product role, and `principaltype = 'user'`. Each of those
   mutations survives today.
2. **Cleanup scope.**
   - The header (`test-db-setup.sh:8-9`) says the test only touches objects ending in `_t18s`, but it creates and
     `DROP SCHEMA ... CASCADE`s `pgaadauth_stub`, which is unsuffixed.
   - The fixed names mean two runs at once against one server destroy each other's fixture. CI is safe (one container
     per job); it matters for shared local servers like this one.
   - Fix: rename the schema to `pgaadauth_stub_t18s`, or correct the comment.
   - Otherwise cleanup is tightly scoped: two databases and five named roles. `rogue_t18s` and `t_t18s` go with the
     schema and the database.
3. **Fixture errors go unchecked.** The script uses `set -uo pipefail` without `-e`, and the fixture heredoc's exit
   status (`test-db-setup.sh:64-81`) is never checked. Only `rolsuper` is. A half-built fixture would show up as
   confusing failures further down. Add `|| { echo FIXTURE; exit 1; }`.
4. **What only Azure can verify** (the stub cannot show any of these; add them to the first-deploy checklist):
   - (a) An Entra admin is allowed to run `SECURITY LABEL FOR "pgaadauth"`. The real branch is never executed in CI; I
     only checked the generated text.
   - (b) `GRANT <role> TO CURRENT_USER WITH INHERIT FALSE, SET TRUE` is permitted for `azure_pg_admin` members. It is
     proven locally for a plain CREATEROLE user.
   - (c) The column casing from `pgaadauth_list_principals`, and that `principalType` is exactly `service` for a
     managed identity (N4).
   - (d) `pgaadauth_list_principals(true)` lists the deploy SP under the name `current_user` returns, and lists no
     non-Entra or system roles. Otherwise the other-admin check fails every release.
   - (e) A new label replaces the old mapping rather than adding to it.
   - (f) The unqualified call resolves to Azure's function.
   - The stub does match the documented signature and the `false`/`true` semantics.
5. **PG16 ADMIN OPTION on roles that already exist.** `ALTER ROLE`, `SECURITY LABEL` and `GRANT ... TO CURRENT_USER`
   need ADMIN OPTION. The admin gets it only on roles it created itself. Nothing exists in Azure yet (BUDGET.md says
   "planned"), so this is moot today. After a recreated deploy SP (ADR failure mode N2), though, every product's
   roles would fail here. Add it to that runbook row (`GRANT <role> TO <new admin> WITH ADMIN OPTION` from the old
   admin).
6. **Merge order: agree, keep this on the branch until slice 4.** On main, `_starter-deploy.yml:~290-296` calls
   `db-setup.sql` with verifier env vars and no `app_oid`/`migrator_oid`, so it would stop at `app_oid is not set`.
   The separate psql call to `db-grants.sql` as `<db>_migrator` with a password would also fail now that roles have
   `PASSWORD NULL`. Nothing is deployed, so the breakage would be latent, not live. Still, main should never hold a
   deploy that can't succeed. Merge slices 3 and 4 together, or rebase 3 into 4's PR, after reviewer PASS on both.
   NEXT.md already lists what slice 4 must pass.
7. **The admin has no `pg_catalog`-first guarantee in CI.** The stub works through `ALTER ROLE ... SET search_path`,
   which is fine. The comment at `db-setup.sql:17-20` could say the stub relies on `search_path`, so nobody later
   schema-qualifies the call and breaks CI.

## Evidence

- Test run (renamed `_t18v` copy): `passed: 28  failed: 0`.
- Mutation one-liners and outputs: see Summary. Afterwards no `_t18v` roles or schemas were left on the local server.

## Re-check (6dd1d34, 2026-11-24): PASS

I ran a copy renamed to `_t18v` against local PG16: **passed 33, failed 0**. Afterwards no `_t18v` roles or schemas
were left on the server.

- **B1 fixed.** The test now gives both roles a password after the first run, checks it took, and asserts the re-run
  wipes it. Removing `PASSWORD NULL` from the migrator, or from the app, now fails `rolpassword IS NULL` (1 fail each).
- **B2 fixed.** `\set ON_ERROR_STOP on` is now in the script. Run without the flag and with `app_oid=bad`, it stops at
  `app_oid is not a lower-case UUID` and creates no roles (0 `zz_t18v` roles). The test harness passes the flag
  itself, so this line is checked by hand, not by the test. Acceptable.
- **Item 1 fixed.** There are now six skew cases: objectid, isadmin and principaltype, each for both app and migrator.
  Removing any of the six checks fails exactly 1 test: migrator oid, migrator isadmin, app isadmin, app type,
  migrator type, and app oid (the existing case).
- **Item 2 fixed.** The stub schema is now `pgaadauth_stub_t18s`, passed in as `-v entra_stub=<schema>` and used as
  `:"entra_stub".principals`, which is quoted as an identifier. db-setup.sql has no hard-coded suffix. The header
  comments now say the stub works through `search_path` and that calls must stay unqualified.
- **Item 3 fixed.** The fixture heredoc's exit status is checked.
- **Still open, non-blocking:** item 4 (Azure-only checks, record them at the first deploy) and item 5 (ADMIN OPTION
  runbook line).
- **Merge:** item 6 stands. This stays on the branch and merges together with slice 4.
