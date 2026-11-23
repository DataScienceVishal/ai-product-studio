# Idea ranking

Ordered by score, then build feasibility. The validator keeps this current.

Updated 2026-11-23 (T-4 and T-11 complete: 25 scored, 0 PASS, 2 KILL). No idea has passed G1 (70+) yet.

| Rank | Slug | Stage | Score | One-line pitch | Next step |
|---|---|---|---|---|---|
| 1 | pepr-packaging-data-pipeline | G0 (REVISE) | 68 | Turns SKU, bill-of-materials and supplier spec exports into recyclability evidence and a validated packaging data report, with a fee forecast (includes the PPT ledger as a later module) | T-13 desk checks on Clarity, ERP, OPRL and PackTotal pages; T-14 spec-sheet extraction benchmark (needs Azure OpenAI). Best bet so far |
| 2 | restaurant-margin-copilot | G0 (REVISE) | 66 | Photograph each supplier invoice; AI matches lines to recipes, recalculates dish margins and sends weekly fixes | T-9: check Jelly, Profito and KitchenIQ on their own pages; independents' price sensitivity; then a 50-invoice synthetic extraction benchmark |
| 3 | mtd-quarterly-prep | G0 (REVISE) | 65 | Practices get sole traders' messy statements and receipts categorised into HMRC categories, with plain-English client queries | T-10: confirm the gap against Dext, AutoEntry and Xero help docs; test the add-on framing; verify the Wolters Kluwer 59% figure. Vishal's tax edge is the tiebreaker |
| 4 | wedding-venue-enquiry-agent | G0 (REVISE) | 63 | Answers every couple's venue enquiry within a minute from the venue's own brochure and books the show-round | Desk check of 20 UK venue sites: which channels enquiries arrive through. Kill on a second failure if directory messaging dominates |
| 5 | sme-council-tender-drafting | G0 (REVISE) | 60 | Drafts compliant council tender answers from a service firm's own past bids | Park: CleanTender already sells this to the same niche. Re-score only for a segment none of the tools serve, sized from Contracts Finder |
| 6 | subcontractor-rams-drafting | G0 (REVISE) | 59 | Drafts site-specific RAMS from the principal contractor's site pack and a short job description | Fallback (easiest build). One desk check: principal contractors' public RAMS standards that no tool produces |
| 7 | b2b-win-loss-interviewer | G0 (REVISE) | 59 | AI interviews buyers after every closed deal and writes a weekly win-loss brief | Low priority: only re-score with a narrower wedge (churn interviews, lost-tender debriefs) |
| 8 | wholesale-email-order-entry-sage | G0 (REVISE) | 55 | Turns emailed purchase orders into draft Sage 50/200 sales orders | Desk check: a free or cheap Sage 50/200 test route on Sage's developer pages, and whether Y Meadows supports Sage UK. Re-score only if both hold |
| 9 | fmcg-distributor-claim-reconciler | G0 (REVISE) | 55 | Reads brand scheme circulars, computes what the distributor is owed and matches credit notes | Needs a non-UK sales channel (Q-2); otherwise parked |
| 10 | customs-entry-prep-small-forwarders | G0 (REVISE) | 54 | Pre-fills a checked CDS import entry from the client's invoice and packing list | Park low: free AI drafting tools already exist, and HMRC's 2026 survey puts the job at under half an hour |
| 11 | marketplace-return-claim-recovery-india | G0 (REVISE) | 54 | Matches marketplace orders, returns and payouts, and drafts claims before the window closes | Needs a non-UK sales channel (Q-2); otherwise parked |
| 12 | sop-to-induction-course | G0 (REVISE) | 54 | Turns a company's SOPs into induction modules with traced answers and sign-off records | Park; re-score only with a legal forcing function (e.g. construction site inductions) |
| 13 | gem-bid-readiness-checker | G0 (REVISE) | 53 | Checks a GeM bid's eligibility conditions against the supplier's own documents | Needs a non-UK sales channel (Q-2); otherwise parked |
| 14 | letting-agent-repair-triage | G0 (REVISE) | 53 | Triages tenant repair messages and photos, drafts contractor and landlord messages, keeps an Awaab's Law log | Park until the government's response to the private-rented Awaab's Law consultation (closes 18 Dec 2026) |
| — | esos-phase4-evidence-pack | G0 (REVISE) | 58 | Builds the ESOS Phase 4 data and evidence pack for the lead assessor | Park (four-yearly; assessors bundle data collection). Ceiling about 62 |
| — | nhs-supplier-scope3-crp-pack | G0 (REVISE) | 57 | Builds an NHS-format carbon reduction plan from a supplier's ledger | Park until NHS publishes the 2028 product-footprint method. Ceiling about 60 |
| — | uk-cbam-import-ledger | G0 (REVISE) | 56 | Per-import ledger, £50k threshold tests and a return pack for UK CBAM from 2027 | Park: most importers fall under the threshold. Ceiling about 62 |
| — | ppt-recycled-content-ledger | merged | 51 | Plastic Packaging Tax recycled-content ledger | Merged into pepr-packaging-data-pipeline |
| — | merchant-whatsapp-order-desk | G0 (REVISE) | 56 | Turns tradespeople's WhatsApp messages and photographed lists into draft sales orders in the merchant's ERP | Desk check SalesApe, Klipboard and Otis pages and the BisTrack/Merlin import formats; consider merging with wholesale-email-order-entry-sage |
| — | vet-cma-compliance-desk | G0 (REVISE) | 53 | Builds the CMA price list from a practice system's export and monitors the estimate and complaint duties | Cheap desk check: does anyone charge vets for CMA monitoring? Otherwise park |
| — | agency-whatsapp-timesheet-desk | G0 (REVISE) | 53 | Reads temps' timesheet photos, matches them to bookings and produces a payroll file | Park: Bullhorn Amplify Extract already does this |
| — | haulier-whatsapp-pod-matcher | G0 (REVISE) | 51 | Matches drivers' proof-of-delivery photos to jobs and invoices | Park low; a second failure kills it |
| — | skip-hire-phone-booking-desk | G0 (REVISE) | 44 | AI phone agent that takes skip bookings into the firm's system | Park; needs a paid telephony provider and skip-specific evidence |

Killed (in `killed/`): homestay-rate-copilot-india (38), bali-villa-rate-copilot (39). Both fail the data red flag: their value needs booking and market data the studio can't lawfully get.

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

