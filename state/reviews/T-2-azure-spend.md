# Review: T-2 daily Azure spend report

- **Commit:** `01850fa` on `vishal/blissful-cray-v1s3ys`. The T-2 files are unchanged at the branch tip (`326b5d3`).
- **Scope:** `.github/workflows/azure-spend.yml`, `scripts/azure_spend.py`, `scripts/tests/test_azure_spend.py`, and the SETUP.md and README.md lines from the same commit. The rest of the branch (kit move, ideas, starter) is not covered here.
- **Reviewer:** reviewer agent, 2026-11-23
- **Verdict: CHANGES**

## Summary

The code is tidy and mostly right. The query bodies match the Microsoft docs. The $80 cap uses cumulative spend since 2026-11-01. The token never reaches logs or disk. The shell steps handle pipefail and grep exit codes correctly, and the tests check behaviour.

Three things block it:

1. Microsoft lists Azure for Students as **not supported** by Cost Management, and the script has no path for that case.
2. The BUDGET.md rewrite can delete the hand-kept table or leave a stale duplicate block after some ordinary edits.
3. A Telegram failure stops BUDGET.md being committed, and that happens exactly on the days spend crosses a level.

Merging the branch now is low-risk, because without `AZURE_CREDENTIALS` the job only runs the tests and posts a notice. Fix these before the secret is added, and leave T-2 open until a real run has written real figures to BUDGET.md.

## Evidence

- **Tests:** `python3 -m unittest discover -s scripts/tests` ran 11 tests, all OK, on Python 3.11, 3.12 and 3.13.
- **Docs fetched from Microsoft Learn on 2026-11-23:**
  - *Query - Usage*, api-version 2026-06-01: the version exists, and the request and response shapes match the code. 204 is a documented response. "'Usage' is equivalent to 'ActualCost'". `granularity: "None"` with grouping appears in the docs' own examples.
  - *Understand Cost Management data* (learn.microsoft.com/azure/cost-management-billing/costs/understand-cost-mgt-data, updated 2025-06-27): the table after "The following offers aren't supported:" has the row `Pay-as-you-go | Azure for Students² | AzureForStudents_2018-01-01 | MS-AZR-0170P`.
  - *Azure Education Hub FAQ* (learn.microsoft.com/azure/education-hub/azure-dev-tools-teaching/program-faq): "How do I know how much of the $100 credit I have left? You can see your remaining credit in the Azure Sponsorships portal."
  - *Assign access to Cost Management data*: "Access to a resource group requires at least the Cost Management Reader (or Contributor) permission."
  - *Cost Management automation* (costs/manage-automation): on a 429, back off for the time in `x-ms-ratelimit-microsoft.costmanagement-qpu-retry-after`. The docs also recommend calling no more than once a day.
- **Probes:** scratch scripts only; no product code was edited.
  - `render()` edge cases.
  - `post()` against a local fake server: 204, 503 with Retry-After, 429 with the QPU header, and 400.
  - The Report step's shell with stubbed output: no alert, alert plus unlisted resources, and a crash.
  - The Commit step against local git remotes: first run and steady state, each with an agent editing BUDGET.md at the same time.

## Critical issues (must fix)

### C1. The data source is documented as unsupported for this subscription, and nothing handles that

**Where:** `scripts/azure_spend.py:120-131` (fetch), `:112` (exit on any 4xx); `.github/workflows/azure-spend.yml:46-51`; `SETUP.md:57`.

**Why it matters:** Microsoft's own support table lists Azure for Students (MS-AZR-0170P) under "aren't supported". The same page also names it in a historical-data footnote, so the docs contradict themselves. Only one real call will tell.

If it is unsupported, the first run after `AZURE_CREDENTIALS` is added stops with "Cost Management returned 400/404: …", and every daily run after that fails the same way. BUDGET.md keeps saying "not reported yet". Nobody watches Actions (CLAUDE.md section 2), so the studio has no spend meter while T-2 looks finished, and the $80 rule in CLAUDE.md section 10 has nothing behind it.

If the API instead returns 200 with no rows, or 204, the report shows "$0.00" every day. `rows()` and `total()` treat "no data" and "no cost" the same way (`:134-151`).

