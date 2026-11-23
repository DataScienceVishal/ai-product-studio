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

## Gate log
- 2026-11-23: G0 spotted by scout.
