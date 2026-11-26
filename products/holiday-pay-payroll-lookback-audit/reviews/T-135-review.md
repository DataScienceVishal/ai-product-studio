# Review: p/holiday-pay-payroll-lookback-audit/T-135

Reviewer gate. Scope: `git diff main...HEAD` adds `tests/test_differential.py` (300 lines) and `reviews/T-135-qa.md` (33 lines). No product code changed.

## Verdict: CHANGES

The test is good and can merge almost as it is. The QA report labels F-3 a doc ambiguity, but going by the engine code and the gov.uk rule it is a probable engine bug that understates holiday pay due. The report's headline "0 engine bugs" is therefore wrong, and the oracle locks in that behaviour without saying it is disputed. Only the report and a comment need to change; no code needs to be rewritten.

## Evidence

### 1. Deterministic, hermetic, passes
- Command, run from the product folder: `python3 -I -X dev -W error::ResourceWarning -m unittest discover -s tests -t .`
- Result: `Ran 293 tests in 30.400s` / `OK` (wall clock 30.5 s). No ResourceWarning was raised.
- Deterministic: each case uses `random.Random(seed)` with seeds 0..329 and a fixed base date. The leave dates are a set, but they are sorted before use. Nothing depends on the clock.
- Hermetic: every input and output sits in a `tempfile.TemporaryDirectory()`. All files are opened in `with` blocks. The CLI runs with `-I` and a 60 s timeout. The only places the CLI writes are `report/builder.py:231` (`out_dir`) and its fdopen. Nothing in `audit.py`, `report/` or `ingest/` uses the network. `git status` was clean after the run.

### 2. The oracle tests real behaviour
- Imports (lines 19-28) are all stdlib: csv, os, random, subprocess, sys, tempfile, unittest, datetime, decimal, fractions. Nothing from engine, report, ingest or mapper is imported. The CLI is driven as a black box.
- The oracle is not a tautology. It computes with exact `Fraction` arithmetic and its own windowing and leave-year logic, then compares paid, due, difference, direction and ref_weeks_used to the penny.
- Mutation check: each mutation was made in a scratch copy of the product folder, then the copy was deleted. The real tree was never edited, and `git status` was clean afterwards.

| Mutation | Result |
|---|---|
| `engine/reference.py` `MAX_PAID_WEEKS = 52` -> `51` | 155 of 330 cases disagree; the sample test also fails (failures=2) |
| `engine/reference.py` `MAX_LOOKBACK_WEEKS = 104` -> `103` | 183 of 330 cases disagree |
| `engine/lookback.py` `NORMAL_WEEKS = Decimal(4)` -> `Decimal(3)` | 277 of 330 cases disagree |

### 3. Triage of F-2 and F-3

**F-3 (fixed_pay drops weeks with overtime but no basic): probable ENGINE BUG, not just a doc ambiguity.**
- Code: `engine/lookback.py` lines 77-83, in the `_fixed_pay_refs` loop, `if b == 0: continue`. A week counts as "paid" only if basic > 0, so regular_overtime, commission and allowance paid in that week leave the variable average.
- Rule: gov.uk says to average pay over the 52 weeks in which the worker was paid, skipping only weeks with no pay. The product's own docs say the same: BRIEF.md line 31 ("skipping weeks with no pay") and FORMAT.md line 50 (`ref_weeks_used`: paid weeks). A week with regular overtime is a paid week, and regular overtime counts for reg 13 pay (`engine/elements.py`, `COUNTS_FOR_NORMAL`).
- Effect: due is understated. The QA repro gives 120.00 where 124.00 is due, so a real underpayment can be missed. For an underpayment audit this is the worse direction to be wrong in. It also does not match variable_hours, which counts the same week (`engine/reference.py`: any pay > 0 counts).
- In practice such weeks are uncommon for a fixed-pay worker (for example a week of unpaid leave with overtime paid in arrears), so severity is medium. The direction of the error is still the wrong one.

