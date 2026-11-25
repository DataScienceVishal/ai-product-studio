Merged into inbound-order-entry-desk.md on 2026-11-25 (T-79).
KILLED 2026-11-25 (T-79 validator, second G1 failure): the merged inbound-order-entry-desk scored 57; see its Gate log. To be git mv'd to killed/.

# Merchant WhatsApp order desk

- slug: merchant-whatsapp-order-desk
- stage: G0
- market and segment: UK independent builders', timber, plumbing and electrical merchants (1 to 10 branches) whose trade customers order by WhatsApp, photo of a handwritten list, voicemail or phone, and whose stock and order system is an on-premise merchant ERP
- one-line pitch: Turn a tradesperson's WhatsApp message, photo of a list or voicemail into a draft sales order with matched product codes, stock check and price, for the counter clerk to confirm in one click and push into the merchant's own system.

## Problem and who has it

Trade customers order from the van. Counter staff then read messages, decode handwritten lists ("4x 2.4 PAR 4x2"), look up product codes, check stock and key a sales order. Trade press says branch teams have moved to WhatsApp, often on personal phones. The merchant's ERP (Kerridge, Epicor Eclipse, TCS and others) is a closed system, so generic WhatsApp tools stop at the chat.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://professionalbuildersmerchant.co.uk/?p=39086 | 2026-11-23 | Stitch AI article (vendor): counter and branch teams use WhatsApp; personal phones can't connect to CRM or support tools; the suite offers shared inbox, templates, automation. Page mentions no ERP or order entry. |
| https://www.buildersmerchantsnews.co.uk/news/news-archive/whatsapp-warning-merchant-sector | 2026-11-23 | Trade press warning on WhatsApp use in the merchant sector (seen via search; page not opened, read before G1). |
| https://amasty.com/blog/construction-ecommerce/ | 2026-11-23 | Vendor blog: online ordering avoids deciphering "a handwritten list or a rushed voicemail". Vendor framing of the manual work. |
| https://reed.com/jobs/trade-counter-sales-advisor-tonbridge-1325093/ | 2026-11-23 | Trade Counter Sales Advisor, Tonbridge, £30,000 to £35,000 (per search summary). Staff-cost signal. |
| https://www.driverhire.co.uk/?p=394644 and https://findajob.dwp.gov.uk/details/18055317 | 2026-11-23 | Trade counter job ads surfaced by search (Plumb Centre Brentwood about £25,653 plus bonus; Eurocell £29,080 to £32,680; timber yard counter staff). Salaries as reported by search summary, confirm on the pages. |
| https://www.epicor.com/en-us/products/enterprise-resource-planning-erp/eclipse/ptw-api/ | 2026-11-23 | Eclipse exposes a REST API sold in paid bundles including Sales Order and Purchase Order APIs. So writing orders needs the merchant to license it. |
| https://www.truecommerce.com/en-gb/integrations/erp/ | 2026-11-23 | Kerridge listed as a flat-file integration, not a direct API. Order import by file is a realistic route. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| SalesApe (https://www.salesape.ai/articles/how-local-independent-timber-yards-secure-high-volume-trade-accounts) | Not published; demo by request | Reads photos of cutting lists on SMS, WhatsApp, email; interprets timber grades; checks stock; FAQ says "native integration pathways" pass quotes to an ERP without naming any. Page does not say it creates sales orders. Timber-led. Could widen. |
| Stitch AI (article above) | Not published | Shared WhatsApp inbox and automation; no product-matching or order entry on the page. |
| Travis Perkins Online Trade Counter (https://theretailbulletin.com/home-and-diy/travis-perkins-launches-online-trade-counter-02-06-2023) | n/a | Customer must adopt a portal; independents rarely have one. Shows the big merchants' direction. |
| Trade counter clerk | £25.6k to £35k a year | Cost of the manual keying. |

Gap claimed: per-ERP order drafting with a human confirm for the independents, covering plumbing, electrical and building materials, not only timber. SalesApe is the nearest rival and could close this for timber. Not a month-proof gap unless the ERP adapter set is the barrier.

## Why AI is essential (and the moat)

Free-text, abbreviations and handwriting must be mapped onto a 20,000 to 60,000 line product file with synonyms ("PAR", "4x2", brand shorthand). That needs a retrieval and matching layer evaluated against the merchant's own order history. The moat is the cleaned product file, learned customer aliases ("Dave's usual") and ERP adapters; data engineering is the owner's edge.

## Rough build plan and Azure cost

- Inbound adapter: mock mode reads a folder of sample chats and images; live mode uses WhatsApp Business Platform (paid per conversation, needs Meta business verification and approval) or a shared inbox forward.
- Product matcher: embeddings plus rules over a product CSV; confidence score; low confidence goes to the clerk.
- Order output: CSV or flat file in a Kerridge-like layout; Eclipse API adapter only if the merchant licenses it.
- Review UI for the counter.
- Azure: Container Apps scale-to-zero, Postgres burstable, blob for images, a vision-capable model API; estimate under £30 a month for a demo.
- Demo with synthetic data: build a product file from public merchant catalogue pages that allow it or an invented one of about 5,000 lines; 100 synthetic messages and photographed lists made by us. Measure line-match accuracy and clerk seconds per order.

## Risks, and what would prove this wrong

- WhatsApp Business API terms and cost; Meta restricts some AI chatbot use on the platform (verify current terms before building).
- SalesApe or an ERP vendor may ship the same inside a quarter.
- Merchants may refuse to install an adapter on a legacy server; sales go through a UK business.
- Photographed handwriting accuracy may be too low to save time.
- Wrong if: line-match accuracy on realistic lists stays under about 90 percent in the benchmark, or SalesApe confirms named ERP order creation.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 10 | 11 | 9 | 7 | 8 | 3 | 8 | 56 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area. Personal data is light: trade customers' names and numbers.
- No scraping dependency, as long as the demo product file is invented rather than built from merchants' catalogue pages.
- Synthetic data can credibly demo the core value: an invented 5,000-line product file with merchant shorthand, 100 synthetic messages and photographed handwritten lists, and a synthetic order history for "the usual". The real test (a merchant's own product file and customers' slang) waits for a pilot after `unlock selling`.
- Mock mode keeps most of the value, because the value is the matching and the draft order, not the channel. A merchant could even try it with their own data in under 10 minutes by uploading a chat export from the WhatsApp app, which needs no paid API. Only live, automatic intake needs Meta verification and approval.

**WhatsApp rules (checked on Meta's own pages, accessed 2026-11-23)**
- whatsapp.com/legal/business-solution-terms now redirects to "Meta Terms for WhatsApp Business Platform", last modified 23 September 2026 (https://www.facebook.com/legal/Meta-Terms-for-WhatsApp-Business-Platform).
  - Section 4.7 says providers of "large language models, generative artificial intelligence platforms, general-purpose artificial intelligence assistants" are "strictly prohibited" from the platform "when such technologies are the primary (rather than incidental or ancillary) functionality being made available", but "you may retain an AI Provider as your Solution Provider". An order-intake assistant for a merchant is ancillary, so this use is allowed.
  - The same section bars using WhatsApp Business Platform Data "to create, develop, train, or improve any machine learning or artificial intelligence systems", except fine-tuning a model "for your exclusive use". Per-merchant alias memory is fine; learning across merchants from WhatsApp data is not, which weakens the scout's data moat.
- The Business Messaging Policy (last updated 23 September 2026) allows automation inside the 24-hour window. It requires "prompt, clear, and direct escalation paths" to a human, and opt-in before business-initiated messages (https://whatsappbusiness.com/policy/).
- Pricing has been per message since 1 July 2025, and messages from users are free (https://developers.facebook.com/docs/whatsapp/pricing).
  - Each number gets 1,000 free service messages a month. From 1 October 2026 Meta "charges as of the 1,001st service message", and utility messages sent in an open window are charged too.
  - Third-party tables put the UK utility rate at about £0.0159 a message (https://chatmaxima.com/whatsapp-api-pricing/uk/, search summary only). Small, but still a paid, approval-gated service.
- **Meta now competes on its own channel.** Meta Business Agent (announced 3 June 2026) answers questions, "recommends products from its catalog", "closes sales" and calls the business's own APIs and webhooks. Getting started is free (https://whatsappbusiness.com/blog/introducing-meta-business-agent-ai/; https://developers.facebook.com/documentation/meta-business-agent/overview).

**Falsification findings** (all accessed 2026-11-23)
- **SalesApe, checked on its own pages.**
  - Its timber-yard article (22 July 2026) sells a "24/7 digital trade counter operating directly over SMS, WhatsApp, and email". It reads "a photo of a handwritten timber list", "checks real-time inventory levels" and produces "an accurate quote brief", with "secure, native integration pathways" into the "current ERP or inventory system" (https://www.salesape.ai/articles/how-local-independent-timber-yards-secure-high-volume-trade-accounts).
  - Neither that page nor the homepage names an ERP. The homepage lists HubSpot, Salesforce, Zoho, Zapier and "100+ other tools", and neither page says SalesApe creates sales orders (https://www.salesape.ai).
  - So the scout's gap survives, narrowly, but SalesApe already sells both the channel and the photo reading.
- **The ERP incumbent is one step away.** Kerridge is now Klipboard, and K8 is now ERP One.
  - ERP One's embedded AI (May 2026) lets merchants "take action immediately" on stock, pricing and orders (https://www.klipboard.com/news/klipboard-brings-practical-embedded-ai-into-erp-one).
  - Its AI page lists 10 ERP One agents, including sales orders, plus out-of-stock alternatives and a demo video titled "Order creation". ERP Go's listed actions include creating sales orders (https://www.klipboard.com/en-za/solutions/ai-solutions).
  - A clerk can already type or paste a message into the ERP's own assistant. Reading the photo is the only missing step.
- **Eclipse is covered for larger distributors.** On 14 July 2026 Conexiom and Epicor expanded their partnership to automate RFQs and sales orders for Eclipse and Prophet 21 (https://conexiom.com/blog/conexiom-expands-strategic-partnership-with-epicor, search summary only).
- **Merchant-specific AI agents are arriving.**
  - Beesley & Fildes launched Otis (3 June 2026), built with Optiflow Technologies. It searches stock and writes multi-line quotes on the merchant's website, and Optiflow is "working with a select group of merchant partners" (https://professionalbuildersmerchant.co.uk/news/beesley-fildes-boosts-sales-with-otis-a-fully-autonomous-ai-agent/).
  - Stitch AI sells a shared WhatsApp suite to trade counters (https://www.buildersmerchantsnews.co.uk/news/news-archive/whatsapp-warning-merchant-sector, 22 April 2025; vendor-led, with no figures).
- **Bespoke builds are the cheap substitute, and the best pain signal here.** SpotDev built an agent for an unnamed UK builders' merchant that "reads incoming orders and writes them straight into their CRM", replacing a planned offshore hire "budgeted at over £20,000 a year" (https://www.spotdev.co.uk/blog/ai-order-entry-for-distributors, 4 August 2026). Its channels were email, PDFs, spreadsheets and phone notes, not WhatsApp.
- **The real gap is BisTrack and Merlin merchants, and the studio can't test it.** One consultancy says no Epicor AI agent has been announced for BisTrack, which has only a template OCR add-on for orders (https://www.airdev.co/erp/bistrack, search summary only). Testing against it needs a licence.
- No source counts how many orders arrive by WhatsApp or photo.
- Reach: the BMF has 509 merchant members with over 6,400 branches (page date unclear, search summary only), plus buying groups (NBG) and three trade titles.

**What would change my mind (re-score on this evidence)**
1. Vendor pages showing that SalesApe doesn't create sales orders in BisTrack, Merlin or ERP One, that Klipboard AI can't turn a photo or WhatsApp message into a draft order, and that Otis is web-only.
2. Public sales-order import specifications (flat file or API) for BisTrack, Merlin and ERP One that the studio can target without a paid licence.
3. An independent figure for the share of trade orders reaching UK independents by WhatsApp or photo, from a BMF, NBG or trade-press survey.
4. After T-1, a benchmark of 100 synthetic messages and photographed lists against an invented 5,000-line product file, reaching at least 90% line match (the scout's bar) with under a minute of clerk confirmation per order.

With all four I'd expect the mid 60s. Consider merging with `wholesale-email-order-entry-sage` (55): it's the same engine (match free text to SKUs, draft the order, human confirms, push into a closed system) on a different channel.

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half, channel and closed-system thesis).
- 2026-11-23 | validator | G0→G1 | REVISE 56 | Best AI fit of the five (free text and handwriting matched to a large product file), but SalesApe already reads photographed lists over WhatsApp for merchants, Klipboard's ERP One AI already creates sales orders from plain-language requests, Conexiom covers Eclipse, Meta's own agent is free to start, and the remaining gap (BisTrack and Merlin merchants) can't be tested without a licence.
