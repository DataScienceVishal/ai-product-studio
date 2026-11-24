# Idea ranking

Ordered by score, then build feasibility. The validator keeps this current.

Updated 2026-11-24 (T-4, T-11, T-22, T-28, T-31, T-36, T-42, T-44, T-46, T-47, T-49, T-50, T-51 and T-57 complete, plus the mtd-quarterly-prep second attempt after T-12: 52 scored, 0 PASS, 25 KILL). No idea has passed G1 (70+) yet. Ties are broken by the Build score. T-57 re-scored the Competition row under the Q-10 wedge rule for five parked ideas. Only holiday-pay moved (63 to 64). Restaurant, tender, RAMS and win-loss have no evidenced wedge and are unchanged. pepr is re-scored separately after its benchmark.

| Rank | Slug | Stage | Score | One-line pitch | Next step |
|---|---|---|---|---|---|
| 1 | pepr-packaging-data-pipeline | G0 (parked) | 68 | Turns SKU, bill-of-materials and supplier spec exports into recyclability evidence and a validated packaging data report, with a fee forecast (includes the PPT ledger as a later module) | Parked after T-13: Repackd already sells spec-sheet extraction, RAM scoring and fee simulation (£299-£1,999/month). Revive only if a Repackd trial (needs Vishal's OK to sign up) shows weak extraction on messy spec sheets |
| 2 | restaurant-margin-copilot | G0 (parked) | 66 | Photograph each supplier invoice; AI matches lines to recipes, recalculates dish margins and sends weekly fixes | Parked after T-9: Jelly (£129 per site a month) and MarketMan ($249) already read invoices, cost recipes and alert on margins; only a written weekly-fixes message was missing. Revive only with a channel Jelly doesn't serve, such as an accountant-led offer. 2026-11-24 T-39: the draft spec for Q-6 option B was checked and got REVISE (`products/restaurant-margin-copilot/SPEC-CHECK.md`). Score unchanged; the G1 attempt is not spent. T-57 (wedge rule): Competition stays 3. "Less product for less money" has no evidence that Jelly prices out independents, and Profito, KitchenIQ and Kitchen Porter Tech are already cheaper. Moves only with a measured accuracy gap (the synthetic-invoice benchmark against a documented rival failure) or a partner channel that Jelly prices out |
| 3 | holiday-pay-payroll-lookback-audit | G0 (parked) | 64 | Recomputes each worker's holiday pay from the payroll's own exports under the 2024 rules and lists the exceptions with the working shown, for a payroll professional to sign off | Parked after T-23: kill test passes (no incumbent documents a look-back), but there is no government response, no enforcement date and no FWA calculator scope yet. Re-check monthly; then T-24 data design and T-25 benchmark. T-42: add Fair Work Solutions (UK NMW payroll-upload platform) to the kill test. T-57 (wedge rule): Competition 6 to 7, giving 64. The 2024 rules aren't handled by BrightPay or Xero (own pages) or by Moneysoft and Sage 50, and no product documents a look-back. The FWA calculator scope is the swing factor (one worker at a time: Competition 8 to 9; whole payroll: 2). Consultation outcome still unpublished on 2026-11-24 |
| 4 | sme-council-tender-drafting | G0 (REVISE) | 60 | Drafts compliant council tender answers from a service firm's own past bids | Park: CleanTender already sells this to the same niche. Re-score only for a segment none of the tools serve, sized from Contracts Finder. T-57 (wedge rule): Competition stays 1, because there is no wedge against CleanTender (£99, same niche) or BidWriter and Stotles (free tiers). Kill candidate |
| 5 | subcontractor-rams-drafting | G0 (REVISE) | 59 | Drafts site-specific RAMS from the principal contractor's site pack and a short job description | Fallback (easiest build). One desk check: principal contractors' public RAMS standards that no tool produces. T-57 (wedge rule): Competition stays 1. RAMSGen already drafts from the site pack, the price floor is £7 a RAMS, and no trade segment is ignored. Kill candidate |
| 6 | b2b-win-loss-interviewer | G0 (REVISE) | 59 | AI interviews buyers after every closed deal and writes a weekly win-loss brief | Low priority: only re-score with a narrower wedge (churn interviews, lost-tender debriefs). T-57 (wedge rule): Competition stays 3. User Intuition ($30 an interview, $0 Starter) serves the segment Clozd prices out, and Clozd's HubSpot app already automates invites |
| 7 | esos-phase4-evidence-pack | G0 (REVISE) | 58 | Builds the ESOS Phase 4 data and evidence pack for the lead assessor | Park (four-yearly; assessors bundle data collection). Ceiling about 62 |
| 8 | nhs-supplier-scope3-crp-pack | G0 (REVISE) | 57 | Builds an NHS-format carbon reduction plan from a supplier's ledger | Park until NHS publishes the 2028 product-footprint method. Ceiling about 60 |
| 9 | uk-cbam-import-ledger | G0 (REVISE) | 56 | Per-import ledger, £50k threshold tests and a return pack for UK CBAM from 2027 | Park: most importers fall under the threshold. Ceiling about 62 |
| 10 | merchant-whatsapp-order-desk | G0 (REVISE) | 56 | Turns tradespeople's WhatsApp messages and photographed lists into draft sales orders in the merchant's ERP | Desk check SalesApe, Klipboard and Otis pages and the BisTrack/Merlin import formats; consider merging with wholesale-email-order-entry-sage. T-44: fold in the killed merchant-supplier-price-file-loader findings (Merlin and BisTrack price imports, LUCKINSlive, Data Yard) |
| 11 | fmcg-distributor-claim-reconciler | G0 (REVISE) | 55 | Reads brand scheme circulars, computes what the distributor is owed and matches credit notes | Needs a non-UK sales channel (Q-2); otherwise parked |
| 12 | wholesale-email-order-entry-sage | G0 (REVISE) | 55 | Turns emailed purchase orders into draft Sage 50/200 sales orders | Desk check: a free or cheap Sage 50/200 test route on Sage's developer pages, and whether Y Meadows supports Sage UK. Re-score only if both hold. T-44: if revived, add remittance reading (killed sage-remittance-cash-allocator) as a second module, since it has the same Sage desktop buyer and route |
| 13 | sop-to-induction-course | G0 (REVISE) | 54 | Turns a company's SOPs into induction modules with traced answers and sign-off records | Park; re-score only with a legal forcing function (e.g. construction site inductions) |
| 14 | rates-2026-bill-recalculator | G0 (REVISE) | 54 | Recomputes each 2026/27 business rates bill from the rateable value, multiplier and reliefs, flags council errors and drafts the query | Park: Paddl already does this for multi-site hospitality at £69 per location a month. Re-score only with 30+ public wrong-bill cases or a segment Paddl doesn't serve |
| 15 | customs-entry-prep-small-forwarders | G0 (REVISE) | 54 | Pre-fills a checked CDS import entry from the client's invoice and packing list | Park low: free AI drafting tools already exist, and HMRC's 2026 survey puts the job at under half an hour |
| 16 | marketplace-return-claim-recovery-india | G0 (REVISE) | 54 | Matches marketplace orders, returns and payouts, and drafts claims before the window closes | Needs a non-UK sales channel (Q-2); otherwise parked |
| 17 | gem-bid-readiness-checker | G0 (REVISE) | 53 | Checks a GeM bid's eligibility conditions against the supplier's own documents | Needs a non-UK sales channel (Q-2); otherwise parked |
| 18 | vet-cma-compliance-desk | G0 (REVISE) | 53 | Builds the CMA price list from a practice system's export and monitors the estimate and complaint duties | Cheap desk check: does anyone charge vets for CMA monitoring? Otherwise park |
| 19 | letting-agent-repair-triage | G0 (REVISE) | 53 | Triages tenant repair messages and photos, drafts contractor and landlord messages, keeps an Awaab's Law log | Park until the government's response to the private-rented Awaab's Law consultation (closes 18 Dec 2026) |
| 20 | agency-whatsapp-timesheet-desk | G0 (REVISE) | 53 | Reads temps' timesheet photos, matches them to bookings and produces a payroll file | Park: Bullhorn Amplify Extract already does this |
| 21 | rates-2026-valuation-check-workbench | G0 (REVISE) | 53 | Compares each site's 2026 rateable value with similar properties on the Valuation Office list and drafts the Check case with the evidence | Park: Rightly Rated, BusinessRateChecker and RateRight already sell comparables checks and evidence packs. Ceiling about 58 |
| 22 | charity-fund-coder-for-xero | G0 (REVISE) | 52 | Codes a charity's Xero transactions to restricted and unrestricted funds during the year, from its grant agreements | Park (ceiling about 60): TaxCalc does the year-end SOFA, Access fund ledgers serve grant-heavy charities, shared-cost allocation can't come from grant text, and a chatbot with the grant terms is a substitute |
| 23 | haulier-whatsapp-pod-matcher | G0 (REVISE) | 51 | Matches drivers' proof-of-delivery photos to jobs and invoices | Park low; a second failure kills it |
| 24 | sme-multisite-energy-bill-checker | G0 (REVISE) | 51 | Recomputes each meter's energy invoice from the contract rates and published charges, and drafts queries on likely overcharges | Park: no forcing function; brokers give SME bill validation away |
| 25 | surface-water-drainage-rebate-evidence | G0 (REVISE) | 45 | Measures roofs and hard surfaces from open map data to support surface-water drainage rebate claims | Park; a second failure kills it |
| 26 | skip-hire-phone-booking-desk | G0 (REVISE) | 44 | AI phone agent that takes skip bookings into the firm's system | Park; needs a paid telephony provider and skip-specific evidence |
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
- nmw-salaried-hours-audit (55, T-42): Fair Work Solutions already sells a UK NMW platform (payroll upload, pay codes and deductions, underpayments per worker and pay period in HMRC's format, monitoring); payroll and rota checks, HMRC's free self-review guide and many advisers surround it. Ceiling about 60.
- dmcc-checkout-journey-auditor (52, T-42): Total Price already walks browse-to-checkout journeys for hidden fees, urgency timers and pre-ticked extras, with monthly monitoring at £14.99 a month; TrustYourWebsite scans free; the CMA runs agentic AI over journeys itself. Ceiling about 59.
- uk-export-classification-workbench (50, T-42): the gap is a free ECJU service paused on 12 Oct 2026 with an update due by year end, and the same service came back in 2018 after a four-year suspension; Trademo, Digicust, traide AI and EC Compliance already sell AI dual-use classification from specs; no price; a wrong rating is the buyer's offence. Ceiling about 61.
- sage-remittance-cash-allocator (57, T-44): RemitClear (a UK firm) already reads remittances and allocates them in Xero, QuickBooks Online and Sage Accounting according to its own site, and Sage 50 importers (PostTrans, Adept, Excel2Sage) already post allocated receipts. Only desktop Sage is left, which is the same blocked route as wholesale-email-order-entry-sage. Ceiling about 62. The file is still in `state/ideas/`; the lead should git mv it.
- merchant-supplier-price-file-loader (53, T-44): Merlin's Price Update and BisTrack's import already load supplier price files, LUCKINSlive feeds prices into wholesaler ERPs (Profit4, Intact, OrderWise), BMF and NMBS run the Data Yard pool, and TableFlow sells the AI extraction. The only evidence on Pay is a modelled salary. Ceiling about 60. The file is still in `state/ideas/`; the lead should git mv it.
- [section13-market-rent-evidence-desk](killed/section13-market-rent-evidence-desk.md) (57, T-46): MarketRent (the Fixflo co-founders, April 2026) already sells a rent-review platform with comparables, a rent suggestion and a tribunal-ready pack. LonRes Rental Checker reports from achieved rents, PropertyData includes rental valuations from £15 a month, and Rightmove and Goodlord serve the notice. Good comparables need achieved or licensed data, and the AI is only the narrative. Ceiling about 62. The file is still in `state/ideas/`; the lead should git mv it.
- [food-supplier-cost-price-increase-pack](killed/food-supplier-cost-price-increase-pack.md) (57, T-46): no supplier-side tool was found, but a CPI happens once or twice a year per retailer (no basis for a subscription; only FD day rates and unpriced workshops), and the core is a weighted cost change. Buyers already run Expana's AI cost models against supplier increases. Ceiling about 63. The file is still in `state/ideas/`; the lead should git mv it.
- [dental-nhs-contract-delivery-desk](killed/dental-nhs-contract-delivery-desk.md) (47, T-47): Dentally's product team has been designing NHS contract-performance reporting with practices since May 2026; EXACT already sells a predictive UDA manager; CareStack reports 2026 unscheduled care and claim exceptions; NHSBSA's Compass and eDEN views are free. The core is arithmetic, there is no price for the job, and the API is partner-only (no practice tokens). Admin only, so not off-limits. Ceiling about 58. The file is still in `state/ideas/`; the lead should git mv it.
- [accountancy-hmrc-post-triage](killed/accountancy-hmrc-post-triage.md) (47, T-47): Karbon AI triage already labels, attaches to the client and creates tasks (Kai, June 2026, adds routing), TaxDome AI files every document on arrival, and Taxfly's free decoder reads HMRC letter types. HMRC has been digital by default since April 2026, so post moves to taxpayers' accounts. One volume figure, no price, personal data on every page. Ceiling about 58. The file is still in `state/ideas/`; the lead should git mv it.
- [trade-job-extras-invoice-guard](killed/trade-job-extras-invoice-guard.md) (46, T-47): no vendor detects unbilled extras yet, but ServiceM8 drafts invoice items from the job with AI and exposes jobs to ChatGPT and Claude through MCP. The only gap is a WhatsApp thread that a free chatbot can read when pasted in, and live capture needs a behaviour change or the paid Business API. No price. Ceiling about 55. The file is still in `state/ideas/`; the lead should git mv it.
- [uk-eu-origin-evidence-desk](killed/uk-eu-origin-evidence-desk.md) (53, T-49): not enterprise-only after all. iCustoms sells a TCA Rules of Origin module (BOM test, CTH, CTSH and MaxNOM, kept as evidence) to importers, exporters and forwarders, with a register button on its homepage. GOV.UK's trade tariff rules-of-origin check and EU ROSA do the per-product test free. Chambers of commerce (Business West Genesis and consultancy at £120-£180 an hour) are both the channel and the competitor. The core is deterministic and the only Pay evidence is one-off consultancy; there is no forcing function. Ceiling about 62. The file is still in `state/ideas/`; the lead should git mv it.
- [sme-quote-price-guidance](killed/sme-quote-price-guidance.md) (50, T-49, data red flag): uplift over the firm's own pricing can only be shown on real won and lost quote histories. The studio can't get them, and about a third of distributors don't measure win rates at all (Phocas 2026 survey). The leakage half is served by the Sage 200 Price Book, Phocas margin floors and the free Cavallo Profit Scan. Pain evidence is vendor-authored and the only prices are mid-market (PriceEdge €1,490 a month). Ceiling about 60. The file is still in `state/ideas/`; the lead should git mv it.
- [sap-design-stage-input-desk](killed/sap-design-stage-input-desk.md) (48, T-50): Specvo's SAP Copilot (live, private beta for OCDEAs) already reads the planning pack, extracts rooms, walls, openings, build-ups and thermal bridges with confidence scores and links to the source page, and exports Elmhurst Design SAP 10 XML at £30 per XML, with a HEM preview and SAP 10.3/FHS on its roadmap. SAPPER gives AI drawing extraction away free for extensions. The buyers are a few thousand OCDEAs under one scheme and software owner (Elmhurst). HEM is not the threat (FHS starts on 24 March 2027 on SAP 10.3, and HEM has been delayed with no date). Ceiling about 55.
- [uk-cosmetic-cpsr-assessor-workbench](killed/uk-cosmetic-cpsr-assessor-workbench.md) (47, T-50 second pass): OrAIsi already sells the same pitch to safety assessors (it reads formulas and SDS "in any source format", computes SED, NOAEL and MoS per ingredient, and assembles the PIF with Part A and Part B for the assessor to sign). Ecomundo COSMETIC Factory (MoS "in one click", a toxicology database, AI document modules, an EU/UK office), Coptis Tox (automatic formula toxicology profiles and MoS) and Cosmetri (assessors sign Parts A and B in the PIF) cover the rest. Curated ingredient toxicology data is the incumbents' moat, and there is no lawful, comprehensive free source. There is no register or count of UK assessors, and the price war from £70 caps a bureau's software spend. It is not off-limits (product-safety compliance, not medical advice, and the assessor keeps the liability), but it is health-adjacent. Ceiling about 55.
- [independent-hire-rate-advisor](killed/independent-hire-rate-advisor.md) (43, T-51, data red flag): rate uplift can only be shown on real hire histories, which the studio can't get. Pain evidence comes only from pricing vendors, and inspHire's own blog says hire firms want to set their own prices. No SMB price exists for rate advice. Point of Rental's AI Insights (UK site) already answers "Where am I under-pricing relative to demand?" with the working shown, and Rouse gives about 80 UK contributors invoice-based rate and utilisation benchmarks. MCS ships rule-based peak pricing. No public HireHop API documentation was found. Fourth pricing-uplift idea killed on the data red flag; stop that thesis until a data partner exists. Ceiling about 55.
- mtd-quarterly-prep (64, after T-12, second failure): the benchmark failed the idea's own test. Model-only review time was 59-72% of manual and never halved; the halving needs a merchant-memory rules layer that Dext (bank and supplier rules) and IRIS (remembered categories) already ship. The scan and photo wedge was barely measured, and Dext Solo's £2.50 per client caps Pay.

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

**Round 7 (T-42): public enforcement costs.** All three were killed on the first attempt (55, 52, 50), each with a ceiling of about 60. The public-cost thesis found real pain each time, but public enforcement is a signal every builder sees.
- Each idea had a direct competitor the scout's search missed: Total Price (DMCC, £14.99 a month), Fair Work Solutions (NMW), Trademo and the EU dual-use classifiers (export). Two are small single-purpose UK firms set up for a new rule or regulator.
- Lessons for the next scout:
  - Search "<regulation or regulator> checker / scan / platform / solutions", not only "<problem> software", and look at recent Companies House incorporations named after the rule.
  - If the regulator runs the same AI technique itself (the CMA's agentic journey monitoring), AI shows feasibility, not a moat.
  - A "free official service closed" gap needs the service's history: ECJU's CLC was suspended from 2014 to 2018 and came back.
  - For harmonised lists (UK and EU dual-use), check the larger jurisdiction's vendors first.
  - Pay is still the weakest score: only adviser fees (Muckle £500 to £1,500 + VAT per area) and a £14.99 scanner were found.

**mtd-quarterly-prep kill (2026-11-24, after the T-12 benchmark).** It was the first idea to get a real model benchmark, and the benchmark killed it.
- Lessons for the next scout:
  - Write the kill test as a number, then run the cheapest benchmark that could fail it before spending a second gate attempt.
  - In bookkeeping, most "AI categorisation" savings come from per-merchant memory, a rules layer incumbents already have. Measure accuracy on the ambiguous lines a human reviews (87.5% here), not on clear lines (98.9%).
  - If the wedge is an input type (scans, photos), benchmark that input first; the easy digital formats only prove what incumbents already sell.
  - Check a model's cost per document against the $80 credit before designing a benchmark.

**Round 8 (T-44): start from a priced job.** Both ideas were killed on the first attempt (57, 53), each with a ceiling of about 60. The validator agrees with the scout: SME "documents into the ledger or ERP" work is now a closed space.
- In both cases the scout's gap was disproved by sources outside the marketplace listing it had checked:
  - RemitClear's own homepage shows it already supports QuickBooks and Sage Accounting, which its Xero listing did not show.
  - Sector data services (LUCKINSlive, Data Yard) already feed supplier prices into merchant ERPs.
- Lessons for the next scout:
  - Fetch the competitor's homepage.
  - Search for the sector's data pool or aggregator, and for the existing desktop import add-ons that set the price of the non-AI half.
  - Next round, try jobs whose output is a judgement or recommendation (pricing, forecasting, exception detection) rather than extraction.

**Round 9 (T-46): judgement outputs.** Both ideas were killed on the first attempt (57 and 57).
- The Section 13 desk lost on Competition (2). A statutory process that started on 1 May 2026 had already drawn four launches, including MarketRent from the Fixflo founders.
- The CPI pack had the round's only open gap, but it lost on Pay (6) and AI (7): the job is seasonal and the core is arithmetic.
- Lessons for the next scout:
  - Search the trade press for "<process> platform launched".
  - For a recommendation job, find out who owns the transaction data before scoring Build.
  - Check how often the job happens: yearly jobs don't support a subscription.
  - Look at what the other side of the negotiation already buys.

**Round 10 (T-47): marketplace add-ons.** All three were killed on the first attempt (47, 47, 46), each with a ceiling of 55 to 58. This is the weakest round since round 1.
- An empty marketplace category was not a gap.
  - Dental: the platform owner was already designing the feature with its users (Dentally community post, May 2026).
  - HMRC post: the practice platforms already sell AI inbox triage (Karbon, TaxDome).
  - Trades: the system exposes its jobs to general assistants through MCP (ServiceM8).
- Pay scored 4 to 5 every time. No add-on job had a public price, because the value is bundled into the host system's subscription.
- Lessons for the next scout:
  - Before writing a marketplace add-on, search the host's community for "we're building" or "help shape" posts, and read the host's own feature pages for the job.
  - Check the host's rival systems (EXACT, CareStack) for the same feature, because in vertical software it gets bundled.
  - Score against the cheapest substitute: the user pasting the input into a free chatbot, or the host's MCP connector.
  - Check whether the input channel is itself moving (HMRC digital by default from April 2026).
  - Recommendation: stop the marketplace-add-on thesis. Next round should start from jobs where buyers already pay a third party per unit (agency, bureau or outsourced fees), so that Pay starts above 10.

**Round 12 (T-49): down-market from enterprise.** Both ideas were killed on the first attempt (53 and 50), each with a ceiling of about 60. The scout's own cheap tests dropped 17 of 19 candidates because SMB tools existed.
- "Enterprise-only" failed both times. The origin desk had a mid-market vendor selling to SMEs and forwarders (iCustoms) and free government rule checkers (GOV.UK trade tariff, EU ROSA). The quote tool had ERP price books, margin-floor alerts and a free marketplace tier (Cavallo Profit Scan).
- Pay stayed at 7 to 8. The only SME-side prices were consultant day rates (one-off, which argues against a subscription) and mid-market licences.
- A "learns from your history" product needs labels that SMEs actually record. Lost quotes often aren't recorded, and synthetic data can't prove uplift, so the data red flag applies.
- Lessons for the next scout:
  - Test "enterprise-only" on the mid-market vendor's homepage (register or "Start Now" buttons), the free government tool and the ERP marketplace's free tier before writing the G0 file.
  - Chambers of commerce and trade bodies sell document and validation services themselves, so treat them as competitors as well as channels.
  - The thesis has now failed both ways: SME AI tools exist for generic jobs, and the trade-specific gaps have deterministic cores and one-off demand. Recommendation: drop this thesis and return to the round-10 advice, starting from jobs bought per unit from a bureau or agency.
