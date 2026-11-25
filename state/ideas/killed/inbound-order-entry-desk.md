# Inbound order entry desk for UK SME distributors and merchants

- slug: inbound-order-entry-desk
- stage: KILLED (T-79 validator, 2026-11-25; second G1 failure for both predecessors)
- market and segment: UK wholesale distributors and independent builders' merchants (10 to 100 staff, 1 to 10 branches) running Sage 50, Sage 200, or a merchant ERP (BisTrack, Merlin, Kerridge/Klipboard), whose trade customers send orders as email text, PDF or spreadsheet, WhatsApp text or photo of a list, or voicemail.
- one-line pitch: Turn any inbound order into a draft sales order with matched product codes, price and stock flags, for a clerk to confirm in one click, then export it in the file format the customer's system imports.
- merged from: merchant-whatsapp-order-desk (56) and wholesale-email-order-entry-sage (55), T-79(a), 2026-11-25. Same engine on different channels.

## Problem and who has it

A clerk reads each message, decodes the customer's own codes or shorthand ("4x 2.4 PAR 4x2", "same as last week"), checks price and stock and keys a sales order. Email/PDF is the bulk channel in distribution; WhatsApp and photos are the merchant counter's channel. The ERP sits behind the channel, so generic chat or OCR tools stop short of an order the system can use.

## Evidence

Page-verified = I opened the page with WebFetch on 2026-11-25 and the text below is what the page returned. Search-only = seen in a search summary, page not opened or blocked.

| Source (URL) | Accessed | What it shows | Page-verified |
|---|---|---|---|
| https://www.spotdev.co.uk/blog/ai-order-entry-for-distributors | 2026-11-25 | UK builders' merchant agent replaced a planned offshore hire "budgeted at over £20,000 a year". Sources: ERP/trade-counter system, CRM, shared mailbox. Author states no measured time saving, no orders per day, no build price. Vendor blog. | Yes |
| https://zestcode.co.uk/services/sage-200-order-automation/ | 2026-11-25 | UK service (Northamptonshire) reads emailed POs, PDF, CSV/Excel, Word, order-in-body for Sage 200 Standard (API) and Professional (data service). Fixed quote within 2 working days, no price, no numbers, no Sage 50 mentioned. | Yes |
| https://www.airdev.co/erp/bistrack | 2026-11-25 | Consultancy page: BisTrack has eBusiness file import, EDI, and a separately licensed API; customer-order OCR is template-based only; no Epicor AI agent announced for BisTrack; API docs "sparse". Consultancy marketing. | Yes |
| https://www.posttrans.co.uk/sage-line-50-import-sales-invoice-order | 2026-11-25 | Sage 50 sales orders import from Excel/CSV/fixed-length file; trial on Sage demo company; monthly subscription for live company; price on separate page; no AI/PDF mentioned. | Yes |
| https://developer.sage.com/200/api/get-started and /guides/api_faq | 2026-11-25 | Direct fetch returned 403. Search summary: UK Sage 200 API by developer registration and subscription keys; FAQ says developing against it needs no Developer Programme membership; no hosted sandbox, you run your own test Sage 200; sales orders under /sop_orders; one community thread reports 403 on sop_orders. | No (search-only) |
| https://developer-community.sage.com/topic/495-api-for-sage-50/ (and search summary) | 2026-11-25 | Sage 50 UK has no REST API; route is Sage Data Objects (COM) via paid developer programme; a 2022 thread quoted £2,500+VAT a year. | No (search-only, old) |
| https://www.questemployment.co.uk/job/sales-and-purchase-order-clerk-orderclk | 2026-11-25 | Search summary: Didcot order clerk £25,000, "action orders received by email", Sage 50 essential. Page now returns 404 (closed). | No |
| Reed job via Gumtree https://www.gumtree.com/p/sales-customer-service-jobs/sales-order-processor/5418649912 | 2026-11-25 | Search summary: Braintree Sales Order Processor £28,000 to £30,000, Sage 50. Not opened. | No |
| https://uk.indeed.com/career/order-processor/salaries | 2026-11-25 | Search summary: average £27,049, 797 salaries, updated July 2026. Page returned 403. | No |
| https://www.payscale.com/research/UK/Job=Order_Processor%2FSales_Coordinator/Salary | 2026-11-25 | Search summary: £20,317 average, 90th percentile £28k. Not opened this run (earlier file says last updated Jan 2021 on the page). | No |
| https://www.klipboard.com/en-za/solutions/ai-solutions and https://www.klipboard.com/news/klipboard-brings-practical-embedded-ai-into-erp-one | 2026-11-25 | ERP One: 10 agents / 35 capabilities incl. sales orders; plain-language actions such as creating sales orders and draft invoices; video titled "Order creation". Neither page mentions reading email, PDF, WhatsApp or photo orders, nor BisTrack or Merlin. Price not given. | Yes |
| https://www.salesape.ai | 2026-11-25 | No price (tailored); says "about 90% cheaper than hiring"; targets 20 to 100 staff; channels incl. WhatsApp, SMS, email; integrations HubSpot, Salesforce, Zoho, Zapier, "100+ other tools", custom CRMs; no sales orders or ERP named. /pricing is a 404. | Yes |
| https://www.sage.com/en-gb/sage-copilot/ and search of Sage newsroom | 2026-11-25 | Page 403. Search: Copilot in Sage Operations (Jan 2026, German early access creates records after approval), Sage X3 agents, Sage 50 Copilot rolling to early adopters. No source shows AI sales-order capture from email/PDF in Sage 50 or Sage 200. Absence in a search, not proof. | No (search-only) |
| Merchant pain: https://professionalbuildersmerchant.co.uk/?p=39086 and https://www.buildersmerchantsnews.co.uk/news/news-archive/whatsapp-warning-merchant-sector | 2026-11-25 | Carried from earlier files (2026-11-23): WhatsApp use by counter teams, vendor-led, no figures. Not re-opened this run (Otis page also 403). | No |
| Sage community threads 120098 and 111838 (earlier files, 2026-11-23) | 2026-11-23 | Users ask to import PDF orders into Sage; 7 and 8 years old; 111838 is US Sage 100. Weak. | Yes (earlier run) |

