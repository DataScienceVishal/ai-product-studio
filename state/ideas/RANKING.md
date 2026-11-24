# Idea ranking

Ordered by score, then build feasibility. The validator keeps this current.

Updated 2026-11-24 (T-4, T-11, T-22, T-28, T-31 and T-36 complete: 37 scored, 0 PASS, 9 KILL). No idea has passed G1 (70+) yet. Ties are broken by the Build score.

| Rank | Slug | Stage | Score | One-line pitch | Next step |
|---|---|---|---|---|---|
| 1 | pepr-packaging-data-pipeline | G0 (parked) | 68 | Turns SKU, bill-of-materials and supplier spec exports into recyclability evidence and a validated packaging data report, with a fee forecast (includes the PPT ledger as a later module) | Parked after T-13: Repackd already sells spec-sheet extraction, RAM scoring and fee simulation (£299-£1,999/month). Revive only if a Repackd trial (needs Vishal's OK to sign up) shows weak extraction on messy spec sheets |
| 2 | restaurant-margin-copilot | G0 (parked) | 66 | Photograph each supplier invoice; AI matches lines to recipes, recalculates dish margins and sends weekly fixes | Parked after T-9: Jelly (£129 per site a month) and MarketMan ($249) already read invoices, cost recipes and alert on margins; only a written weekly-fixes message was missing. Revive only with a channel Jelly doesn't serve, such as an accountant-led offer. 2026-11-24 T-39: the draft spec for Q-6 option B was checked and got REVISE (`products/restaurant-margin-copilot/SPEC-CHECK.md`). Score unchanged; the G1 attempt is not spent |
| 3 | mtd-quarterly-prep | G0 (parked) | 65 | Practices get sole traders' messy statements and receipts categorised into HMRC categories, with plain-English client queries | Parked after T-10: Dext Solo and Sage's MTD agent cover most of it. A narrower wedge (scans, photos and spreadsheets in, reviewed quarter totals out) waits for the T-12 extraction benchmark, which needs Azure OpenAI |
| 4 | holiday-pay-payroll-lookback-audit | G0 (parked) | 63 | Recomputes each worker's holiday pay from the payroll's own exports under the 2024 rules and lists the exceptions with the working shown, for a payroll professional to sign off | Parked after T-23: kill test passes (no incumbent documents a look-back), but there is no government response, no enforcement date and no FWA calculator scope yet. Re-check monthly; then T-24 data design and T-25 benchmark |
| 5 | sme-council-tender-drafting | G0 (REVISE) | 60 | Drafts compliant council tender answers from a service firm's own past bids | Park: CleanTender already sells this to the same niche. Re-score only for a segment none of the tools serve, sized from Contracts Finder |
| 6 | subcontractor-rams-drafting | G0 (REVISE) | 59 | Drafts site-specific RAMS from the principal contractor's site pack and a short job description | Fallback (easiest build). One desk check: principal contractors' public RAMS standards that no tool produces |
| 7 | b2b-win-loss-interviewer | G0 (REVISE) | 59 | AI interviews buyers after every closed deal and writes a weekly win-loss brief | Low priority: only re-score with a narrower wedge (churn interviews, lost-tender debriefs) |
| 8 | esos-phase4-evidence-pack | G0 (REVISE) | 58 | Builds the ESOS Phase 4 data and evidence pack for the lead assessor | Park (four-yearly; assessors bundle data collection). Ceiling about 62 |
| 9 | nhs-supplier-scope3-crp-pack | G0 (REVISE) | 57 | Builds an NHS-format carbon reduction plan from a supplier's ledger | Park until NHS publishes the 2028 product-footprint method. Ceiling about 60 |
| 10 | uk-cbam-import-ledger | G0 (REVISE) | 56 | Per-import ledger, £50k threshold tests and a return pack for UK CBAM from 2027 | Park: most importers fall under the threshold. Ceiling about 62 |
| 11 | merchant-whatsapp-order-desk | G0 (REVISE) | 56 | Turns tradespeople's WhatsApp messages and photographed lists into draft sales orders in the merchant's ERP | Desk check SalesApe, Klipboard and Otis pages and the BisTrack/Merlin import formats; consider merging with wholesale-email-order-entry-sage |
| 12 | fmcg-distributor-claim-reconciler | G0 (REVISE) | 55 | Reads brand scheme circulars, computes what the distributor is owed and matches credit notes | Needs a non-UK sales channel (Q-2); otherwise parked |
| 13 | wholesale-email-order-entry-sage | G0 (REVISE) | 55 | Turns emailed purchase orders into draft Sage 50/200 sales orders | Desk check: a free or cheap Sage 50/200 test route on Sage's developer pages, and whether Y Meadows supports Sage UK. Re-score only if both hold |
| 14 | sop-to-induction-course | G0 (REVISE) | 54 | Turns a company's SOPs into induction modules with traced answers and sign-off records | Park; re-score only with a legal forcing function (e.g. construction site inductions) |
| 15 | rates-2026-bill-recalculator | G0 (REVISE) | 54 | Recomputes each 2026/27 business rates bill from the rateable value, multiplier and reliefs, flags council errors and drafts the query | Park: Paddl already does this for multi-site hospitality at £69 per location a month. Re-score only with 30+ public wrong-bill cases or a segment Paddl doesn't serve |
| 16 | customs-entry-prep-small-forwarders | G0 (REVISE) | 54 | Pre-fills a checked CDS import entry from the client's invoice and packing list | Park low: free AI drafting tools already exist, and HMRC's 2026 survey puts the job at under half an hour |
| 17 | marketplace-return-claim-recovery-india | G0 (REVISE) | 54 | Matches marketplace orders, returns and payouts, and drafts claims before the window closes | Needs a non-UK sales channel (Q-2); otherwise parked |
| 18 | gem-bid-readiness-checker | G0 (REVISE) | 53 | Checks a GeM bid's eligibility conditions against the supplier's own documents | Needs a non-UK sales channel (Q-2); otherwise parked |
| 19 | vet-cma-compliance-desk | G0 (REVISE) | 53 | Builds the CMA price list from a practice system's export and monitors the estimate and complaint duties | Cheap desk check: does anyone charge vets for CMA monitoring? Otherwise park |
| 20 | letting-agent-repair-triage | G0 (REVISE) | 53 | Triages tenant repair messages and photos, drafts contractor and landlord messages, keeps an Awaab's Law log | Park until the government's response to the private-rented Awaab's Law consultation (closes 18 Dec 2026) |
| 21 | agency-whatsapp-timesheet-desk | G0 (REVISE) | 53 | Reads temps' timesheet photos, matches them to bookings and produces a payroll file | Park: Bullhorn Amplify Extract already does this |
| 22 | rates-2026-valuation-check-workbench | G0 (REVISE) | 53 | Compares each site's 2026 rateable value with similar properties on the Valuation Office list and drafts the Check case with the evidence | Park: Rightly Rated, BusinessRateChecker and RateRight already sell comparables checks and evidence packs. Ceiling about 58 |
| 23 | charity-fund-coder-for-xero | G0 (REVISE) | 52 | Codes a charity's Xero transactions to restricted and unrestricted funds during the year, from its grant agreements | Park (ceiling about 60): TaxCalc does the year-end SOFA, Access fund ledgers serve grant-heavy charities, shared-cost allocation can't come from grant text, and a chatbot with the grant terms is a substitute |
| 24 | haulier-whatsapp-pod-matcher | G0 (REVISE) | 51 | Matches drivers' proof-of-delivery photos to jobs and invoices | Park low; a second failure kills it |
| 25 | sme-multisite-energy-bill-checker | G0 (REVISE) | 51 | Recomputes each meter's energy invoice from the contract rates and published charges, and drafts queries on likely overcharges | Park: no forcing function; brokers give SME bill validation away |
| 26 | surface-water-drainage-rebate-evidence | G0 (REVISE) | 45 | Measures roofs and hard surfaces from open map data to support surface-water drainage rebate claims | Park; a second failure kills it |
| 27 | skip-hire-phone-booking-desk | G0 (REVISE) | 44 | AI phone agent that takes skip bookings into the firm's system | Park; needs a paid telephony provider and skip-specific evidence |
| — | ppt-recycled-content-ledger | merged | 51 | Plastic Packaging Tax recycled-content ledger | Merged into pepr-packaging-data-pipeline |

Killed (in `killed/`):
- homestay-rate-copilot-india (38) and bali-villa-rate-copilot (39): both fail the data red flag, because their value needs booking and market data the studio can't lawfully get.
- margin-scheme-dealer-desk (45): VAT Margin already sells margin-scheme VAT for non-vehicle resellers at £25-£79 a month.
- tour-operator-contract-rate-loader (59, T-31): TravelBox, Juniper and Travel Compositor already ship AI contract loading, and offshore contract-loading firms sell it as a service.
- wedding-venue-enquiry-agent (62, T-31, second failure): Perfect Venue, iVvyAI, Mikla and Hyperleap already sell AI enquiry replies, and there is no UK channel-share data or UK price.
- housing-complaint-response-qa (57, T-36): VerseOne already sells AI-drafted social-housing complaint responses, complaints systems (MRI, Crimson, Neo) sell compliance with the Code, Housemark and HQN sell reviews, and the Ombudsman decisions carry no reuse licence. Not a legal-advice product as scoped. Ceiling about 67.
- apprenticeship-evidence-preaudit (53, T-36): Bud already alerts on missing, unsigned and overdue evidence and sells "Funding confidence" under its agents line, and Aptem bundles an independent compliance review (ACAR). Minors' data at scale. Ceiling about 63.
- haulier-audit-workpapers (52, T-36): the buyers are about 50 DVSA-accredited audit providers plus consultants, with no current prices; records platforms (Samsara, Roadsoft, FleetCheck) hold the data. Ceiling about 60.
- mot-advisory-dealer-risk-score (51, T-36): Car Guide and VehicleStats already predict MOT failures from MOT history, MOTCost is free, and dealers pay £1 to £4 per trade check, which already includes the MOT history. Ceiling about 60.

**Pattern:** every idea lost most of its points on Competition (1 to 5 out of 10; four of the UK batch scored 1). By late 2026 incumbents ship "AI over your documents" as a standard or free feature, so a gap has to be checked on the competitor's own product pages, and the stronger wedges are ones incumbents can't easily follow: a regulatory deadline, deep domain workflow, a channel they don't serve, or liability they won't take.

**Round 2 (T-11).** Neither thesis beat round 1:
- Regulation-driven data ideas averaged 58.
- Channel and closed-system ideas averaged 51:
  - Meta now sells its own AI agent on WhatsApp.
  - The "closed" systems had APIs.
  - Vertical incumbents ship the channel feature.
  - A free practitioner-made tool closed the vet gap within weeks.
- Lessons for the next scout:
  - Check the channel owner's own AI and free community tools, as well as competitors' own pages.
  - Any idea whose value depends on a paid service (telephony, WhatsApp) loses most of its demo in mock mode.

**Round 3 (T-22).** Five UK finance, tax and data ideas averaged 53; none passed.
- The holiday-pay look-back audit (63) is the first idea whose gap is confirmed on the incumbents' own pages: BrightPay, Moneysoft and Sage 50 don't calculate holiday pay amounts, and Xero says a 52-week holiday pay report isn't on its roadmap.
- Both business-rates ideas were already sold by AI-native rivals built for the 2026 list (Rightly Rated, BusinessRateChecker, RateRight, Paddl).
- Why 30 ideas have produced no PASS, per the validator:
  - scouting starts from public deadlines that every vendor also sees;
  - desk-only evidence and the unknown partner sector cap Pay and Reach;
  - the gaps that survive tend to have deterministic cores (low AI) or personal data (low Risk).
- Lessons for the next scout:
  - keep the 70 bar;
  - run a ten-minute "<problem> tool 2026" search before writing any G0 file (it would have stopped both rates ideas);
  - look for incumbent refusals, such as help docs and idea forums where a widely used tool says it won't do a costly job, rather than new regulation.

**Round 4 (T-27, T-28): incumbent refusals.** The scout dropped 9 of 11 candidates at the add-on check; the 2 written scored 45 (killed) and 52.
- Lesson: a refusal shows a gap in one incumbent, not an empty market. Search for the job itself ("margin scheme software"), not only "<incumbent> add-on".

**Round 5 (T-31).** Two kills: tour-operator contract loader (59) and wedding venue enquiry agent (62, second failure).
- "Unstructured documents into the system of record" is the first AI feature vertical system vendors ship: TravelBox (July 2025), Juniper's AI Contract Builder and Travel Compositor's Dante (February 2026). Check the system vendors' blogs and release notes before writing the G0 file.
- If offshore firms already sell the task as a service (contract loading: Coforge, WNS, Unire, 247tpd), the pain is proven, but buyers already have a cheap option with human checking, and system vendors partner with those firms.
- A RAG receptionist is a feature of the vertical CRM (Perfect Venue AI Reply, iVvyAI), not a product.
- A website desk check shows which channels a business publishes, never the volume through each. Ask for evidence the studio can actually collect.

**Round 6 (T-36): public-data proof tests.** All four ideas were killed on the first attempt (57, 53, 52, 51), each with a ceiling below 70. A self-run proof test doesn't help when Competition and Pay fail first.
- Pay is still the weakest score. No idea had a published price for the job, only salaries, dated audit fees or adjacent per-unit prices.
- Lessons for the next scout:
  - In public-sector niches, read the G-Cloud listings before writing the G0 file. Four listings settled housing Competition in minutes, and their pricing PDFs are the next public source for Pay.
  - "Grounded in a regulator's or ombudsman's decisions" is a moat only if the decisions carry a reuse licence. Non-Crown bodies often publish without the OGL.
  - If the input is records held in a vertical system (an LMS, fleet software), that system's vendor is the main competitor, and some now bundle a human review too (Aptem ACAR).
  - Checker-side buyers (auditors, assessors) are a market capped by their headcount. Count them from gov.uk accreditation lists first.
  - Open datasets with a free government viewer already attract consumer and hobby scoring sites. Search "<dataset> predict/score" and the nearest per-unit data price before scoring Pay.
