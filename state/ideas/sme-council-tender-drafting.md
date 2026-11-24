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
| 12 | 14 | 6 | 8 | 12 | 1 | 7 | 60 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area. Bid drafting is not legal advice.
- Public data can credibly demo it. Council tender packs are published under the Open Government Licence through the official Contracts Finder and Find a Tender OCDS APIs (https://www.find-tender.service.gov.uk/Developer/Documentation, https://www.contractsfinder.service.gov.uk/apidocumentation, search summary only). A fictional cleaning firm's policies and case studies can stand in for the answer library.
- Don't log in to supplier portals such as ProContract or In-Tend to pull packs. That needs accounts (ask first) and may breach the portals' terms.

**Falsification findings** (all accessed 2026-11-23)
- **The scout's suggested niche is already taken.** CleanTender is "For UK soft FM firms: cleaning, security, grounds, waste, catering", at "£99 a month, or £990 a year" (https://cleantender.co.uk/). It offers:
  - AI scans of the contract pack that score fit from 0 to 100, plus a bid or no-bid verdict;
  - a "Selection Questionnaire response generated against your profile";
  - a one-click claim check on every answer, and a compliance vault.
- **SME-focused general tools:**
  - BidWriter (WinAContract) has "word limit & marks-aware responses", a bid library and a response evaluator, aimed at "SMEs and sole traders". Plans are free, £49, £149, £279 and £799 a month (https://bid.winacontract.co.uk/).
  - 2026 comparisons also list AI Tender Writer, TenderDraft (from £49) and SwiftBid at £149 to £749 per bid (https://bid.winacontract.co.uk/blog/best-ai-bid-writing-software-uk-2026, search summary only).
  - Stotles has a free Bid Studio tier and writes AI drafts from "past wins, case studies, and tender documents" (https://www.stotles.com/platform/win-bids, search summary only).
  - AutogenAI and Thornton & Lowe cover the top end.
- **The cheapest substitute** is Copilot or ChatGPT plus a Word library of past answers.
- **The pain evidence checks out but is thin.** The FSB's 35% and one-in-20 figures appear in the SME Web article, which gives no sample size (https://www.smeweb.com/?p=21289). The techUK survey covered 100 tech firms in 2023, not service SMEs.
- **Regulatory trap: hallucinated content can get a client excluded.**
  - Under Procurement Act 2023 Schedule 7 para 13, "providing information that is incomplete, inaccurate or misleading" is an example of acting improperly, which is a discretionary exclusion ground (https://www.legislation.gov.uk/ukpga/2023/54/schedule/7/paragraph/13). An invented case study or statistic could trigger it.
  - PPN 017 says suppliers' AI use "is not prohibited", but suggests buyers ask suppliers to disclose it and confirm they checked it. It formally covers central government; other authorities "may wish to apply" it (https://www.gov.uk/government/publications/ppn-017-improving-transparency-of-ai-use-in-procurement/ppn-017-improving-transparency-of-ai-use-in-procurement-html).
  - Drafts must cite only the firm's own evidence, and a human must sign off every bid.
- **Reach is good and clean.** Contracts Finder award notices are public, company-level data under the OGL. Firms that have won council work can be listed by sector and region without scraping.

**What would change my mind (re-score on this evidence)**
1. A segment these tools don't serve, shown on their own pages and sized from Contracts Finder data. For example, a sector with a mandatory accreditation or framework re-application cycle that none of them handle.
2. Public evidence (reviews, forum complaints) that SMEs are unhappy with the existing AI bid tools, in ways a citation-first product would fix.
3. Data on how many bids a typical 10 to 150-staff service SME submits a year, showing that a subscription beats per-bid tools.

My estimate is that even with all three, the score tops out in the mid 60s, because Competition can't rise far against this many priced tools.

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 60 | Small firms clearly pay to bid, but the scout's proposed niche is taken: CleanTender already sells AI questionnaire drafts, compliance scoring and claim checks to cleaning, security, grounds, waste and catering firms for £99 a month, alongside SME tools such as BidWriter from £49 and Stotles' free tier.

### Re-score 2026-11-24 (T-57, Q-10 wedge rule)
Validator. Only the Competition row is re-scored, under the wedge rule in `playbooks/pipeline.md`. This is not a new G1 attempt.
- **Competition: 1 → 1.** No wedge is named and evidenced. The incumbent the buyer would otherwise pay sells the same job to the same segment at a similar or lower price.
  - CleanTender sells AI pack scanning, SQ drafting and claim checks to soft FM firms (cleaning, security, grounds, waste, catering) at £99 a month (https://cleantender.co.uk/, validator read).
  - BidWriter has a free tier and plans up to £799 a month for "SMEs and sole traders".
  - Stotles has a free Bid Studio. SwiftBid sells per bid.
  - Round 11 (T-48) tested the segment, adviser-resale and cheaper-tier wedges and found none. No sector excluded by these tools was found, and Contracts Finder sizing was not done.
  - The "citation-first, no invented claims" idea (relevant to Procurement Act Sch. 7 para 13) is not evidenced as a gap: CleanTender already sells a one-click claim check.
- **Knock-on:** none. Pain 12, Pay 14, AI 6, Reach 8, Build 12 and Risk 7 are unchanged.
- **New total: 60 (unchanged). Verdict: REVISE (parked, kill candidate).** No red flag. Below the 63 proof-test floor, and the validator's ceiling stays in the mid 60s. A second failed attempt kills it.
- **The one piece of evidence that would move it:** a tender segment that CleanTender, BidWriter and Stotles don't serve, shown on their own pages and sized from the Contracts Finder OCDS API. For example, a sector with a mandatory accreditation or framework re-application cycle. That could take Competition to 5, which is still about 64.