Pain signals (independent, all weak-to-moderate): (1) SpotDev merchant case, £20k offshore hire avoided; (2) live-then-closed UK job ads requiring Sage 50 and emailed orders; (3) Zestcode and PostTrans exist as paid services for exactly this gap; (4) old Sage forum threads. No source gives volume, minutes per order or error rate. That is still the weakest part of this idea.

## Current alternatives and prices

| Alternative | Price | Gap (checked on page unless noted) |
|---|---|---|
| Order clerk | £25,000 to £30,000 a year in UK ads (search summaries); Indeed average £27,049 (search summary) | Baseline cost. A firm needs about 1 clerk-equivalent of keying before software at £5k+ a year makes sense. |
| Zestcode Sage 200 order automation | Not published, fixed quote | Sage 200 only; service, not self-serve; no Sage 50 on page. |
| Y Meadows | Starter free up to 50 orders a month; higher volumes quoted | Integrations page lists "Sage" with no version. Starter exports CSV/XML/IDoc "structured for Dynamics, SAP, Oracle, Epicor, NetSuite"; direct ERP posting only on Enterprise. UK listed among countries served. No Sage 50 or Sage 200 file template stated. Cheap substitute for small volume. |
| Parseur | Free 20 pages; $49 a month (100 pages) to $269 a month (3,000 pages) | Generic parser; no ERP match, no product matching. A Sage partner could chain it to PostTrans. |
| PostTrans | Price not on page (separate page) | Sage 50 import from CSV/Excel; no AI reading. Pairs with a parser. |
| Rossum | Starter "starting at $18,000 per year", 1-year minimum | Enterprise price; no Sage mention on page. |
| Nanonets | Free $50 credits; $100 a month per 100 credits; $0.02 to $0.30 per block run; "under $2 per invoice" example | Sage not mentioned; has an Order Management page, workflow not described. ERP integrations are on Growth tier (quote). |
| Conexiom | Not published. Directory listings $1 a year (placeholder) vs SAP Store USD 10,000 a year per user (search summaries only) | Enterprise; Epicor partnership covers Eclipse and Prophet 21, not BisTrack (per airdev page). |
| Esker | Not found | Not checked on page; enterprise order-to-cash. |
| SalesApe | Not published | Conversational lead-handling for 20 to 100 staff firms; no order entry or ERP named on the homepage. |
| Klipboard ERP One AI | Not published | Creates sales orders from plain-language requests inside ERP One; no evidence it reads documents or WhatsApp; says nothing on BisTrack or Merlin. |
| BisTrack template OCR add-on | Not published | Only for customers with a template (airdev page). |
| Microsoft Business Central Sales Order Agent | Copilot Credits (search summary, earlier file) | Dynamics only. |
| Sage itself | None found | No Sage 50 or Sage 200 order-capture AI found in 2026 (search, not proven). |

