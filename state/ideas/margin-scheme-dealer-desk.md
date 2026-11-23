# Margin-scheme dealer desk (non-vehicle second-hand dealers on Xero)

- slug: margin-scheme-dealer-desk
- stage: G0
- market and segment: UK VAT-registered dealers in second-hand goods, antiques, art and collectables (not vehicles) who keep their books in Xero. Examples: antiques and vintage shops, bike resellers, camera and instrument dealers, auction-buying resellers.
- one-line pitch: Reads each purchase receipt, auction invoice and sale, decides if the margin scheme applies, keeps the stock book and posts the right VAT figures to Xero, so nobody edits tax amounts by hand.
- found by: incumbent-refusal method (T-27)

## The refusal (quoted)
Xero's Product Ideas board, "VAT - Automatically calculate VAT using the Marginal Scheme", 82 votes, status "Not in pipeline", posted 5 April 2022. Xero Community Manager Kelly Munro, 6 November 2025: "this isn't in our roadmap." She points users to editing the Tax Amount on each line by hand. An admin (Hannah G, 21 December 2023) gives the workaround: record the purchase as VAT Exempt, record the sale tax exclusive and type the VAT in manually (her example: a vehicle bought for GBP 1,500 and sold for GBP 2,000 gives GBP 83.33). Source: https://productideas.xero.com/forums/967133-reports-tax/suggestions/45048502-vat-automatically-calculate-vat-using-the-margin (accessed 2026-11-23).

## Problem and who has it
Under the VAT margin scheme the dealer pays VAT only on the profit on each item, not the sale price. The seller must keep a record for each item (purchase invoice, sale invoice, margin) and must not show VAT on the invoice. Xero cannot compute this, and its "new invoicing" removed the old manual-adjustment option (a user comment, Gavin Barlow, 15 February 2025, says so). Dealers therefore do one of: edit VAT by hand on every invoice; prepare margin invoices outside Xero and upload them; use manual journals; or build a spreadsheet stock book. With many small items a week this is slow and error-prone, and an error means wrong VAT paid to HMRC.

Eligibility is also a judgement per item. HMRC says you cannot use the scheme for an item bought with VAT charged, or for precious metals (gov.uk, accessed 2026-11-23). That check needs the purchase document read, which is where AI helps.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://productideas.xero.com/forums/967133-reports-tax/suggestions/45048502-vat-automatically-calculate-vat-using-the-margin | 2026-11-23 | Refusal quoted above. 82 votes, "Not in pipeline". Users describe separate invoicing (Gemma Dyer, 10 May 2024), manual journals (Julie Romain, 21 June 2023), custom VAT codes (Sarah Verge, 15 May 2025). Several say manual calculation is tedious at volume. No add-on is named in the thread. |
| https://productideas.xero.com/forums/939198-for-small-businesses/suggestions/45048502-vat-automatically-calculate-vat-using-the-margin?page=2 | 2026-11-23 | Second page of the same thread (seen in search results only; not read in full). |
| https://www.gov.uk/guidance/the-margin-and-global-accounting-scheme-vat-notice-718 | 2026-11-23 | HMRC Notice 718 (seen in search results; title only, not read in full). The rules the product must encode. Next step for the validator: read sections on records and the global accounting scheme. |
| https://gov.uk/vat-margin-schemes/keeping-records | 2026-11-23 | HMRC record-keeping page (search result; per the search summary, a stock book tracking each item individually plus purchase and sale invoices is required for vehicles; confirm scope for other goods). |
| https://apps.xero.com/uk/app/motordesk | 2026-11-23 | Substitute for vehicle dealers only (see below). |

