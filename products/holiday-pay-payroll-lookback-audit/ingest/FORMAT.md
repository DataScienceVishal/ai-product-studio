# Input format

UTF-8 CSV with a header row. Column order does not matter. Money is plain decimal pounds (`412.50`): no currency symbols, commas, signs, NaN or Infinity. Dates are `YYYY-MM-DD`.

**Privacy:** use a pseudonymous payroll ID in `worker_id`. No names, NI numbers, addresses, emails or birth dates. A column that looks like personal data, or a `worker_id` that looks like an NI number, is refused.

## history.csv (required)
One row per worker, week and pay element. Weeks with no pay need no rows. Columns: `worker_id`, `week_ending`, `element_category`, `amount`.
`element_category` is one of: basic, regular_overtime, commission, bonus_non_regular, allowance, expense_excluded, holiday_pay, statutory. The `holiday_pay` amount in a leave week is what was actually paid for that leave. All of a worker's `week_ending` dates must fall on the same weekday. One row per worker, week and category (no duplicates).

## leave.csv (required)
One row per leave week. Columns: `worker_id`, `week_ending` (same weekday as that worker's history), optional `weeks` (default 1; use 0.5 for half a week).

## workers.csv (optional)
Columns: `worker_id`, `worker_type` (`variable_hours` default, or `fixed_pay`), optional `contract_weekly_basic` (fixed_pay: the contractual weekly basic; blank means inferred and flagged). Workers not listed are `variable_hours`.

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
