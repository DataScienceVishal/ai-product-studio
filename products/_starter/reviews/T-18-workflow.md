# Review: T-18 slice 4, deploy workflow for passwordless Postgres (ADR 0003 decision 4)

- Branch: `p/_starter/T-18-sql`, reviewed at `c123254` (slice 4). `4c00a03` is the merge of the already-reviewed
  Bicep slices 1-2 (`reviews/T-18-bicep*.md`, PASS); slice 3 `db-setup.sql` has PASS in `reviews/T-18-sql.md`.
- Diff: `git diff origin/main...origin/p/_starter/T-18-sql`, focus on `git show c123254`.
- Reviewer: reviewer agent, 2026-11-24.

## Verdict: PASS

The workflow matches ADR 0003 decision 4: the database step now runs on every release, after the `main.bicep`
deploy (which produces the identity object ids) and before the migration job; it reads its own oid from the
token, refuses when any other Entra admin is listed, reads the role name back from `principalName`, and runs
`db-setup.sql` with `ON_ERROR_STOP=1` and all five psql variables. The token reaches psql only through
`PGPASSWORD`, is empty-checked before `::add-mask::`, and is never an argument. The phase 1 admin password is
generated, masked and used inside the `deploy_shared` step only. URLs carry no password and the host comes only
from `PG_SERVER`. The seed, verifier and `setup_database` paths are gone from all code and CI. No blocking items.
S1 should be fixed before or with the first real deploy because the test suite says the opposite of what the
code does.

## What was checked

| Area | Result |
|---|---|
| Step order vs ADR | Deploy main.bicep (writes `APP_OID`, `MIGRATOR_OID`) -> database step -> firewall cleanup (`always()`) -> migration. Matches decision 4. Test asserts the order by line number. |
| Entra admin check | `.name` of each `administrators` child (the object id) compared lower-cased with the token's oid via `jq --arg` (no injection). Any other entry: stop, with the ARM fix in README. Missing own entry or odd name: stop, "run deploy_shared". Missing `.value` makes jq fail, and `-eo pipefail` (workflow `defaults.run.shell: bash`) stops the step. |
| psql invocation | `-X -w -U "$admin" -d postgres -v ON_ERROR_STOP=1 -v db migrator app app_oid migrator_oid -f "$PRODUCT_DIR/infra/db-setup.sql"`. `\ir db-grants.sql` resolves relative to db-setup.sql, both in `infra/`; the separate migrator psql call is gone. `db-setup.sql` also sets `ON_ERROR_STOP on` itself. |
| oid validation | Lower-cased, then matched against an anchored UUID regex in the shell; `jq -r` on a missing output gives `null`, which fails the regex. Re-checked in SQL (slice 3). |
| Token handling | Initial token: empty check, then mask, then piped (stdin) to jwt-oid.sh, then `unset`. Per-attempt token in `run_psql`: `local`, empty check, mask, `PGPASSWORD="$t" psql`. No `set -x` anywhere. Inside `if run_psql`, errexit is off, so an az failure lands in the explicit empty check. See S1 for the mask in the retry loop. |
| Phase 1 admin password | `openssl rand -base64 32` + `Aa1!` (3 of 4 classes, N10), masked before the deployment, exported only in that step, read by `shared.bicepparam` `readEnvironmentVariable`. Not in `GITHUB_ENV`/`GITHUB_OUTPUT`/a file/an argument (grep plus test). |
| Shell injection / quoting | All expansions quoted; `DB_NAME`, `PRODUCT_DIR`, `PG_SERVER` are workflow env constants; `$admin` checked against `^[A-Za-z0-9_.@-]{1,63}$` before use; `$other` comes from ARM and is only echoed. |
| Password deploys when DB_AUTH unset | `main.bicepparam`: `readEnvironmentVariable('DB_AUTH', 'password')`, so `az bicep build-params` in the check job and any manual deploy keep the pre-T-18 template. Only the deploy step exports `DB_AUTH=entra`. The backend's `config.py` default is also `password`. |
| Dangling references | `grep -rnE "STUDIO_DB_SEED|scram_verifier|VERIFIER|setup_database|entra_stub|SETUP_DATABASE|PG_(APP|MIGRATOR)_PASSWORD"`: none in workflows, infra scripts (apart from the intended CI-only `entra_stub` in db-setup.sql/test-db-setup.sh and the negative checks in test-deploy-workflow.sh), README or backend. Remaining hits are docs scheduled for slice 5 (ADR 0002, ADR 0003 history) and state/SECURITY files (S4). |
| jwt-oid.sh | Strips CR/LF/space, takes field 2, maps base64url to base64, pads for residues 2 and 3, rejects residue 1, `jq -e .oid` fails on missing/non-object payloads; errors never print the token or payload. A dot-less input yields the whole string, which then fails decode or jq: still exit 1 and empty stdout. Non-UUID oids (numbers, etc.) are caught by the workflow regex. |
| README runbook | Setup steps 3, 4, 6 and the "making a product" step updated; new "Database sign-in" section (NOLOGIN cut-off, identity replacement order, recreated deploy principal with `WITH ADMIN OPTION`), first-deploy checklist with the five Azure-only unknowns, troubleshooting rows for each new error text. Accurate against the workflow. |

