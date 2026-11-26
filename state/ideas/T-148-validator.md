VERDICT: PASS

# T-148 validator check of state/ideas/T-148-scout.md (2026-11-26)

All fetches ran on 2026-11-26. Page text was treated as data, and no injection was seen.

## 1. PayslipIQ claims: verified

| Claim | Result | URL |
|---|---|---|
| Not for sale, no launch date | Holds. The page says "Not available yet", "nothing is for sale here" and marks the checks "Planned". | https://payslipiq.co.uk/business |
| Names "holiday-pay miscalculations" | Holds. It is one bullet with NMW/NLW, auto-enrolment and NI category, and gives no method. | https://payslipiq.co.uk/business |
| No 52-week or look-back method | Holds. None of 52-week, reference period, look-back, historic runs or arrears appears. The checks run "before anyone is paid", so they are forward checks. | https://payslipiq.co.uk/business |
| Bureau page omits holiday pay and SSP | Holds. Coverage is PAYE, NI, pension, student loan, salary sacrifice, Irish PAYE/USC/PRSI and umbrella rate checks. It has an email waitlist. | https://payslipiq.co.uk/business/bureau |
| No employer or bureau price; Pro £19 not on sale | Holds. The pricing page shows "Planned, not live" and "Not on sale yet". | https://payslipiq.co.uk/pricing |
| Free consumer checker live | Holds. It is "educational guidance only". | https://payslipiq.co.uk/ |

**Operator (company level):** GoldPaid Ltd, England and Wales, company no. 17382540. The footer also shows a GoldPaid ad for buying gold and silver, which is unrelated to payroll.

**Minor nuance:** the scout wrote "waitlist only". The /business page actually offers a newsletter sign-up, and /business/bureau offers an email waitlist. Either way, nothing is on sale.

## 2. Effect on holiday-pay-payroll-lookback-audit: no score change

The score stays at 64, with Competition at 7. PayslipIQ is an unlaunched waitlist with no method, price or date, and it is designed as a pre-pay-run check, not a look-back. The T-57 reasons for scoring 7 rather than 8 already cover the risk that a payroll-upload checker adds holiday pay. PayslipIQ is now named in the kill test, and its launching a whole-payroll look-back would drop Competition to 2. RANKING.md is not changed.

## 3. Spot-check of the scout's verdicts

- #1 AE reconciliation, WATCH: correct. The TPR enforcement counts give no causes, and in-run and provider checks already exist.
- #2 SSP look-back, WATCH: correct. Software does SSP in the run, and the penalty claim rests on one search summary.
- #3 Leaver holiday, WATCH as a module: correct. It reuses the ingest but has no price of its own.
- #4 Variance QC, DROP: correct. Sage Payroll Copilot already ships it.
- #5 NI and Employment Allowance, DROP: correct. There is one weak signal and no price.
- #6 Salary sacrifice vs NMW, DROP: correct. It repeats a killed idea, and Fair Work Solutions exists.
- #7 Other ERA 2025 checks, DROP for now: acceptable, but the commencement dates are unverified, so revisit once they are set.

No KEEP was missed. Lesson 2 (stay narrow and deep rather than widen into a generic checker) is sound.
