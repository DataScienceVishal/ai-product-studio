# MTD quarterly prep for small practices

- slug: mtd-quarterly-prep
- stage: G0
- market and segment: UK small accountancy and bookkeeping practices (sole practitioners to about 10 staff) with many sole-trader clients brought into Making Tax Digital for Income Tax (from April 2026 above £50k qualifying income; £30k from April 2027; £20k from April 2028), especially clients who are "non-digital" and send paper, PDFs or spreadsheets
- one-line pitch: Clients send bank statements, receipt photos and spreadsheets however they like. The tool extracts and categorises every transaction into HMRC self-employment categories, raises queries back to the client in plain English, and gives the accountant a reviewed, export-ready quarterly update to file through the practice's existing MTD software.

## Problem and who has it

MTD for Income Tax turns one annual self-assessment job per sole trader into four quarterly updates plus a final declaration. Many clients keep poor records and deliver them late. Agents expect much more work, with deadlines that all land at once. Practices are repricing, dropping low-fee sole traders, or considering leaving that market. The filing software itself is cheap (bridging software at about £20 to £60 a year). What costs money is the accountant's time turning messy records into categorised figures each quarter. This is the owner's finance and tax domain.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/publications/research-into-agents-preparedness-for-making-tax-digital-for-income-tax-headline-findings/research-into-agents-preparedness-for-making-tax-digital-for-income-tax-headline-findings-report | 2026-11-23 | HMRC agent research (506 agents in Dec 2024, 502 in Jul 2025). 86% of agents expect to take on additional tasks to support client MTD compliance. 73% have already helped clients with digital record keeping. 27% worry about the extra time needed. |
| https://www.aatcomment.org.uk/audience/members/how-are-members-repricing-their-services-to-reflect-incoming-mtd-changes/ | 2026-11-23 | AAT member accounts. Firms expect 20 to 25% more work once embedded, rising to 30 to 50% during transition. One expects 2 to 3 times the workload ("we'd have to quadruple our fees"). One says about 90% of clients supply tax information at the last minute in January. Firms are considering dropping sole traders. Quarterly deadlines can't be staggered the way VAT can. |
| https://www.icaew.com/insights/tax-news/2025/nov-2025/most-businesses-and-agents-see-no-benefits-to-mtd-income-tax | 2026-11-23 | ABAB 2025 survey reported by ICAEW (3,146 responses, 23% agents). 40.8% expect a significant cost increase from quarterly updates, and 40.7% from digital record keeping. 65.2% see no benefits. |
| https://www.wolterskluwer.com/en-gb/expert-insights/non-digitalised-clients-key-challenges-mtd-income-tax | 2026-11-23 | Wolters Kluwer research (as summarised in search results; page returned 403 on fetch). 59% of accountants say at least half their income tax clients are still non-digitalised. Data quality and reconciliation (47%) and client onboarding (44%) are the top hurdles. Not verified on the page itself. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Dext Solo, receipt and bank capture for MTD sole traders (https://dext.com/uk/partner/pricing, accessed 2026-11-23) | from £2.50 per client per month ex VAT, minimum 5 clients. AI Assist add-on £5 per client. | Strong capture tool, but assumes the client uses an app and the practice uses a full ledger. Weaker on clients who send messy spreadsheets or paper bank statements, and on the query loop with the client. |
| Spreadsheet bridging software, e.g. TaxCalc MTD Quarterly Filer, 123 Sheets (https://www.taxcalc.com/individual-mtdqf, accessed 2026-11-23; prices from a search summary) | about £20 to £60 a year (TaxCalc listed at £24/yr ex VAT; 123 Sheets £19.75/yr first-year discount) | Files numbers that are already categorised. Does nothing about the messy input. |
| Accountant's manual work, priced to the client: £40 to £120 per quarter, or £15 to £60/month extra, per accountancy-firm guides (https://www.accountingfirms.co.uk/?p=161988, accessed 2026-11-23 via search snippet; not fetched) | Substitute cost the practice absorbs or passes on | This labour is what the product cuts. Margin is squeezed for low-fee clients. |
| Full ledger software for the client (Xero, FreeAgent, QuickBooks) | Monthly subscriptions (not priced here) | Many older or non-digital clients won't adopt them (AAT accounts above). |

## Why AI is essential (and the moat)

- The inputs are unstructured: scanned bank statements from many UK banks, receipt photos, owner-made spreadsheets with free-text descriptions. Extracting and categorising them into HMRC self-employment categories (and spotting personal versus business spend, capital items, possible disallowables) needs language and vision models, not rules.
- Query generation: the tool writes plain-English questions to the client ("What was the £420 to B&Q on 3 June: materials for a job, or personal?") and folds the answers back in. This replaces the accountant's chasing emails.
- Confidence scoring: the accountant reviews only low-confidence lines. This is where time is saved.
- Moat (moderate to strong): an evaluation set of UK bank-statement formats and categorisation decisions, built with the owner's tax domain knowledge; a practice-first workflow (bulk client queue for each quarterly deadline); and export formats for the common MTD bridging tools. Big ledgers target app-using clients. This targets the non-digital tail that practices find hardest.

## Rough build plan and Azure cost

- Week 1: upload portal (per-client link), extraction for PDF and CSV bank statements and receipt photos, normalised transaction table, synthetic evaluation set (fictional statements).
- Week 2: categorisation to HMRC self-employment categories with confidence scores and an accountant review UI.
- Week 3: client query loop (email or portal through an adapter, mock by default), quarter totals, CSV export in a bridging-software-friendly layout. No direct HMRC API submission in MVP, so HMRC software recognition is not needed at first.
- Week 4: practice deadline dashboard, audit trail, UK GDPR controls (retention, deletion, processor list), demo with three fictional sole traders.
- Azure (estimate): Container Apps scale-to-zero (about $0 to $5/mo), Azure OpenAI small model plus vision for extraction and categorisation (about $5 to $15/mo at demo volume), Postgres (about $0 to $15/mo), Blob Storage (about $1/mo). Projected total about $6 to $35/mo.

## Risks, and what would prove this wrong

- Financial personal data at scale (bank statements of individuals). This needs strong security, UK GDPR processor terms, and probably UK data residency. Risk is moderate.
- Must not present categorisation as tax advice. The accountant stays the decision-maker and the tool's output is a draft for professional review.
- Policy risk: HMRC thresholds, timelines and quarterly-update rules have already shifted. A further delay or simplification would shrink demand.
- Strong incumbents (Dext, Xero, IRIS, TaxCalc) could add the same messy-input features. Dext's £2.50 per client sets a low price anchor.
- Synthetic test data may not reflect real bank-statement chaos, and real client data is not available to the studio (check this against the red-flag rule).
- Proved wrong if: practice owners say most MTD clients already use an app (Dext or a ledger) and the messy-input tail is small; or extraction and categorisation on realistic statement formats can't reach accuracy high enough to cut review time by about half; or practices refuse to upload client bank data to a new vendor.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
