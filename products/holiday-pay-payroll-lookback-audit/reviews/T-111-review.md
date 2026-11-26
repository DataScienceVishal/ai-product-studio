# Review: p/holiday-pay-payroll-lookback-audit/T-111 (kill-test Part A)

Reviewer run, 2026-11-26. Branch HEAD `42d355f`, diff vs `main` is limited to `products/holiday-pay-payroll-lookback-audit/` (10 files, +552). The branch merges cleanly with `origin/main` (`82ec2ee`).

## Verdict: CHANGES

The engine is small, readable, stdlib-only and uses Decimal throughout. The official figures I re-fetched reproduce exactly, and the builder's recorded disagreements with gov.uk arithmetic are all real. Mutation testing kills 18 of 20 mutants; one survivor is equivalent. It does not pass yet for four reasons:
1. Two of the "encoded" official examples (E12, E13) never run the engine on the published inputs.
2. Basic pay is averaged for every worker, which gives the wrong answer for fixed-pay workers.
3. The look-back fails silently when dates are misaligned.
4. One test does not test the rule it is named for.

## Kill-test marks

| Mark | Result | Evidence |
|---|---|---|
| A1 Official examples | **FAIL (not a KILL)** | 15 of 17 encoded examples run engine code and match the published figure, or a correctly recorded disagreement. E12 sums the 52 *published intermediate* weekly figures (Table 4), not the published inputs (Table 3 monthly pay and hours plus weekly hours). E13 is arithmetic inside the test (`D(1250)/D(130)`): the engine has no monthly-to-weekly function at all. So for these two the "engine's output equals the published figure" condition is unmet. The KILL line is not hit, because none are left out without a reason and none disagree. |
| A2 Coverage | **PASS (grey zone: 3 of 4 areas)** | 52-week, skip and 104 cap: E11, E14, E15, E16. 12.07%: E3. Rolled-up: E5, E6. Overtime/commission: no official numeric example exists. I re-fetched G1, G3, A2 and A4 and found only the rule text ("overtime payments, if a worker has regularly been paid these during the last year"). The kill line is "fewer than 3", so it is not hit. The 4th area is covered only by the builder's own tests (`Elements`, `Lookback`). |
| A3 Look-back | **PASS** | `lookback()` returns, for each leave week, `paid`, `due` and `difference` (positive means underpaid), the normal/basic split, and `working` for both normal and basic (`weeks_used`, `weeks_scanned`, `weeks_skipped`, `total`, `average`, `shortened`). Checked on 110 weeks of 300 basic + 60 overtime: paid 300.00, due 360.00, difference 60.00, 52 weeks used, total 18,720.00. Suggestion S1 covers what is still missing. |
| A4 Tests | **Tests PASS; reviewer PASS withheld** | `python3 -I -m unittest discover -s tests -t .` from the product folder on Python 3.11.18 gives `Ran 38 tests in 0.007s` / `OK`. I got the same result (`Ran 38 tests in 0.012s OK`) on the simulated merge tree (`git merge-tree --write-tree origin/main HEAD`, archived to a scratch dir). A4 needs a reviewer PASS, and this review is CHANGES. |

## Official examples re-checked

I fetched these pages with curl on 2026-11-26 and treated them as data: Acas irregular-hours, rolled-up, calculating-holiday-pay (irregular), checking-holiday-entitlement/calculating-holiday-pay; gov.uk calculate-holiday-entitlement, holiday-pay-the-basics, holiday-pay; and the gov.uk PDF via pdftotext. Then I recomputed each figure in Python with Decimal and ROUND_HALF_UP.

| ID | Published text (verbatim figure) | Recomputed | Test asserts | OK |
|---|---|---|---|---|
| E1/E2 | "3 days a week ... 16.8 days (3 × 5.6)"; "6 days a week ... 28 days" | 16.8; min(33.6, 28) = 28 | 16.8, 28 | yes |
| E3 | Jamie "70 hours ... works out as 8 hours, after rounding down the part hour that is less than 30 minutes" | 70 × 0.1207 = 8.449 h (27 min), so 8 | 8 | yes |
| E5/E6 | Jian "£1,000 ... £120.70"; "£500 ... £60.35" | 120.70; 60.35 | same | yes |
| E11 | Table 5 "£12,040 ÷ 52 = £231.34" | sum = 12,040; 12,040/52 = 231.54 | 231.54, with the disagreement recorded | yes (published typo confirmed) |
| E12 | Annex "total pay received was £14,606.66 ... average ... £280.90" | the 52 test values match the Annex week by week; sum 14,606.66, average 280.90 | same | figure yes, method no (B1) |
| E13 | "£1,250 ÷ 130 = £9.62 ... £9.62 x 25 = £240.38" | the unrounded rate gives 240.38 / 192.31 / 336.54; the rounded 9.62 gives 240.50 / 192.40 / 336.70 | the unrounded figures, with the disagreement recorded | figure yes, engine not used (B1) |
| E17 | Table 7 "£20,520 ÷ 52 = £394.62", "1.66 weeks", "£394.62 x 1.66 = £652.09", note "figures used ... are the exact, unrounded figures" | 108/366 × 5.6 = 1.652459...; 394.615... × 1.652459 = 652.09; 394.62 × 1.66 = 655.07 | 394.62 and 652.09, plus 655.07 to document the conflict | yes (disagreement recorded correctly) |

