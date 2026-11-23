# Wedding venue enquiry agent

- slug: wedding-venue-enquiry-agent
- stage: G0
- market and segment: UK independent wedding venues (barns, country houses, small hotels with one to three events staff), England first
- one-line pitch: An answering agent trained on the venue's own packages, prices, availability rules and FAQs. It replies to every couple's enquiry within a minute, day or night, on web chat, email and WhatsApp, then books the show-round and hands a qualified lead to the coordinator.

## Problem and who has it

A UK wedding is a high-value, one-off purchase. Bridebook puts average venue hire at £6,040, excluding catering, and the average wedding at £20,604 (2026 report). Couples contact several venues and move fast: Savills reports that 4 in 5 couples book within a month of first contact. Enquiries pile up in the evenings and at weekends, when the one or two coordinators at a small venue are running weddings or are off shift. Slow or missed replies send couples to the next venue. A coordinator costs a venue roughly £19k to £32k a year, and much of that time goes on answering the same questions about price, capacity, dates, corkage and accommodation.

The RAG angle: most enquiry questions can be answered from documents the venue already has (brochure, price list, T&Cs, supplier list, availability calendar). A generic chatbot gets these wrong. A grounded agent that refuses to guess and hands over to a human when unsure does not.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.savills.co.uk/research_articles/229130/390561-0 | 2026-11-23 | UK research. 4 in 5 couples book within a month of first contact, and 72% of couples won't contact a venue unless pricing is clear online. 40% of bookings fell in May to August. Speed matters, and couples want price answers up front. |
| https://www.mumsnet.com/talk/wedding/5412472-venue-taking-forever-to-respond-is-this-normal | 2026-11-23 | UK couple's thread. Emails to a booked venue went unanswered for two weeks, and a promised booking form never arrived. The venue later blamed its email system and a coordinator change. Pain on the buyer's side, from a UK forum. |
| https://www.realweddings.com.au/rw/blog/after-hours-problem-when-couples-actually-enquire-and-why-it-changes-everything/ | 2026-11-23 | Australian wedding platform. It estimates that 40 to 50% of weekly venue enquiries arrive outside the window where a 9-to-5 team can reply within an hour, and that Sunday evening is the highest-intent window. This is the platform's own observation, with no sample size given. Not UK. |
| https://www.weddingwire.com/wedding-forums/venues-not-returning-email-quote-request/889e573868aa5d69.html | 2026-11-23 | US couples' forum, one of many similar threads found in search: venues not returning quote requests. Not UK; shows the pattern is common. |
| https://www.venuescanner.com/blog/speed-is-the-new-sales-strategy-why-venues-are-losing-leads-in-the-first-few-hours | 2026-11-23 | UK venue marketplace. It says from its own platform that venues replying within 4 to 6 hours outperform slower ones. Other figures on the page (for example "up to 78% choose the first venue that responds") have no named source, so they are not relied on here. |
| https://partners.bridebook.com/uk/pricing/venues | 2026-11-23 | The UK's largest wedding directory sells paid VenuePro tiers with enquiry response templates, auto follow-ups and "Lost Leads Insights". Venues already pay for faster enquiry handling. Prices are not public. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Hyperleap AI wedding-venue chatbot (https://hyperleap.ai/agents/wedding-venues, accessed 2026-11-23) | Plus $40/mo (3,000 AI responses), Pro $100/mo, Max $200/mo; 7-day trial | Generic chatbot builder priced in USD. Tour booking and human handoff only on Pro and up. No evidence of UK venue workflow (wedding fairs, licensing, exclusive-use rules) or email-inbox answering. |
| In-house wedding coordinator, UK. Payscale (https://www.payscale.com/research/UK/Job=Wedding_Coordinator/Salary/dfe9686a/Sales, accessed 2026-11-23): average £19,215 base, but only 14 profiles, last updated Jan 2023. UK job ads found via search (https://uk.indeed.com/Wedding-Coordinator-jobs, accessed 2026-11-23) mostly show about £26k to £32k. The individual ads were not fetched. | about £19k to £32k a year plus on-costs | Works office hours. Cannot reply at 9pm on a Sunday during a wedding. |
| Bridebook VenuePro (https://partners.bridebook.com/uk/pricing/venues, accessed 2026-11-23) | Not published (quote only) | Templates and scheduled follow-ups, but no AI answers. Only covers enquiries that come through Bridebook. |
| Mikla, VenueAI, Breezit (US venue AI tools). Prices from a search summary only, not verified on vendor pages: Mikla from $149/mo, Breezit from $199/mo. | unverified | US-focused. Listed so the validator can check them. |

## Why AI is essential (and the moat)

- Answers have to come from the venue's own documents (packages, seasonal price bands, minimum numbers, corkage, curfew, accommodation). This is retrieval with citations, and the agent should decline when the documents don't cover the question.
- The agent understands free-text enquiries ("about 90 guests, a Friday in September 2027, dogs allowed?"), checks them against availability rules and produces a structured lead for the coordinator.
- It writes follow-ups in the venue's own tone.
- Moat (moderate): a UK wedding-specific evaluation set (common questions, trap questions about prices and dates), connectors for UK venue tools, and email-inbox answering, not only web chat. These are not hard to copy. The defensible part is grounding quality plus workflow fit for venues that do not want another dashboard.

## Rough build plan and Azure cost

- Week 1: ingest venue PDFs and web pages into a search index. Web chat widget, plus email reply drafting (with an IMAP or Microsoft Graph mailbox adapter). Grounded answers with citations and a "hand to human" fallback.
- Week 2: availability rules (from a simple calendar or iCal), lead capture form, show-round booking link, coordinator digest email.
- Week 3: WhatsApp adapter behind a mock mode (paid, needs approval). Evaluation set of about 100 venue questions, admin page to upload documents.
- Week 4: hardening, GDPR (consent notice, retention, deletion), demo venue built from a fictional brochure.
- Azure (estimate, not a quote): Container Apps scale-to-zero (about $0 to $5/mo at demo volume), Azure OpenAI pay-as-you-go small model for chat plus embeddings (about $2 to $8/mo for a demo), Azure AI Search free tier or pgvector in a small Postgres (about $0 to $15/mo). Projected total about $5 to $20/mo. Method: demo traffic of fewer than 2,000 messages a month at small-model token prices. Check against BUDGET.md before building.
- Phone answering is deliberately out of MVP scope: it needs paid telephony and brings voice-data risk.

## Risks, and what would prove this wrong

- Competition is cheap: Hyperleap at $40/mo sets a low price anchor, and Bridebook could add AI to VenuePro.
- A wrong price or a wrong "date available" answer creates a disputed-booking risk. The agent must never confirm a booking, only qualify the lead.
- Personal data (couples' names, contacts, dates) needs a UK GDPR-compliant design. Risk is moderate and not special-category.
- Several of the strongest numbers come from Australian or vendor sources. UK-specific data on after-hours enquiry share is missing.
- Proved wrong if: UK venue owners say most enquiries come by phone, not chat or email; or venues already reply within an hour using templates; or 10 venue websites checked show they already run chatbots that work.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