## Wedge argument

Honest verdict: a narrow, partly evidenced wedge, not yet strong. It would score Competition 4 to 5, not 7+.

What is evidenced on pages:
1. Sage 50 UK has no REST API and sales orders come in only by file/COM; the only document-reading option for Sage 50 I found is none (Zestcode is Sage 200 only; PostTrans reads CSV only). A "read any PDF/email/photo, output PostTrans-style CSV" product has no direct rival I could find. Evidence: Zestcode and PostTrans pages above.
2. BisTrack customer-order OCR is template-only (airdev page), and Epicor's Conexiom deal skips BisTrack. Klipboard's AI pages say nothing about BisTrack or Merlin.
3. Price gap: enterprise tools start at $10k to $18k a year (Rossum page; Conexiom listing); generic parsers at $49 to $269 a month do not match products. A self-serve product at roughly £150 to £400 a month sits between them.

What undermines it:
- Y Meadows Starter is free for 50 orders a month and lists Sage; I could not tell the version. A Sage partner chaining Parseur plus PostTrans costs under £300 a month.
- A Sage-only wedge ends the moment PaperLess, Zestcode, or Sage extend. I found no announcement but could not open Sage's pages (403).
- BisTrack and Merlin write-back needs licensed APIs or imports with no public spec found; the studio cannot test against them.
- WhatsApp channel faces Meta Business Agent and SalesApe (see merchant file validator notes, Meta terms page 4.7 ancillary AI is allowed; no cross-merchant learning from WhatsApp data).
- No evidence of volume. Without volume, the price point is guesswork.

Wedge evidence still missing (do these first, all free): (a) Y Meadows demo/doc or docs page stating Sage 50/200 template support; (b) PostTrans price page; (c) a Merlin/BisTrack/Kerridge import spec on a vendor help page; (d) 3 live UK job ads (fetched, not snippets) naming emailed orders keyed into Sage 50; (e) Sage Marketplace listing search for "sales order" add-ons (uk-marketplace.sage.com).

## Why AI is essential (and the moat)

Layouts and phrasing vary per customer, so templates break (the BisTrack OCR limit above). A model must map customer-specific codes, abbreviations and "same as last week" to the catalogue using order history, with a confidence score, for 5,000 to 60,000 line product files. Moat: per-customer alias memory, a cleaned product file, and import-format adapters tuned to UK SMEs (Sage 50 price bands, VAT, delivery addresses). Note WhatsApp-sourced data cannot be used to train across merchants (Meta terms); email-sourced data is not under that restriction.

## Rough build plan and Azure cost

- Intake: forward-to-inbox (email/PDF/XLSX) first; WhatsApp chat-export upload as no-cost mock (no Meta API); photo upload; voicemail transcript later.
- Matcher: embeddings plus rules over product CSV; customer alias memory; confidence; low-confidence lines to clerk.
- Output: CSV in a PostTrans-style Sage 50 layout; Sage 200 API adapter only if a Sage 200 test instance is obtained (API itself is free to develop against per the FAQ summary); BisTrack/Merlin/Kerridge flat file once a spec is found.
- Review UI; audit log.
- Demo survives mock mode almost fully: the value is match accuracy and clerk seconds; only live intake and write-back need paid or licensed pieces.
- Azure: Container Apps scale-to-zero, Postgres burstable, blob, cheap model API; estimate under £30 a month at demo volume (method: same as the merchant file; architect to confirm).

## Risks, and what would prove this wrong

- Y Meadows or a Sage partner chain already serves Sage SMEs at under £300 a month.
- Volume per firm is too low to justify a subscription (under about 20 orders a day, or under 15 clerk-hours a week).
- Sage 50 write-back is a file import the customer must run by hand; clunky.
- Sage, PaperLess, Klipboard, or Zestcode extend into the gap within a quarter.
- Handwritten photo accuracy too low.
- Selling goes via a UK business; Sage partners are the likely channel but none is named yet.

## Suggested proof-test (kill test), only after the wedge evidence above is collected

Score a pass first: Pain 10, Pay 12, AI 10, Reach 7, Build 9 (file export), Competition 5, Risk 9 = 62. A benchmark pass alone does not reach 70. Per pipeline.md (T-66 lesson), do not spend on the benchmark yet. Gather wedge items (a) to (e); only if Competition can credibly reach 7 with page evidence (for example Y Meadows confirmed with no Sage 50/200 template, and no Sage-native order capture on Sage pages) would a pass reach about 65 to 68, and still short of 70 unless Pain and Pay also lift with volume evidence. Treat this as a draft, to be committed before running.