The Table 4 weekly figures in the PDF itself use unrounded hourly rates. For example, 25 × 1300/105 = 309.52, while 25 × £12.38 = 309.50. This confirms the builder's E13 note.

### "Left out" reasons

All but one hold up. I checked each against the PDF and the Acas text, and they have no numeric answer (Joe, Tables 1, 6, 8, 9, short contract, payment timing, Sam/Alex/Mel/Frankie, Pat's reduced hours).

The weak one is **Table 4 "Weeks 9-43 ... Average = £281.56"**. It is a published figure and reproduces exactly: the Annex weeks 9-43 sum to 9,854.56, and 9,854.56/35 = 281.5589, which rounds to 281.56. It is easy to encode, so the builder is not dodging a hard example, but "illustrative, not a full calculation" is not a reason to leave out a published number. Encode it (N1).

## Mutation testing (scratch copy, product code untouched)

| Mutant | Result |
|---|---|
| M1 ACCRUAL_RATE 0.1207 to 0.12 | killed (4 fails, incl. E5, E6) |
| M2 drop the 104-week cap (104 to 100000) | killed (`test_104_cap`) |
| M3 count zero-pay weeks (`if pay == 0` to `if False`) | killed (9 fails, incl. E11, E14) |
| M4 52 paid weeks to 53 | killed (3) |
| M5 4 normal-pay weeks to 5.6 | killed (`test_fifth_week_basic_only`) |
| M6/M7/M8 remove overtime / commission / allowance from normal pay | killed |
| M9 `>=` to `>` on the 1 April 2024 start | killed |
| M10 remove the 28-day cap | killed (E2) |
| M11 accrual rounding HALF_UP to DOWN | killed (E4 only) |
| M12 money rounding HALF_UP to DOWN | killed (E11, E12, E13, E17) |
| M13 look-back scan 104 to 52 weeks | killed |
| M14 look-back scan 104 to 105 weeks | **survived** (equivalent mutant: `reference_average` slices to 104 anyway) |
| M15 holiday weeks counted by default | killed |
| M16/M17 non-regular bonus / statutory pay counted | killed |
| M18 4-week split not reset at a new leave year | **survived** (real gap, B4) |
| M19 5.6 to 5.5 weeks | killed |
| M20 difference sign flipped | killed |

## Blocking findings

**B1. E12 and E13 do not exercise the engine on the published inputs, and the engine has no monthly-to-weekly conversion.** Files: `tests/test_official_examples.py:76-87`; no engine function exists.
- *Why:* A1 requires the published inputs to go in and the engine's output to equal the figure. E13 tests the test's own arithmetic. E12 starts from figures the guidance derived, so the split-week logic (Table 4 weeks 5, 18, 22, 31, 35, 44: hours split across two months at two rates) is never implemented or tested. Most UK payroll is monthly, and this product's input is payroll exports, so this is the core path, not an edge case.
- *Fix:* add `weekly_pay_from_monthly(month_pay, month_hours, week_hours_by_month)` (unrounded rate, money at the end). Rewrite E13 to call it. Rewrite E12 to start from the Table 3 monthly pay/hours (Annex, May-20 to May-21) and the Annex weekly hours with month splits, and assert every one of the 52 weekly figures plus 14,606.66 and 280.90.

**B2. Basic pay is averaged over 52 weeks for every worker, so "due" is wrong for workers whose pay does not vary.** File: `engine/lookback.py:46-48`.
- *Why:* for a worker with normal hours and pay that does not vary with the work done (ERA 1996 s221(2)), a week's pay is the contractual weekly pay in force on the calculation date. Only variable elements (regular overtime, commission) are averaged. Reproduced: basic 400, then a rise to 500 for the last 4 weeks, holiday paid at 500. The engine reports due 407.69 and difference -92.31 ("overpaid"), where the correct due is 500.00 and the difference is 0. Any salaried worker with a pay change in the year gets a wrong audit line. E10 ("fixed hours 500") passes only because all 52 weeks are 500.
- *Fix:* add a worker type, or take `contract_weekly_basic` as an input. For the fixed-pay type, `due = contractual basic + 52-week average of the variable normal-pay elements`. As a minimum for Part A, document that the engine covers s224 (no normal working hours) only, and raise or flag for any other type. Add a pay-rise test.

**B3. Misaligned or missing data fails silently as "no difference".** File: `engine/lookback.py:46-50`.
- *Why:* if `LeaveEntry.week_end` is not on the history's week-ending cadence (for example a Friday when history keys are Saturdays), every `history.get` misses. The result is `paid 0.00, due 0.00, difference 0.00, weeks_used 0`. I reproduced exactly that. An audit tool must not report "fine" when it found no data. `test_no_history_zero_due` locks this behaviour in.
- *Fix:* validate that all history keys share one weekday and that each leave `week_end` is on it, and raise if not. Add a `flags` list to each row (`no_reference_weeks`, `shortened`, `leave_week_missing_from_history`) and change the test to expect the flag.

**B4. `test_leave_year_boundary_resets_split` does not test the reset.** File: `tests/test_edge_cases.py:113-122`.
- *Why:* 3 weeks in the old year plus 1 in the new year gives `normal_weeks == 1` whether or not the counter resets (M18 survives).
- *Fix:* take at least 4 weeks in the old year (or 5), then assert that the first week of the new year is fully at normal pay.

## Should fix (not blocking)

- **S1 (A3 working).** `working` gives counts but not *which* weeks. Add `first_week_used` / `last_week_used` (or the list of week-ending dates), and split `weeks_skipped` into no-pay weeks and holiday weeks. Holiday weeks are currently reported as "skipped" with no reason. The adviser cannot tick the working without this.
- **S2. Dead, misleading parameter.** `engine/accrual.py:45`: `part_year_entitlement_weeks(..., round_up_2dp=True)` ignores the flag and always returns the unrounded value, and the docstring says the example "rounds ... up". Either implement it (round up to 2 dp; the default should be False to reproduce 652.09) or remove it.
- **S3. Floats reach Decimal.** `Decimal(v)` on floats (`elements.py:24`, `reference.py:44`, `accrual.py:19,31,41`) carries binary noise: `normal_pay({'basic':0.1,'commission':0.2})` returns `0.30000000000000001665...`. A payroll CSV parsed with float can then mis-round at half-pennies. Either reject floats or convert via `Decimal(str(v))`, and test it.
- **S4. Input validation in the look-back.** Negative or zero `LeaveEntry.weeks` is accepted: `weeks=-1` gives due -300.00. A leave year starting 29 Feb raises an unhelpful `ValueError('day is out of range for month')` in `_leave_year_start`. The leave year is chosen by `week_end`, so a leave week that straddles the leave-year start is attributed by its last day. Document this or split it.
- **S5. Undocumented assumption.** "The first 4 weeks taken in a leave year are the reg 13 (normal-pay) weeks" is a choice that the rules do not dictate. Put it in the README next to the `allowance` assumption, and in SOURCES.md for adviser sign-off.
- **S6.** `rolled_up_pay` and `accrual_hours` take a single figure. Say in the docstring that `period_pay` must be the pay that counts as normal pay (not expenses or a non-regular bonus), or accept a pay dict and use `normal_pay`.

## Nits

- **N1.** Encode Table 4 "weeks 9-43 average £281.56" (9,854.56/35) once B1 exists.
- **N2.** `test_official_examples.py:89`: there is a trailing space after `* 26`. Also, E15 builds 78 paid weeks, not Amy's 75. The assertion still holds, but either match the published 75 or say why not.
- **N3.** `ReferenceResult.weeks_skipped` counts skips only up to the point where 52 paid weeks are found. That is fine, but say so in the field comment.
- **N4.** M14 is equivalent: the `range(1, 105)` in `lookback.py:46` duplicates the cap in `reference_average`. Use `MAX_LOOKBACK_WEEKS` so the cap lives in one place.

## Security and performance

No I/O, network, deserialization or secrets. The look-back is O(leave entries × 104) dict lookups, which is fine. There is no AI cost in Part A.
