# Packaging EPR data pipeline for mid-size UK producers

- slug: pepr-packaging-data-pipeline
- stage: G0
- market and segment: UK brands, manufacturers and importers that are "obligated" under packaging EPR (pEPR), mainly large producers (turnover over £2m and over 50 tonnes) and upper-band small producers. Typically 20 to 250 staff, hundreds to thousands of SKUs, no sustainability team.
- one-line pitch: Turns a producer's SKU, bill-of-materials and supplier spec exports into a validated Report Packaging Data (RPD) upload and a fee forecast, and flags errors before the producer pays a resubmission fee.
- forcing function: Packaging EPR is live. Large producers file H2 2026 data (1 July to 31 December) by **1 April 2027**, and small producers file full-year 2026 data by **1 April 2027**. H1 data is due 1 October each year. Source: https://www.gov.uk/guidance/packaging-data-check-reporting-periods-and-submission-deadlines (accessed 2026-11-23). Changing data after submission can cost a resubmission fee of £807 (direct) or £512 (through a compliance scheme). Source: same page. Regulator: PackUK and the four UK environment agencies. Legislation: The Producer Responsibility Obligations (Packaging and Packaging Waste) Regulations 2024, https://legislation.gov.uk/uksi/2024/1332/schedules/made (appeared in search results 2026-11-23; schedule text not read).

## Problem and who has it

Every obligated producer must report packaging by activity, class, material and weight in kg, plus nation of sale, on a fixed cycle. The data sits in ERPs, Shopify exports, supplier spec sheets in PDF and spreadsheets in mixed units. Large producers also pay per-tonne disposal fees, and data accuracy drives the fee. The producer stays legally responsible even when a scheme or consultant files for them.

