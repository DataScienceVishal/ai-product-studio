# Review: p/holiday-pay-payroll-lookback-audit/T-112 (fixes for T-111 re-review R1, S1)

Reviewer run, 2026-11-26. Branch HEAD `3de6dcc`, reviewed against `origin/main` `be60b9f`. Product diff: `engine/lookback.py`, `engine/reference.py`, `tests/test_edge_cases.py`, plus KILL-TEST.md results.

- **Branch suite:** `python3 -I -m unittest discover -s tests -t .` gives `Ran 51 tests in 0.015s` / `OK`.
- **Simulated merge:** `git merge-tree --write-tree` with main is clean, and the archived merged product folder gives `Ran 51 tests in 0.014s` / `OK`.

## Verdict: CHANGES

The explicit `contract_weekly_basic` path is sound. `weeks_used_dates` (S1) is correct. The requested flag property holds: it fires whenever the rate used differs from the latest week's basic. But the 8-week heuristic only protects against weeks that are *too low*. A one-off high basic week (back-pay arrears, a correction or a one-off payment mapped to basic) becomes the rate silently, and that produces a false underpayment claim with no flag. This is the arrears case named in T-111 R1, and it is not handled.

## Does the flag fire whenever the rate used is not the latest week's?

**Yes, by construction.** `differs = basics[0] != current`, where `basics[0]` is the week immediately before the leave week.
- If that week has pay, it is the latest paid week, so any other rate fires the flag.
- If that week has no basic (unpaid, or a previous holiday week), `0 != current` fires the flag.
- With `contract_weekly_basic`, the flag fires whenever the contract rate differs from the latest week.

I found no case where the rate used differs from the latest week and the flag stays silent. Mutant T1 (`differs = False`) is killed by 3 tests.

## Does the heuristic give silent wrong answers?

Yes. The flag only compares the rate against the latest week, so whenever the latest week itself is the outlier, nothing fires.

Each scenario below is my own run: 60 weeks at basic 500, a week of leave, holiday paid 500, `worker_type="fixed_pay"`.

| Scenario | due | difference | flags | Correct? |
|---|---|---|---|---|
| Latest week basic 1000 (arrears/one-off) | 1000.00 | **+500.00 (underpaid)** | `[]` | **No, and silent** |
| Arrears 1000 two weeks back, latest week 500 | 1000.00 | +500.00 | flag | No, but flagged. One high week marks the following 7 normal weeks as "reduced" |
| Pay rise to 550 in latest week only | 550.00 | +50.00 | `[]` | Right if the rise is real, wrong and silent if one-off. The engine cannot tell |
| Sick week (basic 100, SSP 99) before leave | 500.00 | 0.00 | flag | yes |
| Pay cut to 450 for 3 weeks | 500.00 | 0.00 | flag | No (should be 450), but flagged, as the builder disclosed |
| Pay cut to 450 for 9 weeks | 450.00 | -50.00 | `[]` | yes |
| Unpaid week before leave | 500.00 | 0.00 | flag | yes (flag is noise) |
| Every week has statutory pay (basic 200 + 50) | 200.00 | -300.00 | `[]`, `basic_source: latest_week_fallback` | Ambiguous, and the fallback is not flagged |
| 2nd week of a 2-week holiday | 500.00 | 0.00 | flag | yes (flag is noise on every consecutive leave week) |

## Blocking

**C1. A high outlier week is used silently as the rate.** File: `engine/lookback.py` `_fixed_pay_refs`, the loop `if not reduced and b >= max(basics[i:i + 8])`.
- *Why:* a week whose basic is at or above the 8-week maximum is always accepted. The flag compares only against `basics[0]`, so when the outlier *is* the latest week nothing fires. Result: a £500 false underpayment line with no flag. In an audit tool, a false claim is the worst failure. Arrears and one-off payments landing in "basic" are routine in payroll exports, and Part B's mapper may well map "Back pay" to basic.
- *Fix (small):* add a second flag, for example `rate_used_differs_from_prior_full_week`. It fires when the chosen rate differs from the basic of the next older full week (or from the most common basic in the 8 weeks). That catches real rises too. Flagging those is right: an adviser should confirm a rate change. Also flag `latest_week_fallback`. Add tests: latest week 1000 must flag, and latest week 550 must flag.

## Should fix

- **S1. Untested branches (surviving mutants).**
  - T2, ignoring the statutory check: survives, because the SSP test uses basic 100, which the max rule already catches. Add an SSP week whose basic equals the normal rate.
  - T4, window 8 to 2: survives. Pin the 8-week window with a test where the drop is in week 3 to 8.
  - T7, empty `weeks_used_dates` for fixed pay: survives. Assert the dates on a fixed-pay row.
  - T8, fallback value: survives. Test the all-reduced fallback.
- **S2. One spike poisons 8 weeks.** With arrears 2 weeks back, the normal 500 week is marked "reduced" because it is below the 1000 maximum, so the rate becomes 1000. It is flagged but wrong. Consider using the most common basic in the 8 weeks instead of the maximum. That resists outliers in both directions and makes a pay cut take effect after about 4 weeks instead of 8.
- **S3. Flag noise.** The flag fires on every second and later week of consecutive leave, and after any unpaid week. For "latest", compare against the latest *paid, non-holiday* week, so the flag keeps its meaning.
- **S4. One contract rate for the whole look-back.** `contract_weekly_basic` is one number for leave spanning up to six years (gov.uk record keeping from April 2026). Older leave weeks are then judged at today's rate. It is flagged when it differs, but a dated rate table (`[(effective_from, weekly_basic)]`) is what an audit needs.

## Verified fixed

- **S1 from T-111 (week dates):** `weeks_used_dates` is oldest first, excludes skipped weeks, and is correct for both variable and fixed pay. My run: 52 dates, last = the week before leave. Mutant T6 (off-by-one in dates) is killed.
- **Contract path:** `basic_source: "contract"`, due 520.00, flag fires when the latest week differs. Mutant T5 is killed.
- **Sick or short week before leave:** handled and flagged. Mutants T3 and T9 are killed.

## Kill-test marks (unchanged from T-111 re-review)

A1 PASS, A2 PASS (grey zone 3/4), A3 PASS (now with week dates), A4 tests green: 51/51 on the branch and on the simulated merge. This branch is CHANGES only because of C1 in the `fixed_pay` path. The default `variable_hours` path is unaffected.
