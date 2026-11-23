# Marketplace return and payout leak finder (India)

- slug: marketplace-return-claim-recovery-india
- stage: G0
- market and segment: India. Small multi-marketplace sellers (roughly 30 to 1,000 orders a day) on Meesho, Flipkart and Amazon.in, especially apparel and home-goods sellers in clusters such as Surat, Jaipur and Delhi NCR, who track returns and payouts by hand in Excel.
- one-line pitch: Upload your marketplace order, return and settlement reports (or forward them on WhatsApp). The tool matches every order to its payout and return, flags short payments, missing and wrong returns and deductions while the claim window is still open, and drafts the claim text with the evidence checklist, in Hindi, Gujarati or English.

## Problem and who has it

Marketplaces settle in batches (Meesho about every 15 days per search results), with deductions for returns, RTO, shipping and penalties. Small sellers get high return rates. Some returns come back wrong, damaged or not at all, and claim windows are short (Flipkart SPF 14 days for damaged/wrong returns, Meesho about 30 days from settlement per eVanik). Matching thousands of rows across order, return, payment and bank reports is messy data engineering. The reports have different formats and IDs per marketplace, partial settlements and reversals. Sellers do it by hand or not at all, so money leaks. Existing reconciliation tools are aimed at larger D2C brands and priced per order volume. Small cluster sellers organise in WhatsApp groups and are price-sensitive.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://inc42.com/buzz/meesho-sellers-protest-change-return-policy/ | 2026-11-23 | (23 Jan 2023) Surat sellers protested Meesho's return policy. Some say they "did not receive compensation despite receiving tampered products from customers". Sellers organised in WhatsApp groups. Older, but it shows the pain and the WhatsApp-first channel. |
| https://voxya.com/consumer-complaints/claim-for-lost-disposed-return-orders-meesho-seller-/259931 | 2026-11-23 | (25 Feb 2026) A Meesho seller complains that return orders were disposed of without delivery to the seller, and that returns arrived with mismatched items with no compensation. The seller attached an order-ID sheet, which shows manual tracking. Anecdotal, unverified. |
| https://www.consumercomplaints.in/flipkart-spf-claim-rejected-for-a-number-of-fraud-returns-c3215505 (plus similar listed in search) | 2026-11-23 | Flipkart sellers report SPF claims for fraudulent or wrong returns rejected, often for missing proof. Anecdotal, but the same complaint recurs. |
| https://www.deccanherald.com/india/karnataka/bengaluru/gang-registers-as-seller-with-e-commerce-company-exploits-returns-policy-swindles-rs-5-5-crore-3302465 | 2026-11-23 (search summary; page not opened) | Police case: a Surat-based ring defrauded Meesho of about Rs 5.5 crore through fake returns, and Meesho's audit found sold-vs-returned mismatches. Shows returns are a high-loss, high-fraud area where both sides now demand evidence. |
| Search-result summary of https://unicommerce.com/blog/marketplace-claims-management/ | 2026-11-23 | Incumbent vendor notes marketplaces refund the customer first and reject the seller's claim if evidence is not supplied in the window. Missing or "delivered but not received" returns need investigation. Vendor content. |
| https://www.evanik.ai/reconciliation | 2026-11-23 | A vendor claims "10,000+ sellers" and "Rs 1,098 Cr+ recovered for clients" (self-reported, unverified). If even roughly true, sellers pay for this today. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| eVanik reconciliation (https://www.evanik.ai/reconciliation) | Quarterly, excl. GST: Rs 10,000 for 500 orders (Blue), Rs 18,000 for 1,000, Rs 27,000 for 3,000 ("most popular"). Up to Rs 1,90,000 enterprise. A search snippet quoted lower monthly tiers (Rs 799 to 9,999), which conflicts with the page. Use the page figures. | Priced per order band, so a small seller with high volume and low order value pays a large share of margin. English UI. Claim auto-filing (incl. Meesho) is advertised but not priced. |
| Taxilla Meesho reconciliation (https://www.taxilla.com/marketplace-solutions/meesho-ecommerce-reconciliation) | No public price | Aimed at "high-volume" sellers, sold through demos. |
| Eshopbox claim filing (https://help.eshopbox.com/en/articles/11374141-eshopbox-claim-filing-service-policy) | No public fee. Only available if you use Eshopbox fulfilment or seller-of-record | Tied to their warehouse. Meesho not listed. |
| Hire an e-commerce executive (Surat postings via https://in.indeed.com/E-Commerce-Executive-jobs-in-Surat,-Gujarat and https://apna.co/job/surat/e-commerce-executive-245415833) | Rs 20,000 to 35,000 a month in sampled Surat postings (aggregated in search, individual listings not opened) | Manual Excel work, error-prone, misses windows. |

## Why AI is essential (and the moat)

- The core is data engineering with ML assistance. It parses and normalises each marketplace's changing report formats (LLM-assisted schema mapping when columns change), does fuzzy multi-key matching across order, sub-order, return AWB and settlement IDs, and detects anomalies in deductions (fee or penalty different from the rate card).
- An LLM turns each discrepancy into a claim draft with the exact evidence list (unboxing video, AWB, weight) in the seller's language, and reads marketplace policy pages via RAG so it can explain why a deduction looks wrong.
- Moat: a library of report-format adapters and deduction rules for Meesho, Flipkart and Amazon.in kept up to date, plus outcome data on which claims succeed. A vernacular WhatsApp-first workflow for cluster sellers that incumbents sell to through English demos.

## Rough build plan and Azure cost

- Week 1: Ingest pipeline for CSV/XLSX exports (seller downloads them; no scraping, no seller-portal login automation), canonical order/return/settlement schema, sample files.
- Week 2: Matching engine (deterministic joins plus fuzzy fallback), rate-card checks, claim-window clock per marketplace.
- Week 3: Discrepancy dashboard, claim-draft generation with Azure OpenAI, Hindi/Gujarati output, mock WhatsApp adapter.
- Week 4: Tests on synthetic and anonymised sample reports, DPDP (buyer names and addresses in reports must be stripped on ingest), evaluation of match precision and recall.
- Azure (estimate: Container Apps scale-to-zero, Blob storage for uploads, small Postgres or SQLite, LLM only for drafting): about USD 5 to 15 a month during build. Confirm in state/BUDGET.md.

## Risks, and what would prove this wrong

- Real report samples are needed to build adapters. Public sample formats may be incomplete. If the studio cannot get anonymised real exports, the adapters are guesswork (red-flag watch).
- Marketplaces change report formats and policies often, so maintenance load is ongoing.
- Automating claim filing inside seller portals would need logins and may break marketplace terms. MVP stays at drafting only, and the seller files.
- Reports contain end-customer personal data (names, addresses), so minimise and strip on ingest.
- Incumbents (eVanik, Unicommerce UniReco, Taxilla) already exist, so the gap must be price and language for small sellers.
- Proves it wrong: sample reconciliations show recoverable leakage below about 0.5% of GMV for small sellers, or marketplaces now auto-compensate most wrong returns (Meesho claims its systems cut claim rates by about 30%, https://www.meesho.io/blog/when-the-wrong-thing-comes-back-how-meesho-stopped-putting-the-burden-on-sellers, not opened, from search).

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
