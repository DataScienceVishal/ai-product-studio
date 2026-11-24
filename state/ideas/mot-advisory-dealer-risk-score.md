# MOT-advisory repair-risk score for independent used-car dealers

- slug: mot-advisory-dealer-risk-score
- stage: G0
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
Draft self-score by the scout (validator to re-score):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 10 | 7 | 11 | 5 | 12 | 6 | 8 | 59 |

Rationale: Pain 10 (margin pressure and repair surprises, but no dealer-specific loss figure); Pay 7 (substitute inspection £79 to £267, no dealer tool price); AI 11 (text modelling with a public-data backtest); Reach 5; Build 12 (open data, clear pipeline); Competition 6 (no dealer predictor found, but HPI and Auto Trader sit next door); Risk 8.

## Gate log
- 2026-11-24 scout round 6 (T-36): G0 drafted. Weakest on Pay; the backtest is the strongest evidence the studio can collect itself.