**Fix:**

1. **Verify on the real subscription.** Vishal can do it in a minute from Cloud Shell, using his own sign-in and no secrets:
   ```bash
   SUB=$(az account show --query id -o tsv)
   az rest --method get --url "https://management.azure.com/subscriptions/$SUB?api-version=2022-12-01" --query subscriptionPolicies.quotaId
   az rest --method post --url "https://management.azure.com/subscriptions/$SUB/resourceGroups/rg-ai-studio/providers/Microsoft.CostManagement/query?api-version=2026-06-01" \
     --body '{"type":"Usage","timeframe":"MonthToDate","dataset":{"granularity":"None","aggregation":{"totalCost":{"name":"PreTaxCost","function":"Sum"}}}}'
   ```
   The other route is to merge, run the workflow once by hand (`gh workflow run azure-spend.yml`, then `gh run view --log`) and read the result. Record it in DECISIONS.md or HURDLES.md.
2. **Handle "unsupported or forbidden" explicitly.** For 400, 401, 403 and 404 responses, write a status line into the auto block (for example "Cost Management unavailable for this subscription since <date>: <error code>; spend unknown") and commit it, so the Desk and every run see it. Still exit non-zero.
3. **If it turns out unsupported, pick a fallback and log it.** Options:
   - Use an ARM inventory check (`az resource list -g rg-ai-studio`) to enforce "every resource that costs money is listed", and project spend from the table's monthly estimates.
   - Have Vishal read the balance from the Sponsorships portal now and then.
4. **Say when no rows came back**, as a separate line in the block, so "no data" can't be mistaken for $0.00.

### C2. The marker rewrite can delete the hand-kept table, keep a stale duplicate block, or crash

**Where:** `scripts/azure_spend.py:218-223` (the rewrite), `:164-173` (`listed_names`), `:176-178` (`last_alert`).

**Why it matters:** START and END are matched as substrings anywhere in the file, and only their presence is checked, not their count, order or position. Normal daily runs are fine: on the real BUDGET.md the table survives and the block is replaced in place. These reachable edits break it (all probed):

| What happens to BUDGET.md | Result |
|---|---|
| An agent adds a helpful note above the table that names both markers ("Don't edit between `<!-- spend:auto:start -->` and `<!-- spend:auto:end -->`") | The new block is spliced into the middle of the note, and the real block stays stale forever (2 blocks; "Updated: DAY1" never changes) |
| The note names only the start marker | Run 1 appends a second block. Run 2 deletes everything from the quoted marker to END, **including the whole hand-kept resource table**. The bot commits that to main. |
| The END line is deleted by hand | Run 1 appends a second block. Run 2 deletes everything between the orphaned START and the new END. |
| END appears before START | `IndexError` at `:220`, and the job fails every day until someone fixes the file |
| A conflict is resolved by keeping both sides (CLAUDE.md section 9) | Only the first block is refreshed; the second stays stale |

BUDGET.md is the safety file for Azure, so silent loss of the table matters.

**Fix:**
- Match markers only as whole lines (`re.M`, `^<!-- spend:auto:start -->$`).
- Require exactly one START line followed by exactly one END line.
- If there are no markers, append the block. In any other state, exit non-zero with a clear message and don't write the file.
- Add a test for each row of the table above.

### C3. A Telegram failure freezes BUDGET.md on the days that matter, and with Telegram unset the alert goes nowhere

**Where:** `.github/workflows/azure-spend.yml:64-75`; `SETUP.md:35` and `:57`.

**Why it matters:** The Commit step's `if: env.HAS_AZURE == 'true'` carries GitHub's implicit `success()`. If `tg.py` fails, the commit is skipped. That can happen when the Actions copy of the bot token is stale (SETUP.md step 2 tells Vishal to update only step 5 after `/revoke`) or when Telegram is down. The new level isn't saved, so the next day the alert fires again, fails again, and BUDGET.md stays frozen at the pre-alert figures while spend is at its highest.

The opposite case is also wrong. Without the Telegram secrets, the level is saved as alerted, but the only alert is a `::warning::` annotation that nobody reads.

