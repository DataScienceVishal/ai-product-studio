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

## Re-review (2026-11-23)

- **Commits:** `00c9c9d` (rework), `7fde4b6` (runner-context fix), `422f48e` (two SETUP.md troubleshooting rows; the brief said `0b5e8b1`, a typo the coordinator confirmed). The T-2 files are unchanged through the current branch tip, `eba7c87`: the later commits touch only `products/_starter`, `.github/workflows/_starter-ci.yml` and ideas files.
- **Reviewer:** reviewer agent, 2026-11-23
- **Verdict: PASS.** Safe to merge. T-2 still moves to done only after a real run writes real figures to BUDGET.md, and N1 below should be fixed before then.

### Evidence

- **Tests:** `python3 -m unittest discover -s scripts/tests` ran 25 tests (up from 11), all OK, on Python 3.11, 3.12 and 3.13.
- **Mutation check** (scratch copies only): I reverted twelve fixes one at a time. Each one made at least one named test fail. The twelve were:
  - substring markers;
  - first marker wins;
  - unknown cost not flagged;
  - digest line dropped;
  - currency guard;
  - QPU header;
  - sleep after the last try;
  - rows after the block;
  - substring names;
  - level not tied to the since date;
  - no-rows line;
  - nextLink line.
- **Workflow lint:**
  - actionlint 1.7.12 (built from source into a scratch folder) with shellcheck 0.11.0 reports nothing on HEAD.
  - Control: the `00c9c9d` version fails at 35:18 with `context "runner" is not allowed here`, the error GitHub hit.
  - `gh run list` shows four 0-second `.github/workflows/azure-spend.yml` failures (`00c9c9d`, `5df3b8b`, `f0f5b25`, `017886d`, 11:46 to 11:52Z) and none after `7fde4b6`. The workflow has no push trigger, so a valid file produces no runs on push.
- **Push race, re-simulated.**
  - Setup:
    - a local bare remote;
    - the runner set up the way `actions/checkout@v4` does it (depth-1 fetch of `+<sha>:refs/remotes/origin/main`, then `checkout -B main`);
    - the Commit step's `run:` text extracted verbatim from the YAML and run under `bash -e`, which is GitHub's default shell.
  - A. First run, before the block exists. An agent adds a table row in the same minute, which is the case that used to conflict. One push is rejected, then the step resets, re-renders and pushes. Result: one block, the agent's row kept, the 50% digest line written once. Exit 0 after 5 s.
  - B. Steady state. Spend passes 75% while an agent adds a row and the Desk clears DIGEST_NOTES.md. It recovers the same way: both rows kept, the Desk's clear kept, the 75% line present exactly once.
  - C. The concurrent push deletes the END line. The re-render exits 3 and nothing is pushed.
  - D. No race: the first push works.
  - E. The remote rejects every push. Four attempts, then `could not push BUDGET.md after 4 attempts`, exit 1 after 51 s, and the remote is untouched.
- **Report step shell** (verbatim, stubbed script output): ok, unavailable and currency set `summary`, `status` and `alert` as expected. A marker error fails the step with exit 3.
- **Probes:** scratch scripts against a `git archive` snapshot of HEAD, because the shared working tree has another agent's uncommitted `products/_starter` changes (HURDLES.md:13). No product code was edited. They covered:
  - `render()` edge cases;
  - `budget_line()`;
  - `post()` against a fake server;
  - `az()` with a fake CLI on PATH.

### C1. Unsupported offer: fixed, with one residual (N1)

- **Unavailable path.**
  - Any HTTP error that isn't retried becomes `Unavailable` (`azure_spend.py:186`), and so does any `az` failure (`:130-145`).
  - `cmd_report` catches it and still fetches the inventory (`:437-442`).
  - `render()` writes "Status: unavailable since <first day>: <code> (<detail>). Spend is unknown.", keeps the first day while the code stays the same, and adds a digest line only when the code changes (`:323-329`).
  - The script exits 0 so the commit happens, then the workflow fails the run (`azure-spend.yml:107-114`).
  - Tests: `test_unavailable_is_written_down_with_its_start_date`, `test_unavailable_outcome_still_writes_and_exits_zero`, `test_client_errors_are_unavailable_with_the_azure_code`.
