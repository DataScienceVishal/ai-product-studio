# Review: T-139 (branch `p/holiday-pay-payroll-lookback-audit/T-139`, commit e76e55d)

Reviewer: reviewer agent, 2026-11-26. Diff: `git diff origin/main...e76e55d` (5 files, +26/-8). This branch implements suggestion S1 from the T-138 review.

## Verdict: PASS

## Summary

- **Engine.** In `engine/lookback.py:75-85`, the blank-contract fallback now tries four tiers in order:
  1. the latest basic in a full week (no SSP/SMP and no holiday_pay);
  2. the latest basic in any non-statutory week;
  3. any basic;
  4. 0.

  The window rule and the flags are unchanged. Tier 4 still sets `no_basic_pay_found`. Every tier scans the same 104 weeks as before.
- **Oracle.** `inferred_basic()` in `tests/test_t136_oracle.py` mirrors the same tier order over 104 weeks.
- **New test.** `test_fixed_pay_fallback_skips_part_leave_week` replays the case I probed in T-138 (a part-leave week with basic 200 in the window, full weeks of 500 before it). It now expects 500 and the `latest_week_fallback` source.
- **Docs.** FORMAT.md and BRIEF describe the four-tier order and the corrected trigger ("outside an SSP/SMP or holiday_pay week"). That resolves T-138 S2 as well.
- **Full suite:** `Ran 317 tests in 44.3s, OK`.

## Mutants

| Mutant | Result |
|---|---|
| Tier 1 no longer skips holiday_pay weeks | killed (3) |
| Tier 3 removed (SSP-only basic gives 0) | killed (1) |
| Tier 2 removed (falls straight to "any basic") | **survives** |

## Critical issues

None.

## Suggestions (non-blocking)

- **S1. Tier 2 has no test.** It only matters when two things are both true:
  - no full week with basic exists in the 104 weeks;
  - a statutory week with basic is more recent than a part-leave week.

  That is rare, which is why I am not blocking. One engine test would pin it. History: an SSP week with basic 80 one week before the leave, a part-leave week with basic 200 four weeks before, and no other basic. Expect 200 from tier 2, not the 80 that tier 3 would give.