Small producers have to report: packaging activities, class (single sales unit or grouping), material and weight in kg per material, and a few special cases (bags in England, drinks containers coded SP and HDC). Source: https://www.gov.uk/guidance/epr-for-packaging-what-you-must-do-as-a-small-producer (2026-11-23).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/guidance/packaging-data-check-reporting-periods-and-submission-deadlines | 2026-11-23 | Deadlines (1 Oct, 1 Apr), resubmission fee £807 or £512, 2025 resubmission deadline was 1 Sep 2026. Pain signal 1: a regulator-set cost for getting the data wrong first time. |
| https://www.gov.uk/guidance/epr-for-packaging-what-you-must-do-as-a-small-producer | 2026-11-23 | Data fields required; 2027 registration fee £1,303 direct or £696 via a scheme; late registration fee £386; scheme fees extra. Gov.uk also tells producers they may use a scheme, a consultant, or do it themselves. |
| https://erp-recycling.org/uk/news-and-events/2026/08/poor-packaging-data-could-be-increasing-your-epr-costs/ | 2026-11-23 | Compliance scheme's own article titled "Poor Packaging Data Could Be Increasing Your EPR Costs". Only the title was retrievable; the body was not read. Pain signal 2 (unverified detail). Validator to read it in full. |
| https://www.gov.uk/government/news/new-resubmission-deadline-for-2025-packaging-data | 2026-11-23 | Appeared in search results: PackUK set a 1 September 2026 resubmission deadline for 2025 data from producers who pay pEPR fees. Pain signal 3: the regulator is pushing producers to correct data. Page itself not opened. |
| https://www.valpak.co.uk/knowledge-hub-post/packaging-extended-producer-responsibility-epr-frequently-asked-questions | 2026-11-23 | Valpak (a scheme) offers a data collection service "where data is not sufficient". Shows producers are paying for data collection. No price on the page. |
| Job-ad signal | not collected | TODO for validator: search job boards for "packaging compliance" or "EPR data analyst" roles. Not done in this round. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Compliance schemes (Valpak, ERP, Ecosurety) with data services | Not published. Small-producer registration via a scheme is £696 to the regulator, scheme fee on top (https://www.gov.uk/guidance/epr-for-packaging-what-you-must-do-as-a-small-producer, 2026-11-23). | Service-led and priced by quote. Schemes sell fee-bearing compliance, not a self-serve data tool. |
| Valpak by Reconomy Global Data Insights Platform | Not stated (https://brc.org.uk/news-and-events/news/associate-insight/2026/valpak-by-reconomy-launches-global-epr-platform/, 2026-11-23). Centralises packaging, component and supplier data, models pEPR cost, claims 60m SKUs referenced. | The page does not say it covers UK pEPR specifically, and does not mention RPD submission. Aimed at "brands and retailers". The closest competitor. |
| PackTotal EPR | Price not published; third-party listing says "No data available" (https://netzerocompare.com/software/packtotal-epr, search summary only; page returned 403). | SKU and bill-of-materials model plus import/export for UK EPR and PPT. I could not open its own pricing page. Validator must check packtotal's own site. |
| Lappa (EU-oriented) | Published tiers in euros; extra packaging report €70 (https://lappa.org/epr-pricing/, search summary only) | Not UK-first. |
| Excel plus a consultant | Staff hours; resubmission £807 | The status quo. |

Gap that survives: unproven. On features, PackTotal and Valpak overlap. The only gaps I can name are price transparency for mid-size producers and a pre-submission validator (unit errors, missing nation split, mismatches against purchase volumes) tied to a fee forecast. An incumbent could close that quickly. Expect Competition to score low unless the validator finds a stronger angle.

## Why AI is essential (and the moat)

- Extraction and normalisation: read supplier spec sheets, pack drawings and mixed-unit spreadsheets into materials and weights per component, with a confidence score and a human review queue.
- Reconciliation: compare declared packaging weight against purchase volumes and sales volumes by SKU to catch errors that would trigger a resubmission.
- Fee modelling from the published fee tables, so the producer sees what a design change saves. Needs the Year 2 fee figures from gov.uk (I did not read them; the validator should).
- Moat is the validation rule set plus the evaluation set of messy inputs. It is not the chat layer.

Demo with public or synthetic data: build a fictional brand with about 300 SKUs, synthetic supplier spec PDFs and a messy ERP export. Use the public gov.uk reporting rules and fee tables. No real customer data is needed. Pass criterion: the pipeline produces an RPD-format CSV and a list of seeded errors found.

## Rough build plan and Azure cost

- Weeks 1 to 2: SKU and BoM schema, rules engine for RPD fields, CSV export in the RPD format (spec to be taken from gov.uk "report packaging data" guidance).
- Week 3: LLM extraction from spec sheets and a review UI.
- Week 4: reconciliation checks, fee forecast, audit trail and seven-year record retention.
- Azure: App Service or Container Apps on a scale-to-zero plan, Postgres on a burstable tier, Blob storage. Estimate under $25 a month on the default stack. Not yet written to BUDGET.md.
- The studio does not file on the producer's behalf. It produces a file for a human to upload and sign off.

## Risks, and what would prove this wrong

- Thresholds are quoted inconsistently across sources (£1m to £2m and 25 to 50 tonnes). Use gov.uk as the authority.
- Not legal advice. Output is a data file and a checklist. Producers remain responsible. Legal or compliance-consultant review needed before any wording about "compliant" appears in the product.
- Gap may not exist. If PackTotal's own site shows RPD CSV export and validation at SME prices, kill on Competition.
- Reachability: producers buy through schemes. A scheme could be the channel or the competitor. The selling channel is a UK business, so UK buyers fit.
- Small producers (the easiest to reach) pay no disposal fees, so willingness to pay may be low. Target is large and upper-band producers.
- Would prove wrong: three or more mid-size producers say a scheme's free data service is enough; or RPD changes its upload format often enough to make a file generator a maintenance burden.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor own-page check done for Valpak (via BRC release) only; PackTotal own page not reachable (403 on aggregator). Open items listed above.
