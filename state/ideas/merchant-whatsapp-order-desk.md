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
| pending | pending | pending | pending | pending | pending | pending | pending |

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half, channel and closed-system thesis).
