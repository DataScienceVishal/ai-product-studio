# Review: T-102 spend sign-in fails loudly, truth-table test (`p/_starter/T-102-spend-loud`)

Reviewer: `reviewer` agent, 2026-11-25. Commit reviewed: `3bd5098` (diff `main...p/_starter/T-102-spend-loud`,
3 files, +36/-5). Follow-up to suggestions S1-S3 in `T-63-review.md`.

## Summary

- **S1 (done):** `azure-spend.yml` gains `HAS_SPEND_ID` (job env, line 40) and a first branch (lines 57-59) that
  exits 1 with a `::error::` when `AZURE_SPEND_CLIENT_ID` is set but tenant or subscription is missing. So a
  half-set spend identity now fails loudly. Before, it fell back without a word to the deploy identity or the SP.
  The `HAS_SPEND != true` guard on the oidc branch is gone. It was redundant because the spend branch comes
  first, and the test proves that.
- **S2 (done):** `test-deploy-workflow.sh` (lines 196-223) takes the real `run:` block of "Work out the Azure
  sign-in" with awk, runs it under bash for all 32 combinations of spend_id / tenant+sub / deploy_id / cost_sp /
  on_main, and compares the `AZURE_MODE` it writes to `$GITHUB_ENV` (or a non-zero exit) against an
  independently written oracle.
- **S3 (done):** the infra README now says both `query/action` and `query/read` can be dropped once the spend
  identity is live.

The new error message prints only `$GITHUB_REF` and fixed text. No secret value or ID is printed. `HAS_SPEND_ID`
is a boolean expression, so the secret is not copied into env.

## Evidence

| Check | Result |
|---|---|
| `bash products/_starter/infra/test-deploy-workflow.sh` (actionlint 1.7.x on PATH) | passed: 107, failed: 0, rc 0 (actionlint ran and was clean) |
| `python3 -m unittest discover -s scripts/tests` | Ran 43 tests, OK |
| bash used | GNU bash 5.2.21 (same major/minor as ubuntu-latest 24.04) |

**Oracle check (by hand).** I traced the workflow's `if` chain against the test's expected table:
1. a=1, t=0 -> fail (S1 branch). Oracle row 1 matches.
2. a=1, t=1, m=1 -> spend. The oracle's `a=1 && m=1` is reached only when t=1, so it matches.
3. a=0, d=1, t=1, m=1 -> oidc. When a=1 and t=1 on main, spend wins first, so the oracle's `a=0` guard is right.
4. Off main with HAS_SPEND or HAS_OIDC -> fail. Here the oracle's `a=1` means HAS_SPEND, because t=0 was
   already taken by step 1. Matches.
5. Otherwise c=1 -> sp, else none. Matches.

The oracle is correct. It is written in different terms (raw secret presence) from the workflow (derived
HAS_* flags), so it is a real second derivation, not a copy.

**Mutation checks (my own, on a scratch edit of the workflow, then reverted).** Every one failed the suite with rc 1:

| Mutation | Rows wrong |
|---|---|
| Rename the step, so awk extracts an empty script | 32 (every `got` empty) |
| Remove the S1 branch | 8 |
| Drop `else mode=none` | 6 |
| Put the `sp` branch before `oidc` | 4 |
| Break the shell syntax (unterminated `if`) | 18 |
| S1 branch `exit 1` -> `exit 0` | 8 |

The author's own checks are also confirmed: removing S1 gives 8 wrong. An empty extraction does **not** pass
quietly. An empty script exits 0 and writes no `AZURE_MODE`, so `got` is empty on every row and all 32 rows fail.

**awk extraction robustness.** It is anchored on the step name and starts after `run: |`. It stops at the next
step marker at 6-space indent (`^      - name:`) and removes 10 spaces of block indent. If the step were the
last one, extraction would run to end of file. That is harmless here because a later step follows. If the
block's indent changed, sed would leave the lines indented, which bash doesn't care about. Robust enough.

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. Name the empty-extraction failure.** Today a renamed step shows as "32 wrong" plus 32 rows of `got `.
  That is loud but unclear. Add `[ -s "$choose" ] || bad "azure-spend: could not extract the sign-in run block"`
  right after line 198.
- **S2. Run the block the way Actions does.** A `run:` with no `shell:` runs as `bash -e {0}` on ubuntu. The
  test calls plain `bash "$choose"` (line 206). Use `bash -e "$choose"` so `-e`-only behaviour (for example a
  failing `[ ]` outside a conditional) is tested the same way it runs.
- **S3. The job-level env expressions aren't pinned.** The test models `HAS_SPEND`/`HAS_OIDC`/`HAS_SPEND_ID`
  itself (lines 202-205). If someone edits the `${{ }}` expressions at lines 39-41 (for example drops the tenant
  term from `HAS_SPEND`), the truth table still passes. Add `grep -qF` checks for the three expressions.
- **S4. Same silent fallback for the deploy identity.** If `AZURE_CLIENT_ID` is set but tenant or
  subscription is missing, `HAS_OIDC` is false and the run drops quietly to `sp`/`none`. This is the same gap
  as S1, but for a temporary identity that is going away, so it is low priority. It could also be closed by
  failing whenever exactly one of `AZURE_TENANT_ID`/`AZURE_SUBSCRIPTION_ID` is set. The table merges tenant and
  subscription into one variable, so it can't see that case either.
- **S5. Small test nits.** The test doesn't assert `HAS_AZURE` (it could check `HAS_AZURE=false` exactly when the
  mode is `none`). The helper is called `want` but returns the actual value, so `got_mode` fits better. `hs`/`ho`
  leak as globals: add them to the `local` line.

## Verdict

**PASS.** S1-S3 from the T-63 review are done correctly. The truth-table oracle is right, and the test fails
loudly on an empty extraction and on every logic mutation tried. 107/107 workflow checks and 43/43 unit tests
pass. The suggestions above can go into the next touch of this file.
