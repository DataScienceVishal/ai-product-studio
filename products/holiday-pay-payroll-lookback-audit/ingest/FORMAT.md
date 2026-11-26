# Input format

UTF-8 CSV with a header row. Column order does not matter. Money is plain decimal pounds, up to 9 digits and 2 decimals (`412.50`): no currency symbols, commas, signs, NaN or Infinity. Dates are `YYYY-MM-DD` and must fall between 2000-01-01 and 2100-12-31 (anything else is refused with its line). `--threshold` must be 0 to 1,000,000 pounds.

**Privacy:** use a pseudonymous payroll ID in `worker_id`. No names, NI numbers, addresses, emails or birth dates. A column that looks like personal data, or a `worker_id` that looks like an NI number or a date, is refused.
The NI check ignores separators (`.`, `_`, `-`, spaces), accepts a missing suffix letter, and also looks at parts after a prefix (`EMP-QQ123456C`). It follows the HMRC prefix rules (first letter not D F I Q U V, second not D F I O Q U V, never BG GB NK KN TN NT ZZ), with one deliberate exception: `QQ` (the HMRC example prefix) is still refused. So IDs of the form two letters + six digits (`EM100234A`, `AB123456`) are refused. Use a longer prefix (`EMP100234`), which is allowed, or a different shape. An NI number glued to a letter prefix with no separator (`EMPAB123456C`) is deliberately not detected. A scan of every 8 or 9 character window after letters would also refuse the recommended `EMP100234` and `EMP100234A` (window `MP100234A` looks like an NI number), and nothing in the shape tells `EMPAB123456C` from `STAFF100234A`. So do not rely on the check; just do not put NI numbers in the file.
**Keeping and deleting data (DRAFT, not legal advice):** the input files are your files, and pseudonymised payroll data is still personal data (UK GDPR). The tool keeps nothing beyond the two output files it writes to `--out`: no copies, caches, logs of values or network calls. Keep inputs and outputs only for the engagement, delete `out/` and the exports after sign-off (`rm -r out/`), and do not email `exceptions.csv` unencrypted. Any hosted version must delete uploaded inputs within 30 days.
Error messages never print a full cell value from any column (`worker_id`, `week_ending`, `element_category`, `amount`, `weeks`, `worker_type`, `leave_year_start`, `contract_weekly_basic`): they show the first 2 characters and the length (invisible characters such as a byte-order mark inside a cell are removed first, and the message says so), plus the file and line. At most 50 errors are printed, then `... and N more`; the last line gives the total.

## history.csv (required)
One row per worker, week and pay element. Weeks with no pay need no rows. Columns: `worker_id` (letters, digits, `_ . -`, max 64, starting with a letter or digit), `week_ending`, `element_category`, `amount`.
`element_category` is one of: basic, regular_overtime, commission, bonus_non_regular, allowance, expense_excluded, holiday_pay, statutory, rolled_up_holiday_pay. The `holiday_pay` amount in a leave week is what was actually paid for that leave. All of a worker's `week_ending` dates must fall on the same weekday. One row per worker, week and category (no duplicates).
`rolled_up_holiday_pay` is holiday pay paid with each wage packet to an irregular-hours or part-year worker (12.07% of pay). It never counts as normal pay, basic pay or holiday pay in the 52-week look-back. Use it only for workers whose `worker_type` is `irregular_rolled_up`; for any other worker a `report.md` warning lists the weeks and the rolled-up pay is not checked.

**Negative amounts are refused for now** (clawbacks, corrections, reversals). Net any correction into the week it relates to before exporting, so each week and category carries one non-negative amount.

**Missing weeks:** a week with no rows is treated as unpaid. If a week between a worker's first and last record is absent, `report.md` lists it under "weeks missing from the export" so you can confirm it was genuinely unpaid and not left out of the export. Results are not changed by this warning.

