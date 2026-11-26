# Input format

UTF-8 CSV with a header row. Column order does not matter. Money is plain decimal pounds, up to 9 digits and 2 decimals (`412.50`): no currency symbols, commas, signs, NaN or Infinity. Dates are `YYYY-MM-DD`.

**Privacy:** use a pseudonymous payroll ID in `worker_id`. No names, NI numbers, addresses, emails or birth dates. A column that looks like personal data, or a `worker_id` that looks like an NI number, is refused.

## history.csv (required)
One row per worker, week and pay element. Weeks with no pay need no rows. Columns: `worker_id` (letters, digits, `_ . -`, max 64, starting with a letter or digit), `week_ending`, `element_category`, `amount`.
`element_category` is one of: basic, regular_overtime, commission, bonus_non_regular, allowance, expense_excluded, holiday_pay, statutory. The `holiday_pay` amount in a leave week is what was actually paid for that leave. All of a worker's `week_ending` dates must fall on the same weekday. One row per worker, week and category (no duplicates).

**Negative amounts are refused for now** (clawbacks, corrections, reversals). Net any correction into the week it relates to before exporting, so each week and category carries one non-negative amount.

**Missing weeks:** a week with no rows is treated as unpaid. If a week between a worker's first and last record is absent, `report.md` lists it under "weeks missing from the export" so you can confirm it was genuinely unpaid and not left out of the export. Results are not changed by this warning.

## leave.csv (required)
One row per leave week. Columns: `worker_id`, `week_ending` (same weekday as that worker's history), optional `weeks` (default 1, must be above 0 and at most 1; 0.5 is half a week).

## workers.csv (optional)
Columns: `worker_id`, `worker_type` (`variable_hours` default, or `fixed_pay`), optional `contract_weekly_basic` (fixed_pay: the contractual weekly basic; blank means inferred and flagged). Workers not listed are `variable_hours`.

## Output columns: reference weeks (exceptions.csv)
- `ref_weeks_used`: paid weeks that went into the average.
- `ref_weeks_skipped`: weeks inside the worker's history (on or after their first payroll row) that were looked at but did not count because there was no pay that counts (no pay at all, or only excluded items such as SSP).
- `ref_weeks_before_first_record`: look-back weeks earlier than the worker's first payroll row. There is no data for them, so they are not counted and not treated as skipped.

**Changed in T-115:** `ref_weeks_skipped` used to include the before-first-record weeks. It now counts only no-pay-that-counts weeks, and the other weeks are in `ref_weeks_before_first_record`. Compare earlier output with this in mind.

## Example
history.csv
```
worker_id,week_ending,element_category,amount
W1,2025-06-07,basic,400.00
W1,2025-06-07,commission,30.00
W1,2025-06-14,holiday_pay,400.00
```
leave.csv
```
worker_id,week_ending
W1,2025-06-14
```
workers.csv
```
worker_id,worker_type,contract_weekly_basic
W1,fixed_pay,400.00
```
Run: `python3 audit.py --history history.csv --leave leave.csv --workers workers.csv --out out/`
(exit 0 = done, 2 = validation errors, listed in full on stderr, nothing written).
