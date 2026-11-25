# Review: p/_starter/T-95-ai-budget (commit 10fa14a)

Reviewer, 2026-11-25. Diff: `git diff main...p/_starter/T-95-ai-budget` (11 files, +63 / -47).

**Verdict: CHANGES.** One blocker, and it is small: `.env.example` still ships the old cap and the old budget.

## Summary

T-95 puts the default AI budget back to the approved $6.10 and lowers the global daily cap to 98,000 tokens.
The code side is correct and consistent: `aicost.py`, `config.py`, `main.bicep` and `cost-guard.sh` all agree, every
boundary number in the tests checks out, and the new consistency test catches drift in each of the four files it reads.
README, ADR 0002, BRIEF and infra/README were updated correctly. The brief now says that with gpt-5.4-pro AI is effectively
off at this budget.

The one file the change missed is `products/_starter/.env.example`. It still pins the old 100,000 cap and says the
default budget is 6.20. That file is the documented source of setting names (README line 77), and `Settings` reads `.env`.

## Evidence (commands run on 10fa14a)

| Check | Command | Result |
|---|---|---|
| Backend suite | `cd products/_starter/backend && .venv/bin/python -m pytest -p no:warnings` | **647 passed, 1 skipped** (648 collected), 65.5 s |
| Touched tests | `pytest tests/test_aicost.py tests/test_cost_guard.py` | 67 passed |
| Infra | `bash infra/test-deploy-workflow.sh` / `test-deploy-role.sh` / `test-db-setup.sh` | 102/0, 67/0, 33/0 |
| New test is meaningful | copied backend+infra to a scratch dir, applied one mutation at a time, ran `test_shipped_defaults_match_and_fit_the_approved_budget` | fails for each of: Bicep cap 98000 to 99000; cost-guard default 6.10 to 6.20; config cap 98_000 to 100_000; `DEFAULT_MONTHLY_BUDGET_USD` 6.10 to 6.20. Passes unmutated. Product tree left untouched (`git status` clean) |
| Leftover references | `grep -rnE '6\.20\|100,000\|100000\|1,110\|\$558\|x ?30\b\|about one summary' products/_starter .github/workflows` (excluding reviews/, .venv) | hits in `.env.example` (below). Others are SECURITY.md history, the trial plan's 100,000 a month (`billing.py`, BRIEF line 87/136, which is correct), tests that use 100000 on purpose as an over-budget input, and NEXT.md history. `.github/workflows`: no cap or budget literals |
| Bicep compile | not run (no az CLI) | the change is a param default and description text only |

Arithmetic, checked by hand:
- 98,000 x 31 x 2.00 / 1e6 = **$6.076** (fits within 6.10; docs say $6.08, $0.196 a day).
- At $2: 6.10 / 62 x 1e6 = 98,387.1, so **98,387 passes** ($6.099994) and **98,388 fails** ($6.100056). Correct.
- At $120: 6.10 / 3,720 x 1e6 = 1,639.8, so **1,639 passes** ($6.0971) and **1,640 fails** ($6.1008). Correct.
- At $180: 6.10 / 5,580 x 1e6 = 1,093.2, so **1,093 passes** ($6.0989) and **1,094 fails** ($6.1045). Correct; the comments in the test match.
- 98,000 x 31 x 180 / 1e6 = **$546.84** (docs round it to $547). Correct. 1,000 tokens at $180 = $5.58. Correct.
- 98,000 / 4,004 = 24.5, so "at least 24 calls" holds. Trial half = 49,000. Correct.
- The guard's own suggestion `int(budget / (31 x price) x 1e6)` gives 98,387 / 1,093, the same numbers as the docs.

## Critical issues

### C1. `.env.example` still ships the old cap and budget (lines 35-37, 41)

```
AI_GLOBAL_DAILY_TOKENS=100000
# With AI_PROVIDER=azure the app refuses to start when tokens x 31 x price is above this many USD a month (default 6.20).
# AI_MONTHLY_BUDGET_USD=6.20
...
# lower AI_GLOBAL_DAILY_TOKENS: 6.20 / (31 x price) x 1,000,000.
```

