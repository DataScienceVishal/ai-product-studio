# Review: T-138 (branch `p/holiday-pay-payroll-lookback-audit/T-138`, commit af98a92)

Reviewer: reviewer agent, 2026-11-26. Diff: `git diff origin/main...af98a92` (5 files, +36/-6). This branch implements suggestions S2 and S4 from the T-137 review.

## Verdict: PASS

## Summary

- **S2.** `engine/lookback.py:69`: for a blank contract, the 8-week rate window now also skips weeks with `holiday_pay` > 0. A part-leave week, where basic is reduced and holiday pay is paid beside it, no longer sets the rate. It also no longer makes the next 8 weeks of leave forced exceptions at difference 0.
  - The statutory filter, the fallback and the flags are unchanged.
  - The leave week itself was already outside the window.
  - Consecutive full leave weeks were already skipped, because they carry basic 0.
- **S4.** `tests/test_edge_cases.py` adds an `AlwaysException` class that unit-tests `always_exception()` for each flag on its own and for flags that should not trigger it.
- **Oracle.** `inferred_basic()` applies the same holiday_pay filter. `finish_paid()` now gives 25% of generated leave weeks a reduced basic beside the holiday pay, so the random oracle tests exercise the new filter, including through the variable-pay averages.
- **Hand test.** `test_part_leave_week_in_window_is_not_ambiguous` checks that the rate is 100.00 and that the row has no ambiguous flag.
- **Docs.** BRIEF, FORMAT.md and the docstring all describe the new filter.
- **Full suite:** `Ran 316 tests in 56.7s, OK`.

## Mutants (each applied alone, full suite)

| Mutant | Result |
|---|---|
| holiday_pay filter removed | killed (3) |
| `holiday_pay <= 0` changed to `< 0` | killed (6) |
| `no_basic_pay_found` removed from `ALWAYS_EXCEPTION_FLAGS` | **killed (1)**. This mutant survived in T-137; the S4 test now catches it. |
| `always_exception` returns true for any flag | killed (9) |

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. The fallback can still take basic from a part-leave week.** `lookback.py:75` prefers non-statutory weeks but does not skip holiday_pay weeks. I probed this case:
  - weeks 0 to 9 before the leave are unpaid, except one part-leave week with basic 200 and holiday pay 300;
  - full basic before that is 500.
  - The engine picks rate 200 (`latest_week_fallback`), not 500.

  The row is flagged `rate_inferred_ambiguous`, so it is always listed and the error is not silent. The case is also rare: it needs no clean basic week in the 8 weeks before the leave. That is why I am not blocking. For consistency with the window rule, the fallback could try, in order:
  1. non-statutory weeks without holiday pay;
  2. any non-statutory week;
  3. any week;
  4. 0.

  If you make that change, mirror it in the `stat_ok` loop of `inferred_basic()` in the oracle.
- **S2. FORMAT.md fallback trigger.** The text says "If none of those 8 weeks has basic pay outside an SSP/SMP week". It should now say "outside an SSP/SMP week or a week with holiday_pay". Today the value comes out the same, because the fallback then picks that same part-leave week, but the trigger is described inaccurately.
- **S3. Cosmetic.** `tests/test_edge_cases.py` gains a trailing blank line at the end of the file.

## Security / performance

No new input surface. The extra filter adds one dict lookup per window week.
