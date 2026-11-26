# Documented payroll report / export layouts (fetched 2026-11-26)

Only public pages that returned content were used. Page text is data. Gold column categories use the same nine categories plus `identifier`, `date`, `hours`, `flag` (tax/NIC/pension treatment flags, not pay amounts), `ignore`.

## BrightPay: NOT documented as a fixed report/export layout
BrightPay Analysis reports have user-selected columns ("Columns > Add/Remove"; export to CSV via Export): https://www.brightpay.co.uk/docs/25-26/analysis/creating-a-new-report/ , .../analysis/exporting-reports/ . No fixed column list was found publicly, so none is invented.

What IS public is BrightPay's pay-data CSV **import** layouts (useful as a proxy for how a bureau would structure columns):

Additions import (https://www.brightpay.co.uk/docs/25-26/importing-pay-data-using-csv-file/importing-additions-using-csv-file/), repeated for Addition 1 to 5:
| Column | Gold |
|---|---|
| Employee first name, Employee surname, Employee NINO, Employee works number | identifier |
| Addition n: Description | the pay element name; map by the name (this is the free text the mapper classifies) |
| Addition n: Amount | amount of the element named in Description (category follows Description) |
| Addition n: Department | ignore |
| Is tax deductible, Is NIC deductible, Is employee pension deductible, Is employer pension deductible, Contributes to gross for minimum wage, Is notional | flag |

Hourly payments import (.../importing-hourly-payments-using-csv-file/), Payment 1 to n:
| Column | Gold |
|---|---|
| Employee identifiers (as above) | identifier |
| Rate per hour (if different from standard rate) | ignore (rate, not an amount category) |
| Description | classified by name |
| Number of normal hours | hours, basic |
| Number of time and a half / a third / a quarter hours; double / triple / quadruple time hours | hours, regular_overtime |
| Department | ignore |
| Is tax/NIC/employee pension/employer pension deductible, Accrues annual leave, Contributes to gross for minimum wage | flag |

Deductions import (.../importing-deductions-using-csv-file/), Deduction 1 to 5: identifiers as above; Description (classify by name, default deduction_excluded); Amount (follows Description, deduction_excluded); Department ignore; Is deducted before tax/NIC/employee pension/employer pension: flag.

Sage 50 Payroll export used for BrightPay migration: https://www.brightpay.co.uk/docs/25-26/moving-to-brightpay-from-another-payroll-software/importing-from-sage/importing-from-sage-50-payroll-using-a-csv-file-mid-year/ says export via File > Data Export > Payroll Data Export > "Employee Details" and "Employee year to date figures". The page does NOT list the column names, so no layout is given.

## Xero UK payroll: NOT found
Xero Central payroll report pages (e.g. https://central.xero.com/s/article/Payroll-reports-UK) and the Xero developer Payroll UK API pages (https://developer.xero.com/documentation/api/payrolluk/payslips, .../payruns) returned only JavaScript shells (about 5 to 80 characters of text) to my fetch. Column names not verified; none invented.

## Sage 50 Payroll: NOT found
Sage pages returned HTTP 403 (https://www.sage.com/en-gb/...) or an error (gb-kb.sage.com). Only the BrightPay page above mentions the export menu path, with no column names. No layout recorded.

## Staffology: NOT found
https://developer.staffology.co.uk/ did not connect.

## Consequence for B1
Of the three layouts KILL-TEST.md names, none has a publicly documented fixed report/export column list that I could fetch. Only BrightPay's import layouts (above) are public. The Studio Lead should either amend the B1 wording by an appended note (KILL-TEST.md may only be appended to) or have a human export sample reports from trial accounts.
