# T-121 review: fixes for T-119 QA and T-120 security findings

Reviewer: reviewer agent, 2026-11-26. Branch `p/holiday-pay-payroll-lookback-audit/T-121` at `a8e7a27`, diffed against `origin/main` (`85d3fff`). The review ran in a scratch worktree. No product code was changed.

## Verdict: CHANGES

Every finding in scope is fixed and the tests cover the fixes. However, the new NI check brings in a cubic-time hang on untrusted input (C-1). The T-120 resource-exhaustion row passed before this branch and would fail now. The fix is a single line.

## Evidence

- **Suite:** `python3 -I -m unittest discover -s tests -t .` gave `Ran 188 tests ... OK`.
- **Samples unchanged:** I ran `samples/` on main and on the branch at threshold 0.01 and 0, each with and without `--include-flagged`. `exceptions.csv` is byte-identical in all four runs. The only change in `report.md` is the new line `- Leave weeks that could not be checked: 0`.
- **Repros rerun** (T-119 scratch dirs, on the branch):
  - **M1 (`unl`):** the result is still 0 exceptions, due 430 = paid 430, the same as main. `report.md` now has a "holiday pay recorded but no leave row" section that lists `A: 4 week(s): 2025-07-26 to 2025-08-16`. With `--include-flagged`, the row carries `holiday_pay_week_not_in_leave_file`. This meets QA's minimum fix, the warning. The count is not corrected, and that limitation is documented.
  - **M2 (`lb2`):** the row is flagged `leave_week_without_holiday_pay` and the report shows "Pay in this week that was not marked as holiday pay: £400.00". Fixed.
  - **M3 (`early`, `early2`):** the week is always listed with `direction=cannot_check`, the summary shows "could not be checked: 1", Overpayments is 0, and the misleading "overpaid by £100" text is gone. Fixed.
  - **L1:** thresholds `1e27`, `1e30`, `1e400` and `1000000.01` exit 2 with a one-line message. `1000000`, `1e6` and `0` exit 0. Fixed.
  - **L2 (`d0001`, `d9999`):** each bad date gets a line error and the run exits 2. Fixed.
  - **Security L-1:** `week_ending` `QQ123456C John Smith` is printed as `'QQ...' (20 chars)`. A 131,000-char category is printed as `'JJ...' (131000 chars)`. 204 errors produce 50 lines, then `... and 154 more`, then the total (3.8 KB on stderr). Headers are cut to 20 characters. Fixed.
  - **Security M-1:** I probed 34 IDs. Refused: `QQ.12.34.56.C`, `QQ_12_34_56_C`, `QQ123456`, `EMP-QQ123456C`, `ab123456c`, `AB.123456`, `1985-03-12`, `12-03-1985`. Allowed: `EMP100234`, `EMP100234A`, `W-1`, `STORE12-123456`, and the HMRC-invalid prefixes `DE`, `ZZ` and `GB`. Glued `EMPAB123456C` is still accepted, as documented. Some false positives are accepted: `HR-AA-000001`, `AB-1-23456` and `TEAM-AB-100200` are refused. Failing closed is the right bias here, and FORMAT.md explains it.
- **CSV and Markdown injection:** `direction` is an engine enum (`cannot_check` included). The new flags are fixed strings and go through `_safe`. The unlisted-weeks section and the flagged-workers summary now use `_md` (this also fixes I-3). Safe.
- **Mutations:** each mutation was applied to a copy and the suite rerun. These were caught (the suite failed):
  - M1 flag removed
  - M2 flag removed
  - `cannot_check` removed from the exceptions filter
  - `cannot_check` direction removed
  - `cannot_check` exclusion removed from the over list
  - `_NI_NEVER` check removed
  - runs of parts not joined
  - QQ exception removed
  - date-shaped ID check removed
  - date range check removed
  - error cap removed
  - category masking removed
  - threshold maximum removed

  One mutation survived: removing the exclusion from the `under` list. That branch cannot be reached, because no reference weeks means due is 0 and the difference is 0 or less. So this is not a real gap.

## Critical issues

### C-1: the NI check is cubic in the number of separators and runs before the 64-character limit, so one long cell hangs the audit

- **Where:** `ingest/loader.py:58-70` (`_looks_like_ni`), called at `ingest/loader.py:142` before `_ID.match` enforces the 64-character maximum.
- **What happens:** `_looks_like_ni` joins every run of parts, `i..j`, which is O(parts²) joins of O(n) length each. The `worker_id` value is untrusted and is limited only by the csv field limit of 131,072 characters.
- **Measured:**
  - 1,000 parts: 1.0 s. 2,000 parts: 7.5 s.
  - A history file with one `worker_id` cell of 3,000 space-separated words (6 KB) takes 22.6 s end to end on the branch and 0.05 s on main.
  - A cell near the field limit (about 65,000 parts) would run for days.
- **Why it matters:** a misaligned free-text column, or a hostile file, stalls the CLI instead of returning the usual exit 2. T-120 passed "Resource exhaustion" on main. This branch would fail it.
- **Fix:**
  - Run the length and charset check first: `elif len(wid) > 64` gives the existing format error, before the NI check runs.
  - Or bound the inner loop: stop extending `j` once `len(c) > 9`, because an NI number is at most 9 characters with separators removed.
  - Add a test that times a cell of about 4,000 parts and requires it to finish in under 1 s.

## Suggestions (not blocking)

1. **M1 visibility.** The warning sits at the bottom of `report.md`, and the summary does not mention it. Without `--include-flagged`, `exceptions.csv` says nothing about it. Add a summary line, `- Workers with holiday pay outside leave.csv: N`. A follow-up could count unlisted holiday-pay weeks towards the first 4 weeks, which is QA's preferred fix.
2. **Summary label.** `report/builder.py:280` reads "Exceptions (difference over £X): N", but N now includes `cannot_check` rows. Reword it to "Exceptions (difference over £X, or cannot be checked)".
3. **`cannot_check` rows show a `difference`.** For example, `early2` shows -100.00. If someone sums that CSV column in Excel, the result is distorted. Consider leaving `due` and `difference` blank for these rows.
4. **Dead code.** `audit.py:21` calls `v.quantize(Decimal("0.01"))` and discards the result. With the upper bound in place it cannot raise, so delete it.
5. **Private import.** `report/builder.py` imports `engine.lookback._leave_year_start` and hard-codes April 1. This is consistent today, because `audit()` never passes a leave year. Expose the function publicly, or take the leave-year start from the engine row (`r["leave_year_start"]`), so the two cannot drift apart.
6. **Still open (as the builder said):** QA L3 `contract_weekly_basic` validation (ignored for `variable_hours`, 0 accepted for `fixed_pay`). Track it as a board task.