**Fix:**
- Add `continue-on-error: true` to the Telegram step, or put `if: always() && steps.report.outcome == 'success'` on Commit, so a good report is always committed.
- Choose the delivery rule on purpose. For example, save the new level only when the send succeeded or Telegram isn't configured. When Telegram isn't configured, also add a line to `state/DIGEST_NOTES.md` so the 08:00 digest carries the alert (CLAUDE.md section 11: tell Vishal when money is at risk).
- Change SETUP.md step 2's rotation line to say the Actions secret needs updating too.

## Should fix

- **S1. Currency vs the USD cap** (`azure_spend.py:148-151, 189, 200-201, 213`). The currency is printed but never checked. A probe with GBP gave "$70.00 GBP" and "$70.00 of $80 cap (88%)", and alert 75 fired. In GBP, the 95% alert would fire only past the real $80 cap. **Fix:** if Currency isn't USD, don't compare it with the cap. Either flag it and exit non-zero, or switch to a USD-normalised column after checking which one this account returns. Never print "$" next to another currency code.
- **S2. Push loop after a rebase conflict** (`azure-spend.yml:85-92`). Reproduced with local remotes: on the first run, before the block exists, an agent adding a table row in the same minute makes `git pull --rebase` conflict. The loop never runs `git rebase --abort`, so attempts 2 to 4 fail with "Pulling is not possible because you have unmerged files". After 100 s of sleeps it reports a misleading "could not push". The next day's run recovers, and once the block exists, concurrent table edits merge cleanly (also probed). **Fix:** on failure, abort the rebase, `git fetch`, then `git reset --hard origin/<ref>`. Re-render from saved responses (`--save-dir` in Report, `--from-dir` here, so no new API calls), recommit and retry.
- **S3. Failures are invisible to the studio.** A red run and the "secret missing" notice both live only in the Actions tab. **Fix:**
  - Add a step with `if: failure() && env.HAS_TELEGRAM == 'true'` that sends one short line.
  - Have the Desk (or `studio.py status`) flag the report as stale when "Updated:" is more than about 30 hours old.
- **S4. Spend outside rg-ai-studio still uses the credit.** SETUP.md step 3 asks for "your Azure OpenAI endpoint" but never puts that resource in rg-ai-studio. Token spend from runs and products may therefore be invisible to this report, so "$X of $80 cap" would understate total credit use (safety.md: total credit use within $80). **Fix:** confirm where the Azure OpenAI resource lives. If it's outside the RG, move it in, or say in the block that the figure covers rg-ai-studio only.
- **S5. Least privilege.** An unattended daily job holds the Contributor deployer credential and runs repo code: `scripts/azure_spend.py` and every file in `scripts/tests/`. Agents can change those files on main without a workflow-scope token. The query only needs Cost Management Reader at RG scope. **Fix:**
  - Use a second service principal with Cost Management Reader on rg-ai-studio, stored as its own secret.
  - Pin `actions/checkout` and `azure/login` to commit SHAs.
  - Consider OIDC federated credentials instead of a client secret.
