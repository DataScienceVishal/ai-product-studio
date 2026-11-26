# Review: p/holiday-pay-payroll-lookback-audit/T-140 (commit 3321ed6)

Reviewer: reviewer agent, 2026-11-26. Diff: `git diff origin/main...p/holiday-pay-payroll-lookback-audit/T-140`.

## Verdict: PASS

## Summary

One test added to `tests/test_edge_cases.py` (+9 lines, no product code changed):
`Lookback.test_fixed_pay_fallback_tier2_prefers_part_leave_over_newer_ssp`. It closes
suggestion S1 from `reviews/T-139-review.md` (tier 2 of the blank-contract rate fallback in
`engine/lookback.py` lines 74-85 had no test).

## Does it exercise tier 2 specifically?

Fixture: 60 weeks of `regular_overtime: 20` (no basic), plus the most recent week
`{basic 80, statutory 99}` (SSP) and the week 3 weeks earlier `{basic 200, holiday_pay 300}`
(part-leave). No contract basic is passed.

- 8-week window branch: not taken. Both basic-bearing weeks sit inside the window, but one is
  statutory and the other has holiday pay, so `cands` is empty and the code falls through to the fallback.
- Tier 1 (no statutory and no holiday pay): no week passes it, because every week with basic > 0 is
  excluded.
- Tier 2 (not statutory): matches the part-leave week, so the result is 200.
- Tier 3 (any week with basic): would return 80, the newer SSP week. The test asserts 200, so it
  tells tier 2 apart from tier 3.

The assertions on `basic_source == "latest_week_fallback"` and the `rate_inferred_ambiguous` flag
confirm that the fallback path ran, not the window path.

## Mutation evidence

I deleted the tier-2 lambda (`lambda p: dec(p.get("statutory", 0)) <= 0,`) from `engine/lookback.py`:

- Result: `Ran 318 tests ... FAILED (failures=1)`. The only failure was the new test:
  `AssertionError: Decimal('80.00') != Decimal('200.00')`.
- So this test is the only one that kills the mutant, which matches the T-139 finding that the
  mutant survived without it.
- I restored the file with `git checkout engine/lookback.py`, and `git status` was clean afterwards.

## Test run

From the product folder, `python3 -I -m unittest discover -s tests -t . -v`:
`Ran 318 tests in 44.3s, OK`, with the new test reported as `ok`. Test definitions in
test_edge_cases.py went from 46 on origin/main to 47 on the branch.

## Critical issues

None.

## Suggestions (non-blocking)

- S1: The inline comment `# no full week with basic anywhere` is accurate. A short comment saying
  why the SSP week has to be the more recent one (so that tier 3 would give a different answer)
  would help a future maintainer keep the test meaningful.