Independent pain signals so far: (1) the 82-vote Xero thread with named workarounds; (2) HMRC's per-item record burden; (3) the existence of a dealer-system market (MotorDesk) that has to build margin VAT in, showing dealers pay to avoid the manual job. A fourth signal (bookkeeper or accountant fee for margin-scheme returns) is not yet found; needs a UK bookkeeper fee page.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| MotorDesk (Xero app, vehicle dealer system) | GBP 79 / 149 / 269 per month (Starter 5 vehicles, Growth 25, Scale 50), 30-day trial. Source: https://apps.xero.com/uk/app/motordesk, accessed 2026-11-23 | Built for used-vehicle dealers; the page says it calculates margin VAT per vehicle and syncs to Xero. It does not say it supports non-vehicle goods. It is a full dealership system, not a bolt-on for a bike shop or antiques dealer. |
| Manual workaround in Xero (edit tax amount, journals, spreadsheets) | Staff or bookkeeper time; no hour figures published in the thread (not estimated here) | Error-prone, no per-item stock book, breaks in new invoicing per user comment |
| Odoo module "gb_vat_margin_scheme_second_hgoods" (https://apps.odoo.com/apps/modules/19.0/gb_vat_margin_scheme_second_hgoods) | Price not read | Needs a move off Xero to Odoo; shows the stock-book and margin calculation is a known need |

## Add-on search result (required check)
Searches run 2026-11-23: "Xero margin scheme VAT app add-on 2026 second-hand dealer stock book" and "Xero margin scheme app second-hand goods antiques OR jewellery OR bicycles stock book VAT 2026 software". Found: MotorDesk (vehicles only, full DMS) and an Odoo module (not Xero). No Xero marketplace add-on for non-vehicle margin-scheme dealers turned up. Caveat: the search tool does not index the whole Xero marketplace. Before G1 the validator should browse apps.xero.com/uk directly for "margin", "stock book", "antiques", "second hand". If one exists, KILL.

## Why AI is essential (and the moat)
Weak to moderate, said plainly. The VAT arithmetic is deterministic (margin = sale price minus purchase price, VAT = margin x 1/6). AI is needed for the front end: reading messy purchase documents (auction buyer's invoices that bundle premium, VAT and lots; private-purchase receipts; handwritten notes), deciding per line whether the item qualifies (VAT charged on purchase? precious metal? mixed lot that must be split), matching a sale back to the right purchase from loose descriptions, and flagging items sold below cost or unmatched. An incumbent (Xero) has said it will not build this, so the gap does not close in a month; a Xero-integrated bolt-on is the natural shape. Doubt: a deterministic stock-book spreadsheet template with a Xero journal export could cover 80% with no AI.

## Rough build plan and Azure cost
- Inputs: Xero bills and invoices via the Xero API (needs a Xero developer app and demo company) plus uploaded purchase documents.
- Pipeline: document extraction (LLM) -> eligibility rules (code) -> stock book table -> margin VAT -> journal or invoice-adjustment drafts for approval -> HMRC-style stock book export.
- Demo on synthetic data: yes. Generate 100 synthetic auction invoices, receipts and sales for a fictional antiques shop, and use a Xero demo company (free). No paid service needed, so nothing is lost in mock mode.
- Azure estimate (not yet costed): small web app, storage and Azure OpenAI extraction. Expected tens of pounds per month at demo scale; the architect should confirm.

## Risks, and what would prove this wrong
- A non-vehicle Xero add-on or a cheap stock-book spreadsheet service already exists (check the marketplace).
- Market size: no count of non-vehicle margin-scheme dealers found. Not estimated; needs a source (HMRC VAT statistics or trade bodies).
- Xero API limits: whether the bolt-on can edit tax amounts on approved invoices; the user comment says the manual option is missing in new invoicing, so it may need to create the sale as a draft with tax-exclusive lines.
- Liability: VAT errors. A human sign-off step is required; no tax advice given.
- Willingness to pay: only vehicle dealers have a visible price anchor (GBP 79 to 269 per month).

## Injection notes
None seen. The Xero thread contains user posts that recommend a PDF guide and a LinkedIn article; not followed.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 written by scout (T-27). Add-on check run; MotorDesk covers vehicles only.