- **"No rows" vs $0.**
  - The block now carries the row counts and "No cost rows came back…" (`:358-360`), which is what the fix asked for. Test: `test_no_rows_is_not_reported_as_zero_spend`.
  - The headline, `studio.py status` and the digest still say $0.00, and the inventory check is off in that case. See N1.
- **Inventory fallback.**
  - `az resource list` provides the inventory (`:207-215`).
  - Unlisted resources are flagged whenever cost is unknown (`:381-387`).
  - The projected monthly total comes from the table (`:285-297`, `:367`).
  - An inventory line, or the inventory error, is written into the block (`:390-394`).
  - Tests: `test_unavailable_is_written_down_with_its_start_date` (`ca-new` flagged from the inventory alone), `test_free_inventory_items_are_not_flagged_when_figures_exist`, `test_projected_monthly_sums_the_estimates_column`.
  - The fallback is in DECISIONS.md:24 and the open question in HURDLES.md:12. A real call is still pending (needs credentials, Q-1).

### C2. Marker rewrite: fixed

- Markers match only as whole lines (`:50-51`).
- `split_block()` accepts either no markers or exactly one START followed by one END, and raises `MarkerError` for anything else (`:255-263`).
- `cmd_report` checks before any API call and exits 3 without writing (`:425-429`). pipefail turns that into a failed step.
- The original table, row by row:
  - An inline note naming both markers: `test_a_note_that_mentions_the_markers_inline_is_left_alone`.
  - A note naming only START: probed; the block is written once and the table is kept.
  - END deleted, END before START, and both conflict sides kept: `test_malformed_markers_refuse_to_write`, which also covers a missing START.
  - Exit 3 with the file byte-identical: `test_malformed_markers_exit_3_and_leave_the_file_alone`.
- Also probed: leftover `<<<<<<<` conflict markers, and a marker quoted alone on a line inside a code fence. Both refuse. Simulation C shows the same refusal inside the push loop.

### C3. Telegram and the commit: fixed

- **Telegram can't block the commit.**
  - The alert step has `continue-on-error: true` (`azure-spend.yml:74`).
  - Commit runs on `always() && steps.report.outcome == 'success' && env.ON_MAIN == 'true'` (`:83`).
  - `tg.py` uses a 30 s timeout and exits non-zero on failure, so a stale token or a Telegram outage can no longer skip the commit.
- **Alerts reach the digest.**
  - Alerts are appended to DIGEST_NOTES.md (`azure_spend.py:355-357`, `:452-453`) and committed with BUDGET.md (`azure-spend.yml:88`).
  - The level is always saved, the digest is the guaranteed channel and Telegram is best-effort. That's a deliberate, sound delivery rule.
  - Tests: `test_alert_fires_once_per_level_and_goes_to_the_digest`, `test_report_from_saved_outcome_alerts_and_notes_the_digest`. Simulation B shows the line surviving a concurrent Desk clear.
- SETUP.md:35 now says to update the `TELEGRAM_BOT_TOKEN` Actions secret after `/revoke`.

### Should-fix items

