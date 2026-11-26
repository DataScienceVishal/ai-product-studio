# Review: p/holiday-pay-payroll-lookback-audit/T-136 (T-136 part B)

Reviewer: reviewer agent, 2026-11-26. Diff: `git diff main...p/holiday-pay-payroll-lookback-audit/T-136` (b04caac..8203d5e, 4 commits, 6 files, +38/-13).

## Summary

Small, well-scoped follow-ups from reviews/T-135-qa.md and reviews/T-135-review.md:

- **F-1:** `report/builder.py:140-143` blanks `due` and `difference` in exceptions.csv for `cannot_check` rows. `paid` and `direction` are still shown.
- **F-4:** the pro-rata split at the 4-week point is documented in `ingest/FORMAT.md:20` and pinned in `tests/test_t135.py:33-42`.
- **Flag change:** `engine/lookback.py:93`. `reference_week_basic_differs_from_contract` now ignores reference weeks with zero basic. The flag text in `report/builder.py:30` was updated to match.
- **Test nits:** dead code removed from `tests/test_differential.py` and a docstring corrected. What the test checks is unchanged.

Test run, from the product folder in /home/user/wt-build:

```
python3 -I -X dev -W error::ResourceWarning -m unittest discover -s tests -t .
Ran 299 tests in 30.516s
OK
```

## Correctness

**F-1 (blanking `due` and `difference`).** The change is only in how the CSV is written. `_csv_row` formats strings from the engine row and does not change the row itself. So:

- **Totals and counts.** The summary totals and counts (`builder.py:424-439`) already left out `cannot_check(r)` rows and still read the numeric `r["difference"]`. They are unchanged.
- **Exception selection.** `audit()` (`builder.py:80`) still selects `cannot_check(r) or abs(diff) > threshold`, so these rows are still exceptions and the exception count is unchanged.
- **Direction.** `_direction(r["difference"], r)` still returns `cannot_check` first.
- **report.md.** `explain()` (`builder.py:169-171`) already printed no due figure for these rows.
- **Downstream readers.** No production code reads exceptions.csv back. `report/rolled_up.py` builds its own rows and already used blank `due` and `difference` for rule flags (`builder.py:131-135`). `audit.py` and the mapper do not parse the output. Neither do the golden or sample files: none contain `cannot_check`.
- **Differential test.** It already treated `cannot_check` rows as not comparable (`test_differential.py:225-227`).

The blank is consistent with the existing rolled-up `rule_flag` convention, and FORMAT.md says so. Excel and pandas users will see empty cells, not 0.00. That is the intended behaviour.

**Flag change.** The new condition is `basics[i] > 0 and basics[i] != current`, applied only when `contract_basic` is given. I checked whether this could hide a real contract-rate mismatch:

- **Partial-basic weeks still fire.** A week where basic was paid at a different amount (part-basic or a rate change, for example 60 against a contract of 100) still raises the flag. `test_part_basic_week_still_fires_basic_differs_flag` pins this. That is the mismatch a payroll professional cares about.
- **What it no longer flags.** It no longer flags a reference week with pay but zero basic, for example an overtime-only week. For fixed-pay workers, `due` uses the contract basic plus the variable average (`lookback.py:95`), so basic in reference weeks does not change `due`. The flag was noise in those weeks.
- **Residual visibility.** If the zero-basic week is the latest week, `latest_week_basic_differs_from_rate_used` (`lookback.py:91`) still fires. Earlier zero-basic reference weeks are now silent (see S-1).

## Test quality

- `test_t121.py:87-91` asserts the exact CSV triple `("100.00", "", "")`. It is behavioural, but it only checks `ex[0]`. That is fine because it is a single-row case.
- `test_t121.py:85` adds an "Underpayments: 0" assert. Good.
- `test_t135.py:44-50`: the two flag tests cover both sides of the new condition.
- `test_t135.py:33-42` (straddle): the arithmetic is right. Normal pay is 200 and basic is 100, so 0.5 x 200 + 0.5 x 100 = 150. But the first `LeaveEntry` has `weeks=3.5`, which the CLI rejects (FORMAT.md: weeks at most 1). So the test does not exercise the "fractions accumulate across rows" claim the doc makes. It reaches the same counter, but a test made of realistic rows would pin the documented behaviour (see S-2).

## Docs accuracy

- FORMAT.md:20 (straddle) and FORMAT.md:24 (blank `due`/`difference`) match the code.
- The flag text change is accurate.
- `builder.py:170` still says "Any recalculated figure shown is not reliable". No figure is shown in report.md or in the CSV now, so the sentence is stale but harmless (S-3).
- README.md:27 describes exceptions.csv as "one row per leave week whose difference exceeds the threshold". It omits `cannot_check` rows. This was already true before this branch, and BRIEF.md:32 is correct (S-4).

## Security and performance

There is no new input handling. CSV output still goes through `_safe`. The flag check is O(52) per leave week, the same as before. There is no AI cost.

## Critical issues

None.

## Suggestions (non-blocking)

- **S-1** `engine/lookback.py:93`: for a fixed-pay worker with a contract basic, a reference week with pay but zero basic (not the latest week) is no longer flagged. It is usually overtime-only or unpaid-leave-plus-overtime. It can also mean a basic element was mapped to the wrong category in the export. If buyers want that signal, add a separate, softer flag such as `reference_week_without_basic`, so it is not folded back into the mismatch flag.
- **S-2** `tests/test_t135.py:38`: replace the single 3.5-week `LeaveEntry` with rows that are valid at the CLI. For example, three 1.0 rows, one 0.5 row, then one 1.0 row, asserting the last row is 0.5/0.5 and due is 150.00. That pins the cross-row accumulation FORMAT.md:20 describes.
- **S-3** `report/builder.py:170`: drop "Any recalculated figure shown is not reliable", or reword it to say no recalculated figure is given.
- **S-4** `README.md:27`: add "and every leave week that cannot be checked (`direction` = `cannot_check`)" to the exceptions.csv description.

Verdict: PASS (non-blocking follow-ups: engine/lookback.py:93, tests/test_t135.py:38, report/builder.py:170, README.md:27)
