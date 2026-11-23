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
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor own-page checks done for Green Calculus, Fastmarkets, Dcycle. Not checked: CBAMDesk (403), customs software vendors.
