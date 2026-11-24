# Food supplier cost-price-increase pack

- slug: food-supplier-cost-price-increase-pack
- stage: G0
- market and segment: UK small and mid-size food and drink manufacturers (about £2m to £50m turnover) selling to supermarkets and wholesalers, who must justify cost price increases (CPIs) to buyers
- one-line pitch: Turns a supplier's recipes and purchase prices into a line-by-line cost-change analysis, recommends the price rise to ask for per SKU, and builds the evidence pack the buyer will ask for, using public commodity indices as third-party proof.

## Problem and who has it
Supermarkets resist CPIs. A supplier has to show which input costs moved, by how much, and what share of the pack they are, then choose how much to ask for per SKU (and whether to trade pack size instead). Small suppliers do this in Excel or with a part-time finance director. The output is a judgement: how much to ask, for which SKUs, with what proof.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.thegrocer.co.uk/news/suppliers-facing-supermarket-brick-wall-on-cost-increases/724223.article (search summary) | 2026-11-24 | Grocer survey: suppliers meet a "brick wall" on cost increases; Tesco rated hardest on CPIs (26.5%). |
| https://www.fdf.org.uk/globalassets/resources/publications/reports/uk-food-inflation-forecast-2026-27.pdf (search summary) | 2026-11-24 | FDF forecasts food inflation reaching 3.9% by December 2026 and says retailers have resisted supplier increases more than expected. |
| https://assets.publishing.service.gov.uk/media/6ab54e4a8cb3c0580e5011b2/2026_GCA_conference_slide_deck.pdf (search summary) | 2026-11-24 | Groceries Code Adjudicator material lists refusal or unreasonable delay on CPIs among common complaints; the Adjudicator cannot decide whether a CPI is accepted, so suppliers must argue their own case. |
| https://www.igd.com/articles/food-inflation-costs-vs-profits-explainer/73187 (search summary) | 2026-11-24 | IGD May 2026: recent food inflation overwhelmingly cost-driven. Usable as third-party evidence in a cost case. |
| https://www.thegrocer.co.uk/supermarkets/supermarkets-harder-than-ever-to-deal-with-report-challenger-brands/662776.article (search summary) | 2026-11-24 | Challenger-brand SMEs find it very hard to hold productive conversations with buyers about cost pressure. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Fractional finance director | £600 to £1,300 a day depending on the vendor page (FD Capital; Lanop gives £600 to £1,200) | The substitute cost. Vendor marketing pages, so treat as indicative. |
| Fractional head of finance | £400 to £650 a day (FD Capital) | Cheaper human substitute for building the cost model. |
| Excel plus the supplier's own accountant | Staff hours (no public price) | Today's default for small suppliers. |
| Food ERP and costing modules (not checked this round) | Not found | Must be checked at G1: recipe-costing modules in food ERPs (for example Foodware 365, Sage-based add-ons) may already show cost changes by SKU. |
| A CPI-specific tool | None found in one search | A thin result; the validator should repeat the search ("cost price increase" tool, "CPI pack", "price increase request template") before trusting it. |

## Why AI is essential (and the moat)
The hard part is mapping messy inputs (recipe cards, supplier price lists, invoice lines named differently each month) to public indices (ONS producer prices, AHDB, Defra commodity series, energy and packaging indices), then writing the argument per buyer. An LLM reads and maps the inputs and drafts the narrative. Deterministic maths does the weighted cost change. The moat is the supplier's own cost history and a library of buyer-specific formats, not the model.

## Rough build plan and Azure cost
- Inputs: recipe or BOM export, purchase price history, current retail price list. Public data: ONS and Defra series (OGL), AHDB prices, IGD explainer as citable context.
- Output: per-SKU cost movement, recommended ask and a fallback (pack-size change), a buyer-ready evidence pack for human sign-off, and a log of past submissions and outcomes.
- Demo with a synthetic bakery or sauce maker and real ONS and Defra series. No paid service needed.
- Azure: Container Apps and Postgres, under £30 a month for a pilot (estimate).

## Risks, and what would prove this wrong
- Biggest doubt: Pay. No public price exists for CPI support. The only substitute cost is a fractional FD, and a supplier may see this as a few hours of FD time a year, not a subscription. CPIs happen once or twice a year per buyer.
- Competition unknown: food ERPs and pricing consultancies may already do this; one search found nothing, which is weak evidence.
- The outcome rests on the retailer's willingness, not the pack's quality; a supplier may judge a good pack worthless if Tesco says no.
- Test: ask the validator to find three public examples of a supplier's CPI evidence pack (Adjudicator case studies, trade press) and check whether AI saves a day or an hour on a real one.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- G0 written by scout, round 9 (T-46), 2026-11-24. Not scored. Weakest of the round on Pay evidence.
