# DMCC checkout-journey auditor

- slug: dmcc-checkout-journey-auditor
- stage: G0
- market and segment: UK consumer-facing online sellers outside Shopify and with bespoke checkouts, where drip pricing is the CMA's focus: ticketing, travel and holiday sellers, gyms and leisure memberships, driving schools, home-services booking sites (about 20 to 500 staff)
- one-line pitch: A browser agent walks the firm's own booking and checkout journeys, spots hidden mandatory fees, late-added charges and unsubstantiated urgency messages against the CMA's published price-transparency guidance, and keeps a dated evidence log with a fix list for the compliance owner.

## Problem and who has it
Since 6 April 2025 the CMA can fine consumer-law breaches directly, up to 10% of global turnover. Drip pricing (mandatory fees shown late) is a banned practice. The CMA runs its own sweeps rather than waiting for complaints. The first fines are out (AA/BSM £4.2m, StubHub £889,200) and a third wave of investigations opened on 18 November 2026 (Bannatyne, Caledonian Travel, Secret Escapes). The failure is rarely one page; it sits in the multi-step journey: a fee added at step 4, a single-supplement revealed after a date is picked, a countdown timer on a promotion that never ends. Marketing and product teams change journeys weekly and nobody re-tests them end to end.

Who pays: the head of compliance, legal or ecommerce at a mid-sized seller. Today this is covered by an ad hoc law-firm review or an agency "CRO audit".

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.lewissilkin.com/insights/2026/11/18/drip-pricing-cma-opens-three-new-investigations-into-holiday-and-gym-pricing-102oa5o | 2026-11-24 | Three new investigations announced 18 Nov 2026 (Bannatyne, Caledonian Travel, Secret Escapes); CMA has opened cases against 23 businesses; article says "more than £12 million in fines" and £2.3m refunds; CMA runs its own sweeps; advice to review journeys from first click to payment is the law firm's |
| https://www.lewissilkin.com/en/insights/2026/06/24/another-costly-penalty-as-cma-continues-its-drip-pricing-crackdown-102n65z (search result, not fetched) | 2026-11-24 | A further penalty reported June 2026 |
| https://www.dlapiper.com/insights/publications/2026/04/the-aa-agrees-a-fine-in-the-first-cma-consumer-protection-enforcement-under-the-dmcca (search result, not fetched) | 2026-11-24 | First DMCCA fine: AA/BSM, reported as £4.2m plus about £760k redress (figure from a search summary; confirm on the CMA case page before use) |
| https://www.linklaters.com/en/insights/blogs/linkingcompetition/2025/june/consumer-deep-dive_understanding-drip-pricing-under-the-dmcc (search result, not fetched) | 2026-11-24 | Drip pricing explained; CMA209 gives worked examples of prohibited drip and partitioned pricing |
| https://www.simplybusiness.co.uk/knowledge/retail/new-consumer-rights-laws-for-online-sellers/ (search result) | 2026-11-24 | Countdown timers must be substantiable; fines up to 10% of turnover |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Upfront - DMCC Compliance (Shopify app) | A search summary said $9.99 a month; the app page I fetched (https://apps.shopify.com/upfront-uk-price-check, 2026-11-24) says it is "not currently available on the Shopify App Store" and gives no features or price | Shopify only, and appears withdrawn; cannot walk multi-step bespoke journeys. Price anchor if it is live is low |
| Law-firm or consultant journey review | Not found in public sources; estimate needed (needs Vishal's OK for price quotes) | One-off; stale after the next release |
| Review-fraud audit services (Feefo page: https://business.feefo.com/resources/what-is-the-dmcc-ruling-fake-reviews) | Not published | Covers fake reviews only, not pricing journeys |
| Trustpilot "DMCCA compliance toolkit" (https://business.trustpilot.com/webinars-videos/build-trusted-brand/the-dmcca-compliance-toolkit) | Not published; page not read | Reviews focus (unverified) |
| Generic cookie/consent scanners | n/a | Not pricing-aware (unchecked) |

## Competitor search done (2026-11-24)
Queries: "DMCC Act compliance checker ecommerce website drip pricing fake urgency scanner tool"; "website consumer law compliance audit tool UK online pricing practices urgency claims reviews automated crawler DMCC compliance platform". Found only Upfront (Shopify) and review-audit services. Not yet checked: CRO/QA vendors (Contentsquare, Hotjar), enterprise compliance suites (OneTrust, Skyhigh), pricing-compliance vendors, and travel-sector tools; do this before G1.

## Evidence the studio can collect itself
- CMA case list and decisions on gov.uk (OGL): which journeys and which fee types drew enforcement. Label each decision's breach type to build a test set of "what the CMA flagged".
- CMA209 price transparency guidance (published, with examples).
- Run the agent on sandbox shops the studio builds and on public demo stores (own-site testing only; no scraping of third-party sites that forbid automated access, no live purchases).

## Demo plan on public or synthetic data
Build three synthetic booking sites (ticketing, gym, holiday) seeded with the CMA's published drip-pricing patterns, plus clean controls. The agent walks each journey to the payment page (no card entry), records price at each step, and reports the step where the total changed, the fee type and a guidance citation. Measure detection against seeded defects. No paid service is needed; the LLM and browser run locally, so the full demo works with no mock mode.

## Why AI is essential (and the moat)
A rule-based crawler cannot walk dynamic journeys, choose dates or options, or decide whether a line item is a mandatory fee, an optional extra or a tax. An LLM agent with vision does. The moat is a test corpus built from CMA decisions and a recurring regression schedule that proves compliance over time. An incumbent can't close it in a month only if none is already pointed at this; unconfirmed.

## Rough build plan and Azure cost
Playwright agent with an LLM planner, a rules layer for CMA209 patterns, a journey recorder (screenshots with timestamps), a weekly scheduler and a report. Estimated Azure cost £40 to £120 a month at pilot scale (container jobs plus model calls); estimate, no quote taken.

## Risks, and what would prove this wrong
- Legal-advice line: output must be framed as an evidence and testing tool, with a human sign-off, not a legal opinion.
- Pay: no published price for the job; Upfront's price (if live) is $9.99.
- Many penalised firms are large and use law firms; the mid-market may do nothing until enforcement hits its sector.
- Wrong if a CRO or QA vendor already ships "price-at-each-step" checks, or if the Upfront team has a full-journey product.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-24 T-42 scout round 7: written as G0. Most facts come from search summaries; only the Lewis Silkin Nov 2026 note and the Upfront page were fetched.
