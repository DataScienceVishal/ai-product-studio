# UK CBAM import ledger and return-ready data pack

- slug: uk-cbam-import-ledger
- stage: G0
- market and segment: UK importers of iron and steel, aluminium, fertiliser, cement and hydrogen goods that will cross the £50,000 threshold (steel and aluminium stockholders, fabricators, fertiliser distributors, builders' merchants), and the customs agents that act for them.
- one-line pitch: Tracks every CBAM-scope import from 1 January 2027, runs the £50,000 registration tests, holds the supplier emissions and verification evidence, and assembles the return data for the 2028 filing, with a human sign-off.
- forcing function: UK CBAM applies to goods imported on or after **1 January 2027**. Registration opens 1 January 2028; the registration deadline for 2027 liability is 31 January 2028; the first return and payment (period 1 Jan to 31 Dec 2027) are due **31 May 2028**; quarterly periods start in 2028. Source: https://www.gov.uk/government/publications/carbon-border-adjustment-mechanism-cbam-policy-summary/carbon-border-adjustment-mechanism-cbam-policy-summary (accessed 2026-11-23). Registration threshold: £50,000 of CBAM goods, tested forward (next 30 days) and backward (12 months, checked on the first day of each month). Same page. Regulator: HMRC. Draft secondary legislation consultation ran 10 Feb to 24 Mar 2026: https://www.gov.uk/government/consultations/draft-legislation-carbon-border-adjustment-mechanism/draft-tax-information-and-impact-note (2026-11-23).

## Problem and who has it

From the first import in January 2027 the importer needs, per good: 8-digit commodity code, net weight in kg, emissions intensity (HMRC default value or verified actual data), any carbon price paid abroad in GBP, country of origin under non-preferential rules, and the tax-point quarter. Actual data must be verified by an accredited verifier (ISO/IEC 17029 and ISO 14065, materiality 5%) and the importer must hold the report. Precursor rules block mixing actual and default data. Small importers have no simplified regime beyond the threshold. The 2027 records have to be kept from day one although registration only opens in 2028. Source: gov.uk policy summary above.

The pain is therefore a record-keeping and supplier-data problem that starts in January 2027. It is not a filing problem yet.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/publications/carbon-border-adjustment-mechanism-cbam-policy-summary/carbon-border-adjustment-mechanism-cbam-policy-summary | 2026-11-23 | All dates, data fields, verification rules, penalties (failure to notify, return, pay, errors, information notices), no small-importer simplification. Pain signal 1: the obligation and data list are heavy and start before registration opens. |
| https://greencalculus.com/calculators/uk-cbam-calculator/ | 2026-11-23 | Competitor page itself says: estimate only, not an HMRC filing figure, does not check the £50,000 threshold, no returns, and advises importers "to keep their own records of every CBAM import from 1 January 2027". Pain signal 2: even the tool vendors point to a record-keeping gap. |
| https://www.fastmarkets.com/insights/fastmarkets-launches-uk-cbam-calculator-to-help-importers-estimate-carbon-costs-ahead-of-january-2027/ | 2026-11-23 | Market data vendor sells a UK CBAM cost calculator (HMRC default values published 16 Oct 2026). Page does not say it produces returns or records, and does not describe supplier data collection. Pain signal 3: paid demand for exposure estimates exists. |
| https://dcycle.io/post/cbam-software-united-kingdom | 2026-11-23 | Vendor states it "does not file UK returns" and does not itself perform a CBAM calculation; UK-specific calculations to be confirmed in a pilot. |
| https://kpmg.com/uk/en/insights/tax/tmd-the-clock-is-ticking-for-importers-cbam-comes-into-force-in-10-months.html | 2026-11-23 | Adviser alert aimed at importers (appeared in search results; page not opened). |
| Number of importers in scope | not established | A search snippet attributed to the HMRC draft tax information and impact note says over four-fifths of otherwise affected importers fall below the threshold. The fetched page did not show this figure, so treat it as unverified. Market size is a major open question. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Green Calculus UK CBAM calculator | Calculator price not stated; API free tier of 1,000 calls a month (own page, 2026-11-23) | Estimate only; no threshold test; no returns; JSON/CSV export and audit trail only. |
| Fastmarkets UK CBAM calculator | "Get in touch"; no price (own page, 2026-11-23) | Cost forecasting for exposure; no records or return pack described. |
| Dcycle (environmental data platform) | "Start for free" or demo; no price (own page, 2026-11-23) | Collects supplier data; does not file, does not itself calculate CBAM. |
| SAP with PwC Carbon Border Manager | €990 a month Standard Edition, 3-year minimum (https://www.sap.com/greece/products/scm/partners/pwc-solutions-gmbh-carbon-border-manager-check-your-value-chains-cbam-module.html, search summary; not clear it covers UK CBAM) | Enterprise priced and tied to SAP. |
| Adviser or customs-agent time | not found | Not priced in any source I found. |

Gap that survives (on these pages): the rolling £50,000 threshold test, a per-import ledger tied to supplier verification documents, and a return-ready data pack are not described on any of the pages above. This is a narrow, checkable gap, but a customs-software vendor or one of these tools could add it. I did not check the major customs software vendors (for example CDS-integrated systems) or CBAMDesk (its Capterra page returned 403).

## Why AI is essential (and the moat)

Honest view: the core is deterministic (threshold maths, default value lookups, ledger). AI is useful at the edges: reading commercial invoices and mill certificates to match goods to 8-digit codes and weights, matching supplier verification reports to import lines, and chasing missing evidence. The moat would be the rules engine kept current with HMRC's published values and the verifier-document matching. Moderate AI advantage only. The validator should score AI low to medium.

Demo with public data: HMRC default values and the commodity code annex are public. Build synthetic importer data (40 invoices of steel and aluminium goods from synthetic suppliers across several countries) and show the rolling threshold flipping, default versus actual intensity cost, and a missing-verification flag.

## Rough build plan and Azure cost

- Weeks 1 to 2: commodity code annex loader, ledger, threshold tests, default value tables.
- Week 3: invoice and certificate extraction, supplier evidence tracker.
- Week 4: return data pack export (CSV and PDF), audit log, record retention.
- Azure: same default stack, estimate under $20 a month. Not yet in BUDGET.md.
- No HMRC filing integration is assumed. Registration and return filing open in 2028 and no API is described on the pages read.

## Risks, and what would prove this wrong

- Market may be small if most importers fall under £50,000. Size it from HMRC trade statistics by commodity code (not done).
- Tax advice risk: the product produces data and estimates. Human sign-off and tax-adviser review needed. Legal review needed on wording. Do not describe outputs as an HMRC liability.
- Rules are still moving (draft legislation; rates are "illustrative"). Green Calculus notes default values come from a draft notice.
- Customs agents could be the real buyers. They are the channel, and may also build it.
- Would prove wrong: five importers in the segment say their agent or ERP will handle it; or the first HMRC guidance in 2027 introduces a simple spreadsheet return.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 11 | 13 | 6 | 6 | 11 | 2 | 7 | 56 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area, but CBAM is a tax, so this idea sits nearer to tax advice than the other four (see sign-off below).
- No paid service or scraping is needed. HMRC's default values, the in-scope code list and the guidance are free on gov.uk.
- Public and synthetic data can credibly demo the value. The demo uses HMRC's default values (published 16 Oct 2026), the in-scope commodity codes, and synthetic invoices and mill certificates. It shows the rolling threshold tests, default versus actual emissions cost, and missing-verification flags.
- Sign-off design to keep it a data tool:
  - Every figure shows its inputs, the rule version and the gov.uk source, and is labelled "estimate for your review".
  - The tool never says "you must register" and never states a liability.
  - The importer, with its adviser, signs off. The tool files nothing.
  - A tax adviser reviews the wording before G4.
  - CBAMable positions itself the same way: it "does not provide legal or tax advice" (search summary).

**Forcing function: confirmed on gov.uk**
- Policy summary (updated 2 Nov 2026):
  - CBAM starts 1 Jan 2027 and registration opens 1 Jan 2028.
  - The deadline to register for 2027 liability is 31 Jan 2028.
  - The first period is 1 Jan to 31 Dec 2027, with the return and payment due 31 May 2028. Periods are quarterly from 2028.
  - The £50,000 threshold is tested forward over 30 days and backward over 12 months on the first day of each month.
  - Records are kept for 6 years. Verifiers must be accredited, with 5% materiality.
- Record-keeping guidance (published 16 July 2026, updated 3 Nov 2026):
  - Required records: 8-digit code and description, tax-point date, value, net weight and exemption evidence. Where relevant, also the quarter, proof of origin and the verification report.
  - HMRC gives no template. Records can come from import declarations and commercial documents, so the importer's customs data already holds most of the ledger.
- HMRC's 16 Oct 2026 package (KPMG, fetched): default values for all five sectors, illustrative rates with a worked example, and a 313-page monitoring, reporting and verification guide. No threshold checker or record template.

**Market size (open item)**
- HMRC's impact note (updated 9 Sep 2026, fetched): CBAM will have "a significant impact on an estimated 10,000 businesses importing CBAM goods". "Over 80% of otherwise affected importers will be excluded from CBAM altogether", and over 70% of those excluded are SMEs.
- Costs and revenue in the same note: £9m one-off and £16m a year in continuing admin costs to business. Revenue is £140m in 2027-28 and £180m in 2028-29.
- The note doesn't say whether 10,000 is before or after the threshold:
  - If before, fewer than about 2,000 importers are liable (my arithmetic).
  - Either way, HMRC's admin cost works out at roughly £1,600 to £8,000 per liable business a year (£16m divided by 10,000 or by 2,000; my arithmetic). That caps what a tool can charge.

**Falsification findings**
- UK-ready software already exists, with published prices:
  - Dubrink (own pricing page): importer Starter €1,990 a year (1 entity, up to 1,000 tonnes, 10 suppliers), Premium €2,990, and a free Connect tier when suppliers pay. It has a UK CBAM page, though its features there are generic.
  - CBAMable (own page): built for customs brokers. £229 a month for 1 client space, £499 for 5, £999 unlimited, and it lists "UK CBAM readiness preparation (from Jan 2027)". New-customer prices rise in December 2026. Brokers can white-label it (FBJ, July 2026, search summary).
  - CarbonChain scopes goods by code, holds emissions data and supports returns (cbamguide.com directory, fetched; its own page not checked).
  - CBAMDesk (open item, own page): EU CBAM only, from €145 a month. It imports purchase orders, holds default values and supplier and plant data, and exports declarations; it doesn't mention the UK. The UK regime copies the EU design, so adding the UK is about a month's work for it.
  - Green Calculus, Fastmarkets and Dcycle: the scout's own-page checks stand.
- Services already cover it. cbamguide.com (updated 21 Nov 2026) lists 16 UK advisers, brokers and forwarders:
  - Denholm Good Logistics already "monitors volumes, calculates liability, prepares return-ready reports".
  - Valpak sells an end-to-end service that includes preparing the return.
  - Hooper & Co offers a free threshold check.
  - The customs broker, who already holds the import data, is the natural owner of this job.
- Cheapest substitute: a spreadsheet built from the importer's customs declaration data plus HMRC's default values, both free.
- Why buyers won't switch: the broker already has the data and is adding CBAM as a service, and HMRC's filing service and return format don't exist until 2028.
- Job ads (search summaries):
  - Tata Steel UK CBAM Compliance Advisor, £33k to £37k (closed 18 June 2026).
  - An AVK Import/Export Specialist role covering UK CBAM preparation.
  - CBAM roles at Redshaw Advisors, EY and Isometric.
  - Most are advisers or large firms, not mid-size importers.

**Scoring rationale**
- **Pain 11.** A real new obligation starts 1 Jan 2027, but the first return isn't until May 2028, default values are allowed, and few importers are liable.
- **Pay 13.** Dubrink, CBAMable and CBAMDesk publish prices, and HMRC estimates the admin cost.
- **AI 6.** The core is deterministic (threshold maths, lookups, a ledger). AI only helps at the edges: reading invoices and certificates and matching verification reports.
- **Reach 6.** There is no public register of importers until 2028. Buyers can be reached through brokers and trade bodies, but brokers are also CBAMable's channel.
- **Build 11.** The core is small, but HMRC hasn't published a return format and the rules are still settling.
- **Competition 2.** Several UK-ready tools exist, brokers and accountants sell it as a service, and EU tools can add the UK quickly.
- **Risk 7.** It computes a tax, the rules are still in flux, and a wrong figure costs the buyer money.

**What would change my mind**
1. HMRC's count of liable importers after the threshold, showing at least 5,000, and the expected split between default values and verified actuals.
2. Own-page or help-doc evidence that Dubrink, CBAMable and CarbonChain lack the rolling threshold test and a per-import ledger tied to customs declarations. Also that the main CDS software vendors on HMRC's software developer list have no CBAM module.
3. Evidence that brokers want to buy rather than build, such as CBAMable's traction or brokers complaining about the workload.

Even with all three I'd expect a ceiling of about 62, because AI isn't essential to this job. Recommend parking it.

**Sources** (all accessed 2026-11-23)
- https://www.gov.uk/government/publications/carbon-border-adjustment-mechanism-cbam-policy-summary/carbon-border-adjustment-mechanism-cbam-policy-summary (fetched)
- https://www.gov.uk/guidance/keeping-records-for-carbon-border-adjustment-mechanism-cbam (fetched)
- https://www.gov.uk/government/publications/introduction-of-carbon-border-adjustment-mechanism/carbon-border-adjustment-mechanism (fetched)
- https://www.gov.uk/government/consultations/draft-legislation-carbon-border-adjustment-mechanism/draft-tax-information-and-impact-note (fetched; consultation dates only)
- https://kpmg.com/us/en/taxnewsflash/news/2026/10/uk-cbam-practical-tools-importers-assess-liabilities.html (fetched)
- https://www.dubrink.com/pricing and https://www.dubrink.com/uk-cbam (fetched)
- https://cbamable.com/ (fetched)
- https://cbamdesk.com/ (fetched)
- https://cbamguide.com/learn/uk-cbam/services/ (fetched; third-party directory)
- https://www.fbj-online.com/?p=57466 (search summary)
- https://www.jobijoba.co.uk/detail/92/4b71b5b11f055cb33069e8d4f41329f8, https://jobs.workable.com/jobs/ffe7f397-5f98-4793-b651-1bbce4393d30.md and https://carbon-pulse.com/538475/ (search summaries)

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor own-page checks done for Green Calculus, Fastmarkets, Dcycle. Not checked: CBAMDesk (403), customs software vendors.
- 2026-11-23 | validator | G0→G1 | REVISE 56 | The dates check out, but HMRC expects over 80% of importers to fall under the £50,000 threshold, the core is deterministic, and Dubrink (€1,990 a year), CBAMable (£229 a month for brokers) and brokers' own CBAM services already serve the UK regime.
