# Review: T-18 slice 5 (ADR 0002 seed text superseded, live-doc grep check)

- Branch: `p/_starter/T-18-slice5` at 847ef03, diff `git diff origin/main...HEAD` (2 files, +20/-10)
- Scope: ADR 0003 section 6 row 5. ADR 0002 marked superseded in part without rewriting history; a grep check
  in `infra/test-deploy-workflow.sh` that no live doc, workflow or script mentions `STUDIO_DB_SEED`.
- Reviewer: reviewer agent, 2026-11-24

## Verdict: CHANGES

The grep check works and the live docs are clean. ADR 0002's banner says every passage about derived role
passwords is marked, and that isn't true yet: the SCRAM-verifier passage still describes a deleted file as
how things work today. Two of the markers also don't show up on GitHub. The fixes are small and docs-only.

## Evidence

- `bash products/_starter/infra/test-deploy-workflow.sh`: `passed: 66  failed: 0`, exit 0 (actionlint
  skipped, not installed).
- Mutation proof: I appended `Set STUDIO_DB_SEED in GitHub.` to `products/_starter/README.md` and
  `STUDIO_DB_SEED` to `products/_starter/infra/README.md`. Result: `FAIL STUDIO_DB_SEED still in: .../README.md`
  (both paths listed), `passed: 65  failed: 1`, exit 1. Reverted with `git checkout`; `git status` was clean afterwards.
- Second mutation: a file `products/_starter/backend/reviews_helper.md` was caught (a filename that only
  contains "reviews" isn't excluded). `.github/x/NEXT.md` was not caught, because any file named `NEXT.md`
  anywhere is excluded (see S1). Both removed afterwards.
- Repo-wide grep for `STUDIO_DB_SEED|setup_database`, leaving out ADR 0002 and reviews: the only hits are ADR 0003 (design
  history), `products/_starter/NEXT.md` (history), the test script itself, and `state/` logs. None of them is a live
  instruction.
- Live docs checked by hand for `seed|derived|scram|HMAC|setup_database`: `products/_starter/README.md`,
  `products/_starter/infra/README.md`, `products/_starter/SECURITY.md`, `products/_starter/DATA.md` and
  `.github/` (dependabot.yml, three workflows) have no seed instructions. SECURITY.md's "seed" hits are about test
  data. `infra/README.md` has the "Database sign-in (Entra, ADR 0003)" section that the banner points to (line 122).

## Critical issues

### C1. The ADR 0002 SCRAM-verifier passage and condition 5.3 are unmarked and read as current
`products/_starter/ADR/0002-azure-deploy.md` lines 146-152 (decision 4) and line 177 (decision 5,
condition 3); also line 136.

- Lines 146-148: "**Passwords never reach the server.** The workflow sends SCRAM-SHA-256 verifiers made by
  `infra/scram_verifier.py`, which Postgres stores as given." Slice 4 deleted `scram_verifier.py`, and the test
  script checks that it's gone. The verifiers were of the seed-derived role passwords, so this is a
  derived-password passage. Lines 149-152 ("verifiers match Postgres's own") are the test evidence for that
  mechanism.
- Line 177: "3. **Passwords never reach the server** (SCRAM verifiers, decision 4), so nothing can log one." This
  is listed as a compensating control that is still in force. The workflow no longer sends role verifiers.
- Line 136: "Only the migration job has its password." Roles now sign in with Entra tokens and have no password.
- Why it matters: the banner (lines 3-6) promises that "Every passage below about the seed, derived role
  passwords ... is ... marked". A reader who trusts the banner will take these unmarked lines as current design,
  and line 148 points to a file that no longer exists. The brief for this slice was that nothing should still
  read as a current instruction.
- Fix: add "(superseded by ADR 0003)" to the lines-146-152 bullet, to condition 3 on line 177 and to line 136. One
  option is a single note after the decision-4 role list: "Role passwords and SCRAM verifiers: superseded by
  ADR 0003; roles sign in with Entra tokens." Also think about line 198 ("the workflow masks derived values"),
  which refers to the derived URLs.

### C2. The table-row markers don't show up on GitHub
Lines 193 (decision 6 secrets table) and 458 (failure modes table).

- `| ... | Container Apps secret ... | (superseded by ADR 0003)` adds a fourth cell to a three-column table.
  GitHub's Markdown rules ignore cells beyond the header's count, so the marker is dropped when the page is
  shown. Both rows look current on GitHub, and one of them is the `DATABASE_URL ... derived ... from STUDIO_DB_SEED` row.
- Fix: put the marker inside an existing cell, for example
  `| derived in the workflow from STUDIO_DB_SEED (superseded by ADR 0003) |`, or prefix the first cell with it.

## Suggestions (not blocking)

- S1. Make the exclusions narrower. `grep -vE '/(ADR|reviews)/|/NEXT\.md$'` drops any `ADR/` or `reviews/`
  directory and any `NEXT.md` under the search roots. A product copied from the starter could easily have a
  `backend/app/reviews/` feature package (restaurant reviews, for example), and it would be skipped silently.
  Anchor them instead: `^$root/products/_starter/(ADR|reviews)/` and `^$root/products/_starter/NEXT\.md$`.
- S2. `"$root/SECURITY.md"` doesn't exist (the file is `products/_starter/SECURITY.md`, which the
  `products/_starter` root already covers), and `2> /dev/null` hides that. The same redirect would also hide a
  wrong `.github` path. Either drop the dead path or test the roots with `[ -d ]` first, so a wrong path fails
  loudly instead of passing.
- S3. Root `SETUP.md` and `playbooks/` are operator docs too. Both are clean today but aren't searched. Adding them
  costs nothing.
- S4. Markers in the middle of a sentence read awkwardly, for example line 219 "...can't be rolled (superseded by ADR 0003)
  back to afterwards" and line 318. Put each marker once at the start of its bullet instead of where a line wraps.
- S5. In the CI job, `grep -r` over `products/_starter` will go into `frontend/node_modules` if that job runs
  `npm ci` first. Add `--exclude-dir=node_modules`.
- S6. Nit: the check message says "script, README or SECURITY.md". With S1 and S3 applied, "live doc,
  workflow or script" is more accurate.

## What is good

- History isn't rewritten: the original text stays, with markers and a clear banner pointing to ADR 0003 and
  the runbook.
- The check fails for the right reason and lists the files; the mutation test above proves it.
- No product code changed; slice scope respected.
