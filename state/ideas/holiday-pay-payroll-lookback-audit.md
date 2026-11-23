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
| 15 | 12 | 7 | 7 | 11 | 6 | 5 | 63 |

## Validator notes (2026-11-23)

**Verdict: REVISE, 63.** This is the best idea of round 3, and the first of 30 with an incumbent gap confirmed on the incumbents' own pages. It falls short of 70 for three reasons:
- Enforcement has no start date, and the Fair Work Agency (FWA) is building its own free calculator.
- The core is a deterministic rules engine, so AI is a helper, not essential.
- Holding workers' pay and absence data pulls Risk down.

**Red-flag check: none.**
- **Legal advice: no, if built as a calculation tool with a professional's sign-off.** Payroll software already does this job; IRIS, for example, lets users "define pay elements to include in your Holiday Pay calculation". The guardrails that keep it a calculation tool:
  - The user, not the tool, decides each worker's status and whether they are an irregular-hours or part-year worker. AI may suggest, quoting the statutory definition, and the suggestion is labelled as one.
  - Which pay elements count as "normal pay" is a per-element setting, with the gov.uk or Acas guidance quoted next to it. Rounding and method variants are explicit options.
  - Outputs say "recalculated under these settings", never "compliant", "owed" or "liable". A named payroll professional or adviser signs off.
  - It is sold to bureaux, accountants and employers, never to workers. No tribunal or FWA letters in the MVP.
- No paid service and no scraping.
- Synthetic data can credibly show the value, because the rules are public and deterministic. A synthetic 60-worker payroll with seeded errors shows exactly what the tool finds:
  - regular overtime missing from the 52-week average;
  - 12.07% accrual applied to a leave year that started before 1 April 2024;
  - rolled-up pay not shown as a separate payslip item.
- Real-world error rates stay unproven until a pilot.

**Forcing function: confirmed on primary sources, with one limit the file missed**
- **Records duty.** "Since April 2026, employers have been required to keep holiday pay records for six years (regulation 16B of the Working Time Regulations 1998) that are adequate to show whether they have complied with the requirements" (DBT consultation, 30 June 2026, p.14). Acas lists holiday taken, leave carried over and holiday pay as the records to keep (search summary).
- **FWA timing.** The FWA launched on 7 April 2026 (law-firm summaries). Its delivery plan (updated 21 Aug 2026) says "Holiday pay enforcement is expected to begin in 2027". No date is fixed.
- **Proposed penalties** (consultation pp.6 and 27):
  - 200% of arrears per worker, at most £20,000 per worker and at least £100 per case;
  - "effectively 100% of arrears" if the arrears and half the penalty are paid within 14 days;
  - naming is only under consideration (p.21).
  - The consultation closed on 22 September 2026. I found no government response yet.
- **Claim period.** Six years is proposed, the legal maximum (p.25). **But the FWA cannot enforce underpayments from before Royal Assent on 18 December 2025** (pp.25-26).
  - So the state look-back starts in December 2025 and grows a year at a time. It is not "the past 2 to 3 years", as the pitch says.
  - Older exposure comes only through tribunal claims, which carry a two-year backstop (Deduction from Wages (Limitation) Regulations 2014; not re-read in this pass) and a three-month time limit that becomes six months "no earlier than October 2026" (p.25).
- **The strongest reason to self-audit:** "A penalty would not ordinarily be issued where an employer has correctly repaid all holiday pay arrears that are owing to the workers before the start of an FWA investigation" (p.21).
- **What softens it:**
  - The same page shows the FWA's first step is a letter asking the employer to check and repay, so an accidental underpayer may simply wait for the letter.
  - The FWA will deliver "an online payslip explainer, a holiday pay calculator" in 2026-27 (delivery plan; scope not stated).
  - The consultation also floats "a more detailed calculator or self-assessment tool" (p.23).