## leave.csv (required)
One row per leave week. A header-only leave.csv (no data rows) is accepted only when `workers.csv` sets every worker in history as `irregular_rolled_up`, so a firm with only rolled-up workers can run the rolled-up checks; otherwise it exits 2 with `no data rows`. **List every leave week of the leave year**: the first 4 leave weeks of a leave year count as normal pay and later ones as basic pay only, so a missing row can change the result. If history holds `holiday_pay` for a week that is not in leave.csv, `report.md` warns ("holiday pay recorded but no leave row") and later leave weeks that year carry the flag `holiday_pay_week_not_in_leave_file`. Columns: `worker_id`, `week_ending` (same weekday as that worker's history), optional `weeks` (default 1, must be above 0 and at most 1; 0.5 is half a week).

**Leave weeks the audit cannot trust:**
- A leave week with pay but no `holiday_pay` row is flagged `leave_week_without_holiday_pay`; nothing counts as paid and the report shows the pay that was in that week. Re-export it as `holiday_pay` if it was the holiday pay.
- A leave week with no paid week before it (`no_reference_weeks`) cannot be checked. It is always listed in exceptions.csv (`direction` = `cannot_check`) and in report.md, is counted under "Leave weeks that could not be checked", and is not counted as an over- or underpayment.

## workers.csv (optional)
Columns: `worker_id`, `worker_type` (`variable_hours` default, `fixed_pay`, or `irregular_rolled_up`), optional `leave_year_start` (see below), optional `contract_weekly_basic` (fixed_pay: the contractual weekly basic, must be greater than 0, or blank to infer it and flag that; a zero or negative value exits 2. variable_hours: ignored, and a value there gives a warning in report.md and a note on stderr, exit stays 0). Workers not listed are `variable_hours`.

**irregular_rolled_up (T-126):** an irregular-hours or part-year worker paid rolled-up holiday pay. The user decides this status, the tool does not infer it. Each pay week in `history.csv` is checked on its own (a week belongs to the leave year containing its week-ending date; the year starts on the worker's `leave_year_start`, 1 April by default):
- leave year starting before 2024-04-01 and `rolled_up_holiday_pay` above 0: flag `rolled_up_before_2024_rules`. Rolled-up pay was not allowed under the rules of that time, so no figure is recalculated;
- leave year starting on or after 2024-04-01, pay that counts above 0 (basic, regular overtime, commission, allowance) and no `rolled_up_holiday_pay` row: flag `rolled_up_not_shown_separately`;
- otherwise the rolled-up pay is recalculated as 12.07% x pay that counts (to the penny) and compared with what was paid. A difference above `--threshold` is an exception (`underpaid` or `overpaid`) with the working in `report.md`. A week with no pay that counts and no rolled-up row has nothing to check.
- `holiday_pay` above 0 in any week of an `irregular_rolled_up` worker: flag `holiday_pay_paid_to_rolled_up_worker` (possible second payment of the same holiday pay, or a worker not really on rolled-up pay). It is listed in exceptions.csv (`paid` = the holiday_pay amount, direction `rule_flag`) and in a `report.md` warning, and is not recalculated.
Rule flags are always exceptions, whatever the threshold.

**leave_year_start (T-127):** optional column in `workers.csv`, `MM-DD` (for example `01-01`, `04-01`, `10-01`), default `04-01` when the column is absent or the cell is blank. It must be a real calendar date; `02-29` is refused, and so is anything not written as two digits, a hyphen and two digits. An invalid value exits 2 with the file and line number and the first 2 characters and length of the cell, not the cell itself; nothing is written. The date is used everywhere a leave year is computed: the first-4-weeks normal-pay count in the look-back (counting restarts on each start date), the `holiday_pay_week_not_in_leave_file` check, and the rolled-up checks, where the leave year start date decides whether the 2024 rules apply (`accrual_applies`: start on or after 2024-04-01). A week ending exactly on the start date belongs to the year that starts that day. Example: with `01-01`, rolled-up pay from April to December 2024 is in the year that began 2024-01-01, so it is flagged `rolled_up_before_2024_rules` instead of being recalculated. With no column the leave years and every result are unchanged from earlier versions: exceptions.csv is identical, and report.md is identical apart from the two rolled-up count lines in its summary, which changed in T-127 (see the counts note below). When any worker has a start date other than 04-01, the report.md summary gains one line, for example `Leave years: 1 April unless set; W006: 1 January`, naming those workers (first 20, then `and K more`); when every worker uses 1 April the line is left out. The setting is per worker, one start date for all years; a change of leave-year start in the middle of the history is not modelled.

**Nothing to check (T-130):** an `irregular_rolled_up` worker with no pay week to check, and a `leave.csv` week of a rolled-up worker that has no row in `history.csv`, are named in a `report.md` note and a stdout `note:` line, never silently dropped. `report.md` writes out at most 20 detailed sections per rolled-up worker and 500 in the whole report, then one line `and K more` per worker with the flag counts and week ranges (for the first 50 workers affected; the rest share one combined line); `exceptions.csv` always lists every exception.

**Leave weeks of rolled-up workers:** Leave weeks listed in `leave.csv` for these workers are not re-audited by the 52-week look-back (their holiday pay is paid as rolled-up pay, not at the average); `report.md` notes how many were skipped. A `contract_weekly_basic` is ignored for them (the report says so in its own words and does not suggest another worker type).

## Output columns: rolled-up rows (exceptions.csv)
`exceptions.csv` has a final column `check`: `leave_lookback` (the look-back rows above) or `rolled_up_pay`. For `rolled_up_pay` rows `leave_week` is the pay week ending, `paid` is the rolled-up pay recorded, `due` and `difference` are the amount recalculated under these settings (blank for the two rule flags, where `direction` is `rule_flag`), and the `ref_weeks_*`, `average` and `fixed_basic_rate` columns are blank. **Changed in T-126:** the `check` column is new, and report.md says "Recalculated under these settings" where it used to say "Due". The column name `due` is unchanged.

**Counts in report.md and on stdout (T-127):** stdout line 1 counts look-back leave weeks and look-back exceptions only (`5 leave weeks checked, 4 exceptions.`). Line 2, shown when there are rolled-up rows, counts distinct worker-weeks (a week with both a rolled-up row and a `holiday_pay` row counts once) and all rolled-up exceptions (`13 rolled-up pay weeks checked, 8 exceptions.`). In report.md the rolled-up exceptions are split into rule flags, differences from 12.07%, and `holiday_pay` weeks, which are three separate groups that add up to the total. exceptions.csv has one row per exception of either kind.

**Wording:** outputs never say "compliant", "owed" or "liable". Figures are recalculated under the settings you gave; "Not legal advice; a payroll professional signs off." stays on every report.

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