## Blocking

None.

## Suggestions (non-blocking)

- **S1. The mask inside the retry loop is a no-op.** `.github/workflows/_starter-deploy.yml:320` and `:324`:
  `run_psql` prints `::add-mask::$t` to stdout, but the loop calls `run_psql -tAc 'select 1' > /dev/null 2> ...`,
  so the workflow command goes to `/dev/null` and the runner never sees it. Only the final `run_psql -f
  db-setup.sql` call (stdout not redirected) registers its mask. Today there is no echo path for `$t` (psql never
  prints the password, and az usually returns the same cached token that line 286 already masked), so nothing
  leaks. But the ADR contract ("masked before any possible echo") doesn't hold, and the test "token is masked"
  passes anyway, which hides the gap. Fix: in the step, `exec 3>&1` before defining `run_psql` and
  `echo "::add-mask::$t" >&3` inside it, or fetch and mask the token outside the redirected call. Add a test that
  the mask line writes to a descriptor that isn't redirected (for example grep for `>&3`).
- **S2. First release: readiness probe vs the new order.** The web container's Readiness probe is `/healthz`,
  which checks the database (`main.bicep:472`). On a first release the roles don't exist until after the
  deploy step, so the only revision can't become ready. With `minReplicas: 0` the ARM deployment probably
  completes anyway, but if Container Apps waits for a ready replica the deploy step fails ("Operation expired")
  before the database step can run, and every retry hits the same wall. ADR 0003 assumed the "first minute
  answers errors" case only. Add this to the README first-deploy checklist ("the deploy step finishes on a first
  release while `/healthz` is down") with the fallback: run once with a temporary `/livez` readiness path, or run
  the database step on `FIRST_RELEASE` after a deploy that skips the revision wait.
- **S3. Firewall cleanup now runs on every failure, including before Azure sign-in.** `if: always()` at
  `:349` means a Trivy or build failure also runs `az ... firewall-rule delete` without a login, and the
  resulting error is neither "not found" nor `ResourceNotFound`, so it prints the "remove it by hand" warning for
  a rule that never existed. Give the database step an `id` and use
  `if: always() && steps.<id>.outcome != 'skipped'`.
- **S4. Stale docs outside slice 4.** ADR 0002 (lines 142, 166, 188, 211-213, 251, 417, 453, 466) still
  describes the seed; slice 5 adds the pointer line, so make sure it also covers the failure-mode row at 453.
  `SECURITY.md:1049` cites `${PG_APP_PASSWORD}`, and `state/QUESTIONS.md:52` and `state/DECISIONS.md:88` list
  `STUDIO_DB_SEED` among Vishal's one-time setup steps: the Studio Lead should note in state that the secret is
  no longer needed (decisions are append-only, so add a new line rather than editing 88).
- **S5. Test gaps in `infra/test-deploy-workflow.sh`.** These are text checks, which is fine for a workflow,
  but some are looser than their names suggest. "firewall rule is removed even when a step fails" matches
  any `if: always()` in the file, not the cleanup step specifically. "no set -x" misses `set -o xtrace`. "token is
  masked" doesn't see the S1 redirection. Nothing checks that the per-attempt token is fetched inside the loop.
  actionlint and shellcheck (named in ADR 0003 slice 4) weren't run here because they aren't installed. CI
  should install them, or the NEXT.md note should stay explicit that they haven't run.
- **S6. `principalName` charset.** The `^[A-Za-z0-9_.@-]{1,63}$` guard is right for the default
  `sp-ai-studio-deployer`, but an operator who sets `postgresEntraAdminName` to a display name with a space will
  get "not an Entra admin ... (or its name is odd)", which doesn't say what's wrong. Split that message
  into two (missing vs disallowed characters), or document the allowed charset next to the param.

## Evidence (run on the worktree at c123254)

```
$ git -C /tmp/claude-0/wt-t18 log --oneline -1
c123254 _starter: T-18 slice 4 deploy workflow (Entra admin db step, passwordless URLs, seed and scram removed)

$ bash products/_starter/infra/test-deploy-workflow.sh | tail -2
skip actionlint (not installed)
passed: 62  failed: 0

$ for f in products/_starter/infra/*.sh; do bash -n "$f"; done   # all 8 scripts: ok

$ psql --version
psql (PostgreSQL) 16.15
$ REQUIRE_PG=1 bash products/_starter/infra/test-db-setup.sh | tail -1
passed: 33  failed: 0

$ cd products/_starter/backend && .venv/bin/python -m pytest -q
391 passed, 1 skipped (exit 0; pyproject addopts "-q" plus -q suppresses the summary line,
counted from the progress dots: 391 ".", 1 "s", 0 "F"/"E")
```