| Item | Status | Where | Proof |
|---|---|---|---|
| S1 currency | Fixed | `azure_spend.py:341-347`, `money()` `:308-309`; the run fails on status `currency` (`azure-spend.yml:107-114`) | `test_non_usd_currency_is_not_compared_with_the_cap` (GBP: no alert, "70.00 GBP", no "$70.00") |
| S2 push race | Fixed | `azure-spend.yml:93-103`: push; on failure fetch, `reset --hard origin/main`, re-render `--from-dir`, recommit | Simulations A to E above |
| S3 failure visibility | Fixed | Ping on `failure()` (`azure-spend.yml:116-123`); `budget_line()` (`studio.py:242-256`) printed by `cmd_status` (`:272`); the Desk runs `studio.py status` before the digest (`prompts/studio-desk.md:11,13`) | Probed: 31 h old → "STALE: check the azure-spend workflow". Unavailable and currency are shown. With no report it says "needs Azure credentials", which also covers the old secret-missing notice. No tests (N4) |
| S4 spend outside the RG | Docs fixed | SETUP.md:76; the block says "Covers resource group rg-ai-studio only" (`azure_spend.py:334`) | Vishal still has to confirm the Azure OpenAI resource is in the group |
| S5 least privilege | Partly fixed; the rest deferred (DECISIONS.md:25) | `AZURE_COST_CREDENTIALS` with Reader and Cost Management Reader (SETUP.md:59-74), preferred by the workflow (`:29`, `:50`) | Without that secret, the job still uses the Contributor credential. The deferral reason doesn't hold here: in this session `git ls-remote https://github.com/actions/checkout 'refs/tags/v4*'`, and the same for `Azure/login`, returned tag SHAs, so pinning can be done now |
| S6 retries | Fixed | `RETRY_HEADERS` `:55-60` (QPU, entity, tenant, then Retry-After); `retry_wait` `:148-156`; no sleep after the last try `:182-183`; 5xx wording `:181`; `az()` makes 3 tries, waiting 5 s and 10 s (`:130-145`) | `test_qpu_retry_header_is_honoured`, `test_persistent_throttling_gives_up_without_a_final_sleep`. Probed: 5xx says "kept failing (503)", and a fake `az` that failed twice then worked waited [5, 10]. The `az` retries and the 5xx wording have no tests |
| S7 main only | Fixed | `ON_MAIN` (`azure-spend.yml:31`), Commit gated on it (`:83`), `push origin HEAD:main` (`:94`), recovery against `origin/main` (`:98-99`) | actionlint is clean; simulation |
| S8 matching | Fixed | Exact first word (`:275-282`); table read from outside the block (`:317`); keyed by lower-cased full ID, with the child path shown (`:371-380`, `:240-252`) | `test_listed_names_are_exact_first_words`, `test_unlisted_costly_resource_is_flagged`, `test_top_level_names_keep_children_distinct`, `test_rows_added_after_the_block_count_as_listed` |
| S9 top line | Fixed | The "Month-to-date spend:" line now carries the since-start figure (`:414-417`); the studio line shows "$X of $80 cap (N%)" | Only tested indirectly: "$60.40 of $80" also matches the Since line. Nit: the label still says "Month-to-date" |
| S10 level vs period | Fixed | Written at `:368`, parsed at `:300-305`, reset on a new since date at `:336` | `test_a_new_since_date_resets_the_alert_level` |
| S11 range length | Fixed (clamped) | `:54`, `:106-111`, note at `:361-362` | `test_window_is_clamped_to_the_api_limit`. Nit: once clamped, the summary still says "Since <configured date>" while the block says "Since <clamped date>" (probed). This only matters from 2027-11 |
| S12 tests | Mostly done | 14 more tests | Still missing: `budget_line()`, `az()` retries, the "(unattributed)" display, the ok-path top line |
| S13 small things | Fixed | nextLink warning (`:363-364`); utf-8 on every read and write (`:424`, `:433`, `:446-453`); "(unattributed)" shows "-" (`:398-399`); SETUP.md:57 says "the values from step 2"; SETUP.md:78 covers the manual first run and the daily bot commit | `test_next_link_is_mentioned`; the rest checked by reading |

### Workflow conditions and contexts

Every expression uses a context GitHub allows where it's used, and actionlint agrees.

