# NMW unpaid-time and salaried-hours audit

- slug: nmw-salaried-hours-audit
- stage: G0
- market and segment: UK employers with low-wage and rota-based staff (care providers, nurseries, hospitality, retail, cleaning), 20 to 300 employees, who run payroll in-house or via a small bureau
- one-line pitch: Re-tests each worker's pay against the National Minimum Wage from payroll and rota exports, including the cases payroll warnings miss (salaried staff with long hours, unpaid pre-shift and training time, deductions and uniform costs, wrong age or apprentice band), and lists the exceptions with the working shown for a payroll professional to sign off.

## Problem and who has it
HMRC and now the Fair Work Agency (FWA) publish NMW naming rounds. Round 24 (3 Sep 2026) named 658 employers, with about £4m arrears to over 27,000 workers and £7m in penalties. Penalties can reach 200% of arrears. Payroll software checks hourly pay against hours it is given, but for salaried staff it needs the hours supplied; the checks miss unpaid time, deductions and mis-set bands. From April 2027 the FWA takes over NMW enforcement with about 500 staff from HMRC (single source: Employment Hero search summary; verify on GOV.UK).

Who pays: owner or finance lead at a care, nursery or hospitality employer; bureaux serving them.

Overlap: sibling to holiday-pay-payroll-lookback-audit (same buyer, same exports). The validator may prefer to merge them as one "pay-compliance audit" product.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/news/short-changing-staff-isnt-a-shortcut-to-success-nearly-660-employers-announced-as-failing-to-pay-the-minimum-wage | 2026-11-24 | 3 Sep 2026: about 660 employers named (spreadsheet has 658); about £4m to over 27,000 workers; £7m penalties. Page gives no causes or sector split |
| https://assets.publishing.service.gov.uk/media/690b1479c22e4ed8b05184a6/national-minimum-wage-enforcement-and-compliance-report-2024-2025.pdf (search result, not read) | 2026-11-24 | Official enforcement report; read for cause breakdown at G1 |
| https://www.cipp.org.uk/resources/news/nmw-naming-and-shaming-list-sep-26.html (search result) | 2026-11-24 | Payroll body's note on the Sep 2026 list |
| https://www.lewissilkin.com/insights/2026/03/19/the-fair-work-agency-launches-in-april-2026-are-you-nmw-compliant | 2026-11-24 | FWA launched April 2026 (search result) |
| https://www.brightpay.co.uk/docs/24-25/national-minimum-living-wage/minimum-wage-flagging-and-reporting/ | 2026-11-24 | BrightPay flags hourly rates below NMW; for salaried staff it needs hours entered |
| https://help.staffology.co.uk/payroll/payroll-guides/other/nmw.htm | 2026-11-24 | Staffology check compares average hourly pay to hours in the period; warns wrong working patterns give false warnings and employers must verify independently |
| https://www.forvismazars.com/uk/en/insights/corporate-tax-insights/how-to-be-compliant-when-paying-salaried-workers | 2026-11-24 | Advisers: salary divided by contracted hours is not sufficient for salaried workers |

Estimates (method): average penalty per named employer about £7m / 658 = £10.6k; average arrears per worker about £4m / 27,000 = £148. Both are crude averages of the headline figures.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Payroll NMW flags (BrightPay, Staffology, Dayforce, Employment Hero) | Included in payroll | Per pay-run warning; relies on hours and working-pattern inputs; no look-back; no unpaid time, deduction or accommodation-offset reasoning (checked on BrightPay and Staffology pages only) |
| HMRC / ACAS calculators | Free | One worker at a time |
| Accountancy or HR consultant NMW review | No public price found | Manual, one-off |
| Rota tools (Planday, Deputy, Workforce) | Not checked | Compliance features unverified; a risk to the idea |

## Competitor search done (2026-11-24)
Queries: "national minimum wage underpayment audit software hospitality rota payroll HMRC named employers 2026"; "minimum wage compliance checker tool payroll salaried hours unpaid working time deductions uniform audit employers software" (returned mostly US results); "BrightPay OR Xero Payroll OR Sage Payroll national minimum wage check ... UK payroll software feature". No UK look-back audit product found. Not checked: Sage and Xero payroll help pages, rota vendors, Moorepay and other bureaux services.

## Evidence the studio can collect itself
- The Round 24 spreadsheet and earlier rounds on gov.uk (company-level, OGL): sector mix and underpayment sizes. Build a table of named employers by sector and band.
- HMRC's published causes in the enforcement report and educational bulletins (https://assets.publishing.service.gov.uk/media/6a98544a5a0c25165ae46815/Educational_Bulletin_R24.docx, search result).
- Gov.uk rules on salaried, unmeasured, deductions and accommodation: the rule set to encode.

## Demo plan on public or synthetic data
Generate a synthetic payroll and rota for a 60-person care provider and a restaurant group (seeded with 12 defect types: 12-hour salaried shifts, unpaid handover, uniform deduction, age-band rollover on a 21st birthday, apprentice rate after year one, sleep-in shifts). The tool returns exceptions with the calculation and the gov.uk rule. Measure recall of seeded defects. Fully demoable with no paid service.

## Why AI is essential (and the moat)
The deterministic NMW arithmetic is easy; the hard part is turning messy rota notes, contracts and pay-element names into the right classification (is this a deduction, a training period, working time). An LLM maps pay elements and flags ambiguous cases, with the arithmetic done in code. Weak moat: payroll vendors could add it; the validator will likely mark AI around 8 to 10.

## Rough build plan and Azure cost
CSV importers for common payroll and rota exports, pay-element mapper, rules engine with rule citations, exceptions report. Azure about £20 to £60 a month; estimate.

## Risks, and what would prove this wrong
- Pay: no public price for an NMW audit; a payroll bureau might give it away.
- Personal data: payroll is personal data; scope as bureau-hosted or client-side processing and keep demos synthetic.
- Overlap with the parked holiday-pay idea; both depend on payroll export access.
- Wrong if payroll vendors' own NMW warnings already cover salaried and unpaid-time cases.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-24 T-42 scout round 7: written as G0. The gov.uk Round 24 release was fetched; payroll vendor claims come from search summaries and BrightPay/Staffology page extracts.
