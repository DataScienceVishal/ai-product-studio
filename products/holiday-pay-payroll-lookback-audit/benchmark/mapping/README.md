# Part B gold labels: pay-element mapping (T-111)

Written 2026-11-26 by the QA agent, who did not write and must not write the mapper prompt. The mapper author must not read `gold.csv`. Frozen: see `FROZEN.md`.

## Files
- `gold.csv`: 200 synthetic pay-element names, columns `id,pay_element_name,source_style,gold_category,note`. `source_style` only says which package's naming habit the name imitates (BrightPay, Xero, Sage50, Staffology, generic, bureau_custom); the names are invented, not copied from any product. 32 rows are tagged `AMBIGUOUS:` in the note with the reason.
- `LAYOUTS.md`: documented report/export column layouts and their gold mapping.

## Categories (nine)
basic, regular_overtime, commission, bonus_non_regular, allowance, expense_excluded, holiday_pay_paid, statutory_excluded, deduction_excluded.

`deduction_excluded` is NOT named in KILL-TEST.md mark B1 (its list has eight). It is added because payroll exports always contain tax, NI, pension, student loan and similar lines, and forcing them into expense_excluded or statutory_excluded would make the label wrong. They never count towards holiday pay. Decision for the Studio Lead: if B1 is scored on eight categories, fold `deduction_excluded` into `expense_excluded` for scoring (both mean "excluded"); I recommend scoring on all nine and reporting both. KILL-TEST.md is not edited.

Counts: basic 28, regular_overtime 24, allowance 24, statutory_excluded 24, bonus_non_regular 22, deduction_excluded 22, commission 20, expense_excluded 20, holiday_pay_paid 16.

## Rules used for the labels
Labels are by element type (what the name denotes), not by whether this worker's history makes it regular; the engine tests regularity on pay history.
1. **Overtime** (any spelling, "Overtime" alone, OT1.5, time and a half): `regular_overtime`. Normal pay includes overtime that is regularly worked (Bear Scotland v Fulton, Hertel v Woolf/Dudley v Willetts line, Flowers v East of England Ambulance Trust). A name alone cannot show irregularity, so default is in. The gov.uk page states "normal rate of pay includes commission, regular overtime payments, and any payments related to length of service or professional qualifications. It does not usually include bonus payments."
2. **Commission and results-linked pay** (commission, piece rate, monthly productivity pay, sales incentive): `commission`.
3. **Bonus**: discretionary, one-off, annual, Christmas, sign-on, ex gratia, spot award: `bonus_non_regular` (not normally in normal pay).
4. **Allowance**: payments intrinsically linked to performing the work or to status: shift, night, on-call/stand-by, unsocial hours, London weighting, first aider, skills/qualification, length of service, acting up.
5. **expense_excluded**: reimbursement of or contribution to a cost (mileage, subsistence, car/phone/uniform/tools allowance, expense claims). Not pay for work.
6. **holiday_pay_paid**: money already paid for leave (holiday pay, annual leave, rolled-up holiday, bank holiday pay, payout of untaken leave). The engine needs it to compare paid vs due.
7. **statutory_excluded**: SSP, SMP, SPP, SAP, ShPP, SNCP, occupational sick/maternity pay, redundancy, PILON, severance. Not pay for work in a leave week's normal pay.
8. **deduction_excluded**: tax, NIC (employee and employer), pension (incl. salary sacrifice), student loan, attachments, union, cycle to work, loan repayments, net pay.
9. **basic**: salary, wages, contracted/normal hours pay, day rate, TOIL paid out, back pay of ordinary pay.

## Sources (fetched 2026-11-26; page text treated as data)
- https://www.gov.uk/holiday-entitlement-rights/calculate-holiday-pay (via https://www.gov.uk/api/content/holiday-entitlement-rights/calculate-holiday-pay): quote above on normal pay; irregular-hours and part-year workers, 12.07% rolled-up.
- https://www.gov.uk/holiday-entitlement-rights and https://www.gov.uk/calculate-your-holiday-entitlement: entitlement background.
- https://www.legislation.gov.uk/uksi/2023/1426/contents (Employment Rights (Amendment, Revocation and Transitional Provision) Regulations 2023): the 2024 changes to holiday pay and rolled-up holiday pay. The fetched page returned only page chrome in text extraction, so I did NOT extract regulation wording from it. The detailed definition of "regular" overtime (regulation 16 Working Time Regulations as amended) was not verified from the fetched text; rule 1 rests on the gov.uk page above and the case-law line named, which I state from memory and the Studio Lead should have checked before relying on it.
