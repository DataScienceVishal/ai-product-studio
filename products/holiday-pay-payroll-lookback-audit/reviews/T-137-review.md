# Review: T-137 (branch `p/holiday-pay-payroll-lookback-audit/T-137`, commit 8a00370)

Reviewer: reviewer agent, 2026-11-26. Diff: `git diff origin/main...8a00370` (8 files, +143/-55).

## Verdict: CHANGES

The engine change is correct for what it sets out to do, and the always-exception rule cannot be bypassed. Two small items block the merge. (1) The report.md summary line now gives a count that its own label does not describe. (2) The docs describe the fallback inaccurately for the long-sickness case, and in that case the code picks a figure that the window rule had just rejected.

## Summary

- `engine/lookback.py:68-78`: for a blank contract, the rate is now the most recent basic > 0 among non-statutory weeks in the 8 weeks before the leave. If there is none, it is the most recent basic > 0 anywhere. The leave week is excluded because `recent_first` starts at i=1 (`lookback.py:136`). New flags: `rate_inferred_ambiguous` and `no_basic_pay_found`.
- `report/builder.py:64-96`: `always_exception()` is OR-ed into the exception filter independently of `threshold` and `include_flagged`. Flags come only from the engine, so input cannot set or suppress them, and no CLI option skips the check. **Bypass: none found.**
- This fixes T-136 F2 (a rise 1 to 3 weeks before the leave was silently missed), F3 (the fallback is now flagged and listed) and F5 (`no_basic_pay_found`).
- Tests: `python3 -m unittest discover -s tests -q` on the branch tree gives **Ran 311 tests in 41.3s, OK**.

### Edge cases probed (direct engine calls)

| Case | Rate used | Flags | OK? |
|---|---|---|---|
| Leave week itself carries basic 999 | 500 (leave week excluded) | inferred only | yes |
| Consecutive leave weeks (basic 0 in leave weeks) | 500 for both | inferred only | yes |
| Part-leave week (basic 200 + holiday 300) 2 weeks before a full leave week | 500 | **ambiguous** (forced exception at diff 0) | correct figure, noisy (S2) |
| 10 SSP-only weeks, then 500 before that | 500 (fallback) | ambiguous | yes |
| 10 weeks of partial basic 100 + SSP, then 500 before that | **100 (fallback)** | ambiguous | **no (M2)** |
| One-off back-pay week of 1000 just before the leave | 1000, shows "underpaid £500" | ambiguous | flagged; wording gap (S1) |

### Mutation check (each mutant applied alone, full suite run)

| Mutant | Result |
|---|---|
| `cands[0]` changed to `cands[-1]` (oldest in the window) | killed (10 failures) |
| statutory filter removed from the window | killed (5) |
| `RATE_WINDOW` 7 / 9 | killed (3 / 5) |
| no ambiguous flag on the fallback path | killed (5) |
| `len(set(cands)) > 2` | killed (8+1) |
| window skips the most recent week (`[1:8]`) | killed (5) |
| `no_basic_pay_found` never set | killed (2) |
| `always_exception` removed from `audit()` | killed (4+1) |
| `rate_inferred_ambiguous` removed from `ALWAYS_EXCEPTION_FLAGS` | killed (3+1) |
| `no_basic_pay_found` removed from `ALWAYS_EXCEPTION_FLAGS` | **survives**. This is an equivalent mutant: `no_basic_pay_found` can only come from the fallback path, which always adds `rate_inferred_ambiguous`. Keeping it is fine as defence in depth (see S4). |

The tests check behaviour and would catch real regressions in the new rule.

## Critical issues (must fix)

