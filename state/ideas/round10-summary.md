# Round 10 scout summary (T-47, 2026-11-24)

Brief: paid add-ons sold inside a UK SME system's app marketplace (Reach from the marketplace, data from the public API). Time box about 25 minutes. Evidence is mostly search summaries; only the Dentally integrations page was fetched in full (the BDA page returned 403). No prompt-injection attempts seen in the pages fetched. Three files written; the marketplace angle produced one real gap and two weaker ones.

## Written (3 files, G0, scores left for the validator)
| Slug | Pitch | Public price evidence | Nearest competitor | Biggest doubt |
|---|---|---|---|---|
| dental-nhs-contract-delivery-desk | Explains Compass versus Dentally mismatches, forecasts UDA, UOA and the 8.2% unscheduled-care duty, drafts claim fixes | None for the job; Zmartly dental accountant from £129 a month is only a proxy | Dentally NHS reporting and CareStack UDA reconciliation (own pages not fetched); the Dentally Marketplace lists no UDA app (fetched) | Pay: no price; core is arithmetic; Dentally API is partner-only |
| accountancy-hmrc-post-triage | Reads HMRC letters, matches client, extracts deadline, drafts action in Xero Practice Manager | None; staff time only | None found in one search (Karbon, Xero Practice Manager, TaxDome, Senta pages not checked) | Competition unverified; personal data in letters; Pay |
| trade-job-extras-invoice-guard | Finds agreed but unbilled extras from the job's message thread before invoicing | Vendor claims only | ServiceM8 billable-item suggestions, Fergus AI (Sept 2026), Tradify SmartRead, simPRO Lightning | Competition: vendors ship this; chat-thread capture is a behaviour change |

## Dropped at the tool search (candidate, evidence, reason)
1. Electrical certificate (EICR) observation coding from photos: Tradecert, dotcert and iCertifi already suggest C1/C2/C3 codes with AI; Elec-Mate sells at £19.99 a month (App Store listings and https://www.tradecert.app/eicr-software, search summaries 2026-11-24). Regulated sign-off also rests on the electrician.
2. Letting-agent check-out versus check-in photo comparison: Imfuna already compares photo by photo and sends to the DPS; Inventory Hive and Kaptur cover capture (https://www.imfuna.com/industries/lettings/).
3. Xero supplier-statement reconciliation: Pulsify and fileLedger by fileAI both list statement matching (apps.xero.com listings).
4. Xero ledger-error and VAT-coding review for practices: XBert runs 150+ checks including VAT coding, duplicates and misallocation with a human-approved fix (https://apps.xero.com/uk/collection/ai-apps-for-accountants/app/xbert); Xero is adding a Books Health page.
5. Xero credit control and month-end accruals: Garfield, Paidnice, EasyAccrue and CoreClose are listed on the UK app store.
6. Supplier bank-detail change fraud checks: Dext Payments Supplier Shield flags mismatched or suspicious supplier details for UK Xero users (https://help.dext.com/en/articles/456505-dext-payments-supplier-shields).
7. ServiceM8 job-notes-to-quote-text: ServiceM8 has an AI writer and auto quote and invoice built in (https://servicem8.com/updates); Tradify has SmartWrite.
8. Employment Rights Act rota compliance (Deputy, Planday): not searched; core is deterministic and rota vendors will ship it. Dropped on reasoning only, label as unverified.

## Lessons for the validator
- The marketplace angle works for Reach and data in principle, but marketplace categories with weekly staff work (bookkeeping, credit control, receipts, quotes) are already full of AI apps; the Xero UK store has an "AI apps" page and every candidate hit it. The surviving gaps sit where the system's own marketplace has no category: NHS contract monitoring (Dentally) and practice-side post (Xero Practice Manager).
- Dentally restricts its API to approved partners and verified marketplace listings. Treat that as a gate to ask about (needs Vishal's OK to apply), and design the first version around file upload so Build does not depend on it.
- Pay is again the weak score. Neither dental nor post triage has a public price for the job; do not accept a modelled salary as Pay evidence.
- The trade idea is only on the list because the brief asked for the trades marketplaces; expect KILL on Competition (ServiceM8, Fergus, simPRO all shipped AI in 2025 to 2026).
- Dental scope must stay admin only. Any clinical, coding or treatment recommendation hits the medical-advice red line.

## Suggested cheap kill tests
- Dental: fetch https://www.dentally.com/en-gb/solutions/nhs and the CareStack NHS reporting page; look for a Compass mismatch explainer or an 8.2% tracker. Search practice-manager adverts for contract-monitoring duties and any consultancy price. Count NHS dental contracts in England from NHS BSA open data (Reach).
- HMRC post: read Xero Practice Manager, Karbon, TaxDome, Senta and Dext help pages for email or post triage; search "HMRC letters AI accountants" plus "AI mailroom". Find a practice-survey figure for letters a week.
- Trades: grep ServiceM8, Fergus and simPRO release notes for "variation", "extras", "WhatsApp".
