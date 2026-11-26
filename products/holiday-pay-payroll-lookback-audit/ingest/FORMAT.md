# Input format

UTF-8 CSV with a header row. Column order does not matter. Money is plain decimal pounds, up to 9 digits and 2 decimals (`412.50`): no currency symbols, commas, signs, NaN or Infinity. Dates are `YYYY-MM-DD` and must fall between 2000-01-01 and 2100-12-31 (anything else is refused with its line). `--threshold` must be 0 to 1,000,000 pounds.

**Privacy:** use a pseudonymous payroll ID in `worker_id`. No names, NI numbers, addresses, emails or birth dates. A column that looks like personal data, or a `worker_id` that looks like an NI number or a date, is refused.
The NI check ignores separators (`.`, `_`, `-`, spaces), accepts a missing suffix letter, and also looks at parts after a prefix (`EMP-QQ123456C`). It follows the HMRC prefix rules (first letter not D F I Q U V, second not D F I O Q U V, never BG GB NK KN TN NT ZZ), with one deliberate exception: `QQ` (the HMRC example prefix) is still refused. So IDs of the form two letters + six digits (`EM100234A`, `AB123456`) are refused. Use a longer prefix (`EMP100234`), which is allowed, or a different shape. An NI number glued to a letter prefix with no separator (`EMPAB123456C`) is deliberately not detected. A scan of every 8 or 9 character window after letters would also refuse the recommended `EMP100234` and `EMP100234A` (window `MP100234A` looks like an NI number), and nothing in the shape tells `EMPAB123456C` from `STAFF100234A`. So do not rely on the check; just do not put NI numbers in the file.
Error messages never print a full cell value from `worker_id`, `week_ending`, `element_category`, `amount` or `worker_type`: they show the first 2 characters and the length, plus the file and line. At most 50 errors are printed, then `... and N more`; the last line gives the total.

## history.csv (required)
One row per worker, week and pay element. Weeks with no pay need no rows. Columns: `worker_id` (letters, digits, `_ . -`, max 64, starting with a letter or digit), `week_ending`, `element_category`, `amount`.
`element_category` is one of: basic, regular_overtime, commission, bonus_non_regular, allowance, expense_excluded, holiday_pay, statutory. The `holiday_pay` amount in a leave week is what was actually paid for that leave. All of a worker's `week_ending` dates must fall on the same weekday. One row per worker, week and category (no duplicates).

**Negative amounts are refused for now** (clawbacks, corrections, reversals). Net any correction into the week it relates to before exporting, so each week and category carries one non-negative amount.

**Missing weeks:** a week with no rows is treated as unpaid. If a week between a worker's first and last record is absent, `report.md` lists it under "weeks missing from the export" so you can confirm it was genuinely unpaid and not left out of the export. Results are not changed by this warning.

## leave.csv (required)
One row per leave week. **List every leave week of the leave year**: the first 4 leave weeks of a leave year count as normal pay and later ones as basic pay only, so a missing row can change the result. If history holds `holiday_pay` for a week that is not in leave.csv, `report.md` warns ("holiday pay recorded but no leave row") and later leave weeks that year carry the flag `holiday_pay_week_not_in_leave_file`. Columns: `worker_id`, `week_ending` (same weekday as that worker's history), optional `weeks` (default 1, must be above 0 and at most 1; 0.5 is half a week).

**Leave weeks the audit cannot trust:**
- A leave week with pay but no `holiday_pay` row is flagged `leave_week_without_holiday_pay`; nothing counts as paid and the report shows the pay that was in that week. Re-export it as `holiday_pay` if it was the holiday pay.
- A leave week with no paid week before it (`no_reference_weeks`) cannot be checked. It is always listed in exceptions.csv (`direction` = `cannot_check`) and in report.md, is counted under "Leave weeks that could not be checked", and is not counted as an over- or underpayment.

## workers.csv (optional)
Columns: `worker_id`, `worker_type` (`variable_hours` default, or `fixed_pay`), optional `contract_weekly_basic` (fixed_pay: the contractual weekly basic, must be greater than 0, or blank to infer it and flag that; a zero or negative value exits 2. variable_hours: ignored, and a value there gives a warning in report.md and a note on stderr, exit stays 0). Workers not listed are `variable_hours`.

## Output columns: reference weeks (exceptions.csv)
- `ref_weeks_used`: paid weeks that went into the average.
- `ref_weeks_skipped`: weeks inside the worker's history (on or after their first payroll row) that were looked at but did not count because there was no pay that counts (no pay at all, or only excluded items such as SSP).
- `ref_weeks_before_first_record`: look-back weeks earlier than the worker's first payroll row. There is no data for them, so they are not counted and not treated as skipped.

**Changed in T-115:** `ref_weeks_skipped` used to include the before-first-record weeks. It now counts only no-pay-that-counts weeks, and the other weeks are in `ref_weeks_before_first_record`. Compare earlier output with this in mind.

## Output files and permissions
`exceptions.csv` and `report.md` hold payroll data, so they are created owner-only (mode 0600), not the 0644 an ordinary `open()` would give. Any mode or owner on files already in `--out` is replaced by this. Change it afterwards with `chmod` if others must read the files. The two files are written together: if either cannot be written, the folder keeps its previous contents (a crash or power loss mid-write is not covered).

**Changed in T-116/T-117:** earlier output was 0644. `report.md` lists missing weeks as ranges, for example `2025-01-04 to 2025-02-01 (5 weeks)`.

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
(exit 0 = done, 2 = validation errors or invalid options, nothing written).
