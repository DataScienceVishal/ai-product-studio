# Review: p/holiday-pay-payroll-lookback-audit/T-126 (head c555c403)

Reviewer run, 2026-11-26. Diff: `git diff main...origin/p/holiday-pay-payroll-lookback-audit/T-126` (merge-base 181f1bc = main). Checked out in a separate scratch worktree, which has since been removed.

## Verdict: CHANGES (one small fix, about 10 lines)

The rules engine wiring, the rolled-up rules, the exceptions.csv schema and the wording guardrail are correct and well tested. One user-facing defect blocks the merge. For an `irregular_rolled_up` worker with a `contract_weekly_basic`, the report calls the worker `variable_hours`, says "their rate is the 52-week average" and advises "Set worker_type to fixed_pay". All three are wrong for this worker type. Following the advice would switch off the rolled-up check for that worker.

## Evidence

- Tests on the branch tree (`python3 -I -m unittest discover -s tests -t .` from the product dir): **247 tests, OK** (main had 228; 19 new tests in `tests/test_rolled_up.py`).
- `git diff main...HEAD --stat -- products/holiday-pay-payroll-lookback-audit/mapper products/holiday-pay-payroll-lookback-audit/benchmark`: **empty**, so mapper/ and benchmark/ are unchanged.
- `python3 samples/generate.py` reproduces `samples/*.csv` byte for byte (`git status` clean afterwards).
- CLI with samples and `--workers`: exit 0. It prints `5 leave weeks checked, 11 exceptions.` and `12 rolled-up pay weeks checked, 7 of the exceptions are rolled-up pay.` exceptions.csv has 4 `leave_lookback` rows that match main (W002 80.00, W003 -10.00, W004 50.00 shortened, W005 15.00) and 7 `rolled_up_pay` rows:
  - W006: 3 rows `rule_flag`, `rolled_up_before_2024_rules`;
  - W007: 2 rows `rule_flag`, `rolled_up_not_shown_separately`;
  - W008: 2025-06-14 paid 20.00, recalculated 24.14, underpaid 4.14; 2025-06-21 paid 30.00, recalculated 24.14, overpaid 5.86.
  - On every rule_flag row, `due` and `difference` are blank. `check` is the trailing column.
- `--threshold 1000000`: 5 rolled-up exceptions remain (the 5 rule flags), so rule flags show whatever the threshold.
- Without `--workers`: the "rolled-up holiday pay for a worker not set as irregular_rolled_up" warning lists W006, W007 and W008 with their weeks. The look-back is unaffected because rolled-up pay is not counted as normal, basic or "other" pay (`engine/lookback.py:163`).
- Wording: there are no hits for compliant/owed/liable in non-test code. The CLI test checks every output, including the warning-section path, with a regex that also catches owe/owing/liability/compliance. The report says "Recalculated under these settings" and keeps the disclaimer on line 3.

## UK rules as encoded: correct within stated assumptions

- Rolled-up pay is accepted only when `accrual_applies(leave_year_start)` (start >= 2024-04-01). Before that date, any rolled-up amount above 0 is flagged and nothing is recalculated (`report/rolled_up.py:47-52`). This matches the 2024 regulations for irregular-hours and part-year workers.
- The recalculation is 12.07% of `normal_pay` (basic, regular_overtime, commission, allowance), rounded to the penny with ROUND_HALF_UP. Expenses, non-regular bonus, SSP/statutory, holiday_pay and the rolled-up item itself are excluded, and a test covers this (`test_pay_that_counts_excludes_...`). 150 x 12.07% = 18.105 rounds to 18.11, also tested.
- `rolled_up_not_shown_separately` fires only when pay that counts is above 0 and there is no rolled-up row. An explicit 0.00 row is treated as underpaid, not as "not shown". That is a defensible reading.
- Leave years are fixed at 1 April and a week belongs to the year that contains its week-ending date. This is the existing look-back assumption and is documented in FORMAT.md. See suggestion S2 for why it matters more here.

## Regressions for existing worker types: none found

`variable_hours` and `fixed_pay` follow the same path. The sample look-back rows are unchanged, and `test_mixed_worker_types_keep_their_own_rules` covers all three types in one file. The edits to `test_audit.py` filter on `check == "leave_lookback"` and do not weaken the assertions. Workers loaded went from 5 to 8 because the sample grew.

## Privacy and permissions: unchanged

There is no new I/O, network access or dependency. Output files are written through the existing `write_outputs` path. In CSV cells, `worker_id` and `flags` still pass through `_safe` (formula-injection guard). Loader validation of IDs, NI and names is untouched; only the accepted worker_type tuple grew.

## Critical issue (blocks merge)

**C1. Wrong label and wrong advice for `irregular_rolled_up` workers with a `contract_weekly_basic`.**
- Where: `report/builder.py:47-49` (`ignored_contract_basic` selects `worker_type != "fixed_pay"`, which now includes irregular_rolled_up), `report/builder.py:304-306` (section text) and `audit.py:54` (stderr note).
- Reproduced with workers.csv `W1,irregular_rolled_up,300` (and also with `0`). stderr shows `note: contract_weekly_basic ignored for 1 variable_hours worker(s)`. report.md shows "These workers are variable_hours ... their rate is the 52-week average. Set worker_type to fixed_pay if the contract rate should be used" and "- W1: contract_weekly_basic ignored (variable_hours)".
- Why it matters: this is user-facing text in an audit tool, and it is false. A user who follows it reclassifies a rolled-up worker as fixed_pay, which silently drops the rolled-up check (the pay only shows up as a stray warning). FORMAT.md already says the value is "ignored for them", so the code and the docs disagree.
- Fix: carry the worker type through. For example, `ignored_contract_basic` returns `[(wid, worker_type)]`, and the line reads `contract_weekly_basic ignored (<worker_type>)`. Give irregular_rolled_up its own sentence ("rolled-up pay is checked as 12.07% of pay that counts; a weekly basic is not used"), make the stderr note type-neutral ("for N worker(s) not set as fixed_pay"), and add a test for `irregular_rolled_up` with a basic, including 0.

