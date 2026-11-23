# Council tender drafting for service SMEs

- slug: sme-council-tender-drafting
- stage: G0
- market and segment: UK service SMEs with roughly 10 to 150 staff and no in-house bid team (for example commercial cleaning, security, grounds maintenance, facilities and training providers) bidding for local-authority and NHS-estate contracts under the Procurement Act 2023.
- one-line pitch: Read the tender pack, pull out every question, word limit and scoring criterion, and draft compliant answers (method statements, social value, case studies) from the firm's own past bids and policies, so a manager edits instead of starting from a blank page.

## Problem and who has it

Small firms repeat the same work for every bid: the same company information, policies, case studies and social value commitments, rewritten to new questions and word limits. The FSB reports that 35% of small firms "repeatedly waste time submitting the same information for each new bid", and only one in 20 gets useful feedback when they lose. techUK members call social value an administrative burden. Government wants more spend with SMEs (Cabinet Office target 30% by 2027/28, against about 19% to 22% recently) and has committed to making tenders less time-consuming. Firms that can afford it hire freelance bid writers at a median £500 a day.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.smeweb.com/?p=21289 (SME Web, 15 Dec 2025, covering an FSB report) | 2026-11-23 | 35% of small firms "repeatedly waste time submitting the same information for each new bid"; only one in 20 bidding firms get "comprehensive and actionable feedback". Sample size not stated. |
| https://www.techuk.org/insights/guest-insights/what-are-the-barriers-for-smes-when-bidding-for-government-contracts (5 May 2023, techUK GovTech SME survey of 100 members) | 2026-11-23 | 76% said addressing social value in contracts is an administrative burden; 52.6% said there are too many frameworks, each needing a separate onerous application. |
| https://www.gov.uk/government/publications/cabinet-office-and-hm-treasury-small-and-medium-sized-enterprise-sme-action-plan-2025-to-2028--2/cabinet-office-and-hm-treasury-small-and-medium-sized-enterprise-sme-action-plan-2025-to-2028-html | 2026-11-23 | Commitment to make tenders "less time-consuming for SMEs"; an SME case study cites "limited bid resources and capacity"; Cabinet Office SME spend 19.2% (2025/26, CO only) against a 30% target by 2027/28. |
| https://www.itjobswatch.co.uk/contracts/uk/bid%20writer.do | 2026-11-23 | Median UK Bid Writer contract rate £500/day, based on vacancies in the 6 months to 23 Nov 2026 (IT-tagged job board, so skewed). |
| https://www.enterprisenation.com/learn-something/new-report-procurement-act-first-six-months/ (5 Mar 2026) | 2026-11-23 | New Procurement Act procedures can add steps (meetings, second rounds, site visits) that change how firms plan bid time and cost. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Freelance bid writer (ITJobsWatch above) | Median £500/day | Too expensive for frequent small council bids. |
| Thornton & Lowe Bid Software, Tender Library (G-Cloud 15 pricing document, https://assets.applytosupply.digitalmarketplace.service.gov.uk/g-cloud-15/documents/722937/235634672648809-pricing-document-2026-01-29-1655.pdf) | £2,750+VAT/yr for 1 user; £4,900 for 2 to 3; £6,500 for 4 to 5; Tender Pipeline Premium £300+VAT/yr | Built "for bid professionals"; assumes a bid team. |
| AI bid tools listed on Capterra/G2 (BidWriter £49 to £549/month; Tenderforge £15.99 to £99.99/month; WinAContract from £39). Seen in search results; listing pages returned 403, so unverified. | £16 to £549/month (unverified) | Crowded and cheap; generic across sectors. Gap to test: sector-specific answer libraries (cleaning, security) and compliance checking against the tender's scoring criteria. |

## Why AI is essential (and the moat)

Each tender pack is a long, differently structured set of PDFs and Word files. The work is extracting questions, word limits, mandatory pass/fail items and scoring criteria, then writing tailored answers from the firm's own evidence. That is long-document understanding and grounded drafting; templates can't do it.

Moat (weak today, must be built): a sector-specific evaluation set (how well drafts score against published criteria), per-firm answer library that improves with every bid, and a compliance checker (every question answered, within limits, mandatory documents attached). Without a sector focus this is a commodity.

## Rough build plan and Azure cost

1. Upload tender pack; extract question list, limits, criteria and deadlines into a checklist.
2. Upload past bids and policies to build the firm's answer library.
3. Draft answers with citations to the firm's own evidence; flag gaps the firm must fill (no invented case studies or figures).
4. Compliance check and export to the buyer's format (Word).

Azure (estimate, method: scale-to-zero container app, small database, blob storage, pay-per-token Azure OpenAI; tender packs are long so token use per bid is higher): likely under $20 a month at demo volume. Architect to confirm in `state/BUDGET.md`.

## Risks, and what would prove this wrong

- Crowded market with cheap AI tools; competition score will be low unless the sector niche proves real.
- Hallucinated claims in a bid could breach tender rules; drafts must cite only the firm's own evidence.
- Buyers may restrict or ask about AI-written bids; check current guidance at G1.
- Proven wrong if: target firms already use a £20 to £50/month AI tool and are happy, or bid volume per firm is too low (a few bids a year) to justify a subscription.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