- **S6. Retries** (`azure_spend.py:80-117`). The 429 handling reads only `Retry-After` and ignores the documented `x-ms-ratelimit-microsoft.costmanagement-qpu-retry-after` header (probe: a 30 s hint was ignored and the script slept 5/10/20/40/60 s). It also sleeps after the last attempt and reports 5xx errors as "kept throttling". The `az` calls have a timeout but no retry, which misses the engineering.md rule. **Fix:** read the QPU header, skip the sleep after the last attempt, report the right reason, and retry `az` 2 or 3 times.
- **S7. Manual runs on other branches** (`azure-spend.yml:86`). A `workflow_dispatch` on any branch other than main commits BUDGET.md to that branch, but state files belong on main (CLAUDE.md section 9). **Fix:** run the Commit step only when `github.ref == 'refs/heads/main'`, or always push to main.
- **S8. Resource matching** (`azure_spend.py:154-173, 186-187`). Three problems:
  - Substring matching counts "pg" or "shared" as listed when only "pg-shared" is in the table (probed).
  - Names taken from the last segment of the resource ID collide: two storage accounts' `blobServices/default` merge into one "default" row.
  - Rows appended after the block (an agent's `>>`) are kept but reported as unlisted, because only the text before START is parsed.

  **Fix:** parse the table from everything outside the block, compare exact names (the first token of the cell), and group by full resource ID while displaying the name.
- **S9. Top line shows month-to-date only** (`azure_spend.py:213`). The digest template reads "Azure $12 of $80". From December, the prominent month-to-date line will understate how much of the cap is used. **Fix:** put the since-start figure on that line too.
- **S10. Alert level isn't tied to the period.** If `STUDIO_SPEND_SINCE` is reset, for example when the credit renews after 12 months, "Last alert level: 95%" carries over and silences every alert. **Fix:** store the level together with the since date.
- **S11. The since-start range keeps growing.** Cost analysis keeps 13 months of summarised data, and the Query API reportedly rejects custom ranges longer than a year. This isn't urgent before 2027-11-01. **Fix:** clamp or chunk the range when it gets close.
- **S12. Tests to add with the fixes:**
  - each marker case from C2;
  - the currency guard (S1);
  - `post()` against a fake server: 204, Retry-After, the QPU header, and 4xx;
  - "no rows" reported differently from $0;
  - rows added after the block.
- **S13. Small things:**
  - `nextLink` is ignored. That's fine for one RG, but warn when it isn't null.
  - Pass `encoding="utf-8"` on read and write.
  - "(unattributed)" rows show "yes" under "In the table above?".
  - In SETUP.md, "the same values as step 5" should point to step 2, where the values come from.
  - SETUP.md should tell Vishal to run the workflow once by hand after adding the secret and check BUDGET.md, and should mention that `github-actions[bot]` commits to main every day.

## Answers to the specific questions

- **Query bodies and parsing:** The bodies match the 2026-06-01 docs. Parsing goes by column name, so column order doesn't matter. A 204 becomes `{}` and then $0.00 (confirmed against a fake server). Gaps: "no data" looks the same as zero (C1), the currency is never checked (S1), and `nextLink` is ignored (S13).
- **Alert once per level:** The arithmetic is right for spend that only goes up, and the tests cover it. Delivery is the problem: a Telegram failure blocks the commit, and with Telegram unset the alert disappears (C3). A reset of the since date silences all future alerts (S10).
- **BUDGET.md rewrite:** Normal runs are fine. After the edits listed in C2 it deletes the hand-kept table, keeps a stale duplicate block, or crashes.
- **Shell:** Clean. pipefail is set explicitly, `grep … || true` handles no matches, and the `$GITHUB_OUTPUT` values are single lines. Values reach the Telegram step through `env:`, not `${{ }}` inside the script, so there's no script injection. I probed the no-alert, alert and crash paths.
- **Token:** It goes from `az` into memory only. It is never printed, never passed on a command line and never written to disk. The error paths print only Azure or az error text.
- **Push loop and first run:** See S2. On the first run after the secret is added, the most likely outcome is C1: a 4xx from Cost Management, and a red run every day after. If the API does work, the first run alerts once at the highest level already crossed, which is fine.
- **Contributor at RG scope:** It's enough. Contributor is `*` minus authorization writes, and the docs name "Cost Management Reader (or Contributor)" at resource group scope. That only holds if the offer is supported (C1), and it is more access than the job needs (S5).
- **Noisy or silent failures:**
  - Noisy: an unsupported offer or a bad api-version (C1), a malformed marker (C2), a Telegram failure (C3), a rebase conflict (S2), a failing test (which stops that day's report), and RBAC lag right after the service principal is created.
  - Silent: empty data shown as $0.00 (C1), a non-USD currency (S1), Azure OpenAI spend outside the RG (S4), alerts lost when Telegram is unset (C3), and every red run, because nobody watches Actions (S3).

## Verdict: CHANGES

For a re-review I need:
- C1: either the result of a real call, or the unsupported path handled and surfaced in BUDGET.md, with a fallback recorded in DECISIONS.md;
- C2 and C3 fixed, with tests;
- ideally S1 and S2 as well.

T-2 should move to done only after a real run has written real figures to BUDGET.md.