### M1. The report.md summary line now gives a count its label does not describe
`report/builder.py:451`: `- Exceptions (difference over {threshold}, or cannot be checked): {len(lb_exc)}`.
`lb_exc` now also includes ambiguous or no-basic rows with a difference of 0 (or under the threshold). Take a firm whose only blank-contract worker had a pay rise and was paid correctly. The summary reads "Exceptions (difference over £0.01, or cannot be checked): 1", "Underpayments: 0", "Overpayments: 0", "could not be checked: 0". The label says something that is false for that row, and nothing in the summary explains the gap. This is the default path, not just `--include-flagged`. The report is the product, and an adviser who reconciles the counts will lose trust in it. I am blocking because this output is misleading and the fix is one line.
**Fix:** change the label to `Exceptions (difference over £x, cannot be checked, or weekly rate guessed): N`. Ideally also add a line `- Leave weeks with a guessed weekly rate (always listed): K` that counts `always_exception` rows. Update `tests/golden/main_report.md` and `main_nw_report.md`, and add one assertion on the new line for a zero-difference ambiguous row.

### M2. The fallback reuses statutory-week basic that the window rule just excluded, and the docs say otherwise
`engine/lookback.py:75`: `next((b for b in basics if b > 0), Decimal(0))` scans all weeks, statutory ones included.
Take a worker on long-term sickness: 8 or more weeks of reduced basic (company sick pay) plus SSP, then holiday, with full basic 500 before the sickness. The window rejects every sick week as unreliable. The fallback then takes the most recent of those same sick weeks, so the rate is 100, not 500 (probed). If the employer correctly paid 500, the report shows a false **overpayment of £400**. If they paid 100, it shows "correct". The row is flagged and listed, so this is not silent. But it is a wrong figure in a scenario that matters legally: holiday at the end of sick leave is the Stringer line of cases.
The logic itself is on main already (pinned by `tests/test_edge_cases.py:224-231`), but this branch writes new docs that describe it wrongly. `ingest/FORMAT.md` says "If none of those 8 weeks has basic pay, the most recent basic anywhere before the leave is used". In this case those weeks do have basic pay, and the code uses it. So docs and code disagree.
**Fix (recommended):** in the fallback, prefer the most recent non-statutory basic > 0 anywhere, then any basic > 0:
`next((b for p, b in zip(recent_first, basics) if b > 0 and dec(p.get("statutory", 0)) <= 0), next((b for b in basics if b > 0), Decimal(0)))`.
I tried this change: it fails only `test_fixed_pay_all_recent_weeks_ssp_fallback` and the two `FixedPayChangingBasic` oracle tests. Update those to expect 500 and update `inferred_basic()` in `tests/test_t136_oracle.py` to match.
**Minimum alternative:** keep the code, and make FORMAT.md, README and BRIEF say "if none of those 8 weeks is a non-statutory week with basic, the most recent basic anywhere before the leave (including a week with SSP/SMP) is used".

## Suggestions (non-blocking)

- **S1. FLAG_TEXT for `rate_inferred_ambiguous`** (`builder.py:29-32`) gives only two explanations: "a pay rise?" or the fallback. The changed tests show two more cases. If the most recent week in the window was a part week, the result is a false overpayment (`test_fixed_pay_short_week_before_leave`, -£400). If it was a back-pay week, the result is a false underpayment (`test_fixed_pay_back_pay_week_not_the_rate`, +£500). Add: "or the most recent week was a part week or contained back pay, so the figure may be wrong in either direction".
- **S2. Noise from part-leave weeks.** A week with `holiday_pay` > 0 and reduced basic sits in the window for 8 weeks. During that time every later leave week becomes a forced exception at difference 0. Consider leaving weeks with `holiday_pay` > 0 out of the window, as statutory weeks are. Real exports from blank-contract firms will often contain these.
- **S3. `explain()`** prints "Result: correct by £0.00" for a forced-exception row. Consider appending "(listed because the weekly rate was guessed; see flags)" when `always_exception(r)` is true. The CSV `direction` of `correct` is fine.
- **S4.** The `no_basic_pay_found` entry in `ALWAYS_EXCEPTION_FLAGS` is currently redundant (equivalent mutant). Keep it, but add a one-line unit test on `always_exception({"flags": ["no_basic_pay_found"]})` so a future refactor of the fallback flag cannot quietly make it matter.
- **S5.** In `tests/test_differential.py:98-101` the oracle models only the fallback path of the ambiguity rule. That is correct because its generator keeps basic constant for blank workers, but say so in the comment so nobody adds varying basic there and gets confusing failures.

