# Trade job extras and variations guard (Tradify, Powered Now, Fergus add-on)

- slug: trade-job-extras-invoice-guard
- stage: G0 (lowest confidence of round 10)
- market and segment: UK small trade firms (electricians, plumbers, heating, builders, 2 to 15 staff) on job-management apps that have a public API or add-on store
- one-line pitch: Before an invoice goes out, reads the job's WhatsApp and email thread, notes and photos against the signed quote, lists extras and variations agreed but never billed, and drafts the variation note and the invoice line.

## Problem and who has it
Verbal extras are agreed on site and never written up. A UK builders' network piece makes the point that without a signed record a variation is "essentially a gift". A consultancy's estimate of leakage ($50,000 to $200,000 a year) is a vendor claim and is not used here.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://probuildersnetwork.substack.com/p/stop-giving-away-your-profit-the | 2026-11-24 | Pain signal 1: unrecorded variations are given away (search summary; not read) |
| https://enterprisedna.co/resources/guides/trades-stop-losing-unbilled-change-orders | 2026-11-24 | Pain signal 2: consultancy describes the problem and an agent that checks completed jobs against the change-order queue (vendor claim) |
| https://www.capterra.co.uk/software/1112297/Variation-Tracker | 2026-11-24 | Pain signal 3: a product exists because subcontractors lose extras; shows paid demand |
| https://sitemate.com/use-cases/daywork-sheet/ | 2026-11-24 | Daywork sheet app with voice logging and photos: substitute that captures work as it happens |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| ServiceM8 billable-item suggestions from notes, supplier invoices and tracked time (https://servicem8.com/updates) | Included in app; plan price not checked | The closest incumbent. Reviews notes and time, but one search found no reading of chat threads or photos |
| Fergus AI (launched 13 Sept 2026 per https://completeaitraining.com/news/fergus-launches-ai-first-job-management-for-tradespeople/) | Included at no extra cost for now | Voice quotes and "why is this job losing money"; extras not shown |
| Tradify SmartRead and SmartWrite (Plus plan, about $61 a user per one blog) | see left | Reads supplier invoices and helps wording; no extras detection found |
| simPRO Lightning agents (announced 15 May 2026) | Not checked | Agent platform for larger firms |
| Variation Tracker, Dayworkbook, Sitemate | Not checked | Capture tools, not readers of existing messages |

## Why AI is essential (and the moat)
Reading informal chat, voice notes and photos for scope changes is judgement over unstructured text. The moat is weak: three system vendors are shipping AI quoting and invoicing in 2026, and ServiceM8 already reviews notes for billable items. The only gap is the messaging channel (WhatsApp, email) the system does not see.

## Rough build plan and Azure cost
Demo from synthetic quote, thread and photos. Data route: each system's API needs checking (ServiceM8 and Tradify have add-on or partner programmes; Fergus and simPRO have public APIs, not read). Capture of WhatsApp threads depends on the business forwarding them, or on the paid WhatsApp Business API (mock mode works for the demo, not live). Azure under £30 a month for a pilot (estimate).

## Risks, and what would prove this wrong
- Competition (main): vendors ship this in months. Kill test: search each vendor's release notes and help pages for "variations" or "extras".
- Reach and channel: forwarding threads is a behaviour change; the studio has no evidence tradespeople will do it.
- Pay: no public price for leaked revenue; only vendor claims.
- Legal: a variation draft is a commercial note, not legal advice, but contract terms vary.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-24 round 10 scout (T-47): written at G0 with low confidence. Scores left for the validator. Suggest killing quickly if ServiceM8 or Fergus already reads message threads.
