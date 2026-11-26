# Holiday pay look-back audit

**Not legal advice; a payroll professional signs off.**

Every figure here is recalculated under these settings. It is a calculation to check, not a finding.

## Summary

- Workers loaded: 8
- Workers with leave: 5
- Leave weeks checked: 5
- Exceptions (difference over £0.01, or cannot be checked): 4
- Leave weeks that could not be checked: 0
- Underpayments: 3, total underpaid £145.00
- Overpayments: 1, total overpaid £10.00
- Workers with flags: 1 (W004)
- Workers with weeks missing from the export: 0
- Rolled-up pay weeks checked (worker-weeks, each counted once): 13
- Rolled-up pay exceptions: 8 (5 rule flags, 2 differences from 12.07% of pay that counts, 1 holiday_pay week(s) paid to a rolled-up worker)
- Workers with holiday_pay recorded while on rolled-up pay: 1

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

### W006, pay week ending 2024-03-16 (rolled-up holiday pay)

- Leave year starting 2023-04-01. Pay that counts this week: £200.00. Rolled-up holiday pay recorded: £24.14.
- Flag `rolled_up_before_2024_rules`: rolled-up holiday pay is recorded in a leave year that started before 1 April 2024; the rolled-up method only applies to leave years starting on or after that date, so no recalculation is made.

### W006, pay week ending 2024-03-23 (rolled-up holiday pay)

- Leave year starting 2023-04-01. Pay that counts this week: £200.00. Rolled-up holiday pay recorded: £24.14.
- Flag `rolled_up_before_2024_rules`: rolled-up holiday pay is recorded in a leave year that started before 1 April 2024; the rolled-up method only applies to leave years starting on or after that date, so no recalculation is made.

### W006, pay week ending 2024-03-30 (rolled-up holiday pay)

- Leave year starting 2023-04-01. Pay that counts this week: £200.00. Rolled-up holiday pay recorded: £24.14.
- Flag `rolled_up_before_2024_rules`: rolled-up holiday pay is recorded in a leave year that started before 1 April 2024; the rolled-up method only applies to leave years starting on or after that date, so no recalculation is made.

### W007, pay week ending 2025-06-21 (rolled-up holiday pay)

- Leave year starting 2025-04-01. Pay that counts this week: £150.00. Rolled-up holiday pay recorded: £0.00.
- Flag `rolled_up_not_shown_separately`: this week has pay that counts but no rolled_up_holiday_pay row; rolled-up holiday pay must be shown as a separate item on the payslip, so a figure cannot be compared.

### W007, pay week ending 2025-06-28 (rolled-up holiday pay)

- Leave year starting 2025-04-01. Pay that counts this week: £150.00. Rolled-up holiday pay recorded: £0.00.
- Flag `rolled_up_not_shown_separately`: this week has pay that counts but no rolled_up_holiday_pay row; rolled-up holiday pay must be shown as a separate item on the payslip, so a figure cannot be compared.

### W008, pay week ending 2025-06-14 (rolled-up holiday pay)

- Leave year starting 2025-04-01. Pay that counts this week: £200.00. Rolled-up holiday pay recorded: £20.00.
- Recalculated under these settings: 12.07% x £200.00 = £24.14. Result: underpaid by £4.14.

### W008, pay week ending 2025-06-21 (rolled-up holiday pay)

- Leave year starting 2025-04-01. Pay that counts this week: £200.00. Rolled-up holiday pay recorded: £30.00.
- Recalculated under these settings: 12.07% x £200.00 = £24.14. Result: overpaid by £5.86.

### W008, pay week ending 2025-06-28 (rolled-up holiday pay)

- holiday_pay recorded: £200.00. Pay that counts this week: £0.00.
- Flag `holiday_pay_paid_to_rolled_up_worker`: holiday_pay was paid in this week to a worker whose holiday pay is rolled up into each wage packet; check whether this is a second payment of the same holiday pay or whether the worker is not on rolled-up pay.


## Note: leave weeks of irregular_rolled_up workers

1 leave week(s) listed in leave.csv for 1 irregular_rolled_up worker(s) were not re-audited by the 52-week look-back, because their holiday pay is paid as rolled-up pay in each wage packet. Their pay weeks are checked under the rolled-up rules above: W008 (1).

## Warning: holiday_pay recorded for an irregular_rolled_up worker

These workers are paid holiday pay rolled up into each wage packet, but these weeks also carry a holiday_pay row. That may be a second payment of the same holiday pay, or the worker may not be on rolled-up pay. Each week is listed in exceptions.csv with the flag `holiday_pay_paid_to_rolled_up_worker`; it is not recalculated.

- W008: 1 week(s): 2025-06-28