| Where | Contexts used | Allowed there |
|---|---|---|
| Job `env` (`:29-34`) | `secrets`, `github` | github, needs, strategy, matrix, vars, secrets, inputs. `runner` is not allowed, and the fix removed it |
| Step `if` (`:43`, `:47`, `:54`, `:73`, `:83`, `:108`, `:117`) | `env`, `steps`, `always()`, `failure()` | Adds job, runner, env and steps. `secrets` is not allowed, and none is used |
| Step `with` (`:50`) and step `env` (`:76-79`, `:110-111`, `:120-122`) | `secrets`, `steps`, `github` | All of these |

How each kind of run plays out:
- **No Azure secret:** a notice, a green run, no ping. `studio.py status` says "no spend report yet".
- **A test fails, or sign-in fails:** Report and Commit are skipped and the ping fires. BUDGET.md isn't touched, so the status line flags it as stale after 30 h (N11).
- **Report ok:** the alert is best-effort, then Commit runs, and the run is green.
- **Report `unavailable` or `currency`:** Commit runs, then "Fail the run when spend is unknown" turns the run red, then the ping fires. That order is right: the figures are committed before the run fails.
- **Marker error:** Report fails, Commit is skipped (its `outcome` is `failure`), and the ping fires.
- **Push fails 4 times:** Commit fails, the "Fail…" step is skipped, and the ping fires.
- **Manual run on another branch:** no commit. A Telegram alert can still fire, which is harmless.
- **Nit:** `always()` also runs after a cancel. GitHub's docs suggest `!cancelled()`.

### New findings

**N1. "No cost rows" still reads as $0.00 where people look, and it switches off the inventory check. Fix before T-2 moves to done.**

- **Where:**
  - `azure_spend.py:349-360`: status stays `ok`, and the Since line says "$0.00 of $80 cap (0%)".
  - `:414-417`: the top line.
  - `:381-387`: a resource with unknown cost is never flagged when results are present.
  - `studio.py:250-254`: the budget line.
- **Probe:** all three queries returned no rows, and the inventory held `ca-new`, which isn't in the table.
  - The status was `ok` and the unlisted list was `[]`.
  - The top line read "(Since 2026-11-01: $0.00 of $80, …)".
  - `studio.py status` read "budget: $0.00 of $80 cap (0%) · updated 6h ago", so the digest would say "Azure $0 of $80".
  - The run is green, so there's no ping.
- **Why it matters:**
  - This is the "200 with no rows, or 204" half of C1. The block line is there, as the fix asked.
  - The point was that "no data" can't be mistaken for $0.00, and the three places people read still show $0.00 with no caveat.
  - The inventory check is the fallback for exactly this situation, and here it flags nothing.
- **Mitigation for now:** SETUP.md:78 has Vishal run the report once by hand and read BUDGET.md, and T-2 stays open until real figures appear.
- **Fix:**
  - When the month-to-date and since-start queries both return zero rows, use a separate status, for example `no_data`.
  - Make the summary, the top line and the `studio.py` line say "no cost data yet" instead of "$0.00".
  - Treat costs as unknown in `needs_listing`, so unlisted inventory is flagged.
  - Optionally, fail the run only if it lasts more than 2 days, since a day of data lag is normal.
  - Add a test that checks the top line and the unlisted list.

**N2. A long outage pings Telegram every day. Fix once the first real run settles C1.**

- **Where:** "Fail the run when spend is unknown" (`azure-spend.yml:107-114`) plus the `failure()` ping (`:116-117`).
- **What happens:** "the daily Azure spend report failed" goes out every morning while Cost Management is unavailable, though the digest line is only written once (`azure_spend.py:327-329`).
- **Why it matters:** if the offer is unsupported, that's a permanent daily ping, and playbooks/telegram.md keeps urgent pings for when money is at risk.
- **Fix:** fail and ping only on the first day of an outage or when the error code changes. The script already knows when that is, because that's when it writes the digest line. Alternatively, have the C1 fallback decision switch the failure off.

