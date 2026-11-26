# T-143 scout (round 21): new 2026-27 rules that create recurring per-firm work (2026-11-26)

Method: started from rules with a 2026-27 date, checked the AI or software vendor price first, then the outsourced price. 20 WebSearch calls and 7 WebFetch calls, all accessed 2026-11-26. Claims marked (fetched) come from a page I read; (summary) means a WebSearch result summary only. No injection attempts seen. Nobody contacted. No other file touched. Does not repeat anything ranked or killed (nearest: killed section13-market-rent-evidence-desk, parked letting-agent-repair-triage, T-141 candidate 7 on block accounts).

Result: 10 tested, 1 KEEP (low confidence), 9 DROP.

## 1. Leasehold service-charge reform: prescribed demands, standard accounts, annual report (KEEP, low confidence)
- Pitch: for small managing agents and RTM/RMC companies, build each block's budget, prescribed-format demand and standardised accounts pack from the invoices and ledger, with budget-versus-last-year and an annual building report, ready for a qualified accountant's report.
- Buyer: independent managing agents (roughly 5 to 200 blocks) and self-managed RTM companies in England. Social landlords come a year later.
- Rule and dates (fetched, CMS law-firm summary of SI 2026/1128): 1 April 2027 prescribed future-demand notice and right to request information; 1 November 2027 prescribed demand form, standardised accounts with a qualified-accountant report for relevant buildings, annual report, insurance-commission ban and published admin-charge schedule; social landlords 1 November 2028. A non-prescribed demand means the lease's non-payment provisions do not apply. https://cms.law/en/gbr/legal-updates/leasehold-reform-dates-set-for-service-charge-and-litigation-costs-changes. Statute: https://www.legislation.gov.uk/ukpga/2024/22/contents. Detailed prescribed forms are "separate regulations"; the Qualified Accountant Regulations are still draft (summary, CMS: https://cms.law/en/gbr/legal-updates/leasehold-reform-detailed-new-service-charge-rules-published).
- Recurring: per demand (twice a year or more) and annually, per block.
- Pain signals: (1) the statutory consequence above is the pain (fetched). (2) Trade article names invoice-to-ledger as the bottleneck (summary: https://www.flat-living.co.uk/?p=25800, vendor-side). (3) First-tier Tribunal cut a block's management fee to GBP 225 a unit and treated accountancy costs as unreasonable (summary: https://assets.publishing.service.gov.uk/media/6979ff68d6ab92f1d3a4d741/CAM-34UD-LSC-2024-0012_Scott_Schedule__MT_Final_.pdf).
- Price points: Ringley ServiceChargeSorted "from GBP 525 per annum" or "from GBP 54 per month" (the page gives both), year-end service charge accounts included but not 1985 Act certification, trading-company accountant fee not stated (fetched, https://ringley.co.uk/block_management/service_levels). Blockman from GBP 195 a month to GBP 450 for 2,000 units (summary, a listing site; G2 says the vendor gave no price: https://softwarereview.com/s/blockman). PropLinker from GBP 24 a month (summary, https://www.capterra.com/p/10044279/PropLinker/). No accounts-only fee found.
- Incumbents: Fixflo, Blockman, PropLinker, Inox, Arthur, Qube, MRI, Alto. No page I fetched or searched shows an AI service-charge budget or prescribed-demand product; vendor release notes for the new form were not found and the form is not yet published, so all vendors are on the same start line. Not verified on each vendor's own page (summary only).
- AI vendor price check (first step): no AI service-charge product with a price found (summary). Flat Living mentions AI invoice batch processing without a named product.
- Wedge: forcing function with a date and a draft-statutory "qualified accountant" sign-off that practice-management vendors will not take on. Sign-off stays with the accountant, so the product prepares, a human certifies.
- Doubts (large): the core is a deterministic form fill, so AI is mainly invoice-to-service-charge-head coding and the accounts narrative; platform vendors can ship the prescribed form in a month once it is published; the Pay price for the job (accounts-only) is unproven; the prescribed form is not final so a demo can only use the 2025 consultation draft (Annex B, https://assets.publishing.service.gov.uk/media/684bfe2a928e5ebb68e3f95c/ANNEX_B_-_Service_charge_demand_form.odt, summary-only). Demo with synthetic block ledgers is possible. Needs a validator test: wait for the final form and check Qube, MRI and Alto release notes before scoring.

## 2. Umbrella-company joint and several liability, from 6 April 2026 (DROP)
- Rule (fetched, GOV.UK): agencies must run "regular, reasonable and proportionate" checks and keep records; list includes payslip checks, reconciliation statements, Companies House, bank name. https://www.gov.uk/guidance/responsibilities-for-employment-businesses-working-with-umbrella-companies
- AI vendors already exist (summary): SafeRec reads and audits umbrella payslips with AI (LITRG's free worker audit runs on it), Giant Group CompliancePro with SafeRec, FCSA veriPAYE, People Group Services portal. No prices published. https://www.litrg.org.uk/working/umbrella-company-workers/free-umbrella-company-payslip-audit, https://www.fcsa.org.uk/veripaye-by-fcsa/
- Outsourced price: none found. DROP: direct AI incumbent, REC-promoted.

## 3. EU Pay Transparency Directive, first reports 7 June 2027 (DROP)
- Rule (summary, law firms): transposition deadline 7 June 2026 missed by most states; first reports for 150+ staff on 7 June 2027; non-EU employers with EU staff in scope. https://www.morganlewis.com/pubs/2026/06/eu-pay-transparency-directive-the-deadline-for-transposition-has-passed-what-now
- Software priced: Syndio from USD 5 per user a month (summary); Deel, Workday, ADP, PayGapCheck, PAY_transparency, orbiq sell it. https://www.capterra.com/p/10045940/PayGapCheck/. Mostly 150+ employee firms, out of reach for a two-person seller. DROP.

## 4. Companies House software-only filing and full P&L for small companies (DROP)
- The April 2027 date is dead: GOV.UK and ICAEW say April 2028 (summary). https://www.gov.uk/government/news/companies-house-to-bring-in-changes-to-accounts-filing-from-april-2028. Outside the brief's window, and accounts software (Xero, CCH, IRIS) will carry it. DROP.

## 5. Guaranteed-hours offers for zero and low hours workers, expected 2027 (DROP, watch)
- Offer must be repeated each reference period (government preference 12 weeks); consultation closed 25 August 2026, response awaited, start "2027" or "Autumn 2027" (summary). https://www.cipd.org/en/about/blogs/era25-what-zero-hours-contract-rules-mean/, https://www.burges-salmon.com/our-thinking/era-reforms-in-depth-zero-low-hours-and-shift-workers/
- Rules not final (threshold, period, mean or median); no priced outsourced service; rota and payroll vendors own the data. DROP until the response, then re-check. It would be a strong recurring job (per worker, per period).

## 6. Mandatory payrolling of benefits in kind, 6 April 2027 (DROP)
- Phase 1 company cars, vans and fuel and employer-provided medical cover; phase 2 April 2028 (summary, HMRC pages: https://www.gov.uk/guidance/prepare-for-mandatory-payrolling-of-benefits-in-kind). Payroll software handles the FPS submission; ADP, Sage and ICAEW already publish prep guidance. No bureau or software price found. The core is arithmetic inside payroll software. DROP.

## 7. Digital waste tracking (DROP)
- Receiving sites mandatory 1 October 2026 (England, Wales), January 2027 Scotland; carriers October 2027 (summary, Clyde & Co: https://www.clydeco.com/en/insights/2026/08/on-the-horizon-digital-waste-tracking-becomes-mand).
- Defra's own list holds 266 self-certified software providers, including skip and weighbridge tools and three with "AI" in the name; no prices (fetched, https://www.gov.uk/government/publications/report-receipt-of-waste-choose-a-software-provider/report-receipt-of-waste-choose-a-software-provider). Saturated. DROP.

## 8. Private-rented sector database registration (DROP)
- GBP 65 per property per year, registration opens 15 December 2026, regional deadlines from 14 March 2027; agents cannot register for landlords (fetched, NRLA: https://www.nrla.org.uk/resources/renters-rights/landlord-database-register-your-rental-property-service). A form the landlord must complete personally; nothing for AI. DROP.

## 9. Martyn's Law standard tier (DROP)
- Royal Assent 3 April 2025, enforcement about April 2027, 200 to 799 capacity (summary). Government's own cost estimate is about GBP 330 a year per premises, mostly staff time (summary, https://www.protectuk.police.uk/sites/default/files/2026-04/46.39_HO_Martyns%20Law_Myth_buster_Final_WEB.pdf). No consultant or software price found. Too small a spend; free ProtectUK guidance. DROP.

## 10. EUDR due diligence statements (DROP)
- Large operators 30 December 2026, micro and small by 30 June 2027; micro and small primary operators get a simplified one-time declaration (summary). Priced vendors: Live-EO EUR 15 per supplier a month up to 20, IntegrityNext fixed annual price, osapiens (summary, https://www.live-eo.com/tradeaware-pricing). AI-priced incumbents exist. DROP.

## Lessons
- Every rule I checked with a firm date already had an AI or software vendor with a listed price (umbrella, pay transparency, EUDR, waste tracking) or was unfinished (guaranteed hours, prescribed service-charge forms) or moved (Companies House).
- The only rule where the vendor field was still empty is the one where the detailed regulations are unpublished. That is the same reason the gap exists and the reason it may close fast. Re-check candidate 1 after the final prescribed form is published.
- Pay is again the weak point: only bundled management fees (Ringley) and generic software prices.