**Why it matters:** line 35 is an active setting, not a comment. Suppose a developer copies `.env.example` to `.env`
(`Settings` reads `.env`, `config.py:23`) and switches `AI_PROVIDER=azure` with the file's own `AZURE_OPENAI_DEPLOYMENT=gpt-5-mini`.
The app then **refuses to start**: 100,000 x 31 x 2.00 = $6.20 is over $6.10. The branch's own test asserts exactly that
refusal (`test_aicost.py:27`). The comments also still say the default budget is 6.20, which contradicts T-95's goal of having
every default and its docs agree. The task explicitly asked for all remaining 6.20 / 100,000-cap references in
`products/_starter` to be found.

**Fix:** set line 35 to `AI_GLOBAL_DAILY_TOKENS=98000`, change "(default 6.20)" and `# AI_MONTHLY_BUDGET_USD=6.20` to 6.10,
and change line 41 to `6.10 / (31 x price) x 1,000,000`. Also extend
`test_shipped_defaults_match_and_fit_the_approved_budget` so it checks that `.env.example`'s `AI_GLOBAL_DAILY_TOKENS` equals the
app default (the same regex approach as for Bicep). That way this file can't drift again.

## Suggestions (not blocking)

1. **`state/BUDGET.md` line 20** (main, a state file, so it's the Studio Lead's to fix, not this branch's) still says "at most 6.10
   with azure and the 100,000-token daily cap". After merge it should say 98,000.
2. **`NEXT.md` line 10** (the current T-91 status block, whose line 4 this branch edited) says the pro cap must drop "to about
   1,100". With $6.10 it is 1,093. That's close enough to be harmless, but it's an easy fix while the file is open.
3. **ADR 0002 line 227**: "98,000 tokens cost at most $0.20 a day". That's $0.196 rounded, which is fine, but Bicep says $0.196.
   Using the same figure in both would be tidier.
4. The new test hardcodes `"gpt-5-mini"` as the shipped deployment. It could read `param azureOpenAiDeployment string = '...'`
   from `main.bicep` instead, so a change to the default model is also checked against the budget.
5. `test_cli_matches_the_app_rule` still asserts `$558.00` for pro at 100,000 tokens. That's correct for that input, but 98,000 /
   `$546.84` would keep the examples in one place. Cosmetic.

## Security / performance

No new endpoints, inputs or secrets. The cost guard still never prints the deployment name (`test_pro_deployment_from_env_fails_at_default_cap_without_printing_it`
now expects $546.84 and still asserts the name is absent). No performance impact.

---

# Re-review: delta 10fa14a..89f55b3

Reviewer, 2026-11-25. Diff: `git diff 10fa14a 89f55b3` (.env.example, ADR 0002, NEXT.md, test_aicost.py; the commit also adds this review file).

**Verdict: PASS** on content. C1 is fixed, and suggestions 2, 3 and 4 were taken.

**Merge precondition (git, not code):** `89f55b3` is **not on the branch**. It was committed on a detached HEAD: the reflog shows
`checkout: moving from p/_starter/T-95-ai-budget to 10fa14a` and then the fix commit. Both `p/_starter/T-95-ai-budget` and
`origin/p/_starter/T-95-ai-budget` still point at `10fa14a` (`git rev-parse`, `git ls-remote`). The detached checkout came from
the reviewer's first pass. Before merging, fast-forward the branch to 89f55b3 and push it: `git branch -f p/_starter/T-95-ai-budget 89f55b3`
while on another branch, or `git checkout p/_starter/T-95-ai-budget && git merge --ff-only 89f55b3`. Then merge the branch, not 10fa14a.

## Evidence (run on 89f55b3, the current working tree)

| Check | Result |
|---|---|
| `.env.example` | lines 35-37 and 41 now read 98000 / 6.10 / 6.10 / 6.10 |
| Leftover grep (`6\.20`, `AI_GLOBAL_DAILY_TOKENS=100000`, outside reviews/, SECURITY.md, lockfiles, and the deliberate over-budget inputs in test_aicost.py) | no hits |
| Backend `pytest -p no:warnings` | 647 passed, 1 skipped (648) |
| Infra scripts | 102/0, 67/0, 33/0 |
| Mutation of the extended test, in a scratch copy | fails for each of: `.env.example` cap back to 100000; `.env.example` `# AI_MONTHLY_BUDGET_USD` to 6.20; Bicep `azureOpenAiDeployment` default to gpt-5.4-pro. Passes unmutated |
| ADR line 229 / NEXT.md line 10 | $0.196 and 1,093, both correct |

Still open, not blocking: `state/BUDGET.md` line 20 (100,000 cap), which the coordinator will update on main at merge.
