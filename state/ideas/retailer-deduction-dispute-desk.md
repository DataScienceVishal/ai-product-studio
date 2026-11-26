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
| 13 | 7 | 8 | 6 | 7 | 2 | 8 | 51 |

## Gate log
- 2026-11-26 G0 scout (T-142): evidence gathered; scout recommendation DROP unless a buyer or recovery-firm quote is obtained.
- 2026-11-26 G1 validator (T-142): 51, REVISE (first G1 failure, no red flag). No public fee was found, and a UK supplier-side incumbent the scout missed (Salitix) already sells recovery to grocery suppliers with no upfront fee. A second failure kills it. See the Validator (T-142) section.

## Validator (T-142)

Verdict: **REVISE, 51/100** (first G1 attempt; pipeline.md kills only on a second failure or a red flag). Ceiling about 58. Park low. The board's "drop if no public fee is found" condition is met, so this should not get more scouting time unless the revive evidence below turns up for free.

Top reason: no UK fee exists for the job, and the supplier-side market is already served in the UK. **Salitix** is a profit-recovery sales auditor "working exclusively with grocery suppliers", is an FDF professional affiliate, and handles retailer audit claims and trade-spend recovery "without upfront cost" (contingency model, rate not published). Esker also sells Claims & Deductions to a UK food supplier selling through supermarkets. So the wedge comes down to "cheaper for the smallest suppliers", and nothing evidences that.

### Spot checks (validator, 2026-11-26)
1. **Published UK recovery fee: none found (confirms the scout).** Searches for no-win-no-fee, contingency and success-fee terms found only retailer-side audit fees (The Grocer: more than 20% common a decade ago, some first-audit fees now below 10%; https://www.thegrocer.co.uk/suppliers/forensic-auditors-how-they-pile-pressure-on-suppliers/354535.article, search summary only). Those are what retailers pay to audit suppliers, not what suppliers pay.
2. **UK supplier-side incumbent: Salitix (the scout missed it).** Grocery Gazette feature (https://www.grocerygazette.co.uk/?p=117688), FDF affiliate listing (https://www.fdf.org.uk/fdf/about-fdf/professional-affiliates/salitix-ltd), Retail Bulletin Q&A with its CRO, 1 Jul 2026 (https://www.theretailbulletin.com/retail-solutions/qa-ben-lewis-chief-revenue-officer-salitix-ltd-01-07-2026/, HTTP 403 on fetch). Vendor claim: it recovers on average 5% of net profit, with no upfront fees. All of this is from search summaries; I did not open salitix.com. Salitix proves that suppliers pay for this, but it gives no figure.
3. **Esker covers UK grocery suppliers.** The All About Food customer story, fetched 2026-11-26 (https://www.esker.com/resources/customer-story/all-about-food/), describes a UK food company (GBP 130m revenue, about 180 staff, Sage 200) selling "through major supermarkets and wholesalers". It uses Esker Cash Application plus Claims & Deductions, and Esker reports short-payment resolution 97% faster and DSO down from 95 to 79 days. No retailer is named, so Esker does not need retailer connectors to serve this market. The company is above the target's 5 to 100 staff band, so the small-supplier gap stays open but unevidenced.
4. **YouGov pain item.** A search summary of the 2025 GCA YouGov deck (https://assets.publishing.service.gov.uk/media/68dd3fdb8c1db6022d0c9fbb/YouGov_slides_-_GCA_Annual_conference_2025.pdf) confirms that "not allowing time (30 days) to challenge proposed invoice deductions, or deducting even if challenged" is a tracked issue. I did not open the slide to check the roughly 51% figure.

### Score
| Criterion | Score | Evidence and reasoning |
|---|---|---|
| Pain /20 | 13 | Real and regulator-recognised. GCA 2026 survey: 20% of suppliers raised invoice-discrepancy handling. The GCA forensic-auditing statement documents the 30-day and deduct-anyway practice. The YouGov deduction item is tracked in both 2025 and 2026 (about 51% is from a search summary). There is a job ad for an in-house deductions analyst. Held back because no frequency or cost figure exists for small suppliers, and the GCA's 2026/27 priorities don't name deductions (no forcing function) |
| Pay /20 | 7 | Buyers do pay: Salitix contingency, Esker licences, in-house analysts. But there is no public price: no fee, no software price (Esker, SPS, Promomash and Roma are all quote-only), one non-food salary estimate and two unverified credit-controller salaries. The G1 minimum of "2 competitor prices or a clear substitute cost" is not met. Contingency pricing also undercuts a subscription, because a supplier who pays only on recovery has no reason to pay monthly |
| AI advantage /15 | 8 | Reading varied remittances and reason codes and drafting a dispute that cites GSCOP is real LLM work. But the core is matching deductions to POs, PODs and promotion terms (mostly deterministic once extracted), Esker already ships AI capture and matching, and GSCOP wording is public. Copyable in weeks |
| Reachability /10 | 6 | The buyers can be found: the FDF and its affiliates, GCA supplier events, The Grocer, regional food groups. The partner sector is unknown, Salitix already holds the FDF channel, and selling is locked |
| Build feasibility /15 | 7 | The extraction, matching and drafting are buildable on the stack at low Azure cost. But retailer remittance and deduction layouts sit behind portal logins (Tesco Partners Toolkit, Sainsbury's), so the demo would run only on synthetic layouts, and matching needs the supplier's ERP, POD and promotion data. This is not a red flag (an extraction flow can be shown on synthetic data, as in T-56), but accuracy on real layouts can't be shown, which repeats the restaurant and pEPR lesson |
| Competition /10 | 2 | Wedge rule: there is no evidenced advantage over the incumbent the buyer would otherwise pay. That incumbent is Salitix for a UK grocery supplier (no upfront cost, so "cheaper" is hard to claim), with Esker for mid-size suppliers. GSCOP-specific letters are a feature a UK recovery firm already applies by hand. "Priced out" has no evidence because nobody publishes a price |
| Risk /10 | 8 | Commercial data only, no personal data at scale. Small deductions: dispute letters citing the Code sit close to legal drafting (not advice as scoped), and a wrong dispute could harm the supplier's relationship with the retailer |
| **Total** | **51** | |

Red flags: none fire. Not an off-limits area, no paid service dependency, no scraping. The data flag is near: if a reviewer holds that the value is accuracy on real retailer layouts, it would fire.

### What would change my mind (revive evidence, all needed)
1. A published or quoted price for the job: a Salitix or other UK recovery firm's contingency rate, or a deductions-software price that a 5 to 100 staff supplier pays. This needs contact, which is locked until `unlock selling`.
2. Evidence that Salitix and Esker turn away or price out small suppliers, for example a minimum-recovery threshold or minimum turnover on their own pages.
3. A public sample or spec of at least one designated retailer's remittance or deduction-notice format (CSV or PDF fields), so that the demo isn't purely invented.
Without points 1 and 2, Pay stays at about 8 and Competition at about 3, and the ceiling is about 58.

### Lessons
- For any "supplier versus big buyer" money-recovery job, search for the supplier-side recovery auditor and the trade body's affiliate list (FDF professional affiliates) before writing the G0 file. Here the market was already served by a contingency firm the scout's software-only search missed.
- A contingency incumbent makes the "cheaper" wedge almost impossible to evidence, because the buyer pays nothing up front. It also argues against a subscription.
- This confirms the T-141 lesson. Where no public price exists, desk research can't lift Pay above about 8. Stop scouting jobs whose only price is behind a quote or a contingency agreement until selling is unlocked.
