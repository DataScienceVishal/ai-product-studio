# Repair triage for letting agents

- slug: letting-agent-repair-triage
- stage: G0
- market and segment: UK (England first) independent letting and property-management agents managing roughly 100 to 1,500 rented homes, with 1 to 5 property managers handling tenant repair reports by email, phone, WhatsApp and portal.
- one-line pitch: Read every tenant repair message, photo and video, ask the follow-up questions, set urgency (flagging damp, mould, heating and electrical hazards), draft the contractor instruction and landlord approval request, and keep a timestamped log ready for Awaab's Law.

## Problem and who has it

Property managers spend much of their day receiving repair reports, working out how urgent they are, chasing tenants for photos and access, getting landlord approval and quotes, instructing contractors and chasing jobs to completion. Reports arrive through many channels, not just the agent's portal. Lettings is the largest category of complaints to Property Redress, and complaints rose 47% in 2025. The government is consulting (closing 18 December 2026) on applying Awaab's Law to private renting, which would impose deadlines for investigating and fixing serious hazards; around one in 10 private rented homes has a category 1 hazard. Agents will need evidence of what they knew and when.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/news/clampdown-on-dangerous-homes-to-protect-more-tenants-and-families (published 8 Oct 2026) | 2026-11-23 | Consultation on extending Awaab's Law to private renting closes 18 Dec 2026; cites England's 11 million private renters and around one in 10 private rented homes with a category 1 hazard; PRS start date not set. |
| https://blog.goodlord.co/awaabs-law-prs-consultation-2026?hs_amp=true (seen in search results, not fetched) and search summaries | 2026-11-23 | Reported proposal of 10 working days to investigate potential significant hazards in the PRS. Provisional and unverified; treat as a proposal only. |
| https://www.propertyreporter.co.uk/lettings-complaints-drive-sharp-rise-in-property-redress-enquiries.html (3 Mar 2026) | 2026-11-23 | Property Redress complaint enquiries rose to 4,220 in 2025 from 2,863 (up 47%); lettings is the largest category; property-management complaints centre on service quality and maintenance. |
| https://uk.trustpilot.com/review/www.fixflo.com?page=3 | 2026-11-23 | Tenant reviews (Sep 2024, Jan 2025) describe out-of-hours emergencies such as a boiler not handled until days later, and a phone-unfriendly single-line comment box; Fixflo replies that it is software and agents handle repairs. Shows the failure point is triage and follow-through, not report capture. |
| Search-result snippets of UK property manager job ads (Bracknell: "Receive and assess maintenance reports from tenants. Liaise with landlords, contractors and tenants to arrange access, quotations and repairs. Monitor outstanding maintenance and follow work through to completion"; SW London: "Coordinate maintenance and contractor work through Fixflo"). Original ads not fetched (closed or blocked). | 2026-11-23 | Indicative: repair triage and chasing are core paid staff duties. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Fixflo Lettings (https://www.fixflo.com/pricing/lettings) | Tiers "price on request", plus £75/month software fee; minimum 50 properties; contractor marketplace from £0.30/unit/month | Tenants must use its portal; messages arriving by email/WhatsApp still need manual triage. |
| Arthur Online property management (https://www.arthuronline.co.uk/pricing) | From £82.50/month (55 units), £96 (60), £126 (70), then £1.50 to £1.80 per extra unit, billed annually | General PMS; maintenance module is a workflow, not an AI triage layer. |
| Property manager salary (search-result figures: about £28,000 via Indeed, about £32,500 via Totaljobs; not fetched) | Indicative | The real cost: staff hours spent on triage and chasing. |

## Why AI is essential (and the moat)

Tenant reports are free text, voice notes, photos and videos in mixed quality and language. Deciding "is this a leak, mould, a dead boiler in winter, or a sparking socket?", asking the right follow-up question and spotting a potential category 1 hazard needs multimodal understanding, not a decision tree. AI also drafts the contractor brief and landlord approval request from the conversation.

Moat: an evaluation set of real (anonymised) repair cases labelled for urgency; per-agent contractor and landlord-approval rules; a hazard-evidence log built for the final Awaab's Law PRS rules; integrations with the agent's PMS.

## Rough build plan and Azure cost

1. Shared inbox intake (email first; WhatsApp later behind an adapter in mock mode, since WhatsApp Business is paid).
2. Classify issue, urgency and hazard flag from text and photos; ask tenant follow-ups.
3. Draft contractor instruction and landlord approval; manager approves with one click.
4. Timestamped case log and overdue alerts; CSV export to the PMS.

Azure (estimate, method: scale-to-zero container app, small database on free or lowest tier, blob storage for photos, pay-per-token Azure OpenAI with vision at demo volume): likely under $20 a month in build. Architect to confirm in `state/BUDGET.md`.

## Risks, and what would prove this wrong

- Personal data at scale: tenants' names, addresses, photos inside homes, and possibly health hints (for example "my child has asthma from the mould"). Needs UK GDPR design, minimisation and deletion; risk score should reflect this.
- Safety: misjudging an emergency (gas, electrics) could cause harm; the product must escalate conservatively and never tell tenants how to fix hazards.
- Awaab's Law PRS rules and dates are not final; the compliance angle could shift or be delayed to 2028 or later.
- Incumbents (Fixflo, PMS vendors) could add AI triage quickly.
- Proven wrong if: agents say most reports already come through Fixflo with enough detail, or triage takes them little time, or they won't add another tool on top of their PMS.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 12 | 12 | 6 | 8 | 10 | 1 | 4 | 53 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area. Repair triage is not legal advice, but the Awaab's Law angle must never be sold as compliance advice.
- WhatsApp and telephony are paid, so they sit behind adapters; email and a web form are free. Tenants report through the paid channels, and competitors already work there, so a demo using only the free channels will look weaker.
- Synthetic data can credibly demo the core flow: fictional tenant messages, openly licensed photos of leaks, mould and boilers, and a fictional contractor list. Urgency accuracy on real reports stays unproven.

**Falsification findings** (all accessed 2026-11-23)
- **The strongest competitor, Lettie, already sells almost the whole pitch** (https://asklettie.com/for-agencies):
  - intake by "WhatsApp or email, with photos, at any hour", with urgency "set on every report, urgent ones first";
  - contractors it "invites by trade, chases, books the visit", and landlord approval "by link, chased until answered";
  - "every step time-stamped, export as PDF", with imports from Street, Arthur, agentOS, Apex27 and Loop;
  - "Agency plans start from £40 a month". Its own example is 100 properties and 4 seats for £119.80 a month.
- **Fixflo already sells AI triage.** The scout says Fixflo "still needs manual triage", but its parent Aareon bought Help me Fix in Sept 2025, and Fixflo now sells that company's Aidenn assistant (https://www.fixflo.com/solutions/aidenn-ai-repairs-diagnosis, https://www.fixflo.com/blog/fixflo-bets-big-on-ai-with-acquisition-of-help-me-fix).
  - Aidenn analyses photos, works in "over 200 languages", runs video triage and dispatches emergencies automatically. It was built on "over 100,000 expert engineer calls".
  - Fixflo itself is priced on request, plus a £75/month software fee, with a minimum of 50 properties (https://www.fixflo.com/pricing/lettings).
- **More AI repair tools are aimed at UK agents.**
  - SortX puts an AI voice agent on the agency's own number, threads WhatsApp, takes email in, suggests urgency and offers jobs to contractors one by one (https://sortx.co.uk/).
  - Street.co.uk's AI Maintenance Triage takes tenant reports in any language and gives step-by-step advice first. Contractor quotes and landlord approval run in the same tool (https://street.co.uk/product/index/ai-maintenance-triage).
  - AskPorter's AI agents triage repairs, and it partnered with Checkatrade in 2026 (https://www.lettingagenttoday.co.uk/breaking-news/2026/05/repair-management-made-easier-through-new-collaboration/, search summary only).
- **The Awaab's Law timing is weak.**
  - gov.uk confirms the consultation (8 Oct 2026) closes on 18 Dec 2026. It sets no private-rented timescales or start date, and it mentions landlords only, not agents (https://www.gov.uk/government/news/clampdown-on-dangerous-homes-to-protect-more-tenants-and-families).
  - The NRLA says the consultation contains "no firm proposals" (https://www.nrla.org.uk/news/awaabs-law-consultation-launches). The scout's "10 working days" is unverified.
  - The compliance driver is at least a year away. Lettie's PDF audit trail already records what the agent knew and when.
- **The pain evidence checks out but is general.** Property Redress enquiries rose 47% to 4,220 in 2025. The complaints are about "service quality, maintenance and access to relevant documentation" (https://www.propertyreporter.co.uk/lettings-complaints-drive-sharp-rise-in-property-redress-enquiries.html). No figure isolates repair triage.
- **Risk.**
  - The product would hold tenants' names and addresses, photos inside their homes, and health or child details from damp and mould reports.
  - A missed emergency (gas, carbon monoxide, electrics) can hurt someone, so triage needs conservative escalation and a human sign-off design.
  - Out-of-hours support is hard for a two-person business.
- **Reach is good.** Every letting agent in England must belong to The Property Ombudsman or the Property Redress Scheme, and both offer public member checks (https://www.gov.uk/government/publications/lettings-agents-and-property-managers-redress-schemes, search summary only).

**What would change my mind (re-score on this evidence)**
1. A gap the AI triage vendors can't close quickly, shown on their own pages. For example, after the consultation response, a statutory evidence duty on agents that Lettie, Aidenn and SortX don't meet.
2. Public evidence that Lettie's or Aidenn's triage fails on real reports (reviews, complaints), with failures this product would avoid.
3. The final private-rented Awaab's Law timescales and start date, from the government response.

My estimate is that even with all three, the score tops out in the high 50s. The field is crowded, and personal data plus safety-critical triage keep the Risk score low.

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 53 | Lettie already sells WhatsApp and email repair triage with urgency, contractor chasing, landlord approval and a timestamped PDF audit trail from £40 a month, Fixflo owns the Aidenn AI repairs assistant, the Awaab's Law driver has no private-rented timescale or start date yet, and tenant data plus emergency triage pull the risk score down.
