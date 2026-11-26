# Holiday pay look-back audit

**Not legal advice; a payroll professional signs off.**

Every figure here is recalculated under these settings. It is a calculation to check, not a finding.

## Summary

- Workers loaded: 8
- Workers with leave: 6
- Leave weeks checked: 6
- Exceptions (difference over £0.01, cannot be checked, or weekly rate guessed): 4
- Leave weeks that could not be checked: 0
- Leave weeks with a guessed weekly rate: 0
- Underpayments: 3, total underpaid £145.00
- Overpayments: 1, total overpaid £10.00
- Workers with flags: 2 (W004, W008)
- Workers with weeks missing from the export: 0
- Workers with rolled-up pay but not set as irregular_rolled_up: 3

## Exceptions

### W002, week ending 2025-08-09

- Leave: 1 week(s) in the leave year starting 2025-04-01: 1 at normal pay, 0 at basic pay only.
- Normal weekly pay: average (52 paid week(s) found looking back 52 week(s): 0 week(s) with no pay that counts skipped (no pay, or only excluded items such as SSP), 0 week(s) before the first payroll record in the file not counted (no data)) = £24,960.00 / 52 = £480.00.
- Recalculated under these settings: £480.00. Paid in the leave week: £400.00. Result: underpaid by £80.00.

### W003, week ending 2025-08-09

- Leave: 1 week(s) in the leave year starting 2025-04-01: 1 at normal pay, 0 at basic pay only.
- Normal weekly pay: average (52 paid week(s) found looking back 57 week(s): 5 week(s) with no pay that counts skipped (no pay, or only excluded items such as SSP), 0 week(s) before the first payroll record in the file not counted (no data)) = £15,600.00 / 52 = £300.00.
- Recalculated under these settings: £300.00. Paid in the leave week: £310.00. Result: overpaid by £10.00.

### W004, week ending 2025-05-31

- Leave: 1 week(s) in the leave year starting 2025-04-01: 1 at normal pay, 0 at basic pay only.
- Normal weekly pay: average (47 paid week(s) found looking back 104 week(s): 0 week(s) with no pay that counts skipped (no pay, or only excluded items such as SSP), 57 week(s) before the first payroll record in the file not counted (no data)) = £18,800.00 / 47 = £400.00.
- Recalculated under these settings: £400.00. Paid in the leave week: £350.00. Result: underpaid by £50.00.
- Flag `shortened`: fewer than 52 paid weeks were available, so the average uses what exists.

### W005, week ending 2025-08-09

- Leave: 1 week(s) in the leave year starting 2025-04-01: 1 at normal pay, 0 at basic pay only.
- Normal weekly pay: average (52 paid week(s) found looking back 52 week(s): 0 week(s) with no pay that counts skipped (no pay, or only excluded items such as SSP), 0 week(s) before the first payroll record in the file not counted (no data)) = £16,380.00 / 52 = £315.00.
- Recalculated under these settings: £315.00. Paid in the leave week: £300.00. Result: underpaid by £15.00.


## Warning: rolled-up holiday pay for a worker not set as irregular_rolled_up

These workers have rolled_up_holiday_pay rows but their worker_type is not irregular_rolled_up, so the rolled-up pay was not checked and is not counted as normal pay, basic pay or holiday pay. Set worker_type to irregular_rolled_up in workers.csv if they are paid rolled-up holiday pay, then re-run.

- W006: 5 week(s): 2024-03-16 to 2024-04-13 (5 weeks)
- W007: 2 week(s): 2025-06-07 to 2025-06-14 (2 weeks)
- W008: 3 week(s): 2025-06-07 to 2025-06-21 (3 weeks)