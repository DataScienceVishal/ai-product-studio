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
| 15 | 12 | 7 | 7 | 11 | 7 | 5 | 64 (re-score 2026-11-24, T-57, Q-10 wedge rule; see Gate log) |

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

## Evidence pass T-23 (2026-11-23)

All pages accessed 2026-11-23 by desk research. "Search summary" means the claim comes from a search-engine summary and was not read on the page. No injection attempts seen in fetched pages.

### 1. Kill test (validator item 6): KILL-TEST DOES NOT FAIL on what could be read, with gaps

No page I could read documents a whole-payroll history, arrears or holiday-pay recalculation report that lists past underpayments. Absence is shown by pages that describe the feature set and omit it, so it is "not documented", not "confirmed absent".

| Product | What its own page says | Look-back / arrears report? | Link |
|---|---|---|---|
| Staffology Payroll | Report purpose: "View an employees average holiday pay rate." Run by choosing a Tax Year and Month. Page does not say it identifies underpayments or covers all employees. | Not documented | https://help.staffology.co.uk/payroll/reports/payruns/average-holiday-pay.htm (fetched) |
| IRIS Holiday Pay Module (Earnie) | Will "automatically calculate and pay the 52-week average weekly earnings as part of the payroll run"; chooses pay elements; excludes zero-pay periods. Page mentions no history, back-calculation, arrears or audit report. No price (book a demo). | Not documented | https://www.iris.co.uk/?p=5352 (fetched) |
| IRIS Earnie help | CSV template for importing average holiday pay history; "Average Weekly Earnings" report shows periods used; "Recalculate" applies to the current run (search summary, pages not read: hol-reports page returned 404) | Not documented (forward only) | https://help-iris.co.uk/payroll/earnieiq/modules/holiday/hol-options.htm and https://help-iris.co.uk/payroll/every/leave-and-absence/holidays/average-holiday/pay-history-for-average.htm (search summary) |
| Employment Hero UK | Solutions page describes 52-week averaging and says "We can help you manage leave policies tailored to each employee type"; no arrears or recalculation report, no price. Help article: 52 Week Average report per pay and leave category, fed by an imported data file (search summary). Six-year records blog mentions no audit feature. | Not documented | https://employmenthero.com/uk/solutions/holiday-pay-calculation/ (fetched); https://employmenthero.com/uk/blog/six-year-records-rule-holiday-pay-compliance/ (fetched); https://help.employmenthero.com/hc/en-gb/articles/17426656620815-52-Week-Average-Holiday-Pay (403 on fetch; search summary) |
| PayFit UK | Help article says PayFit supports accrual and rolled-up methods and has "a feature that can be used to calculate ... using an average of their pay or hours over the previous 52 weeks"; no look-back report mentioned | Not documented (search summary only; page not read) | https://support.payfit.com/en/articles/152943-calculating-holiday-pay-and-entitlement-for-irregular-workers |
| Moorepay | Software and bureau marketing: "audit logs" and PAS accreditation; no holiday pay audit product found. Its holiday pay guide carries a note that it predates the April 2024 rules. | None found | https://www.moorepay.co.uk/blog/how-to-calculate-holiday-pay-an-employers-guide/ and https://www.moorepay.co.uk/payroll-bureau/ (search summary only; not read) |
| Sage 50 Payroll | No official help page found. Community threads only: Sage staff "could only point to the 52-week report"; users say it is inaccurate for irregular hours input. | None found | https://communityhub.sage.com/gb/sage-50-payroll/f/general-discussion/263645/52-weekly-average-for-holiday-pay (search summary) |
| Other holiday-specific vendors | Workforce.com "automated leave averaging": calculates hours and pay for staff without fixed hours from existing data; page "doesn't say" it audits past holiday pay; no price. Weightmans "Calculate - Holiday Pay": guided or lawyer-led service; fixed fee, amount not stated; back-calculation not addressed. | Not documented | https://www.workforce.com/uk/software/automated-leave-averaging ; https://www.weightmans.com/products/calculate-holiday-pay (both fetched) |

