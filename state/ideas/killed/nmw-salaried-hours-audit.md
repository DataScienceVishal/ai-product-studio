# NMW unpaid-time and salaried-hours audit

- slug: nmw-salaried-hours-audit
- stage: killed (T-42 validator, 2026-11-24, 55)
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
Validator score, 2026-11-24 (T-42):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 14 | 10 | 6 | 6 | 11 | 3 | 5 | 55 |

**Verdict: KILL (first attempt; ceiling below 70). Do not merge into the holiday-pay idea as a scored module; carry over the competitor finding below.**

**Falsification findings** (all accessed 2026-11-24; "fetched" means the page itself was read)
- **The naming round holds on gov.uk** (fetched): 3 September 2026, "around 660 employers" (658 in the spreadsheet), about £4m repaid to over 27,000 workers, £7m in penalties. HMRC "enforces the minimum wage on behalf of the Fair Work Agency", so the FWA already owns NMW policy; the scout's "from April 2027" handover is not what the page says. The page gives no causes.
- **A dedicated UK NMW SaaS already sells the pitch.** Fair Work Solutions Limited (Ruislip) calls itself the UK's "first dedicated National Minimum Wage compliance" platform. Its site says you upload payroll data; it handles worker categories, pay codes and deductions; dashboards flag at-risk workers and pay periods; it "calculates underpayments by worker and pay period, in the format HMRC requires"; it tracks remediation with audit trails and offers continuous monitoring. No price; contact by email (https://www.fairworksolutions.co.uk/, fetched; launch release via a LinkedIn repost, search summary). Not documented: how it treats salaried hours and unpaid time. That is the scout's only remaining wedge, and it is the kind of rule a live competitor adds in a sprint.
- **Advisers sell the human version, which proves pain and some Pay.**
  - CIPP's consultancy ran an NMW risk audit for a 1,300-staff hospitality employer: "unpaid uniform requirements, workwear deductions, time rounding practices, and historical underpayments", about £120,000 of arrears, repaid without an HMRC investigation. No fee shown (https://www.cipp.org.uk/best-practice/consultancy/case-studies/case-study-nmw-risk-audit.html, fetched). CIPP also lists an "NMW Health Check" (search summary).
  - Muckle's HR audit prices NMW as one area at £500 + VAT (1 to 19 staff), £750 (20 to 99), £1,125 (100 to 249), £1,500 (250+) (search summary of the PDF the scout cited).
  - BDO ("a methodology that replicates an HMRC NMW enquiry"), Mishcon de Reya, Addleshaw Goddard, Azets, RSM, Grant Thornton and PKF all market NMW reviews (search results).
- **Payroll and rota tools cover the forward check.** BrightPay "applies the correct NMW rate for each employee's age band" for every bureau client, and says bureaux should build the effective-rate-after-deductions review into the run (https://brightsg.com/blog/fair-work-agency-brightpay-nmw-compliance-payroll-bureaus/, fetched, 26 May 2026). RosterElf checks NMW and age tiers while the rota is built; Deputy markets rota-stage NMW flags; Dayforce shows the earnings, deductions and hours behind each NMW calculation (search summaries).
- **Free substitute from HMRC:** the "Carrying out a self-review of the National Living Wage and the National Minimum Wage (NMW FS2)" guide on gov.uk (search result).
- **Off-limits check: not legal advice as scoped.** It is a calculation and evidence tool with a payroll professional's sign-off, the same guardrails as the holiday-pay file.
- **Overlap with holiday-pay-payroll-lookback-audit:** same buyer, same exports, same personal-data problem, same pay-element mapper. Merging would not raise either score: the NMW half brings a named competitor (Fair Work Solutions) into the holiday-pay idea's space rather than a gap.

**Scores in brief**
- Pain 14: official naming, £7m in penalties in one round, penalties of 200% of arrears, and a paid advisory market with a real case (£120k of arrears found). Not higher: arrears average about £148 per worker, and the page gives no cause split.
- Pay 10: published adviser fees (£500 to £1,500 + VAT per area at Muckle) and many firms selling reviews. No software price; Fair Work Solutions hides its price.
- AI 6: the core is deterministic arithmetic on structured payroll data; AI maps pay-element names and flags ambiguous working time. A rival can build it without AI, and Fair Work Solutions already handles pay codes.
- Reach 6: bureaux, care and hospitality associations, CIPP; the partner's channel is unknown.
- Build 11: four weeks is realistic for the rules in the file on synthetic data.
- Competition 3: a dedicated NMW SaaS with HMRC-format shortfall reports, payroll and rota checks, and a crowded adviser market.
- Risk 5: pay and hours for whole workforces, including under-18s and apprentices (−3), and liability if arrears are understated (−2).

**Reason (one paragraph).** The pain is the best evidenced of the round, but the product is already on sale: Fair Work Solutions uploads payroll data, handles pay codes and deductions, and calculates underpayments per worker and pay period in HMRC's format, with continuous monitoring. Around it sit payroll and rota NMW checks (BrightPay, RosterElf, Deputy, Dayforce), HMRC's free self-review guide and a large adviser market (CIPP, BDO, Muckle, Mishcon, Azets, RSM). The remaining wedge, salaried hours and unpaid time, is a set of deterministic rules a live competitor can add in a sprint, so AI stays low and the studio would hold the same high-risk payroll data as the holiday-pay idea. Best plausible re-score: Pain 15, Pay 12, AI 7, Reach 6, Build 11, Competition 4, Risk 5 = 60.

**Lessons**
- A brand-new regulator (the FWA) attracts single-purpose start-ups named after it within months. Search the regulator's name plus "software", "platform" and "solutions", and check Companies House for recent incorporations.
- Pay-compliance audits from payroll exports are now a contested category. Before reviving the holiday-pay idea, check whether Fair Work Solutions or a similar platform adds holiday pay.
- An adviser market with published fees proves Pay for a service, not for software at a software price.

**What would revive it**
- Evidence (on Fair Work Solutions' own pages or a public demo) that it does not handle salaried-hours averaging, unpaid pre-shift time or sleep-ins, plus a published software price of at least £100 a month for NMW monitoring, plus a bureau channel the partner can reach. Even then the ceiling is about 60.

## Gate log
- 2026-11-24 T-42 scout round 7: written as G0. The gov.uk Round 24 release was fetched; payroll vendor claims come from search summaries and BrightPay/Staffology page extracts.
- 2026-11-24 | validator | G0→G1 | KILL 55 | Fair Work Solutions already sells a UK NMW compliance platform: payroll upload, pay codes and deductions, underpayments per worker and pay period in HMRC's format, continuous monitoring. Payroll and rota checks, HMRC's free self-review guide and a large adviser market surround it; the salaried and unpaid-time wedge is deterministic rules. Ceiling about 60. Competitor note added to holiday-pay-payroll-lookback-audit.