**Pain evidence**
- **Government estimates** (consultation pp.14-15). The government notes these are survey-based.
  - Resolution Foundation: 2.2 million jobs were not given any annual leave in 2025.
  - TUC: about 1.1 million workers were not given holiday pay in 2023, about £2 billion in total or £1,800 per worker.
  - Acas: about 8,000 working-time (annual leave) claims and 13,000 Wages Act claims in 2024/25.
- **Practitioners doing it by hand.** Xero's product idea "Run a report to calculate holiday pay based on a 52 week average" has 94 votes (fetched).
  - Users wrote "still stuck manually calculating everything in a spreadsheet" (April 2025) and "Xero doesn't even produce reports with the necessary figures to perform the calculations" (November 2025).
  - On 27 November 2025 a Xero admin replied that it "is not a feature we have planned in our roadmap".
- **Employer survey.** RSM Workforce Survey, reported by consultancy.uk on 13 July 2026 (sample size not stated): 56% of businesses pay all types of holiday at the same rate, and 11% calculate holiday pay by hand.
- **Job-ad signal: still weak.** The only find was a Bournemouth payroll administrator advert (£29,000) listing "statutory payments such as holiday pay" (search summary).

**Competitors on their own pages** (the file's open item)

| Product | Calculates holiday pay amounts? | Whole-workforce look-back or audit? | Source |
|---|---|---|---|
| BrightPay | **No.** "The holiday pay amount due to an employee is not automatically calculated by BrightPay and thus must be entered manually by the user" (2025-26 docs). It accrues hours only (support article; 403, search summary). | No | brightpay.co.uk docs (fetched) |
| Xero Payroll UK | **No** 52-week calculation. The admin says it is not on the roadmap (27 Nov 2025). | No | productideas.xero.com (fetched) |
| Moneysoft Payroll Manager | **Not automatically.** An Average Pay report has a 52-week column, usable only if the employee was paid every period. The irregular-hours rate is worked out by hand. | No | moneysoft.co.uk support (search summary; direct fetch 404) |
| Sage 50 Payroll | **No automatic calculation found.** Sage staff point users to a 52-week report, and one user paid for a custom report. Sage HR doesn't calculate holiday pay amounts. | No | Sage community hub and support.sage.hr (search summaries) |
| Staffology Payroll (IRIS) | Yes, forward only: 52-week averaging, an Average Holiday Pay Rate report and a CSV import of historic earnings | Not documented | help.staffology.co.uk (fetched); IRIS course page (fetched) |
| IRIS Earnie Holiday Pay Module | Yes, forward only, during the payroll run, with chosen pay elements and excluded periods | Not documented | iris.co.uk (search summary) |
| Employment Hero | Yes, forward only, including on its Free Payroll plan, with a 52-week data import | Not documented | help.employmenthero.com (search summary) |
| SafeRec | Per-payslip "forensic" audits for agencies, MSPs and end clients; free to start | No. Works per payslip, with no workforce look-back. | saferec.co.uk (fetched) |
| Limelite HR, Irwin Mitchell, Muckle | Human reviews: Limelite standalone review (no price); Irwin Mitchell £1,500 + VAT fixed fee (March 2024); Muckle £500 to £1,500 + VAT (general HR audit) | Manual | fetched; Muckle from the scout's evidence |
| Free substitutes | gov.uk and Acas calculators (one worker at a time); paiyroll free Excel template; Odoo module for $58 | No | search summaries |
| "PayTime" bureau tool | UNVERIFIED. It appeared in one search snippet only, and its domain now shows unrelated content. | n/a | n/a |

What the matrix shows:
- **The gap is real and specific.** The payroll packages small bureaux use most (BrightPay, Xero, Moneysoft, Sage 50) don't calculate holiday pay amounts at all. None of the ten products documents a whole-workforce look-back.
- **Forward calculation already exists** in Staffology, IRIS and Employment Hero. So a bureau's cheapest substitutes are switching payroll package or keeping its spreadsheet.
- **What an incumbent could copy in a month:** a 52-week calculation and a history report in BrightPay, Xero or IRIS. Xero has declined and BrightPay hasn't added one in six years, but enforcement in 2027 could change that.
- **The FWA calculator is the bigger unknown.** If it accepts a whole payroll upload, the gap closes for free.

**Scoring rationale**
- **Pain 15.** Official non-compliance estimates, a records duty in force, and manual spreadsheets every pay run in the tools bureaux use. Not higher, because:
  - enforcement has no start date;
  - the FWA leads with a letter, not a penalty;
  - there is still no job-ad signal.
- **Pay 12.**
  - For: two published prices for human reviews (£1,500 + VAT; £500 to £1,500 + VAT), the 200% penalty at stake, and staff hours.
  - Against: no published software price for this job. Bureau software is cheap (BrightPay Bureau about £229 a year per startups.co.uk, possibly out of date), and Employment Hero's free plan calculates forward.
- **AI 7.** The core is a rules engine. AI maps export columns and pay-element names and explains exceptions in plain English. That is useful, but payroll reports are structured, so a rival could build this without AI.
- **Reach 7.**
  - Bureaux and accountants: one sale reaches many employers.
  - Professional bodies, and trade bodies such as the ECA, which urged electrical contractors to review holiday pay in February 2026 (search result).
  - The partner's sector is unknown.
- **Build 11.** Four weeks is realistic for this scope, read from BrightPay, Xero and Sage 50 report layouts:
  - 12.07% accrual for leave years from 1 April 2024;
  - checks on rolled-up pay;
  - 52-week averages with the 104-week count-back;
  - the split between regulation 13 and 13A leave.
  - Sickness, family leave and pre-2024 rules come later. Real worker data can't live on the Azure for Students subscription.
  - The scout's £15 to £30 a month would use most of the $80 over three months, so it fits only with scale-to-zero and the shared Postgres. The architect must cost it.
- **Competition 6.** The gap is confirmed on four incumbents' own pages, including an explicit "not on our roadmap". Forward calculators and the coming FWA tool hold it at 6.
- **Risk 5.** Deductions:
  - −2 for personal data at scale: pay and hours for whole workforces across many clients. This also covers the 16 and 17 year olds on hospitality and retail payrolls.
  - −2 because absence periods reveal sickness and family leave, which is health-adjacent data.
  - −1 for the remaining advice-boundary and liability risk if the tool understates arrears.

**What would change my mind (re-score on this evidence)**
1. **Sharpen the pitch.** Make it a holiday pay engine for bureaux on BrightPay, Xero, Moneysoft and Sage 50: it calculates every pay run from the payroll's own reports, and looks back to 18 December 2025 (the FWA window) and two years (the tribunal window). That makes it recurring, not a one-off audit.
2. **Pay.** Two published prices for holiday pay calculation software, or bureau price lists that charge extra for holiday pay calculations. Pay to 14.
3. **Pain.** Bureau or payroll job adverts that name 52-week or 12.07% calculations, or a CIPP survey of holiday pay workload. Also the government's consultation response, confirming the six-year period, the penalties and a start date. Pain to 16.
4. **Risk.** A pseudonymised data design signed off by the security agent: payroll ID only (no names or NI numbers), absences coded as "excluded week" with no reason, UK region, inputs deleted after 30 days. Risk to 7.
5. **AI and Build.** A desk benchmark on the publicly documented report layouts of BrightPay, Xero and Sage 50, plus 200 synthetic pay-element names. Pass: at least 95% correct mapping, and every result reproduces the gov.uk and Acas worked examples. AI to 8, Build to 12.
6. **Kill test.** Read the FWA calculator when it ships, and Staffology's, IRIS's and Employment Hero's own pages for any history or arrears report. If any of them takes a whole payroll and lists past underpayments, Competition falls to 2, and a second failure kills the idea.

Items 2 to 5 together give exactly 70 (16+14+8+7+12+6+7). The idea passes only if all four land and item 6 doesn't fail, so re-score only once they are all in.

**Sources** (all accessed 2026-11-23)
- https://assets.publishing.service.gov.uk/media/6a3e79add52550a19950f617/make-work-pay-holiday-pay-compliance-and-enforcement.pdf (PDF read, pp.1-32)
- https://www.gov.uk/government/publications/fair-work-agency-delivery-plan-for-2026-to-2027/fair-work-agency-delivery-plan-2026-to-2027 (fetched; updated 21 Aug 2026)
- https://www.linklaters.com/insights/blogs/employmentlinks/2026/april/launch-of-the-fair-work-agency (search summary; FWA launch)
- https://www.acas.org.uk/checking-holiday-entitlement/keeping-records (search summary)
- https://brightpay.co.uk/docs/25-26/annual-leave/processing-holiday-pay (fetched)
- https://brightpaydesktopsupport.uk.brightsg.com/hc/en-gb/articles/37042791609361-Holiday-Entitlements-Useful-Information (403; search summary)
- https://productideas.xero.com/forums/967118-payroll-expenses/suggestions/45241594-uk-payroll-reporting-run-a-report-to-calculate (fetched)
- https://moneysoft.co.uk/support/average-pay-for-holiday-calculations/ (404 on fetch; search summary)
- https://communityhub.sage.com/gb/sage-50-payroll/f/processing-your-payroll/219975/52-week-average-holiday-pay and https://communityhub.sage.com/gb/sage-50-payroll/f/general-discussion/263645/52-weekly-average-for-holiday-pay (search summaries)
- https://support.sage.hr/en/articles/9127755-calculate-holiday-entitlement-for-irregular-workers (search summary)
- https://help.staffology.co.uk/payroll/reports/payruns/average-holiday-pay.htm (fetched); https://help.staffology.co.uk/payroll/leave-and-absence/holidays/average-holiday/pay-history-for-average.htm (search summary); https://www.iris.co.uk/?p=228619 (fetched)
- https://www.iris.co.uk/?p=5352 (IRIS Holiday Pay Module; search summary)
- https://help.employmenthero.com/hc/en-gb/articles/17426656620815-52-Week-Average-Holiday-Pay (search summary)
- https://saferec.co.uk/forensic-payslip-audits (fetched)
- https://limelitehr.com/content-corner/article/new-holiday-pay-law-2026-what-do-uk-employers-need-to-know-and-do-now/ (fetched)
- https://www.irwinmitchell.com/news-and-insights/expert-comment/post/102j36k/have-you-budgeted-for-increased-holiday-pay-costs (fetched; dated 20 Mar 2024)
- https://www.consultancy.uk/news/44907/holiday-pay-crackdown-approaches-with-half-of-employers-open-to-errors (fetched)
- https://paiyroll.com/holiday-pay/free-holiday-pay-templates/ and https://apps.odoo.com/apps/modules/18.0/gb_holiday_pay_calculator (search summaries)
- https://startups.co.uk/people/payroll/brightpay/ (search summary; price may be out of date)
- https://findajob.dwp.gov.uk/details/17028627 (search summary)
- https://www.eca.co.uk/news/2026/feb/holiday-pay-why-electrical-contractors-should-review-it-now (search result title only)

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted. Job-ad signal missing, flagged.
- 2026-11-23 | validator | G0→G1 | REVISE 63 | Best of round 3, and the first idea with an incumbent gap confirmed on the vendors' own pages: BrightPay, Xero, Moneysoft and Sage 50 don't calculate holiday pay amounts, and no product documents a whole-workforce look-back. But FWA enforcement has no start date, the FWA is building its own free holiday pay calculator, and its look-back starts only at 18 Dec 2025. The core is a deterministic engine, and holding workers' pay and absence data cuts Risk to 5.