## Security / performance

No new input surface. Flags are engine-generated. The CSV `flags` cell still goes through `_safe()`. The rate logic is O(8) per leave week, with no performance concern.

## Docs vs code

FORMAT.md, README and BRIEF match the code apart from the fallback wording (M2) and the summary label (M1). The F1 limitation line is present and accurate in all three.

## Re-review (commit 401045d, delta `git diff 8a00370 401045d`)

### Verdict: CHANGES (one test-only item)

The code fixes are correct. The one item left is a test-only gap: the report lines added to fix M1 have no test, and mutating any of them leaves the suite green.

- Full suite on 401045d: **Ran 313 tests in 41.8s, OK**.
- **M1 code: fixed.** `builder.py:455` now reads "Exceptions (difference over £x, cannot be checked, or weekly rate guessed)". `:457` adds "Leave weeks with a guessed weekly rate: K". Both goldens are updated. I checked end to end through the CLI with a blank contract, a rise 3 weeks before the leave, and paid equal to the new rate. Result: exceptions.csv `0.00,correct`, summary "Exceptions ... : 1", "guessed weekly rate: 1", 0 under, 0 over. `explain()` prints the new "Listed although the difference is £0.00" line. The counts now add up.
- **M2: fixed.** `lookback.py:75-79`: the fallback takes the latest non-statutory basic, then any basic, then 0. New tests: `test_fixed_pay_long_sickness_uses_last_full_pay_rate` (expects 500) and `test_fixed_pay_only_ssp_weeks_carry_basic` (expects 100, no `no_basic_pay_found`). The pinned SSP test now expects 500. `inferred_basic()` in the oracle is updated to match. BRIEF, FORMAT.md and the docstring all describe the new order.
- **S1: done** (FLAG_TEXT now covers part and back-pay weeks). **S3: done** (explain line).

### Mutants rerun

All 12 engine and gate mutants are killed: oldest-in-window, no statutory filter, window 7 and 9, no fallback flag, `>2`, window skipping the latest week, no zero flag, `always_exception` removed, ambiguous not forced, plus 2 new ones (fallback ignores statutory again: 4 failures; no last-resort step: 1 failure).

**Three report-layer mutants survive. Each one undoes part of the M1 fix without failing a test:**
1. "Leave weeks with a guessed weekly rate" hard-coded to `0`. The goldens only cover 0.
2. The "Exceptions" count with guessed-rate rows subtracted again, which brings back the original mismatch.
3. The `explain()` "Listed although the difference is £0.00" line removed (`if False:`).

### Must fix
- **R1. Add one CLI test** for a zero-difference ambiguous row. In `HandComputed` (`tests/test_t136_oracle.py`), reuse the `test_f2_zero_difference_after_rise_is_still_an_exception` input (paid 200.00, threshold 0.01). Read `out/report.md` and assert all three of: it contains `- Exceptions (difference over £0.01, cannot be checked, or weekly rate guessed): 1`, it contains `- Leave weeks with a guessed weekly rate: 1`, and it contains `Listed although the difference is £0.00`. That kills all three surviving mutants. `run_cli` already writes `out/` into the temp dir, so only the read and the asserts are new.

### Nit (non-blocking)
- FORMAT.md, "Blank contract_weekly_basic": "If none of those 8 weeks has basic pay" should read "has basic pay outside an SSP/SMP week". With the new fallback the outcome is the same, but the trigger is described wrongly.
- S2 (exclude part-leave weeks from the window) and S4 (unit test for `always_exception` with only `no_basic_pay_found`) are still open, and still optional.
