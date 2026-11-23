# Skip hire phone booking desk

- slug: skip-hire-phone-booking-desk
- stage: G0
- market and segment: UK independent skip hire and muck-away firms (roughly 5 to 30 staff, 5 to 40 lorries) that take most orders by phone and run legacy desktop skip or weighbridge software
- one-line pitch: An AI voice agent that takes skip bookings by phone (size, waste type, permit need, delivery slot), refuses or flags prohibited waste, and writes a draft booking into the firm's own skip system for a human to confirm.

## Problem and who has it

Skip firms sell by phone: customers ring, ask what size, whether it needs a road permit, what can go in, and when it can come. The office admin keys each booking into software that is often an on-premise system with a weighbridge module. Calls arrive while the admin is on another call, and the work is a mix of pricing rules, permit rules and waste-type rules, which generic AI receptionists do not know. From October 2027 waste carriers must also record waste movements digitally (see Evidence), so booking data (waste type, EWC code, quantity) will matter more.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.simplyhired.co.uk/job/Ay16rAIIxKZ36VgtssW3GppWyTo7aka4rOFzE0m2wptKRLJLnHnZ1w | 2026-11-23 | Bolton skip firm advertising Office Administrator / Customer Service Coordinator whose duties include taking skip hire bookings and scheduling deliveries and collections. Pay "competitive", no figure. Job-ad signal for manual work. |
| https://apply.workable.com/biffa/jobs/view/BC6BC9A0BA.md | 2026-11-23 | Biffa Customer Service Administrator, Alton, £24,180 to £26,227 (as reported by search summary; open the page to confirm). Staff-cost signal. |
| North London waste firm Customer Service Administrator ad, £28,000 to £30,000, advising on skip sizes, pricing, availability (seen in a search summary; exact URL not captured, re-find before G1) | 2026-11-23 | Staff-cost signal for the same job. Unverified URL. |
| https://www.theaccessgroup.com/en-gb/waste-management/software/skip-hire-management/ | 2026-11-23 | Access Weighsoft skip page: online quote and order via a customer portal, a Reconomy API, "request pricing". Mentions self-service "frees the phones up". No phone, voice or WhatsApp booking feature on the page. |
| https://sagnikbhattacharya.com/blog/skip-hire-software-buying-checklist | 2026-11-23 | One blog (dated 29 Oct 2026 per search summary) says that of five skip software vendors it read, none advertises skip-specific AI. Single author, weak evidence. |
| https://creativepool.com/brant-mcnaughton/projects/skip-hire-made-simple-and-always-open-for-pinden | 2026-11-23 | Case study: Pinden's booking platform feeds its Weighsoft system so bookings go in without manual entry, which shows the integration route exists but was a custom build. |
| https://environmentagency.blog.gov.uk/2026/04/30/digital-waste-tracking-goes-live-a-major-step-forward-in-stopping-waste-crime/ and https://www.clydeco.com/en/insights/2026/08/on-the-horizon-digital-waste-tracking-becomes-mand | 2026-11-23 | Digital waste tracking: receiving sites mandatory 1 Oct 2026; carriers, brokers and dealers public beta from spring 2027 and mandatory from October 2027 (sources differ slightly; confirm on gov.uk). Forcing function for cleaner structured booking data. |

Pain signals so far: (1) job ads for people whose job is taking bookings; (2) Access's own "frees the phones" framing; (3) digital waste tracking raising the data bar. None measures missed calls. This is thin; G1 needs a missed-call or lost-job figure.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Fasthosts AI Receptionist (https://www.fasthosts.co.uk/spark/ai-receptionist, accessed 2026-11-23) | £39 Lite (30 calls, then £0.49), £69 Plus (100 calls, then £0.39), £99 Unlimited. Calendar booking on Plus and up. CRM and API integrations on Unlimited only; Make or n8n linkable. | Generic. Books into a calendar, not into a skip system. No skip pricing, permit or waste-type rules. |
| Access Weighsoft skip hire (page above) | Not published, "request pricing" | Online portal only; no voice or WhatsApp on the page. Incumbent can add a phone agent but would need to build it per customer set-up. |
| SKIPM8, Skip Tracker (https://www.skiptracker.co.uk), Routeware (https://uk.routeware.com/skip-hire-software) | Not captured | Not checked on their own pages for AI or phone features. Must check before G1. |
| Human booking clerk | £24k to £30k a year per the ads above | The cost being replaced or relieved. |

Gap claimed: a phone agent that knows skip rules and writes into a specific legacy booking system. Surviving evidence is only that Access's page shows no phone agent; absence on a marketing page is not proof that it is not on a roadmap.

## Why AI is essential (and the moat)

The call is open-ended speech that must be turned into structured rules (size to price, permit yes or no, prohibited waste, slot). The moat is the per-firm rule pack plus the adapter into the firm's booking system. It is deployment work (data engineering on the legacy system), not a model advantage. A human confirms each draft booking, so the firm carries the liability for waste-type decisions, not the studio.

## Rough build plan and Azure cost

- Voice layer behind an adapter: mock mode uses recorded or typed transcripts; live mode needs telephony (SIP or Twilio-style number) and a speech provider. Both are paid and need approval.
- Rules engine (skip sizes, prices, permit by postcode and council, prohibited items) as configuration per firm.
- Booking adapter: first target is a CSV or database drop that a human imports; second is the Weighsoft or Skip Tracker route if a test route exists (to check).
- Review queue web page (draft bookings, confirm, edit).
- Azure: App Service B1 or Container Apps scale-to-zero plus Postgres Flexible burstable, estimated under £25 a month in demo; voice minutes are extra and not in the Azure budget.
- Demo with synthetic data: invented skip firm, price list, council permit table from public council pages, and 30 scripted call transcripts. Value shown as booking accuracy and time per booking against a typed baseline.

## Risks, and what would prove this wrong

- Voice and call recording are in the rubric's risk list (voice data). Mitigate: transcript only, no biometric use, call-recording notice.
- Skip firms may already have an incumbent phone add-on that we have not found (SKIPM8, Routeware unchecked).
- Willingness to pay unknown: £39 to £99 generic agents set a low price anchor.
- Wrong if: three or more incumbents show phone or voice booking on their own pages; or firms report that bookings arrive mostly online or by WhatsApp; or no test route into any skip system exists.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| pending | pending | pending | pending | pending | pending | pending | pending |

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half, channel and closed-system thesis).
