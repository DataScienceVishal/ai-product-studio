# Email order entry for Sage wholesalers

- slug: wholesale-email-order-entry-sage
- stage: G0
- market and segment: UK wholesale distributors and small manufacturers (roughly 10 to 100 staff) running Sage 50 or Sage 200, whose trade customers send purchase orders as email text, PDFs and spreadsheets that staff key in by hand.
- one-line pitch: Read each emailed customer purchase order, match the customer and their product codes to the Sage records, flag price and stock mismatches, and push a draft sales order into Sage for one-click approval.

## Problem and who has it

Many B2B customers still order by email with a PDF or spreadsheet attached. In a small distributor a sales order processor opens each email, reads the order, looks up the customer's own product codes against the internal catalogue, checks prices and lead times and types the order into Sage. UK job ads for these roles describe exactly this. Sage's own forums show users asking for a way to import PDF orders, being pointed to third-party add-ons. The automation tools that exist are priced and built for larger firms or for Microsoft Dynamics, SAP or NetSuite, not Sage 50/200.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://communityhub.sage.com/gb/sage-50-accounts/f/general-discussion-ireland/120098/sage-50-sales-order-processing | 2026-11-23 | Sage UK/Ireland community user asks for software to "import a pdf order from a customer direct into sage sale orders"; Sage staff point to third-party add-ons. Post is over 7 years old. |
| https://communityhub.sage.com/us/sage100/f/distribution-manufacturing-and-internet-modules/111838/sales-order-pdf-import | 2026-11-23 | US Sage 100 user: a client receives about 50 to 60 sales orders a day as emailed PDFs and wants them auto-imported; replies suggest OCR templates or customer portals. Over 8 years old and not UK, so supporting signal only. |
| Search-result snippets of UK job ads (DWP Find a Job 15969909: orders arrive by "email, portals and order forms", processor inputs "all customer orders, whether via EDI or direct, onto SAGE"; another: "monitor, open, and process orders delivered via emails using Outlook" then "Input orders... using Sage 50"; a sales administrator role: orders from "email, web site and phone calls... processed on Sage 50cloud"). Original pages were closed or returned errors when fetched. | 2026-11-23 | Indicative: manual email-to-Sage order keying is a paid job in UK SMEs. Unverified beyond the snippets. |
| https://conexiom.com/blog/from-inbox-to-erp-without-losing-your-mind-or-your-margin (vendor blog, 6 May 2025) | 2026-11-23 | Vendor claims manufacturers and distributors receive "hundreds (sometimes thousands)" of emailed order documents a day and that keying causes order errors. Vendor marketing, no data. |
| https://docs.zynk.com/workflow/documentation/sage-200/import-sales-orders.html | 2026-11-23 | Sage 200 sales orders can be imported from structured XML via a third-party connector, so the gap is turning unstructured emails into that structure. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Order processor staff (https://www.payscale.com/research/UK/Job=Order_Processor%2FSales_Coordinator/Salary) | Average £20,317/yr base (17 profiles; page also says last updated Jan 2021); job-ad snippets show £26,000 to £30,000 | Full-time cost for keying; errors and backlog at peaks. |
| Rossum document AI (https://rossum.ai/pricing/) | Starter "starting at $18,000 per year", 1-year minimum | Enterprise price; generic document capture, Sage integration not out of the box. |
| Lucy (Microsoft AppSource listing, https://appsource.microsoft.com/en-us/product/dynamics-365-business-central/PUBID.let_lucy%7CAID.f2832b24-d4e5-4c75-a3b00b5-c1de0d9ce203%7CPAPPID.6f96432e-cdcc-41f8-84fa-7ef724ccefd3) | Capterra lists from 1,885 (A$ or US$, unclear) per feature per month (search snippet; Capterra pages returned 403, unverified) | Dynamics Business Central only; US/AU/NZ. |
| Conexiom, FrontFlow and similar | Not published | Built for larger distributors and Dynamics/SAP. |

## Why AI is essential (and the moat)

Orders come in every layout: PDF from a customer's ERP, a scanned form, an Excel sheet, or plain email text such as "same as last week but 20 more of the blue ones". Templates break per customer; a model that reads any layout, resolves the customer's own codes and vague references against order history and the catalogue, and explains its confidence is what makes this work.

Moat: per-customer mapping memory (customer code to internal SKU) that improves with each approval, an evaluation set of real order documents, and a Sage 50/200 connector tuned to UK SME setups (price bands, VAT, delivery addresses).

## Rough build plan and Azure cost

1. Forward-to-inbox intake; parse email body and attachments.
2. Extract header and lines; match customer and SKUs against an exported Sage customer list and catalogue (CSV first).
3. Flag price, unit and stock mismatches; reviewer approves.
4. Export to Sage (CSV/XML via a connector first; direct API for Sage 200 later).

Azure (estimate, method: scale-to-zero container app, small database on free or lowest tier, blob storage, pay-per-token Azure OpenAI at demo volume): likely under $15 a month in build. Architect to confirm in `state/BUDGET.md`.

## Risks, and what would prove this wrong

- Weak UK-specific evidence: the strongest signals are old forum threads, vendor marketing and job-ad snippets; we have no UK survey of time spent or error rates.
- Integration is the hard part: Sage 50 desktop access is awkward, and a CSV round-trip may feel too clunky to buy.
- Demo needs realistic order documents and a catalogue; we must build synthetic ones.
- Customers may move to portals or EDI over time, shrinking email volume.
- Proven wrong if: target firms receive fewer than about 20 emailed orders a day, or they already use a Sage add-on that does this, or they won't pay more than the cost of a few hours of staff time a month.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
