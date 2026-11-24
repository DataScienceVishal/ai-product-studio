# DMCC checkout-journey auditor

- slug: dmcc-checkout-journey-auditor
- stage: killed (T-42 validator, 2026-11-24, 52)
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
Validator score, 2026-11-24 (T-42):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 13 | 4 | 9 | 6 | 10 | 2 | 8 | 52 |

**Verdict: KILL (first attempt; ceiling below 70).**

**Falsification findings** (all accessed 2026-11-24; "fetched" means the page itself was read)
- **Enforcement is real; the scout's figures hold on primary sources.**
  - AA/BSM: 15 April 2026, £4.2m after a 40% settlement discount from £7m, more than £760,000 refunded to over 80,000 customers, for a mandatory £3 booking fee left out of the upfront price. Since April 2025 the CMA "has launched investigations into 14 businesses", and it runs a free "Clear Pricing" campaign with "a practical 3-step checklist" (https://www.gov.uk/government/news/cma-orders-the-aa-and-bsm-driving-schools-to-refund-learner-drivers-over-drip-pricing, fetched).
  - StubHub: £889,200 fine, refunds of more than £590,000 to 51,350 customers (https://www.gov.uk/government/news/cma-orders-stubhub-uk-to-refund-customers-over-hidden-fees, search summary; matches Osborne Clarke, fetched). Marks Electrical: £720,000 for pre-selected paid extras (Osborne Clarke, fetched).
  - The "more than £12 million in fines" in the Lewis Silkin note is not reconciled with nshift's "£5.1m+" (search summary). Use the per-case gov.uk figures only.
- **The product already exists, at £14.99 a month.** Total Price (Total Price Ltd, Companies House 17292844) scans "the same path a customer takes, from browse to checkout" starting from the homepage, and checks booking and service fees, delivery costs, fake urgency timers, pre-ticked extras and subscription terms. Plans: Free (one check per site), £11.99 for 5 credits, Monitoring £14.99 a month with one automatic monthly check. It says it is "a compliance-checking tool, not a law firm or a substitute for legal advice" (https://totalprice.co.uk/, fetched). Its one stated limit: checkouts behind a login, where it "flags what it can see and tells you what to check yourself".
- **Free and cheap rivals too.** TrustYourWebsite runs a free DMCCA scan for drip pricing, manufactured urgency and cancel parity "in under a minute" (https://trustyourwebsite.com/uk/en/guides/dmcca-dark-patterns-uk-cma, fetched; paid prices not shown, multi-step walking not stated). AuditSocials sells an "AI Compliance Audit" of landing and checkout pricing (search summary). Law firms give away checklists (Muckle drip-pricing checklist, search result) and advise "test journeys" (CMS, search summary).
- **The regulator does it itself.** The CMA "has deployed agentic AI" that captures "the consumer journey at scale", and the StubHub, Marks Electrical and Euro Car Parks cases came from it (https://www.osborneclarke.com/insights/cma-issues-first-fines-under-its-new-uk-direct-consumer-enforcement-powers, fetched, 8 July 2026). That proves the technique works, and that it is not hard to copy.
- **Cheapest substitute:** a product manager clicks through each journey after each release with the CMA's 3-step checklist (an hour), or adds one "total price unchanged at payment" assertion to the Playwright or Cypress suite the team already runs. Mid-sized sellers with dev teams already have the tooling.
- **Off-limits check: not legal advice as scoped.** It is testing and evidence; Total Price shows the framing works. No scraping red flag if it only walks sites the customer owns and authorises.

**Scores in brief**
- Pain 13: real fines (£4.2m, £889k, £720k), a 10%-of-turnover cap and active CMA sweeps. Not higher: per-case fines fall on large firms, refunds average £9 to £10 per customer, and mid-market sellers may simply fix one fee line.
- Pay 4: the only software price for this job is £11.99 to £14.99 a month (Total Price), with free scans beside it. No law-firm journey-review price was found.
- AI 9: an agent that picks dates and options and judges mandatory versus optional fees is real AI work, but the CMA and at least two vendors already ship it.
- Reach 6: online sellers are easy to list by sector; the partner's channel is unknown.
- Build 10: a robust agent across arbitrary bespoke journeys is harder than the synthetic-site demo suggests; flaky runs would be the support burden.
- Competition 2: Total Price matches the pitch, including monthly monitoring, at a price a two-person business can't undercut.
- Risk 8: own-site testing, no personal data; a residual liability if a "clean" report misses a fee.

**Reason (one paragraph).** The pitch, "an agent walks your checkout journey and flags hidden fees and urgency claims against CMA guidance, with monitoring", is already sold by Total Price at £14.99 a month with a free tier, offered free by TrustYourWebsite, and run by the CMA itself with agentic AI. The enforcement wave is real and confirmed on gov.uk, but it is equally visible to every vendor, and it has set the price anchor at the level of a cheap website scanner. The one gap left (journeys behind a login, multi-option bookings) is too narrow to lift Pay or Competition anywhere near 70. Best plausible re-score: Pain 14, Pay 7, AI 10, Reach 6, Build 10, Competition 4, Risk 8 = 59.

**Lessons**
- Public enforcement with named fines draws cheap single-purpose tools within months. Search "<regulation> checker / scan / check your website" as well as "<regulation> compliance software", and check Companies House for newly formed single-purpose firms.
- If the regulator's own enforcement uses the same AI technique, treat the AI score as capped: it shows feasibility, not a moat.
- For website-facing compliance, the price anchor is website scanners (£0 to £15 a month), not law-firm fees.

**What would revive it**
- Evidence that Total Price, TrustYourWebsite and similar tools miss authenticated or multi-option journeys (for example, a published comparison or their own documentation), plus a published price of at least £200 a month for authenticated journey testing in travel or leisure. Even then the ceiling is about 60.

## Gate log
- 2026-11-24 T-42 scout round 7: written as G0. Most facts come from search summaries; only the Lewis Silkin Nov 2026 note and the Upfront page were fetched.
- 2026-11-24 | validator | G0→G1 | KILL 52 | Total Price already walks the browse-to-checkout journey for hidden fees, urgency timers and pre-ticked extras, with monthly monitoring at £14.99 a month and a free tier; TrustYourWebsite scans free; the CMA runs agentic AI over consumer journeys itself. Fines confirmed on gov.uk (AA/BSM £4.2m, 15 Apr 2026). Ceiling about 59.
