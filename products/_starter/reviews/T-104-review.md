# Review: T-104 deploy half-set fails loudly, deploy gate truth table, comments (`p/_starter/T-104-nits`)

Reviewer: `reviewer` agent, 2026-11-25. Commit reviewed: `ea6cc9a`, the only commit ahead of main.
Diff `main...p/_starter/T-104-nits`: 3 files, +46/-2. This follows up the three suggestions in `T-103-review.md`.

## Verdict: PASS

## Summary

- **S1 (azure-spend.yml header).** Lines 13-14 now say that a client id (spend or deploy) set without tenant and
  subscription fails the run instead of falling through to the next option. This matches lines 59-65.
- **S2 (deploy gate fails loudly).** The `Credentials, approval and branch` step adds `HAS_DEPLOY_ID`
  (`secrets.AZURE_CLIENT_ID != ''`, a boolean only) and a first branch. When the client id is set but tenant or
  subscription is missing, it prints `::error::` with fixed text and exits 1. If tenant and subscription are set
  without a client id, the step still gives the old notice and `go=false`.
- **S3 (tenant_sub comment).** The comment explains why tenant and subscription can share one bit. The env-flag
  greps prove that every flag needs both secrets.
- **New test.** The test greps the exact `HAS_AZURE` and `HAS_DEPLOY_ID` expressions, extracts the gate's run block,
  fails clearly if extraction comes back empty, runs the block under `bash -e`, and checks it against 16 rows
  (deploy_id x tenant_sub x approved x on_main). The oracle is worked out separately from the `if` chain, not
  copied from it.

**Effect on the rest of the deploy workflow.** The gate is in the `check` job. `deploy` (line 152) and `rollback`
(line 525) both have `needs: check` and an `if:` without `always()`. A gate exit 1 therefore fails `check` and
skips both jobs, so nothing touches Azure. Before this change those jobs were skipped too, through `go=false`. The
only difference is that the run now shows red. No other workflow calls this one (no `workflow_call` and no
`workflow_run` references). The fixed-charge steps run before the gate, so they still run.

**Existing setups.** Vishal has all three secrets (DECISIONS 2026-11-24T23:45Z). That is row d=1, t=1, and it
behaves as before. Only one setup changes: client id set with tenant or subscription missing. It used to be a
green notice and is now a red error. That setup can never deploy, so failing is the intended outcome.

**No secret printing.** The new message is a fixed string. `HAS_DEPLOY_ID` contains `true` or `false`, never the
id. The test sends the block's output to /dev/null and feeds it only synthetic flags.

## Evidence

| Check | Result |
|---|---|
| `bash products/_starter/infra/test-deploy-workflow.sh` | passed: 115, failed: 0, rc 0 (112 at T-103, plus 2 env greps and 1 truth table) |
| `python3 -m unittest discover -s scripts/tests` | Ran 43 tests, OK |
| `actionlint` on `_starter-deploy.yml` and `azure-spend.yml` | clean, rc 0 (also run inside the test script) |
| bash | GNU bash 5.2.21 |

**Mutations.** Each was applied in a scratch worktree and reverted with `git checkout`.

| Mutation | Result |
|---|---|
| Half-set branch disabled (`if false`) | caught: 4 rows wrong |
| `exit 1` in the half-set branch replaced by `true` | caught: 4 rows wrong |
| Half-set branch only fires when approved | caught: 2 rows wrong |
| `HAS_DEPLOY_ID` built from `AZURE_TENANT_ID` | caught: env grep |
| Subscription dropped from `HAS_AZURE` | caught: env grep |
| main-branch check removed | caught: 1 row wrong |
| `go=true` always written | caught: 11 rows wrong |
| Step renamed | caught: "could not extract" |
| `[ "$APPROVED" != "yes" ]` changed to `[ "$APPROVED" = "no" ]` | **survives** |
| `APPROVED: ${{ vars.STUDIO_AZURE_APPROVED \|\| 'yes' }}` | **survives** |
| Job output `go: ${{ steps.gate.outputs.go }}` hardwired to `true` | **survives** (existed before T-104) |
| `deploy` / `rollback` `if:` drop `needs.check.outputs.go == 'true'` | **survives** (existed before T-104) |

## Critical issues

None. The workflow change is correct and safe.

## Suggestions (non-blocking; good material for a small follow-up task)

- **S1. The truth table models "not approved" only as `no`.**
  `products/_starter/infra/test-deploy-workflow.sh`, `gate_out`: `APPROVED=$([ "$3" = 1 ] && echo yes || echo no)`.
  If the variable is unset, which is the real default, Actions passes an empty string. A gate that checks
  `= "no"` would then deploy without approval, and the test would still pass. Test the unapproved case with `""`,
  and ideally also `Yes` or `true`, so that only the exact `yes` deploys.
- **S2. Pin the money-safety wiring around the gate.** The tests don't cover four pieces of wiring. Mutating any
  one of them makes the deploy skip approval, and all 115 checks still pass:
  - `APPROVED: ${{ vars.STUDIO_AZURE_APPROVED }}` (line 131). This is a T-104-sized fix: add one more expression to
    the env-grep loop.
  - The job output `go: ${{ steps.gate.outputs.go }}` (line 96).
  - The `if:` lines on `deploy` (line 153) and `rollback` (line 526). Each must still contain
    `needs.check.outputs.go == 'true'`.

  `grep -F` checks like the existing ones would be enough. These gaps existed before T-104; this branch did not
  create them.
- **S3. The README troubleshooting table has no row for the new error.** In `products/_starter/infra/README.md`
  (around line 284), add a row: "AZURE_CLIENT_ID is set but AZURE_TENANT_ID or AZURE_SUBSCRIPTION_ID is missing"
  -> half-set OIDC secrets -> SETUP.md step 3.
- **S4. Wording.** The deploy header says "set without the other two", and azure-spend.yml says "without
  AZURE_TENANT_ID and AZURE_SUBSCRIPTION_ID". The check actually fails when *either* is missing. "without both of"
  or "missing AZURE_TENANT_ID or AZURE_SUBSCRIPTION_ID" would be exact.
