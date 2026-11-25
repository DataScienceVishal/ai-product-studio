# Review: T-105 deploy/rollback `if:` matched in full, APPROVED label (`p/_starter/T-105-nits`)

Reviewer: `reviewer` agent, 2026-11-25. Commit reviewed: `cc29878`, the only commit ahead of main (base
`0f1abbc`, the T-105 claim on main). Diff `main...p/_starter/T-105-nits`: 1 file
(`products/_starter/infra/test-deploy-workflow.sh`), +2/-2. It fixes R1 and R2 from the T-104 re-review.

## Verdict: PASS

## Summary

- **R1 done.** The test now requires the `deploy` and `rollback` `if:` lines to match these two lines exactly
  (`grep -qxF`):
  - `    if: needs.check.outputs.go == 'true' && inputs.rollback_to == ''`
  - `    if: needs.check.outputs.go == 'true' && inputs.rollback_to != ''`

  It also requires exactly 2 job-level `if:` lines that mention `needs.check.outputs.go`. Anything appended to
  either line is caught, and so is an edited or extra line.
- **R2 done.** The env-check label now reads "built from the right secret or variable".
- The change is test-only. Both workflows are byte-identical to main. Nothing new is printed, and the check reads
  only the workflow file.

## Evidence

| Check | Result |
|---|---|
| `bash products/_starter/infra/test-deploy-workflow.sh` | passed: 118, failed: 0, rc 0 |
| `actionlint` on `_starter-deploy.yml` and `azure-spend.yml` | clean, rc 0 |
| `python3 -m unittest discover -s scripts/tests` | Ran 43 tests, OK |

**Mutations.** Each was applied in a detached worktree and reverted with `git checkout`.

| Mutation | Result |
|---|---|
| `\|\| true` appended to the `deploy` `if:` (line 153) | caught: `if:` check |
| `\|\| true` appended to the `rollback` `if:` (line 526) | caught: `if:` check |
| `deploy` `if:` drops the go condition | caught: `if:` check |
| `rollback` `if:` changed to `go != 'true'` | caught: `if:` check |
| Extra copy of the `deploy` `if:` line | caught: `if:` count check (also by actionlint) |

## Critical issues

None.

## Suggestions

None that block. One limitation, noted for completeness: a brand-new job that signs in without referring to
`needs.check.outputs.go` at all would not be caught by these checks. That is a design-level rule ("every job that
signs in must need `check`"), and it is left for review rather than a grep.
