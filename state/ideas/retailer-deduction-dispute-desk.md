# Retailer deduction dispute desk for small UK food and drink suppliers

- slug: retailer-deduction-dispute-desk
- stage: G0
- market and segment: UK food and drink producers (roughly 5 to 100 staff) selling to the 14 GCA-designated grocers (Tesco, Sainsbury's, Asda, Morrisons and others)
- one-line pitch: AI reads a grocer's remittance or deduction notice, checks each deduction against the supplier's orders, delivery data and agreed terms, and drafts the dispute inside the roughly 30-day challenge window.
- task: T-142 (follow-up to T-141 candidate 8). Scout run 2026-11-26. Public sources only; nobody contacted.

## Problem and who has it

Retailers short-pay invoices (unilateral deductions for shortages, promotions, fines, historic claims). Suppliers lose disputes through weak records and missed windows. The GCA calls out the 30-day challenge window (see Evidence). Buyer: finance person or credit controller at a small supplier. Larger suppliers use enterprise tools; the small segment is the open question.

## Evidence for validator

### Pain signals (3 independent)
1. GCA news, 16 Apr 2026 survey results (fetched 2026-11-26): suppliers reporting any Code issue rose from 30% to 32%; invoice discrepancy handling raised by 20% of suppliers; delays in payment 14%; retailer compliance averaged 92%, range 98% to 69%. https://www.gov.uk/government/news/high-code-compliance-maintained-as-some-supplier-issues-increase
2. GCA annual report news, 16 Jul 2026 (fetched 2026-11-26): 2026/27 priorities "delays in payment, forecasting, marketing costs, and de-listing practices"; targeted investigation of Amazon.com, Inc. under paragraph 5. Deductions are not named in that page. https://www.gov.uk/government/news/gca-publishes-202526-annual-report
3. GCA best practice statement on forensic auditing (fetched 2026-11-26): Annex 2 says a 30-day challenge period became the sector norm and some retailers applied deductions at its end without express agreement; retailers should not deduct disputed sums when challenged; silence is not consent; 60-day rule if supplier does not engage; claims limited to current and previous two financial years under the voluntary commitment. Last updated 8 Feb 2023. https://www.gov.uk/government/publications/best-practice-statement-forensic-auditing/best-practice-statement-forensic-auditing
4. Search-summary only, NOT verified by me: YouGov deck for the 2026 GCA conference ranks "not allowing time (30 days) to challenge proposed invoice deductions, or deducting even if challenged" first among direct suppliers' issues at about 51% (52% in 2025). The PDF text would not decode through WebFetch; validator should open the slide. https://assets.publishing.service.gov.uk/media/6ab54e4a8cb3c0580e5011b2/2026_GCA_conference_slide_deck.pdf
5. Job-ad pain: Esker case material and a Chesterfield deductions analyst ad describe analysts reviewing invoices, POs, remittances and shipment records to dispute retail deductions (see price points).

Caveat: the GCA pages I could open do not show a dated investigation or guidance specifically on deductions since 2023. The 2025-26 annual report PDF (https://assets.publishing.service.gov.uk/media/6a588b4a31fb6daf314137a4/Groceries_Code_Adjudicator_Annual_Report_and_Accounts_2025-2026.pdf) would not decode, so its deductions text is unread. Forcing function is therefore weak: no new rule or deadline found. Priority list for 2026/27 does not list deductions.

### Price points and substitute costs (URL, figure)
Honest result: no published recovery-firm fee, contingency percentage, or outsourced deduction-desk price was found for the UK.
- In-house staff, aggregator estimate (not food, estimate not an advertised salary): Deduction Analyst, Chesterfield, estimated GBP 38,250 to 46,750 a year; duties are reviewing invoices, POs, remittances and shipment records and disputing invalid retail deductions. Fetched 2026-11-26. https://talents.studysmarter.co.uk/companies/lifoam-industries/chesterfield/deduction-analyst-50175316/
- In-house staff, search-summary only (page not verified, I could not open the ad): Compleat Food Group credit controller, GBP 28,000; Belazu senior credit controller GBP 35,000 to 40,000 (ad closed Dec 2025). Bakkavor Newark credit controller ad includes generating debit notes for customer deductions (page now says filled, salary not seen). https://www.compleatfood.com/careers/credit-controller/ (404 on fetch), https://jobs.bakkavor.com/job/Newark-Credit-Controller-NG24-2ER/811859302. Treat as unverified.
- Software, vendor claims only: Promomash prices CPGenius Deductions by monthly deduction invoice volume, one-year commitment, onboarding fee possible, no figures. Fetched 2026-11-26. https://promomash.com/pricing?hsLang=en
- SPS Commerce page shows a calculator citing typical deduction fees of 1% to 5%; that is the retailer-loss rate, not SPS's price. https://www.spscommerce.com/products/revenue-recovery/1p/
- Not a benchmark: invoice finance service fee 0.75% to 2.5% of turnover from a lender-style blog (https://market-invoice.pages.dev/blog/invoice-finance-for-food-and-drink-smes-managing-seasonal-demand-and-supermarket-payment-terms/, search summary only).
- Recovery rate context (vendor claims): SPS "up to 75% of eligible deductions" and 2-10% of revenue lost; Esker citing IOFM/Inmar up to 20% of deductions disputable, 3.7% margin loss. Not UK-specific.
Count: 1 verified-by-fetch figure (an estimate, non-food) plus 2 unverified. Below the template's "2 price points" bar for firm evidence; no contingency/fee figure at all.

### Incumbents (own pages, fetched 2026-11-26)
| Vendor | UK grocers covered? | Public price | Minimum size | Notes |
|---|---|---|---|---|
| SPS Commerce Revenue Recovery | Page names Walmart, Amazon, Kroger, Target, CVS, Walgreens, Lowe's, Home Depot, Kohl's, UNFI, KeHE; no Tesco, Sainsbury's, Asda, Morrisons | None; "free audit" | Not stated | https://www.spscommerce.com/products/revenue-recovery/1p/ |
| Esker deductions (UK page) | No UK retailer named; customers All About Food, Eagle, Damm; AI capture, matching, "AI Agents", ERP posting | None; demo and ROI calculator | Not stated | https://www.esker.com/en-gb/cloud-business-solutions/order-to-cash/accounts-receivable/deductions-software/ ; a UK solution summary PDF exists (https://www.esker.com/sites/default/files/resources_files/003-esker-order-to-cash-claims-deductions-solution-summary-uk.pdf), not read |
| Promomash CPGenius Deductions | US retailers only named (UNFI, KeHE, Target, Whole Foods, Kroger, Walmart, Amazon, CVS); no UK mention | Quote only; by monthly DI volume; 1-year term | Not stated (has "Seed" tiers for events) | https://promomash.com/pricing?hsLang=en ; can include managed service (validates and disputes for you) per G2 summary |
| ARPflow (now redirects to Roma, runroma.com) | Page names UNFI, KeHE, Target, Walmart; no UK | None; G2 says outcome-based (search summary) | Not stated; "170+ brands", example $3.3M brand | https://www.runroma.com/ ; US company |
| iNymbus | Press release lists Amazon, Walmart, Home Depot, Target; no UK grocers | Not found | Not found | https://www.silicon.co.uk/press-release/inymbus-empowers-cpg-companies-to-automate-deduction-management (search summary only) |
| HighRadius, Vividly | No UK grocer evidence found | Not found | Enterprise orientation (HighRadius cites Unilever, P&G on G2) | Not opened; search summary only |
| UK-specific tool | None found | | | Searches found no UK grocer-deduction product |

Strongest threat: Esker. It has a UK-localised deductions page, AI matching of claims to ERP/promotion data, and is the one vendor with a UK summary PDF. Gap unverified: it names no Tesco/Sainsbury's/Asda retailer connectors and no price. Low-cost threat: any ERP or Dext-style incumbent adding a remittance-matching feature; also US vendors (Promomash, Roma) could add UK retailers cheaply since remittances are PDF/CSV.

### Wedge (unproven)
Small UK suppliers too small for Esker/HighRadius, plus UK-specific GSCOP wording (30-day window, 60-day silence rule, two-financial-year audit limit, no deduction on disputed sums) baked into the draft letters. Retailer-specific parsing of Tesco/Sainsbury's/Asda/Morrisons remittance layouts. Weakness: no incumbent weakness evidenced on its own pages beyond "no UK retailers named"; Esker UK collateral not read; no pricing shows incumbents price out small suppliers.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/news/high-code-compliance-maintained-as-some-supplier-issues-increase | 2026-11-26 | 2026 survey: 32% issues, 20% invoice discrepancy handling, 14% payment delay |
| https://www.gov.uk/government/news/gca-publishes-202526-annual-report | 2026-11-26 | 16 Jul 2026 report; priorities exclude deductions by name; Amazon para 5 probe |
| https://www.gov.uk/government/publications/best-practice-statement-forensic-auditing/best-practice-statement-forensic-auditing | 2026-11-26 | 30-day norm, no deduction on disputed sums, 60-day rule, portal data best practice, contingency auditors |
| https://talents.studysmarter.co.uk/companies/lifoam-industries/chesterfield/deduction-analyst-50175316/ | 2026-11-26 | In-house analyst task and estimated salary |
| https://promomash.com/pricing?hsLang=en | 2026-11-26 | Quote-only, volume-based, annual contract |
| https://www.spscommerce.com/products/revenue-recovery/1p/ | 2026-11-26 | US retailers only named; no price |
| https://www.esker.com/en-gb/cloud-business-solutions/order-to-cash/accounts-receivable/deductions-software/ | 2026-11-26 | AI matching, no UK retailer named, no price |
| https://www.runroma.com/ | 2026-11-26 | ARPflow successor; US retailers; no price |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| In-house analyst / credit controller | Est. GBP 38,250-46,750 (non-food estimate); GBP 28,000-40,000 credit controllers (unverified) | Small suppliers rarely have a dedicated person; time split with credit control |
| Enterprise deduction software (Esker, HighRadius, SPS, Promomash, Roma) | Quote only | US retailer focus; UK grocers not named on fetched pages |
| Recovery/contingency firm | Not found | Fee unknown; Pay unproven |
| Spreadsheets and portal chasing | Staff hours | No evidence of hours per month |

## Data red flag (portal export)
Not resolved. Found: the GCA best practice statement says many retailers give suppliers documents through a portal and should provide sales data to verify claims, which implies suppliers can see their own claim data. Sainsbury's supplier portal named as togetherwith.co.uk and Tesco supplier-support email per the gov.uk supplier helplines page (search summary, https://www.gov.uk/government/publications/code-compliance-officer-contact-details/supplier-helplines). No evidence found on whether remittances or deduction notices can be exported (CSV/PDF) from Tesco Partners Toolkit, Sainsbury's or Asda portals; Tesco Partners Toolkit documentation is login-gated. Demo would rely on synthetic remittances, so the value (matching accuracy on real layouts) cannot be shown on real data. Real-data requirement risks the "core value cannot be shown" red flag unless synthetic layouts are accepted.

## Why AI is essential (and the moat)
Messy remittance PDFs and free-text reason codes differ by retailer; reading them and drafting a clause-cited dispute is LLM work. But Esker already ships AI claim capture and matching, and "AI reads documents and drafts" is not a moat by itself. Moat candidates: UK grocer layouts and GSCOP-specific rules; low-price self-serve for small suppliers.

## Rough build plan and Azure cost
Not scoped (G0). Likely: ingest PDF/CSV/email remittances, match to uploaded orders/POD/terms, dispute-letter drafter with deadline tracker. Small Azure footprint expected. Needs estimate by architect if it advances.

## Risks, and what would prove this wrong
- No published fee anywhere: Pay cannot be evidenced by desk research (same hole as T-141).
- Forcing function weak: GCA 2026/27 priorities omit deductions; GCA only covers 14 designated retailers.
- Data access unproven; demo synthetic only.
- Incumbent Esker has UK page and AI matching; others could add UK grocers.
- Would be proven wrong by: a UK supplier quote showing deductions staff cost under about GBP 5k a year, or Esker/ERP vendors listing Tesco/Sainsbury's/Asda connectors with SME pricing.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-26 G0 scout (T-142): evidence gathered; scout recommendation DROP unless a buyer or recovery-firm quote is obtained.
