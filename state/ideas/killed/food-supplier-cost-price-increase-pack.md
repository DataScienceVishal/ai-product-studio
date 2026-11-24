# Food supplier cost-price-increase pack

- slug: food-supplier-cost-price-increase-pack
- stage: killed (G1 attempt 1, 57, T-46)
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
| 14 | 6 | 7 | 6 | 10 | 6 | 8 | 57 |

## Gate log
- G0 written by scout, round 9 (T-46), 2026-11-24. Not scored. Weakest of the round on Pay evidence.
- G1 attempt 1, validator, round 9 (T-46), 2026-11-24: **57, KILL** (ceiling about 63). See "Validator, round 9".

## Validator, round 9 (T-46, 2026-11-24)

**Verdict: KILL, 57/100.** This is the first idea in several rounds where no direct supplier-side competitor turned up. It dies on Pay and AI instead, and neither can rise much.

**Reason.**
- **Pay.** A CPI happens once or twice a year per retailer, in a window from about February to June with at least 12 weeks' notice (Grocery Guru). The only substitutes are a few days of a fractional FD (£400 to £1,300 a day, vendor pages) and CPI workshops from grocery consultancies such as Grocery Guru and The Retail Mind. Neither publishes a price, and neither is a subscription. Nothing public shows a supplier paying monthly for CPI support. A seasonal job buys a project, not a subscription.
- **AI.** The core is a weighted cost change: recipe share times index movement. That is deterministic arithmetic over a BOM the supplier already keeps in Excel or its ERP. The LLM only maps invoice lines to indices and drafts the narrative.
- **The other side has better AI.** Expana (Mintec) sells AI cost models ("Expana IQ ... recommend percentages, sourcing options, and relevant commodities") to *buyers*, explicitly for checking supplier price rises against market benchmarks. Retailers such as Iceland have also hired consultancies (Newton) to validate CPIs. The supplier's pack is judged against the buyer's own licensed model, so a pack built on free ONS and Defra indices adds little.
- **Outcome.** As the scout noted, success depends on the retailer's willingness, which the GCA can't decide. A supplier won't credit the tool when Tesco says no.

**Scores.**
- Pain 14: the GCA survey shows 26% of suppliers faced a refusal or unreasonable delay. The Grocer reports a "brick wall", and The Retail Mind found under a quarter of suppliers recovered all their costs. Retailer forms now ask for cost breakdowns at component level. The pain is real but seasonal.
- Pay 6: no price for the job, only a substitute day rate and unpriced workshops.
- AI 7: deterministic core.
- Reach 6: SME food manufacturers can be found through the FDF, trade shows and The Grocer, but the partner business's sector is unknown.
- Build 10: a synthetic BOM plus ONS PPI and Defra series makes a feasible demo with no paid service.
- Competition 6: there is no supplier-side tool. Excel, the ERP's recipe costing and consultancy workshops are the substitutes, and Expana could point its existing models at suppliers.
- Risk 8: no personal data. Sharing cost data with a buyer is the supplier's own choice.

**Lessons.**
- An "output is a judgement" job still needs a frequency that justifies a subscription. Check how often the job happens (once a year? weekly?) before scoring Pay.
- When the counterparty (buyer) already pays for an AI model of the same costs, the seller-side tool is judged against it. Search the other side of the negotiation too.

**What would revive it.**
- Evidence that SME suppliers pay recurring fees for CPI support: a published retainer, a trade-body member service, or a job ad for a "pricing analyst" at £2m to £50m food firms.
- Or a broader always-on product, such as continuous margin-at-risk monitoring per SKU and per customer across all buyers, with the CPI pack as one output. That would compete with ERP costing modules and needs its own kill test.

**Evidence (accessed 2026-11-24).**
- Expana cost models aimed at buyers, with AI: https://www.expanamarkets.com/product/features/cost-model/ (fetched; no price). Use on supplier increases: https://www.mintecglobal.com/blog/cost-models-how-raw-material-and-commodity-ingredient-price-fluctuations-shape-your-product-costs (search summary)
- Iceland routing CPIs through Newton: https://www.grocerygazette.co.uk/2022/09/05/iceland-drafts-in-external-party-for-price-talks/ (search summary, 2022)
- Grocery Guru CPI workshops, at least 12 weeks' notice, February to June window: https://www.makingbusinessmatter.co.uk/?p=70764 (search summary, undated)
- The Retail Mind survey (fewer than a quarter recovered all costs): https://www.thegrocer.co.uk/news/cost-price-increase-requests-being-rejected-by-supermarkets/705298.article (search summary)
- GCA survey (26% refusal or delay): https://www.gov.uk/government/news/inflationary-pressures-strain-relationships-between-retailers-and-suppliers (search summary)
- Component-level justification forms (Morrisons asks for the last three increases per item): https://thegrocer.co.uk/comment-and-opinion/how-suppliers-can-navigate-the-thorny-issue-of-cost-price-increases-with-demanding-retailers/659115.article (search summary)
- Not checked in the time box: the what-if costing modules in Nutritics, Foodware 365 and Sicon (the search returned only generic recipe-costing tools). These would matter only for the "revive" variant.