**F-2 (basic-only weeks average basic over the 52 most recent weeks with basic > 0): DOC AMBIGUITY is fair, but it also needs a product decision.**
- Code: `engine/lookback.py` line 140 runs a second, separate `reference_average` over `basic_pay`, so weeks with zero basic are skipped on their own. `ref_weeks_used` in exceptions.csv reports the normal-pay count (`wn`), so for basic-only rows it does not describe the average that was used. That is a small reporting inaccuracy.
- On the rule: "basic per week basic was paid" is a defensible reading for reg 13A. It errs towards a higher due, which means false underpayment flags rather than missed ones. That is acceptable for an audit tool if it is documented. Accept the triage, plus a FORMAT.md line, plus either reporting the basic week count or noting that `ref_weeks_used` refers to the normal-pay weeks.

## Critical issues (must fix before merge)
1. **`reviews/T-135-qa.md`, F-3 row and the "No engine bug found" line.** Re-triage F-3 as a probable engine bug (fixed_pay understates due when a week has variable pay but no basic). Record it as a follow-up board task for builder, with the 120.00 vs 124.00 repro and a pointer to `engine/lookback.py:77-83`. Why it matters: once merged, this report is the studio's evidence that the engine is correct, and it hides a gap that can miss underpayments.
2. **`tests/test_differential.py` lines 87-89 (the fixed_pay "probed" branch).** Add a comment that this line pins the disputed F-3 behaviour and must change together with the engine fix. Otherwise whoever fixes the engine will see this test fail and may "fix" the engine back.

## Suggestions (non-blocking)
- Dead code: `LAST_TYPES` (around line 243) is written but never read. In `run_case` the `fr` return from `finish_paid` is unused, and `finish_paid`'s `threshold` parameter is unused.
- The `avg_of_most_recent` docstring says "average rounded half-up", but it returns an unrounded Fraction. The code is right (F-6); fix the docstring.
- The scenario isn't covered (QA lists it): `contract_weekly_basic` changing mid-history, and the rolled-up workers path.
- The run adds about 27 s to the suite. That is fine now; if the suite grows, consider an environment variable to change N.

## Re-review (commit 4ce528c): PASS

Both critical issues from the first review are resolved.

- **The fix matches the rule.** `engine/lookback.py:80` now reads `if normal_pay(p) <= 0: continue`. A paid week is now any week with basic, regular_overtime, commission or allowance above 0. This matches gov.uk ("52 weeks in which they were paid", skipping weeks with no pay) and matches variable_hours (`engine/reference.py`, pay > 0). Weeks with only SSP, a non-regular bonus, expenses or holiday_pay are still skipped, because `normal_pay` excludes those categories.
- **The repro numbers are right.** Four weeks of 100+20 plus one overtime-only week of 40 give variable average (4x20+40)/5 = 24, so due is 124.00. With 60 instead of 40 the average is 28, so due is 128.00.
- **The regression tests check behaviour.** `tests/test_t135.py` checks both the due amount and `weeks_used` (5, or 4 when there is an empty week and a week with only holiday_pay).
- **The oracle was fixed independently.** The fixed_pay special case is gone, and the oracle now uses `s > 0` over its own category sums. It is not a copy of the engine.
- **Goldens and samples are unchanged.** `git diff main...HEAD -- tests/golden samples` produces 0 lines.
- **Suite:** `python3 -I -X dev -W error::ResourceWarning -m unittest discover -s tests -t .` gives `Ran 295 tests in 30.020s` / `OK` (30.2 s wall clock). `git status` is clean.
- **Docs:** README.md and FORMAT.md now cover F-2 (the basic average uses a different set of weeks from `ref_weeks_used`) and the fixed_pay paid-week rule.

Non-blocking follow-ups:
- Overtime-only weeks are now in `idx`, so `reference_week_basic_differs_from_contract` (`engine/lookback.py:93`) fires for them, because their basic is 0 and not the contract rate. That is arguably a useful signal, but its text in `report/builder.py:30` doesn't explain it. With `include_flagged`, the row may also be listed. Consider changing the text to "some reference weeks have no basic or a basic different from the contract", or check only weeks with basic > 0.
- `reviews/T-135-qa.md` line 14 still says "No engine bug found". Update it to say one engine bug was found and fixed (F-3).
- The earlier suggestions about dead code and the docstring still stand.
