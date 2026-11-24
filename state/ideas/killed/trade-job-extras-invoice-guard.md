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
| 9 | 4 | 6 | 6 | 9 | 4 | 8 | **46** |

### Validator checks (T-47, 2026-11-24, all accessed 2026-11-24)
| Check | Source | Finding |
|---|---|---|
| ServiceM8 release notes (fetched, first 100k of 113k characters) | https://servicem8.com/updates | No "extras", "variation" or missed-charge entry. But the system already: drafts invoice items from the job card with AI (Auto Quote and Invoice, Oct 2023 and Sep 2024); has reply suggestions on emails and SMS; adds billable items by voice; and has an Office Agent (Sep 2025, extended Sep 2026) that discusses a job and prepares actions, with MCP connections for ChatGPT and Claude |
| Search for the feature in ServiceM8, Fergus and Tradify | web search | Not shipped by any of the three. Enterprise DNA sells custom "scope-change detector" agents over notes, voice, photos and messages, so the pattern is commodity consulting work |
| Cheapest substitute | reasoning | Paste the WhatsApp export and the quote into ChatGPT and ask "what did we agree that isn't on the quote?". ServiceM8's MCP connector already lets Claude or ChatGPT read the job. No product moat over a prompt |
| Pay | scout's sources plus search | No price for unbilled-extras recovery. The leakage figures are vendor claims. Variation Tracker (Capterra) shows some paid demand for capture, but its price was not found |
| Channel | scout file | WhatsApp threads are outside the system. Live capture needs manual forwarding (a behaviour change, no evidence) or the paid WhatsApp Business API (needs approval) |
| Off-limits check | CLAUDE.md section 5 | Not off-limits. A variation note is a commercial document |

### Score reasons
- Pain 9: real (extras given away), but shown only by a newsletter, a consultancy and a capture app. No reviews or forum threads were counted.
- Pay 4: no public price for the job.
- AI 6: reading informal chat is a genuine LLM task, but copyable in a week and matched by a general chatbot.
- Reach 6: plenty of trades firms, with ServiceM8 and Tradify add-on stores and trade groups.
- Build 9: the demo is easy on synthetic data, but the live input depends on forwarding or a paid API.
- Competition 4: no direct product, but every system vendor ships AI invoice drafting and agents over the job, and ServiceM8's MCP opens it to general assistants.
- Risk 8: business messages with customers' names and addresses; low regulatory risk.

## Verdict: KILL (first attempt, ceiling about 55)
Nobody ships "extras from WhatsApp" yet, but the gap is a prompt, not a product. The job system vendors already read the job card and draft invoice items with AI (ServiceM8 since 2023), run office agents over jobs (ServiceM8 Office Agent, Fergus AI, simPRO Lightning), and ServiceM8 exposes jobs to ChatGPT and Claude through MCP. The one thing outside their view, the WhatsApp thread, can only be captured by a behaviour change or the paid Business API, and a tradesperson can paste the same thread into a free chatbot. There is no price for the job.

**Lessons:** when the only gap is a channel the system can't see, the cheapest substitute is the user pasting that channel into a general assistant. Score the idea against that, and against the vendor's MCP or agent connectors, not only against the vendor's features.

**What would revive it:** evidence that trades firms already route customer WhatsApp through a shared business inbox that has an API (so capture needs no behaviour change), plus a published price or a measured recovered-revenue figure from a pilot.

## Gate log
- 2026-11-24 round 10 scout (T-47): written at G0 with low confidence. Scores left for the validator. Suggest killing quickly if ServiceM8 or Fergus already reads message threads.
- 2026-11-24 validator (T-47): 46/100, KILL. Vendors already draft invoice items from the job with AI and expose jobs to general assistants (ServiceM8 MCP); the only gap is a WhatsApp paste a chatbot handles; no price. Move to `state/ideas/killed/`.