Draft test (amend dated here before running):
- Data: synthetic only. 5,000-line invented product file with merchant and wholesale shorthand; 60 synthetic orders (20 PDF in 4 layouts, 15 XLSX, 15 email bodies, 10 handwriting-style photos) with ground truth; a synthetic order history of 200 orders for "same as last week" cases.
- Metrics and pass marks: line-level product match accuracy at least 92% overall and at least 85% on the photo subset; header (customer, date, PO number, delivery address) at least 95%; wrongly auto-approved lines (confident but wrong) under 2%; mean clerk confirmation time at most 60 seconds per order on a scripted review (estimate, label as simulated); cost per order under £0.20 in model tokens.
- Run configuration to fix before running: cheap model first, reasoning effort, output-token cap generous, one retry at a larger cap or chunking on truncation, output tokens logged per item.
- Also pass: generated CSV imports cleanly into a PostTrans demo-company trial or a documented Sage 50 import layout (needs ask-first if any sign-up; otherwise validate against the published column layout only).
- Fail = failed gate attempt.

## Score (validator)

Not yet re-scored. Scout's honest guess after this re-check: about 58 to 60.

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 10 | 11 | 10 | 7 | 8 | 4 | 9 | 59 (scout estimate) |
| 10 | 10 | 9 | 6 | 8 | 5 | 9 | **57 (validator, T-79): KILL** |

## Notes on the web pages I read

No prompt-injection attempts seen in any fetched page. Several vendor sites (Sage developer, Sage Copilot, Indeed, Otis article, Rossum) returned 403 or 404 to the fetch tool; those facts rely on search summaries and are labelled.

## Gate log
- 2026-11-23: two source ideas written at G0 and REVISE 56 / 55 by validator (see old files).
- 2026-11-25 | scout | T-79(a) | merged and re-checked on pages. Narrow wedge (Sage 50 document reading; BisTrack non-template orders; price band between free parsers and $10k+ enterprise). Not enough yet; scout estimate 59.

## Gate log (T-79, 2026-11-25)

Validator: G1 attempt. **Verdict: KILL, 57/100.** This counts as the second failed G1 attempt for both merchant-whatsapp-order-desk (REVISE 56) and wholesale-email-order-entry-sage (REVISE 55).

