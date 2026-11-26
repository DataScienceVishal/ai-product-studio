# Holiday-pay proof test: pre-registered kill test (T-111 / T-25)

Written 2026-11-26T01:37Z by the Studio Lead (run cf48) **before any engine code or model call exists**. Source: validator item 5 in `state/ideas/holiday-pay-payroll-lookback-audit.md` (line 166). Route: pipeline.md proof-test route (idea at 64, no red flag). This file must not be edited after the first run, except to append results below the line.

## Part A: calculation engine (no spend, this run)

The engine is deterministic Python. The checker (reviewer + qa, not the builder) confirms each mark.

| Mark | PASS if | KILL line |
|---|---|---|
| A1 Official examples | Every worked example on the gov.uk holiday pay / holiday entitlement guidance pages and the Acas holiday pay pages that the builder can fetch (listed with URL and fetched date in `benchmark/examples/SOURCES.md`) is encoded as a test with the published inputs, and the engine's output equals the published figure (money to the penny, hours/days to the published rounding) | Any fetched example with a numeric answer is left out without a written reason, or any encoded example disagrees with the published figure after the engine follows the published method |
| A2 Coverage | Examples cover at least: 52-week reference period average (with weeks of no pay skipped and the 104-week cap), irregular-hours / part-year 12.07% accrual (leave years from 1 April 2024), rolled-up holiday pay, and the inclusion of regular overtime/commission in the 4 weeks of "EU" leave | Fewer than 3 of these 4 areas have at least one official example |
| A3 Look-back | Given a synthetic worker's 104+ weeks of pay history and leave taken, the engine lists per-leave-week what was paid, what the rules give, and the difference, with the working shown (reference weeks used, averages) | No per-week exception output, or working not shown |
| A4 Tests | Full engine test suite green on the exact merged tree; reviewer PASS | Any failing test |

## Part B: AI pay-element mapping (needs token spend approval, not run yet)

| Mark | PASS if | KILL line |
|---|---|---|
| B1 Mapping | On 200 synthetic pay-element names (gold labels written by a different agent from the one writing the prompt, frozen before the run) plus the publicly documented BrightPay, Xero and Sage 50 report column layouts, at least 95% are mapped to the correct holiday-pay category (basic, regular overtime, commission, bonus non-regular, allowance, expense/excluded, holiday pay paid, SSP/SMP/excluded) | Below 95%, or any single run of the mapper is retried with a changed prompt after seeing test labels |
| B2 Cost | Under $0.02 per 200-name payroll on the chosen model | Above $0.05 |

## Effect on the score (validator item 5)

PASS on A and B: AI 7 to 8 and Build 11 to 12 (64 to 66). Part A alone moves nothing on the score; it proves the core is buildable and is reused by any MVP. A FAIL on A1 (the published rules can't be reproduced) is a Build red flag and goes to the validator.

---
## Results (append only)

### Part A result (2026-11-26T01:32Z, run cf48)
PASS on A1-A4 (reviewer re-review PASS, reviews/T-111-review.md; merged to main e888e54; merged tree `Ran 46 tests ... OK`). 17+ official gov.uk/Acas examples encoded and matched (E12/E12b/E13 from published monthly inputs, all 52 weekly figures), 12 left out with reasons (benchmark/examples/SOURCES.md). A2 covers 3 of 4 areas: no official numeric example exists for regular overtime/commission, so that area is unit-tested only. gov.uk arithmetic slips recorded, not fudged (Table 5 £231.34 vs £231.54; Table 7 leaver rounding; £14,606.66 vs .67). Reviewer mutation tests: 18 of 19 caught. Score effect: none (part A alone moves nothing).
### Part B status
Gold labels frozen on branch p/holiday-pay-payroll-lookback-audit/T-111-labels (ec262b5, sha256 in FROZEN.md), deliberately not on main so the mapper author can't see them. 200 names, 9 categories (adds deduction_excluded; fold into expense_excluded if scoring on 8). Only BrightPay's import layouts are public; Xero and Sage 50 export layouts could not be fetched, so B1's layout half covers BrightPay only. Run waits for Q-16.

### Part B result (2026-11-26T21:20Z, run 0abb, T-113)
KILL on B1: nine-category accuracy 92.5% (eight-category 93.5%; AMBIGUOUS rows 71.9%, others 96.4%) against 95% needed. B2 PASS: $0.0059 per 200 names. One clean live run on gpt-5-mini (1 request, 0 failed attempts), prompt mapper-prompt-v2, gold sha256 verified. Results on branch p/holiday-pay-payroll-lookback-audit/T-113 (e23609b). Validator ruling reviews/T-113-validator.md: no legitimate rescue; second failed G1 attempt, idea KILLED.
