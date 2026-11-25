# Review: T-103 spend sign-in test hardening and loud deploy half-set (`p/_starter/T-103-spend-test`)

Reviewer: `reviewer` agent, 2026-11-25. Commit reviewed: `4b6f5eb`, the branch tip and the only commit ahead of
main. The brief named `66a9b31`, but that object does not exist in the repo, so I reviewed the actual tip.
Diff `main...p/_starter/T-103-spend-test`: 2 files, +44/-24. Follow-up to the suggestions in `T-102-review.md`.

## Summary

All five T-102 suggestions are done:

1. **Env flags checked.** `test-deploy-workflow.sh` greps the exact job-level expressions for `HAS_SPEND`,
   `HAS_SPEND_ID`, `HAS_OIDC`, `HAS_DEPLOY_ID` and `HAS_COST_SP`. It matches the 6-space indent and uses
   `grep -F`, so the truth table's assumption about how the flags are built is now enforced.
2. **Empty extraction fails clearly.** If the extracted block is empty or has no `AZURE_MODE=`, the test fails
   with "could not extract the 'Work out the Azure sign-in' run block" and skips the table.
3. **Runs like Actions.** The block runs under `bash -e`, the shell Actions uses for a bare `run:` step on
   ubuntu.
4. **Deploy half-set fails loudly.** `azure-spend.yml` adds `HAS_DEPLOY_ID` (line 42) and a second branch
   (lines 61-63). If `AZURE_CLIENT_ID` is set without tenant or subscription, the step exits 1 with a
   `::error::`. It no longer quietly falls through to `sp` or `none`.
5. **Nits.** The test now asserts `HAS_AZURE`: `got` carries a `,azure` suffix, and the `none` rows expect no
   suffix. `want` is renamed `got_mode`, and its variables are local.

**No secret printing.** The new error message is fixed text. `HAS_DEPLOY_ID` is a boolean expression, so the
client ID never enters env. The test sends the script's output to /dev/null and feeds it only synthetic
true/false flags.

**Existing setups.** Vishal's setup is unchanged. He has `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and
`AZURE_SUBSCRIPTION_ID` set (DECISIONS 2026-11-24T23:45Z). That is row d=1, t=1, and it gives `oidc` on main and
the "re-run from main" error off main, exactly as before. Only one previously green combination changes:
`AZURE_CLIENT_ID` set, tenant or subscription missing, and `AZURE_COST_CREDENTIALS` set. It used to give `sp` and
now fails. No one has that setup today. It is also a broken deploy configuration, because `_starter-deploy.yml`
needs all three secrets. Failing loudly is the intended behaviour.

## Evidence

| Check | Result |
|---|---|
| `bash products/_starter/infra/test-deploy-workflow.sh` (actionlint from scratchpad `al/` on PATH) | passed: 112, failed: 0, rc 0, actionlint clean (was 107 at T-102: +5 env-flag checks) |
| `python3 -m unittest discover -s scripts/tests` | Ran 43 tests, OK |
| bash | GNU bash 5.2.21 (same as ubuntu-latest 24.04) |

**Oracle check (by hand, all 32 rows).** a=spend_id, t=tenant+sub, d=deploy_id, c=cost_sp, m=on_main.

| Rows | Workflow path | Oracle | Count |
|---|---|---|---|
| a=1, t=0 (any d, c, m) | branch 1 (spend half-set) -> exit 1 | `(a or d) and !t` -> fail | 8 |
| a=0, d=1, t=0 | branch 2 (deploy half-set) -> exit 1 | same clause -> fail | 4 |
| a=1, t=1, m=1 | spend | `spend,azure` | 4 |
| a=0, d=1, t=1, m=1 | oidc | `oidc,azure` (a=1, m=1 already taken) | 2 |
| (a or d), t=1, m=0 | off-main error -> exit 1 | fail | 6 |
| a=0, d=0, c=1 | sp | `sp,azure` | 4 |
| a=0, d=0, c=0 | none, HAS_AZURE=false | `none` | 4 |

That is 32 rows. **Both IDs set with the tenant missing** (a=1, d=1, t=0) fails through branch 1 with the spend
message, and the oracle expects fail. Correct. The oracle is still an independent derivation from raw secret
presence, not a copy of the `if` chain.

**Mutation checks (mine, on the worktree copy of the workflow, each reverted with `git checkout`).** Every one
gave rc 1:

| Mutation | Result |
|---|---|
| Remove the deploy half-set branch | truth table, 4 wrong |
| Build `HAS_DEPLOY_ID` from `AZURE_SPEND_CLIENT_ID` | env check `HAS_DEPLOY_ID` fails |
| Drop `AZURE_CLIENT_ID` from `HAS_OIDC` | env check `HAS_OIDC` fails |
| Insert `false` before the `AZURE_MODE` write (catches the `bash -e` change) | 14 wrong (every non-fail row) |
| `HAS_AZURE` always true | 4 wrong (the `none` rows) |
| Rename the step | "could not extract" |
| Skip the deploy half-set branch when `HAS_COST_SP` is true | 2 wrong |

These confirm the author's four reported mutations and add three more.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. The header comment is out of date.** `azure-spend.yml` lines 6-13 describe the order spend > oidc > sp but
  don't say that a client ID set without tenant or subscription now fails the run. Add one line so the
  behaviour is visible without reading the shell.
- **S2. The two workflows now treat a half-set deploy identity differently.** `_starter-deploy.yml` line 128-133
  skips the deploy with a `::notice::` when the three deploy secrets aren't all set. `azure-spend.yml` now fails
  loudly. The deploy skip is reasonable for a fresh setup with no secrets at all, but a half-set
  `AZURE_CLIENT_ID` there is the same misconfiguration. Consider the same loud check in the deploy workflow,
  or note in a decision why they differ.
- **S3. Tenant and subscription are always tested together.** The table uses one `tenant_sub` bit. That is fine,
  because the env-flag grep now proves each flag needs both secrets. Note it in the test's comment so a future
  reader doesn't think the tenant-only case is untested.

## Verdict

**PASS.** The logic is correct and the 32-row oracle is right, including the case with both IDs set and the
tenant missing. The test now catches regressions in the flag expressions, the extraction, the `-e` shell and
`HAS_AZURE`. Vishal's working configuration is unaffected, and no secret is printed.