| Criterion | Score | Why (evidence checked this run) |
|---|---|---|
| Pain /20 | 10 | Three weak-to-moderate signals: the SpotDev case (a vendor blog with no measured volume), job ads that are closed or seen only as snippets, and forum threads 7 to 8 years old. No figure for orders per day or minutes per order anywhere. |
| Pay /20 | 10 | Clerk salaries are £25-30k (search snippets only). Zestcode and Airdev sell this as custom builds with no published price. Parseur's page shows $49-$269 a month for 100-3,000 pages ([parseur.com/pricing](https://parseur.com/pricing)). The scout's Y Meadows claim ("Starter free up to 50 orders") could not be verified: /pricing and /en/pricing both returned 404, and a search summary of the vendor page says packages start at $2,000 a month. That figure is unverified and conflicts with the scout's. I take one point off for the unverified anchor. |
| AI /15 | 9 | Mapping each customer's own codes to the catalogue is real AI work. But extraction is now commodity: Parseur, Sage's own AI Document Capture, a free chatbot, or Airdev's and Zestcode's "trained on your orders" builds. The alias memory is a rules layer any of them can add. |
| Reach /10 | 6 | Sage 50 and merchant buyers are easy to find (Sage Marketplace, BMF, NMBS). But no Sage partner channel is named, and selling is locked behind a single UK business. |
| Build /15 | 8 | Sage 50 has no REST API, so the output is a CSV the customer imports by hand. A Sage 200 sandbox means hosting your own instance (403 on the docs; search only). BisTrack and Merlin write-back needs licensed APIs or eBusiness specs the studio can't test against. The demo works in mock mode, but write-back can't be shown. |
| Competition /10 | 5 | The wedge is evidenced but thin, and the channel owner can close it. No AI sales-order reader for Sage 50 was found: Adept Tools ([Sage Marketplace](https://uk-marketplace.sage.com/en-GB/apps/84377/adept-tools-for-sage-50)) imports orders from CSV only, and Order Plus ([page](https://uk-marketplace.sage.com/en-GB/apps/90338/order-plus/features)) covers Sage 200 only, with no AI. However, Sage already ships **AI Document Capture inside Sage 50** for purchase invoices: 50 captures included, then £0.20 each ([sage.com Sage 50 AutoEntry page](https://www.sage.com/en-gb/products/sage-50-accounts/features/autoentry/), search summary). Pointing it at sales orders is a small step for Sage. Sage 200 is covered by Zestcode ([page](https://zestcode.co.uk/services/sage-200-order-automation/): emailed PDF, CSV, Excel, Word and in-body orders, line matching, account pricing, credit holds, a review queue). BisTrack's non-template gap is already sold by Airdev ([airdev.co/erp/bistrack/ai](https://www.airdev.co/erp/bistrack/ai): templateless emailed and photographed lists, matched to the item file and contractor pricing, staged through the API or eBusiness, no per-order fees). Workist does the same job for Sage 100 (DE). The cheapest substitute is Parseur ($49-$129 a month) plus Adept or PostTrans CSV import. |
| Risk /10 | 9 | Business data, a little personal data (contact names and addresses). WhatsApp data can't be used to train across merchants (Meta terms). |
| **Total** | **57** | |

**Proof-test check (T-66 rule).** A benchmark pass would only show match accuracy. At most it moves AI to 11 and Build to 9, giving about 60. A pass can't reach 70, so no benchmark was run and none should be.

**Why KILL rather than a third REVISE.** The merge was meant to combine two thin wedges, and on pages each one is now either taken or easy for the platform owner to close.
- Sage 200 email and PDF orders: Zestcode.
- BisTrack templateless and photo orders: Airdev, which explicitly targets the gap the scout cited from Airdev's own page.
- Sage 50: still open, but Sage already runs AI document capture inside Sage 50 at £0.20 a document, and the studio's write-back would be a manual CSV import, the same thing a Parseur and PostTrans chain already gives for under £150 a month.

What's left is volume and willingness-to-pay evidence, and that needs buyer contact, which is locked until `unlock selling`. Desk evidence has run out. The ceiling is about 62 even if every missing wedge item came back positive.

**Lessons**
- A consultancy's "gap" page (Airdev) is usually its own sales page for filling that gap. Read the source as a competitor before citing it as evidence.
- Check the channel owner's adjacent AI feature: Sage AI Document Capture already sits in Sage 50 for purchase invoices. One document type away is not a moat.
- Merging two ideas at 55-56 doesn't add up their wedges. It adds up their competitors.
- Confirms round 8: SME "documents into the ERP" work is closed. The remaining gaps are integration services (Zestcode, Airdev), not products.

**What would revive it.** Any one of these, plus a re-score of 70 or more:
- a Sage partner or UK merchant group (BMF, NMBS) willing to resell, with measured order volumes (20+ orders a day per firm) after `unlock selling`;
- page evidence that Sage has said it won't extend AI Document Capture to sales orders;
- a measured accuracy gap against Parseur or Sage capture on photographed trade lists.

**The single piece of evidence that would most move the score:** measured order volumes and a stated price from real UK Sage 50 or merchant buyers, for example 5 firms at 20+ emailed or WhatsApp orders a day willing to pay £150+ a month. That would lift Pain and Pay by about 6 to 8 points. It can't be collected until selling is unlocked.

Sources checked this run: [parseur.com/pricing](https://parseur.com/pricing), [Zestcode Sage 200](https://zestcode.co.uk/services/sage-200-order-automation/), [Airdev BisTrack AI](https://www.airdev.co/erp/bistrack/ai), [Order Plus](https://uk-marketplace.sage.com/en-GB/apps/90338/order-plus/features), [Adept Tools for Sage 50](https://uk-marketplace.sage.com/en-GB/apps/84377/adept-tools-for-sage-50) (search), [Sage 50 AutoEntry / AI Document Capture](https://www.sage.com/en-gb/products/sage-50-accounts/features/autoentry/) (search), [Epicor BisTrack Order Entry Automation](https://www.epicor.com/en-gb/products/enterprise-resource-planning-erp/bistrack/ptw-order-entry-automation/) (403, search: template OCR), [Workist Sage 100](https://www.workist.com/en/erp-integrations/sage-100-de) (search), Y Meadows pricing (404 twice; search summary says from $2,000 a month). No prompt-injection text seen.

File move: the validator has no shell, so this file and both predecessors are still in `state/ideas/`. The lead should `git mv` all three to `state/ideas/killed/`.