Fair Work Agency (FWA) holiday pay calculator: NOT SHIPPED as of 2026-11-23, as far as I can find.
- The delivery plan (updated 21 August 2026) lists "a holiday pay calculator" among year-1 tools, described as one of the "simpler tools" for workers and businesses, next to an online payslip explainer. Scope not stated, so whether it takes a whole payroll is unknown. Source: https://www.gov.uk/government/publications/fair-work-agency-delivery-plan-for-2026-to-2027/fair-work-agency-delivery-plan-2026-to-2027 (fetched). The summary of the plan's own words was returned by the fetch tool, not copied from the page, so re-read before quoting.
- A search for a launched FWA calculator returned only Australian Fair Work Ombudsman tools and the gov.uk holiday entitlement calculator, which is one worker at a time. No UK FWA calculator page found.
- The consultation floats "a more detailed calculator or self-assessment tool" (validator read, p.23). CIPP's response asks for "calculators, self-assessment tools" and "worked examples" (https://www.cipp.org.uk/resources/news/holiday-pay-consultation-response-available.html, fetched). So a free government tool is likely, and a whole-workforce version is plausible. Re-check on the gov.uk FWA pages before any re-score.

Open kill-test gaps: Sage and Moorepay have no readable official page; PayFit, IRIS help and Employment Hero help are search summaries only. A human with product access (not us, no trials allowed) would settle these.

### 2. Pay evidence (item 2)

Published prices found for bureau charges on holiday pay calculations, no published software price for a look-back:
| Price point | Source | Accessed |
|---|---|---|
| DCK Payroll Solutions fee list, effective 1 April 2025: "Additional salary, holiday pay calculations, uplifts, AEO's etc" is a separately charged line at £73.50 per hour (ex VAT). Master file changes £7.50 per person; extra payroll employees £7.35 each. | https://greatandlittlehampdenparishcouncil.gov.uk/wp-content/uploads/2026/04/DCK-Fee-List-2025-26.pdf (PDF read) | 2026-11-23 |
| PSSG outsourced services price list from 1 April 2024: "Average / Enhanced Holiday Pay Calculations - non-standard (not processed via the Supplier's software)" is a separate additional charge, "Price on application via Change Control Process" (no figure). The same list shows the scale of other extras: payroll re-run £100 (up to 100 employees), £200 (101 to 300). Note: file is hosted on a cintra.co.uk domain with PSSG branding; supplier identity as shown on the PDF is PSSG. | https://marketing.cintra.co.uk/hubfs/OSS/OSS%20PRICE%20LIST%20April%202024%20V1.3.pdf (PDF read) | 2026-11-23 |
| Irwin Mitchell: £1,500 + VAT fixed fee for a holiday pay review (20 March 2024; validator fetched) | https://www.irwinmitchell.com/news-and-insights/expert-comment/post/102j36k/have-you-budgeted-for-increased-holiday-pay-costs | validator, 2026-11-23 |
| Muckle HR audit £500 to £1,500 + VAT (general HR audit, not holiday-only) | https://www.muckle-llp.com/files/pdf/Mi-HR-Auditv2.pdf | scout, 2026-11-23 |
| One-off spreadsheet template £13.99 (substitute cost, low end) | https://payhip.com/b/Jhkud (search summary) | 2026-11-23 |

Reading: the two bureau list prices show holiday pay calculation is already billed as an extra, one at £73.50 an hour. Neither is a software price. Estimate of the hours implied by a 60-worker look-back, for scale only: unverified, no method data. I found no published price for holiday pay look-back software, so item 2 is met for "bureau price lists that charge extra" (two found) but not for software.

### 3. Pain evidence (item 3)

