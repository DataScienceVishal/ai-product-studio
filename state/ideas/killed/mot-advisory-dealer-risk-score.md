# MOT-advisory repair-risk score for independent used-car dealers

- slug: mot-advisory-dealer-risk-score
- stage: KILLED at G0 (validator 51, 2026-11-24, T-36)
- market and segment: UK independent used-car dealers (and small fleet remarketers) buying stock at auction or part-exchange, with 20 to 150 cars in stock, who need a fast read on likely repair and prep cost before they bid.
- one-line pitch: Reads a car's full official MOT history, including the free-text advisories and failures, and returns a plain-English repair-risk and likely-cost estimate (brakes, suspension, corrosion, tyres, clocking flags) before the dealer bids.

## Problem and who has it
- Independent dealers say rising prep costs and stock shortages squeeze margins (Car Dealer Live 2026 panel, search summary). Reconditioning time and cost are the main delay: 85% of dealers named it the biggest delay in a 2019 Manheim survey (search summary; dated).
- Used-car buyers face surprises: 37.3% of used-car buyers found unexpected repair costs, averaging £1,288, in a 2026 Blackcircles study (search summary; this is private buyers, so it only shows the size of the problem the dealer absorbs).
- Mileage doubt is a second cost: in a Cazoo-sponsored September 2026 survey of 310 dealers, 77% check MOT history to verify mileage and dealers guessed 14% of cars they see may have altered mileage (search summary; company survey).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://cardealermagazine.co.uk/independent-dealers-warn-rising-prep-costs-and-stock-shortages-are-squeezing-margins/323274 | 2026-11-24 | Search summary only. Independent dealer panel at Car Dealer Live 2026: prep costs and stock shortages squeezing margins. |
| https://www.tyrepress.com/2026/09/blackcircles-study-more-than-a-third-of-used-car-buyers-face-average-1288-unexpected-repair-bill/ | 2026-11-24 | Search summary only. 37.3% of used-car buyers faced unexpected repairs, average £1,288 (private buyers). |
| https://www.cazoo.co.uk/press/cazoo-adds-mot-and-mileage-history-to-car-listings/ | 2026-11-24 | Search summary only. 310-dealer survey: 77% check MOT history for mileage; estimated 14% of cars may have altered mileage. Company survey. |
| https://www.insurancefactory.co.uk/news/October-2019/Reconditioning-is-biggest-barrier-to-getting-vehic | 2019 item, accessed 2026-11-24 | Search summary only. Reconditioning time is the biggest delay for dealers (85%, Manheim survey). Dated. |
| https://documentation.history.mot.api.gov.uk/mot-history-api/download-vehicle-mot-history-data | 2026-11-24 | Fetched. Bulk file every Sunday (full snapshot) and daily delta files; "All content is available under the Open Government Licence v3.0". The page does not list the file fields or say whether registrations are included. |
| https://dvsa.github.io/mot-history-api-documentation and https://www.api.gov.uk/dvsa/mot-history-api/ | 2026-11-24 | Search summaries only. The API needs a key DVSA grants on application; the older API was deprecated on 1 September 2025 and users must re-register. Current quotas not found. |
| https://www.motoringresearch.com/used-cars/new-ai-tool-used-car-blind-spot/ | 2026-11-24 | Search summary only. MotorIQ "Should I Buy This Car?" estimates common faults and costs per model for private buyers. |
| https://www.am-online.com/news/payment-assist-launches-car-assessment-and-repair-prediction-tool | 2026-11-24 | Search summary only. A payment provider launched a car assessment and repair prediction tool. Not read; scope unknown. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Pre-purchase inspection (AA £142 to £191, RAC £116 to £267, ClickMechanic from £79 basic or £137 premium) | £79 to £267 per car; figures from ClickMechanic's own comparison page, undated: https://www.clickmechanic.com/pre-purchase-inspection | A physical inspection; trade dealers cannot afford one per auction lot. Shows the per-car substitute cost |
| cap hpi: an "MOT Data Check" is included with every HPI check, with full MOT history, advisory notes and failures (https://www.cap-hpi.com/product-selection/); "smr actuals" is historic repair and maintenance spend data | Check price not read | Shows the MOT data; no repair-risk prediction was found in the search |
| Glass's repair estimating (AutovistaREPAIR) | Not published | Works from damage calculations, not MOT history (search summary: https://glass.co.uk/sector/bodyshops-assessors/) |
| MotorIQ (private buyers), a payment-provider repair prediction tool | Not read | Consumer and finance channels, not dealer lot-by-lot bidding |
| Garage systems' advisory follow-up (Motasoft "Opportunities", MOT Manager advisory lookup) | Not published | Workshops chasing their own customers; not a dealer buying tool (search summaries: https://garagewire.co.uk/?p=251592, https://www.motmanager.co.uk/features/) |

## Why AI is essential (and the moat)
- The advisories are free text ("nearside front brake disc worn, pitted", "slight play in track rod end"). Turning them into components, severity and time-to-failure, then combining with age, mileage and make and model, is language and statistical modelling, not a lookup.
- The studio can measure the model against reality: use older MOT history to predict what the later test found. That is a backtest on public data, with labels, which most products in this studio's queue cannot do.
- Moat is the trained advisory-to-component model and the backtest record; the data itself is open, so anyone can start, but few will do the text modelling.

## Public data the studio would use to prove the gap and build the demo
- DVSA bulk MOT history files (OGL v3.0). Open item: confirm the bulk file has advisory and failure text and whether it has registrations (the fetched page does not say; read the bulk file format page).
- Proof test: hold out tests dated in the last year; from earlier tests predict (a) failure on the next test, (b) the component categories that appear. Report precision and recall against a simple baseline (age and mileage only). Pass: advisory-text model beats the baseline by at least 10 points of recall on brake and suspension failures.
- A demo needs no customer data. Cost estimates would use published labour rates and parts price lists the studio collects lawfully (not yet located; flag as an open item). Mock mode loses nothing; no paid services.

## Add-on check (does the incumbent already do it?)
- Read: cap hpi product page text via search (MOT data check, no prediction), Glass's page via search (damage estimating). Not read: Auto Trader dealer tools, Cazana, Solera pages. No dealer-side advisory repair-cost predictor found in three searches.
- The channel owner's own tools: DVSA offers the history API and bulk data but no scoring.
- Free community tools: Apify actors that fetch MOT history exist (search result https://apify.com/car_map/apify-mot-history); they fetch, not score.

## How the selling partner could reach buyers
- Dealer trade press (Car Dealer Magazine, Motor Trader), dealer associations and auction buyer communities. Channel unknown: if the partner has no motor-trade contacts, Reach is about 3.

## Rough build plan and Azure cost
- Bulk-data pipeline (data engineering), advisory-text classifier, risk and cost model, registration-lookup web page and API. About 3 to 4 weeks. Azure about £15 to £30 a month plus storage for the bulk file (estimate; the file size is not stated on the page). The API key application needs Vishal's OK (creating an account).

## Risks, and what would prove this wrong
- Pay is the weak point: no price anywhere for a dealer-side tool, and dealers already get MOT history free from DVSA and bundled in HPI checks. If dealers will not pay about £30 to £100 a month for a score, the idea fails. A dealer survey is not possible without contact (locked), so the evidence has to come from comparable tool prices, which have not been found.
- Cost estimates need parts and labour data that may be proprietary.
- Cazoo, Auto Trader or cap hpi could add a "repair risk" panel quickly. Test: read their dealer product pages and release notes.
- Vehicle registration data is not personal data in the same way, but MOT history can be linked to owners by third parties; the tool should not store owner information.

## Score (validator)
Scout draft: 59 (Pain 10, Pay 7, AI 11, Reach 5, Build 12, Competition 6, Risk 8).

Validator score, 2026-11-24 (T-36):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 9 | 6 | 8 | 5 | 12 | 3 | 8 | 51 |

**Falsification findings** (all accessed 2026-11-24; "fetched" means the page itself was read)
- Others already predict next-MOT failures from MOT history:
  - **Car Guide.** Car Guide uses "make, model, mileage, engine size and previous MOT history to ... predict which components are likely to fail on the next MOT". It flags ex-taxis and unrecorded accident damage and is pitched at motorists, car dealers, warranty firms and underwriters, with data available through an API (https://www.just-auto.com/interview/car-guide-using-ai-to-predict-parts-failures, fetched; interview dated May 2022, so it is not known whether the product is still live).
  - **VehicleStats.** VehicleStats estimates the chance of failing the next MOT with a logistic regression on DVSA data (https://www.vehiclestats.co.uk/how-we-calculate-risk, search summary; the fetch returned 403).
  - **MOTCost.** MOTCost publishes a free "failure cost guide" for advisory items (https://motcost.pages.dev/check-mot-history, search result).
  - **Others.** MotorIQ and Payment Assist estimate repairs for consumers (search results).
- Dealer recon-cost tools already exist:
  - autobizCarcheck calculates reconditioning cost from a cost grid during trade-in appraisal. It is a European product priced in euros, and the page doesn't mention MOT history (https://office.autobiz.com/en/autobizcarcheck/, fetched).
  - Glass's dealer tools cover recon and repair cost (https://glass.co.uk/sector/dealers/, search result).
- Pay anchor, and it is low. Trade vehicle checks cost:
  - MotorCheck: £3.30 a check pay-as-you-go, or from £1.20 on monthly plans (https://partner.motorcheck.co.uk/auto-trade, search summary);
  - The Auto Experts: £2.99 to £3.99 a check, or £30 a month;
  - MyCarCheck: £1.40 a check.
  - These already include the MOT history, and gov.uk shows it free. A risk score is an add-on to a £1 to £4 data product. Estimate: at about 100 cars checked a month, even £1 extra per check is £100 a month per dealer, and nothing shows dealers would pay it.
- Cheapest substitutes:
  - the free gov.uk MOT history, read by an experienced buyer;
  - BCA's Car Check and Standard Mechanical Report, which give buyers the condition data "to make your own estimation of the cost of reconditioning", with claims accepted within 48 hours or 500 miles on the mechanical report (https://episerver.bca.com/en/es/MM/Getting-Started/c/Professional-buyer/Appraisal-and-Mechanical-Report/Carcheck1, search summary).
- AI advantage is weaker than claimed. Testers record most MOT defects and advisories by choosing items from DVSA's standard defect list in the MOT inspection manual, then adding a location. Only some entries are free text (validator's knowledge; not verified this run). So much of the "free text" maps through a lookup table, and the competitors above already model failure risk on structured history.
- Data licence: OK.
  - The bulk download is under OGL v3.0 (fetched).
  - The API quota is 500,000 requests a day at 15 requests a second (https://documentation.history.mot.api.gov.uk/mot-history-api/rate-limits/, fetched). Getting a key needs an application that records the applicant and their "use of the data", so it is ask-first.
  - The privacy notice says the data "is intended to be used for services, applications and research that will contribute to improved road safety" (https://www.gov.uk/government/publications/dvsa-privacy-notices/mot-history-api-privacy-notice, fetched). That states an intent, not a restriction, but a dealer bidding tool's link to road safety is thin, and DVSA could weigh that when granting a key.
  - No red flag.

**Scores in brief.**
- Pain 9: no dealer-side loss figure; the cited studies are search summaries, the private-buyer study isn't about dealers, and the survey is from 2019.
- Pay 6: trade checks cost £1.20 to £4, with no dealer price for a risk score.
- AI 8: the defect wording is mostly standardised, and others already model failure.
- Reach 5: many dealers, but a cheap per-check product needs volume, and the channel is unknown.
- Build 12: open data and a clear pipeline.
- Competition 3: Car Guide, VehicleStats, MOTCost, MotorIQ, autobiz and Glass's, with HPI next door.
- Risk 8.

**Verdict: KILL (first attempt; ceiling below 70).**
- MOT-history failure prediction is already done (Car Guide, which is pitched at dealers, and VehicleStats), and advisory repair-cost guides are free (MOTCost).
- Dealers' reference price is a £1 to £4 trade vehicle check that already includes the MOT history.
- The open data makes the product easy to build, but it is just as easy for anyone else to build, and the advisory text is mostly standard DVSA wording, so the AI moat is thin.
- Even with the best plausible evidence (Pain 11, Pay 9, AI 10, Reach 6, Build 12, Competition 4, Risk 8), the score tops out at about 60.

**Lessons**
- An open dataset with a free government viewer sets the price anchor at zero for the data and at a few pounds for the value-added check. Look up the per-unit price of the nearest data product before scoring Pay.
- Ideas built on famous open datasets (MOT, Companies House, Land Registry) attract hobby and consumer sites quickly. Search for "<dataset> risk/score/predict" sites as well as for incumbents.
- Before crediting AI for "free text", check whether the regulator's form uses a fixed code list.

**What would revive it**
- A published dealer price (at least £20 a month, or at least £1 extra per check) for a repair-risk product, plus evidence that Car Guide and VehicleStats no longer sell to the trade.
- Or a backtest on the DVSA bulk data showing that the advisory wording beats an age, mileage and model baseline by at least 10 points of recall. Even then, the per-check pricing limits the upside.

## Gate log
- 2026-11-24 scout round 6 (T-36): G0 drafted. Weakest on Pay; the backtest is the strongest evidence the studio can collect itself.
- 2026-11-24 | validator | G0→G1 | KILL 51 | Car Guide (dealer-pitched ML next-MOT failure prediction) and VehicleStats already model failure risk from MOT history, MOTCost gives advisory cost guides free, and dealers' price anchor is a £1-£4 trade vehicle check that already includes MOT history; ceiling about 60.