## Suggestions (do not block)

- **S1. Holiday pay in leave weeks of rolled-up workers is silent.** `unlisted_holiday_pay` now skips irregular_rolled_up workers (`report/builder.py:38`) and the look-back skips them too. A rolled-up worker who is also paid `holiday_pay` when on leave is therefore never mentioned, beyond the count "N leave weeks not re-audited". The sample does exactly this (W008 2025-06-28, holiday_pay 200). That pattern is either a double payment or a sign that the worker is not really on rolled-up pay. Add a report.md note that lists the holiday_pay weeks for irregular_rolled_up workers.
- **S2. The fixed 1 April leave year matters more for the pre-2024 flag.** If an employer's leave year started on, say, 1 January 2024, rolled-up pay from April to December 2024 was still not allowed, but the tool counts it as in the 2024-04-01 year and recalculates instead of flagging it. Before the seeded-error demo, add a leave-year-start option (or a per-worker start) and state the assumption on the report page.
- **S3.** `explain_rolled_up` puts the raw `r['worker_id']` in the heading (`report/rolled_up.py:92`), while `explain` uses `_md(...)`. The loader's ID charset limits the risk, but pass an escaper for consistency.
- **S4.** The first stdout line, `5 leave weeks checked, 11 exceptions`, adds look-back and rolled-up exceptions together after a look-back-only count. Consider `5 leave weeks checked, 4 look-back exceptions` with the rolled-up line giving its own 7.
- **S5.** The loader imports `INPUT_WORKER_TYPES as WORKER_TYPES` (`ingest/loader.py:12`). The alias hides that the two tuples differ, so use the real name.
- **S6.** The summary line "Workers with leave: 5" leaves out W008, which has a leave row. A short "(excluding irregular_rolled_up)" would avoid confusion.
- **S7.** `history_gaps` will list every no-work week of an irregular-hours worker as "missing from the export". For this worker type that is normal and creates noise. Consider softening the wording or skipping them.

## Test quality

The tests are good. They exercise behaviour: the leave-year boundary on 31 March and 1 April, a zero rolled-up row, a zero pay-that-counts week, exclusions, the strict threshold including 0, rule flags at a huge threshold, penny rounding, the CLI on the samples with exact CSV rows, a mixed-type pipeline, the stray warning, and the banned-words regex across all outputs. The gaps are C1 (no test for irregular_rolled_up with a basic) and S1.

## Re-review at 259176cb: PASS

Checked in a fresh scratch worktree at 259176c, which has since been removed.

- **Suite:** `python3 -I -m unittest discover -s tests -t .` runs **251 tests, OK**. That is 4 new tests: rolled-up wording for a contract basic, holiday_pay flagged, holiday_pay in a pre-2024 week alongside a difference, and no warning for other worker types.
- **mapper/ and benchmark/:** `git diff main...HEAD --stat` over both is **empty**. `samples/generate.py` reproduces the sample CSVs exactly (`git status` clean).
- **C1 fixed.** I ran it with workers.csv `W1,irregular_rolled_up,300`, then with `0`, each time alongside `W2,variable_hours,10`.
  - stderr: `contract_weekly_basic ignored for 2 worker(s) not set as fixed_pay`.
  - report.md gives each type its own sentence. irregular_rolled_up gets "rolled-up pay is checked as 12.07% of pay that counts, so a weekly basic is not used", with no advice to change worker type. The lines read `W1: ... ignored (irregular_rolled_up)` and `W2: ... ignored (variable_hours)`.
- **S1 fixed.** The sample CLI prints `5 leave weeks checked, 12 exceptions` and `13 rolled-up pay weeks checked, 8 ...`. exceptions.csv has the new row `W008,2025-06-28,200.00,,,rule_flag,holiday_pay_paid_to_rolled_up_worker,...,rolled_up_pay`. report.md adds a summary line and a "holiday_pay recorded for an irregular_rolled_up worker" warning. The holiday_pay flag also fires in pre-2024 weeks and alongside a difference row, and there is a test for each case.
- **S2 documented, not built.** The 1 April leave-year assumption and its false-negative case are explained in FORMAT.md. That is acceptable for this task. A leave-year-start option should become a board task before the seeded-error demo.
- **Heading escape fixed.** `explain_rolled_up` now takes `esc` and builder passes `_md`.

Non-blocking nits:
- "Rolled-up pay weeks checked" counts the holiday_pay flag row as an extra week. A week that has both a rolled-up row and holiday_pay is counted twice: 2 pay weeks showed as "3 rolled-up pay weeks checked".
- The summary counts `holiday_pay_paid_to_rolled_up_worker` among the "rule flags".
- In that row's CSV `paid` column, the value is the holiday_pay amount. FORMAT.md documents this.

Verdict: **PASS.** The branch can merge to main once it is rebased cleanly on main.