- Job adverts: NOT FOUND. Two searches (standard and extended) returned no UK advert naming 52-week reference periods, 12.07% or rolled-up calculations. Closest: a DWP-listed payroll officer role requiring staff to calculate holiday payments, overtime and pension (https://findajob.dwp.gov.uk/details/17437892, search summary; not read, does not name the methods). Treat the job-ad signal as still missing. Do not use it for scoring.
- CIPP: ran a holiday pay call for input (closed 11 September 2026; page quote: "Holiday pay remains one of the most complex areas of employment rights and payroll administration"; https://www.cipp.org.uk/resources/news/have-your-say-holiday-pay-compliance.html, fetched, dated 25 August 2026; the page holds no survey data). Its consultation response (24 September 2026) says: "difficulties remain around interpreting and applying the rules in practice", cites "manual calculations and payroll software limitations" as practical difficulties, and notes respondents "showing a strong preference for a two-year period" over six years (https://www.cipp.org.uk/resources/news/holiday-pay-consultation-response-available.html, fetched). No workload figures or sample size given. This is qualitative pain evidence from the payroll professionals' own body, not a workload survey. It also signals pushback on the six-year window.
- Practitioner data gap: Armstrong Watson (July 2026) says payroll providers "are unlikely to hold details around annual leave", which are "employment records, rather than payroll data", and that multiple systems plus spreadsheets are common. Implication for the product: a payroll export alone is not enough; HR leave data must be joined in (https://www.armstrongwatson.co.uk/news/2026/07/holiday-pay-compliance-and-closing-data-gap, fetched). This weakens "upload a payroll export, get the arrears list" and should go into the Build and AI reasoning.
- Survey (consultancy.uk, search summary): 61% of employers use bespoke software, 33% rely on software defaults, 11% calculate by hand. Sample size unknown (https://www.consultancy.uk/news/44907/holiday-pay-crackdown-approaches-with-half-of-employers-open-to-errors).

Government response to the consultation: NOT PUBLISHED. The gov.uk page says the consultation closed at 11:59pm on 22 September 2026, "We are analysing your feedback" and "Visit this page again soon to download the outcome" (https://www.gov.uk/government/consultations/make-work-pay-holiday-pay-compliance-and-enforcement, fetched).

What is confirmed and what is not, from the consultation document (validator read) plus the delivery plan:
- Six-year claim period: PROPOSED, not final. Only for non-compliance after 18 December 2025. CIPP and others push back. The six-year records duty (regulation 16B, from 6 April 2026) is law; the six-year claim window is not.
- Penalties (200% of arrears, cap £20,000 per worker, minimum £100 per case): PROPOSED only, no response yet.
- Enforcement start: "Holiday pay enforcement is expected to begin in 2027" (delivery plan, updated 21 August 2026). No date. Law-firm and vendor pieces say "from 2027" and "April 2027" (Baker McKenzie); the April 2027 date is not in the primary source I read.

### 4. Other products doing whole-workforce holiday pay look-back

Searches run: "holiday pay look-back tool 2026 payroll historic underpayment report"; "holiday pay audit software UK upload payroll data check underpaid holiday pay workers 2026". No UK product found that takes a whole payroll and lists past holiday pay underpayments. Nearest equivalents:
- New Zealand: Inland Revenue built a Holidays Act remediation tool that recalculates every instance of leave across the remediation period (https://ird.govt.nz/topics/holiday-act-remediation-payments-for-former-employees), and third-party calculators exist (https://www.calculate.co.nz/holidays-act-remediation-calculator.php, one describes output as a scoping estimate). This is a useful precedent: a state-driven remediation wave created a market for per-employee, per-pay-period recalculation. Not UK, and the NZ government itself supplied a tool, which is also the risk if the FWA does the same.
- Human services: SafeRec (per-payslip audits), Weightmans guided service, Limelite HR reviews (all from earlier notes).
- Free substitutes: paiyroll template, Odoo module, payslipcheck.co.uk and moonworkers.co.uk calculators (search results only; titles seen, not read).
Caveat: search finds only what is indexed. A small bureau tool or a Big Four internal tool would not show.

### Re-score view (scout opinion; validator decides)
- Item 6 kill test: not failed on readable pages, but the FWA calculator is the main unknown (planned, scope unstated) and 4 of 8 vendors rest on search summaries. Competition stays near 6, not 2.
- Item 2 (Pay to 14): partly met. Two bureau price lists charging extra for holiday pay calculations (£73.50 an hour; a separate line with price on application), plus £1,500 + VAT reviews. No published software price. I would call it a 13, not 14.
- Item 3 (Pain to 16): not met. No job advert, no CIPP workload figure, and no government response. Pain evidence from CIPP is qualitative. The six-year window is under challenge.
- Items 4 and 5 are not touched by this pass. Armstrong Watson's data-gap point suggests Build and AI scoring should assume joining HR leave data, so Build may fall rather than rise.
- Net: a re-score now would not reach 70. Worth re-checking when the government response is published and the FWA calculator scope is known; those two events decide whether urgency is real and whether the gap survives.

## Evidence re-check (2026-11-25)

Scout, Always-On item 6, run 20261125T001943Z-run-cf06. Score not changed by the scout.

| URL | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/consultations/make-work-pay-holiday-pay-compliance-and-enforcement | 2026-11-25 | Still "Closed consultation", "We are analysing your feedback", "Visit this page again soon to download the outcome". No response and no commencement date. |
| https://www.gov.uk/government/publications/fair-work-agency-delivery-plan-for-2026-to-2027/fair-work-agency-delivery-plan-2026-to-2027 | 2026-11-25 | Still "Updated 21 August 2026". Lists "a holiday pay calculator" among simpler tools, no launch date, no scope. "Holiday pay enforcement is expected to begin in 2027"; "processes in place to begin enforcement during 2027". (Fetch-tool quotes; unchanged from 2026-11-23.) |
| Web search "Fair Work Agency holiday pay calculator launched" and "holiday pay consultation government response November 2026" | 2026-11-25 | No UK FWA calculator found (only Australian Fair Work Ombudsman tools and the one-worker gov.uk entitlement calculator). No government response surfaced. Search is indexed content only. |
| https://www.fairworksolutions.co.uk/ | 2026-11-25 | Still NMW only: upload, pay codes, shortfalls per worker and pay period, monitoring. No holiday pay look-back. Nothing marked as new. |
| https://iris.co.uk/blog/payroll/staffology-payroll-summer-2026-software-update/ | 2026-11-25 | Search summary only, page not read: Staffology summer 2026 update adds daily-basis average holiday pay and import of history of previously paid amounts. Forward averaging input, not an arrears or look-back report. Undated in the summary. Worth reading for item 6. |
| Web search for BrightPay, Xero, Sage, Moneysoft holiday pay audit or look-back launches | 2026-11-25 | None of the four appeared. No look-back or audit feature found. |
| https://www.cipp.org.uk/resources/news.html | 2026-11-25 | No holiday pay or FWA item visible; most items undated. |

Bottom line: nothing new since 2026-11-24. The government response is still unpublished, there is no commencement date beyond "2027", and no FWA holiday pay calculator or scope has appeared, so the evidence that would move Competition (to 8-9 or to 2) has not arrived. No vendor in the named set has launched a look-back or audit feature; the only movement is Staffology's summer 2026 update, which adds history import and daily-basis averaging (forward calculation, read from a search summary only). The park decision stands, T-24 and T-25 stay blocked, and nothing justifies a re-score. Next re-check on publication of the response or the FWA calculator, otherwise monthly.

## Re-check 2026-11-26

Scout, about 8 searches and fetches, all accessed 2026-11-26. Score not changed. Verdict: **UNCHANGED**, park conditions all still open.

| Park condition | Finding | Source |
|---|---|---|
| (a) Government response | Not published. Page still reads "Closed consultation" and "We are analysing your feedback ... Visit this page again soon to download the outcome". No "last updated" date shown. | https://www.gov.uk/government/consultations/make-work-pay-holiday-pay-compliance-and-enforcement (fetched) |
| (b) Enforcement date | No fixed date. Delivery plan still "Updated 21 August 2026": "Holiday pay enforcement is expected to begin in 2027". Fetch summary also says the plan targets April 2027 for new powers (fetch-tool paraphrase, not read verbatim; an earlier pass could not find April 2027 in the primary text). Search summaries (law firms, Brightmine legal timetable) say the FWA intends April 2027, exact date unknown, three-year enforcement strategy due April 2027. | https://www.gov.uk/government/publications/fair-work-agency-delivery-plan-for-2026-to-2027/fair-work-agency-delivery-plan-2026-to-2027 (fetched); https://hrcentre.uk.brightmine.com/legal-timetable/fair-work-agency-begins-statutory-holiday-pay-enforcement/168132/ (search summary) |
| (c) FWA calculator scope | Still no launch and no scope. Plan lists "a holiday pay calculator" among simpler tools, with no date. Consultation asked about a detailed calculator or chatbot. Searches found only Australian Fair Work Ombudsman tools and the one-worker gov.uk pages. | delivery plan above; https://www.gov.uk/holiday-entitlement-rights/holiday-pay (search result only) |

New incumbent claims: none found. A search for BrightPay, Xero, Sage or Moneysoft holiday pay look-back or audit launches in November 2026 returned none of the four. Their own pages were not re-read because there was no hint of change. Peripheral items only, none a look-back: Staffology summer 2026 update (daily-basis average holiday pay; https://iris.co.uk/blog/payroll/staffology-payroll-summer-2026-software-update/, search summary); KashFlow (IRIS) holiday pay module, release year unconfirmed (https://www.iris.co.uk/blog/payroll/holiday-pay-solution-with-kashflow-payroll/, search summary); HotSchedules (US) "Holiday Record Keeping Audit", in development, a workforce tool and not UK payroll (https://help.hotschedules.com/hc/en-us/articles/48475729597197-New-Release-WFM-UK-Holiday-Carry-Over-Reason-Codes-03-Sep-2026, search summary).

Bottom line: nothing published since 2026-11-20 moves any of the three conditions. Competition stays 7, total 64, parked. Next re-check on publication of the response or the FWA calculator, otherwise monthly.

## Evidence log 2026-11-26 (T-148, validator)

**Kill test (item 6): add PayslipIQ for Business.** It is a trading name of GoldPaid Ltd (England and Wales, company no. 17382540). The validator fetched all four pages on 2026-11-26.
- https://payslipiq.co.uk/business: "Not available yet", "nothing is for sale here", checks marked "Planned". The list names "holiday-pay miscalculations" with no method. The page has no 52-week, reference period, look-back, historic pay run or arrears wording. The checks run on each pay run "before anyone is paid", so they are forward checks.
- https://payslipiq.co.uk/business/bureau: a waitlist by email. Coverage is PAYE, NI, pension, student loan, salary sacrifice, Irish PAYE/USC/PRSI and umbrella rate checks. No holiday pay or SSP.
- https://payslipiq.co.uk/pricing: Free check £0 "Available now"; Pro Report £19 one-off "Not on sale yet"; the employer and bureau offer is "Planned, not live" with no price.
- https://payslipiq.co.uk/: a free consumer payslip checker, "educational guidance only". No holiday pay.

**Kill rule:** if PayslipIQ ships a whole-payroll holiday-pay look-back that lists past underpayments, Competition falls to 2.

**Effect on the score: none. Competition stays 7, total 64.** It is an unlaunched waitlist with no method, no price and no date. Its only holiday-pay wording is one generic bullet, and its design is a pre-pay-run check, not a look-back. It is already covered by the T-57 reasons for 7 rather than 8 (a payroll-upload checker could add holiday pay, like Fair Work Solutions). It adds a second name to that risk, not new evidence that the gap has closed.

**Part A gate re-check (scout T-148, accepted):** the consultation outcome is unpublished, the FWA calculator is planned with no scope, and there is no fixed enforcement date. All park conditions are still open.

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted. Job-ad signal missing, flagged.
- 2026-11-23 | validator | G0→G1 | REVISE 63 | Best of round 3, and the first idea with an incumbent gap confirmed on the vendors' own pages: BrightPay, Xero, Moneysoft and Sage 50 don't calculate holiday pay amounts, and no product documents a whole-workforce look-back. But FWA enforcement has no start date, the FWA is building its own free holiday pay calculator, and its look-back starts only at 18 Dec 2025. The core is a deterministic engine, and holding workers' pay and absence data cuts Risk to 5.
- 2026-11-24 | validator (T-42 note, no re-score) | New competitor for the kill test: Fair Work Solutions Limited (https://www.fairworksolutions.co.uk/, fetched 2026-11-24) sells a UK NMW compliance platform that takes payroll uploads, handles pay codes and deductions, and calculates underpayments per worker and pay period with continuous monitoring. Holiday pay is not mentioned on the page. Add it to item 6: if it adds holiday pay look-back, Competition falls to 2. The sibling nmw-salaried-hours-audit was killed (55).

### Re-score 2026-11-24 (T-57, Q-10 wedge rule)
Validator. Only the Competition row is re-scored, under the wedge rule in `playbooks/pipeline.md`. This is not a new G1 attempt.
- **Competition: 6 → 7.** This is the only idea in the batch with a named, evidenced wedge. Two of the rule's wedge types apply: UK rules the incumbent doesn't handle, and a segment it ignores.
  - *Named wedge:* a holiday pay engine and look-back for payroll bureaux and accountants running BrightPay, Xero, Moneysoft or Sage 50. It covers 52-week averaging, 12.07% accrual for leave years from 1 April 2024, rolled-up pay checks, and a look-back to 18 December 2025 (the FWA window) plus two years (the tribunal window).
  - *Evidence:* BrightPay's own docs say "The holiday pay amount ... is not automatically calculated by BrightPay and thus must be entered manually" (fetched 2026-11-23). On 27 November 2025 a Xero admin said a 52-week report "is not a feature we have planned in our roadmap" (fetched, 94 votes). Moneysoft and Sage 50 have no automatic calculation (search summaries only). T-23 found no product, out of 8 checked, that documents a whole-workforce look-back. The incumbent "price" is human work billed as an extra: DCK £73.50 an hour, a PSSG list line priced on application, and Irwin Mitchell £1,500 + VAT a review.
  - *Why 7 and not 8 to 10:*
    - Two of the four "doesn't calculate" findings rest on search summaries.
    - Forward-only calculation already exists in Staffology, IRIS and Employment Hero (free plan), so a bureau can switch package instead.
    - The FWA's planned free holiday pay calculator has no stated scope.
    - Fair Work Solutions already runs payroll-upload underpayment checks for NMW and could add holiday pay.
    - Absence of a look-back is "not documented", not "confirmed absent".
  - *Fresh check:* the gov.uk consultation page still says "We are analysing your feedback", with no outcome published (fetched 2026-11-24, https://www.gov.uk/government/consultations/make-work-pay-holiday-pay-compliance-and-enforcement). A search for a launched UK FWA holiday pay calculator found none (2026-11-24).
- **Knock-on:** none justified. Pay stays 12, because a software price is still missing. Pain stays 15 (no response and no job ads). Risk stays 5, because the pseudonymised design is not signed off by security. AI 7 and Build 11 wait for the benchmark, and the Armstrong Watson data-gap point argues against raising Build.
- **New total: 64** (15+12+7+7+11+7+5). **Verdict: REVISE (parked).** No red flag. In the 63 to 69 band, so the proof-test route is open, but a benchmark alone moves at most AI +1 and Build +1, to 66.
- **The one piece of evidence that would move it:** the FWA calculator's published scope (or the government response), confirming it works one worker at a time and doesn't take a whole payroll. That would take Competition to 8 to 9. If it does take a whole payroll, Competition falls to 2.

## Demand test (pre-registered, T-153)

Written 2026-11-26, before any G2 work. Applies only if Q-17 is answered A. **No contact happens now.** Nothing below may be changed after the test starts; changes need a new dated section and reset the test.

**Who is asked.** Up to 5 UK payroll bureaux, accountants running payroll, or in-house payroll leads at firms of 20 to 500 staff with irregular-hours or variable-pay workers: Vishal's friend's business, plus firms it introduces. At least 3 must be interviewed. Asked: the person who runs or signs off payroll.

**First allowed contact.** A demo of the synthetic-data MVP to the friend's business or the firms it introduces, only after Vishal explicitly allows contact (a friend demo or `unlock selling`). No outreach, pricing offer or commitment before that. The 60-day clock starts at the first demo, not before.

**Exact questions (asked in this order, answers written down verbatim by the studio, never paraphrased into a pass).**
1. How do you calculate holiday pay for irregular-hours or variable-pay workers today? (Options read only after the open answer: payroll software automatically; spreadsheet; by hand; outsourced; not done.)
2. When did you last re-check holiday pay for past pay runs, and how many hours did it take?
3. Do you charge clients, or pay anyone, for holiday pay calculations? How much?
4. (Before any price is shown) What would you pay per month for a tool that does this look-back with the working shown? A number, ex VAT.
5. At what monthly price would it be too expensive to consider?
6. Would you run it on your own pseudonymised export within 14 days? Who would sign off the results?
7. What would stop you using it?

**Pass mark (all must hold).**
- At least 3 firms interviewed, and at least 3 of those (and over half of those interviewed) say in answer 1 that they calculate holiday pay manually or in a spreadsheet today; AND
- those same 3 firms each name a monthly price of at least £49 ex VAT in answer 4, unprompted, before seeing any price from us; AND
- at least 2 of those 3 say yes to answer 6 and name a sign-off person.

Answers are scored from the written record only. "Interesting", "send me more" and hypothetical praise count as nothing.

**What counts as a fail (a failed gate attempt; with the earlier REVISE, the idea is killed).**
- Fewer than 3 firms meet any of the three pass lines above.
- Fewer than 3 firms interviewed within 60 days of the first demo (no demand shown, not extended).
- Median unprompted price below £49 ex VAT, or most answers to question 1 say software already does it automatically.
- Any kill trigger meanwhile: the FWA calculator takes a whole payroll, or Fair Work Solutions, PayslipIQ, BrightPay, Xero or IRIS ships a look-back.
If Vishal does not allow contact, the test does not start, the idea stays parked, and the clock does not run.

**On a pass:** record the quoted prices and hours, give the Pain, Pay and Reach contact-only points (up to +2 each) to the validator, who re-scores. The 70 bar still applies before G4.

### Amendment 2026-11-26, before any contact, per T-153 validator review
Where this conflicts with the text above, the amendment wins.
1. **Friend counts once.** The friend's own business counts as at most 1 of the 3 firms meeting any pass line. At least 2 must be other firms, none of them the friend's own payroll clients or suppliers.
2. **Recording.** The interviewer reads Q1 to Q7 word for word, in order, adding no product description beyond the demo. Notes are written during the call or within 24 hours and sent to the studio unedited. Every interview held counts; none may be dropped or repeated. The firms counted are the first 5 interviewed. Firms are recorded by type and size, not by person.
3. **"Unprompted" defined.** The first number given in answer to Q4, before Q5, when no price, range, plan name, discount or anchor (including DCK £73.50, Irwin Mitchell £1,500 or the SPEC's tiers) has been said, shown or put in any document the firm has seen. A range scores its lower end. A yearly or one-off figure is divided by 12 to give a monthly one. "It depends", "no idea" or no number scores £0. The demo build shows no price, plan or checkout page.
4. **Q4 reworded:** "Would you pay for a tool that does this look-back with the working shown? If yes, roughly how much, and per month, per year or per audit? If no, why not?" A "no" scores £0.
5. **Past-behaviour pass line (added):** at least 2 of the 3 qualifying firms give a concrete past fact in Q2 or Q3: a date or period when they last re-checked holiday pay with an hours figure, or an amount they charge or pay for holiday pay work.
6. **Q6** asks them to name the sign-off role (for example payroll manager or external adviser), not a person.
7. **Fail line fixed:** replace "Fewer than 3 firms meet any of the three pass lines above" with "Any one pass line is not met by enough firms." The pass lines are now four: manual or spreadsheet calculation (Q1), unprompted price of at least £49 a month (Q4), past behaviour (Q2 or Q3), and Q6 yes with a sign-off role.
8. **Contact-only points, all or nothing per row.** Pain +2 if at least 2 qualifying firms report a concrete hours figure (median recorded). Pay +2 if the qualifying firms' median unprompted price is at least £49 a month. Reach +2 if the friend's business introduced at least 2 of the qualifying firms, or one bureau named a channel that reaches several employers.
2026-11-26 | validator (T-113) | G1 proof test | KILL (second failure) | B1 92.5% nine-category (8-cat 93.5%, ambiguous 71.9%) < 95% pre-registered; one clean live run, $0.0059; rescues ruled out by DECISIONS run 84ae. See products/holiday-pay-payroll-lookback-audit/reviews/T-113-validator.md (results on branch p/holiday-pay-payroll-lookback-audit/T-113, e23609b).

## Killed 2026-11-26 (T-113)
Reason: pre-registered AI mapping mark missed in one clean run (92.5% vs 95%; ambiguous names 71.9%, where the value lies). Second failed G1 attempt after the 2026-11-23 REVISE. Lessons: give ambiguous rows their own pre-registered threshold; pre-register consequence-weighted scoring with a strict harmful-direction line; don't spend a gate attempt on a test whose pass can't reach 70. Revive only as a new idea (government response + FWA scope, passed demand test, honest deterministic-engine framing or a fresh held-out mapping test). Keep the Part A engine (main e888e54); archive the product folder, do not extend it.