**N3. The Commit step reports git errors as "unchanged". Small fix.**

- **Where:** `commit() || { echo "BUDGET.md unchanged"; exit 0; }` (`azure-spend.yml:87-92`) treats any `git add` or `git commit` failure as nothing to commit.
- **Probe:** with `state/DIGEST_NOTES.md` missing, `git add state/BUDGET.md state/DIGEST_NOTES.md` exits 128 and stages nothing. The step prints "BUDGET.md unchanged" and the run goes green with no commit. The script never creates that file (`azure_spend.py:452`).
- **Fix:** `git add state/BUDGET.md` on its own, add DIGEST_NOTES.md only if it exists, and let any other git error fail the step.

**N4. `budget_line()` has no tests and reads the whole file.**

- **Where:** `studio.py:246-250` searches all of BUDGET.md, not just the report block.
- **Probe:** a hand-written "- Updated: 2026-11-01T00:00:00Z" line above the block made a fresh report show "updated 564h ago (STALE…)". The status text is also cut at 100 characters, mid-word.
- **Fix:** search only between the markers, and add tests for ok, stale, unavailable, no report, and the N1 case.

**Nits**

- **N5. A null outcome crashes `render()`.**
  - If outcome.json has both `results` and `error` null, `money(None)` at `:414` raises `TypeError`.
  - `fetch()` can't produce that, but treat it as unavailable anyway.
- **N6. A non-JSON 200 escapes `post()`.**
  - A 200 with a non-JSON body raises `JSONDecodeError` (`:177`). The step fails and the ping fires, but nothing is written.
  - Raise `Unavailable("bad_response")` instead.
- **N7. Indented markers are read as plain text.**
  - Effect: a second block gets appended, and the old block's generated rows then count as hand-kept. Probed: the unlisted list went from `['ca-unlisted']` to `[]`.
  - Fix: count lines matching `^[ \t]*<!-- spend:auto:(start|end) -->[ \t]*$` as markers.
- **N8. Formatted table names aren't recognised.**
  - Names in bold or written as links ("**ca-bold**", "[ca-link]") don't match.
  - Effect: false "add it" warnings. Noisy, but not silent.
- **N9. The last push attempt is wasted.**
  - On the 4th pass the push loop resets, re-renders, commits and sleeps 20 s, then gives up without pushing.
  - Fix: push after the last re-render, or skip the recovery on the final pass.
- **N10. Error text is published.**
  - The repo is public (`gh api` reports `visibility: public`). Azure error text goes into BUDGET.md and the public log, and unsupported-offer errors usually quote the subscription ID.
  - A subscription ID isn't a credential, but redact GUIDs from `Unavailable.detail`.
- **N11. A sign-in failure isn't written to BUDGET.md.**
  - Only the ping and the 30 h stale flag show it.
  - The likeliest cause is the service-principal secret expiring, one year after it's created (`create-for-rbac`'s default).
  - Put the renewal date in SETUP.md step 3.
- **N12. Throttling hints: the first header wins, not the largest.**
  - Probed: with QPU at 10 s and entity at 40 s, it waited 10 s. Waits are also capped at 60 s.
  - Use the largest hint.

### Verdict: PASS

- C1, C2 and C3 are fixed, and each has tests that fail when the fix is reverted.
- S1 is fixed. S2 is fixed and held up in a fresh simulation.
- The workflow file is valid, and its step conditions do what the rework intends. Nothing in it can lose the hand-kept table or skip a good commit.
- No blocking issue remains for merging.
- Before T-2 moves to done:
  - a real run must write real figures to BUDGET.md (unchanged);
  - N1 must be fixed, because it's the one place where "no data" can still look like $0.00 in the digest.
- After that: N2 once the first run shows whether the offer is supported, and N3 and N4 when convenient.
