# Holiday pay payroll look-back audit

- slug: holiday-pay-payroll-lookback-audit
- stage: G0
- market and segment: UK payroll bureaux, accountants and employers with 20 to 500 irregular-hours, part-year or variable-pay staff (hospitality, care, retail, events, education support, agencies).
- one-line pitch: Reads a payroll export for the past 2 to 3 years, recomputes holiday accrual and holiday pay for each worker under the 2024 rules, and produces an exceptions report with the working shown, for the payroll professional or employment adviser to sign off.

## Problem and who has it
- Since leave years starting on or after 1 April 2024, irregular-hours and part-year workers accrue holiday at 12.07% of hours worked per pay period; rolled-up pay is allowed for them and must be shown as a separate payslip item. Holiday pay for other workers must reflect normal pay, including regular overtime or commission. Sources disagree on rounding (Acas rounds down fractions under 30 minutes; Brightmine rounds to the nearest hour; IRIS says do not round down).
- Variable pay, mid-year status changes and misclassification are where errors arise. Law firms advise employers who pay 'extras' to audit.
- Employers and bureaux have no systematic way to test past payroll runs against the rules; forward accrual is in the software, look-back is not.

## Forcing function
- Duty to keep holiday records in force from 6 April 2026, enforcement by the new Fair Work Agency (law-firm summary: DLA Piper https://knowledge.dlapiper.com/dlapiperknowledge/globalemploymentlatestdevelopments/2026/employment-rights-act-preparing-for-change-duty-to-keep-holiday-records-means-new-legal-risks-for-employers, accessed 2026-11-23).
- FWA holiday pay enforcement intended from April 2027 (Baker McKenzie: https://www.bakermckenzie.com/en/insight/publications/2026/07/united-kingdom-fair-work-agency-holiday-pay-enforcement-strategy). Proposed penalty 200% of the underpayment, capped at £20,000 per worker, with naming (Littler: https://www.littler.com/news-analysis/asap/holiday-pay-enforcement-uk-consultation-launched-role-fair-work-agency). Government consultation document: https://assets.publishing.service.gov.uk/media/6a3e79add52550a19950f617/make-work-pay-holiday-pay-compliance-and-enforcement.pdf. The consultation closed 22 September 2026, so final rules may still change. All from search summaries; the validator should read the primary pages.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.acas.org.uk/irregular-hours-and-part-year-workers | 2026-11-23 | 12.07% accrual of hours worked, per pay period; rounding example |
| https://www.iris.co.uk/blog/payroll/unpacking-the-2024-holiday-pay-changes-for-irregular-hours-workers-and-part-year-workers/ | 2026-11-23 | Accrual vs rolled-up differences; conflicting rounding advice noted by summary |
| https://www.azets.com/en-uk/resources/holiday-pay-enforcement-are-your-payroll-processes-ready-for-increased-scrutiny | 2026-11-23 | Accountancy firm warns of scrutiny; lists overtime and commission checks |
| https://www.consultancy.uk/news/44907/holiday-pay-crackdown-approaches-with-half-of-employers-open-to-errors | 2026-11-23 | Headline claims half of employers open to errors (survey basis not read; low weight) |
| https://lewissilkin.com/en/ireland/services/hr-services/workplace-audits/holiday-pay-audits | 2026-11-23 | Law firm sells holiday pay audits (an Irish page; UK equivalent not verified) |
| https://www.muckle-llp.com/files/pdf/Mi-HR-Auditv2.pdf | 2026-11-23 | Muckle HR audit priced per category: £500 + VAT (1 to 19 employees), £750 + VAT (20 to 99), £1,500 + VAT (250+) |
| https://assets.publishing.service.gov.uk/media/699c81d4d2b9c6ec5b6fbc0d/Oladayo_Akinniyi_-vs-_Altonian_Coaches_Limited___1_other_-_Judgment.pdf | 2026-11-23 | Tribunal judgment (Feb 2026) applying holiday pay rules; holding not read |
| https://assets.publishing.service.gov.uk/media/69e0c09a20b52e41448688e1/6044522.2025_L_Gittins_v_Help_in_homes_ltd_judgment.pdf | 2026-11-23 | Tribunal judgment applying the 12.07% figure; holding not read |
| https://www2.deloitte.com/content/dam/Deloitte/uk/Documents/tax/deloitte-uk-tax-fair-pay-holiday-pay.pdf | 2026-11-23 | Deloitte on holiday pay exposure; government estimate of £3.2bn a year (figures differ across sources) |

Job-ad signal still to find: payroll or compliance roles that list holiday pay checks. Not yet found; the validator or next scout should search.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Payroll and rota software with 12.07% accrual: Moneysoft (https://moneysoft.co.uk/support/holiday-pay-for-irregular-hours-and-part-year-workers/), RotaCloud (https://help.rotacloud.com/en/articles/8228769-introduction-to-holiday-accrual), PayFit (https://support.payfit.com/en/articles/152943-calculating-holiday-pay-and-entitlement-for-irregular-workers), PeopleHR (https://help-peoplehr.theaccessgroup.com/en/articles/12017664-accrue-holidays-for-hours-worked), Employment Hero (https://help.employmenthero.com/hc/en-gb/articles/12586259296271-Rolled-up-holiday-pay-for-irregular-casual-workers-in-Employment-Hero) | Bundled in subscription | Forward-looking, per system. None of these pages describes a multi-year look-back across exports. Not checked: BrightPay, Sage, Xero, Staffology help pages |
| Law-firm or accountancy audits (Muckle HR audit above; Lewis Silkin) | £500 to £1,500 + VAT per category (Muckle, HR audit not holiday-only) | Manual, sampling, slow |
| Gov.uk and Acas calculators | Free | One worker at a time |

Gap that survives (provisional): a whole-workforce look-back across payroll exports with working shown. Risk: payroll vendors could add an 'audit' report in weeks, and BrightPay, Sage, Xero help pages were not checked.

## Why AI is essential (and the moat)
- Exports differ across payroll systems; AI maps columns and pay element names (basic, overtime, bonus, 'holiday', 'rolled-up') into a standard ledger. Maths is deterministic with explicit rule options (rounding variants) so the adviser picks the method. Moat: the mapping library for common payroll exports and test cases from tribunal decisions.

## Public dataset for the demo
- Acas and gov.uk rules, National Minimum Wage rates (gov.uk, OGL v3.0); employment tribunal decisions on https://www.gov.uk/employment-tribunal-decisions (published; reuse terms to verify). Demo uses a synthetic payroll of 60 workers with seeded errors. No customer data needed.

## How the selling partner could reach buyers
- Payroll bureaux and accountants (one sale to a bureau reaches many employers), plus care and hospitality groups. A UK business friend is positioned as the contracting party. Named channel to be confirmed.

## Rough build plan and Azure cost
- Export mapper for 3 payroll formats, rules engine with selectable methods, exceptions report, evidence pack. 3 to 4 weeks. Azure £15 to £30 per month (estimate). Worker personal data is processed in production: UK GDPR, DPA and retention rules needed; not needed for the demo.

## Risks, and what would prove this wrong
- Biggest: legal-advice boundary and personal data of workers (Risk score). Frame as calculation and evidence; a payroll professional or employment solicitor signs off.
- Enforcement is not yet in force (planned April 2027), so urgency may not arrive until 2027.
- Payroll vendors may ship audits. Test: read BrightPay, Sage, Xero and Staffology help pages for look-back or audit reports; if found, drop.
- Case law is unsettled on rounding and 'normal pay'.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted. Job-ad signal missing, flagged.
