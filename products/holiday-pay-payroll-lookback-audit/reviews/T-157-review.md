# T-157 review: fixes for QA bugs B1 to B6

Branch `p/holiday-pay-payroll-lookback-audit/T-157`, commit d14fd3e, diff `git diff main...HEAD` (8 files, +248 / -30).

**Verdict: CHANGES** (1 critical, B2's new warning is wrong for some weeks; everything else is fixed and clean).

## Evidence
- Full suite from the product folder: `python3 -I -m unittest discover -s tests -t .` gave `Ran 345 tests in 37.320s`, `OK` (main had 336; 9 new in `tests/test_t157.py`).
- QA repros rerun in `/tmp/claude-0/t157r` with `python3 -I audit.py --include-flagged ...` (60 weeks basic 100.00, one leave week).
- Engine numbers: `git worktree add /tmp/claude-0/t157main main`, then ran the samples (`samples/history.csv`, `leave.csv`, `workers.csv`) at `--threshold 50` and `--threshold 0` on both trees. `exceptions.csv` and `report.md` byte-identical in both cases; stdout differs only in the `--out` path. The B2 repro's `exceptions.csv` is also identical to main. Worktree removed.

| Bug | Result | Evidence |
|---|---|---|
| B1 headerless file echoes cells | Fixed | headerless history and leave files, and a `John Smith` header: only `column N is not a recognised header; the file may be missing its header row` plus `missing column '<known name>'`. No id, date, amount or header text in stderr. Exit 2, nothing written. |
| B2 excluded_week + counting pay silent | Fixed for that case, but see C1 | stderr `warning: worker_id W1***: excluded_week marked on a week that also has pay; the week was used as a normal week (week ending 2025-03-15)`; report.md summary line and section; no amounts; exceptions.csv identical to the run without the marker. |
| B3 name-like cap | Fixed | 55 name-like ids: 50 warnings, `... and 5 more worker_id warning(s)`, each with `first row at history line N` so identical masks differ; report.md `Worker IDs that look like a person's name: 55`. |
| B4 wording | Fixed | `... 10 underpaid, £500.00 in total. Their week endings: 2026-07-18 to 2026-09-19 (10 weeks). All of them are in exceptions.csv.` |
| B5 leave_year_start text | Fixed | `13-01`, `04-31`, `04/01` no longer mention 02-29; `02-29` still does. |
| B6 non-UTF-8 | Fixed | Latin-1 byte on line 62: `h_latin.csv:62: the file is not valid UTF-8; save the file as UTF-8 (CSV UTF-8 in Excel)`; no codec text, no byte value. |

Leak check: new messages carry only the masked id (`W1***`), line numbers, column positions, counts and week-ending dates (the dates are what the QA report asked for and what every other report.md section already lists). No amounts, full ids or header cells.

## Critical issues

### C1. The excluded_week warning fires on weeks the engine did skip, and tells the user something false
`ingest/loader.py:102-111`, `excluded_week_with_pay`: the predicate is "any other category with amount > 0". The engine does not use the marker at all for averaging; it skips any week whose **normal pay** is 0 (`engine/lookback.py` loop on `normal_pay(p) <= 0`, and `reference_average` for variable hours; `engine/elements.py` `COUNTS_FOR_NORMAL = basic, regular_overtime, commission, allowance`). So a week with `excluded_week` plus only `expense_excluded`, `bonus_non_regular`, `holiday_pay` or `rolled_up_holiday_pay` is skipped, yet the tool says it "was used as a normal week".

Repro (`/tmp/claude-0/t157r/h_fp.csv`): remove the basic row for 2025-05-24 and add `excluded_week,0` and `expense_excluded,37.50` for that week. Output: `warning: worker_id W1***: excluded_week marked on a week that also has pay; the week was used as a normal week (week ending 2025-05-24)`, and the same in report.md. Same with `bonus_non_regular,900.00` (`h_fp2.csv`). 0 exceptions: the week was in fact skipped.

Why it matters: report.md is the adviser's record of what the audit did, and here it states the opposite. Its advice ("To skip a week, remove its pay rows") would, for a week marked excluded_week that carries `holiday_pay`, lead the user to delete the holiday_pay row, which then raises `leave_week_without_holiday_pay` or changes `paid`. A false alarm on the most common real pattern (an absence week with a holiday or statutory-type payment) also trains users to ignore the warning.

Fix: use the engine's own rule, so there is one source of truth: `normal_pay(cats) > 0` from `engine.elements` (with `include_holiday_pay` matching whatever the audit passes as `holiday_weeks_count`; today nothing passes it, so default False). Add tests: excluded_week with only expense_excluded, only bonus_non_regular, only holiday_pay, only rolled_up_holiday_pay gives no warning; with regular_overtime or allowance > 0 gives a warning. Optionally widen the FORMAT.md sentence to "pay that counts (basic, regular_overtime, commission, allowance)".

## Suggestions (not blocking)
1. `_mask_id` import (`audit.py:9`): importing a private helper across the package boundary works, but it couples the CLI to loader internals, and masking now happens in two layers (loader for name-like warnings, CLI for excluded_week). Prefer `excluded_week_with_pay` returning already-masked keys like `name_like_id_warnings` does, or export a public `mask_id` from `ingest/__init__.py`. Acceptable as is; tidy when fixing C1.
2. `FORMAT.md`: the new "Name-like worker_id warnings" paragraph sits after the worked example at the end of the file; move it next to the Privacy paragraph (line 5), which already talks about these warnings. Line 5 also says "(`JSmith1990` is not caught)" twice (pre-existing).
3. The fixed_pay rate inference does read the marker (`"excluded_week" not in p` in `_fixed_pay_refs`), so for a fixed_pay worker "used as a normal week" is not fully true even after C1: the week counts for the average but is not chosen as the inferred basic rate. Consider "its pay still counted in the average".
4. B5: for the value `02-29` the message now prints the full cell (`02-29 is not accepted`). Harmless (a constant, not personal data), but it contradicts the FORMAT.md line 8 rule literally; "29 February is not accepted" avoids it.
5. Duplicate unknown header cells are no longer reported as duplicates (only as unrecognised). Fine, since the file is refused either way.

## Tests
The new tests check behaviour through the CLI (exit codes, absence of secrets in stderr, nothing written, numbers unchanged, cap counts, line number of the bad byte). Good. Missing: the negative cases for C1 above, and a leak assertion on the excluded_week report section beyond `100.00`.
