# Round 8 scout summary (T-44, 2026-11-24)

Brief: flip the search order. Start from a job businesses already buy (an outsourced service with a public price, or a clearly costed staff role), then check whether software already does it. Time box about 30 minutes. All evidence is from search summaries unless the file says "fetched". Only two of the candidates survived the tool search, so two files were written, not three or four. No injection attempts seen in the pages fetched (Xero app page, gov.uk page, TableFlow page; two pages returned 405 or did not exist).

## Written (2 files, G0, scores left for the validator)
| Slug | Pitch | Public price evidence | Nearest competitor | Biggest doubt |
|---|---|---|---|---|
| sage-remittance-cash-allocator | Reads customer remittance advice and builds the invoice allocation for Sage or QuickBooks ledgers | Cash allocation clerk ads at £22k to £27k (Robert Walters, Robert Half, Rentokil, DWP) | RemitClear (Xero only on its own page; quote-priced) | Competition: one vendor can add Sage; the saving is a fraction of a clerk's salary |
| merchant-supplier-price-file-loader | Turns manufacturers' price updates into a checked import file for a merchant's ERP | Pricing coordinator about £25k (Payscale, modelled); Travis Perkins pricing administrator ad has no salary | TableFlow (US; NetSuite, SAP, Epicor; no UK merchant ERP named) | Pay unproven; BisTrack and Merlin may already import price files; overlaps two REVISE merchant ideas |

## Dropped at the tool search (candidate, public price found, reason)
1. Safety data sheet authoring: outsourced about $275 to $500 per SDS (UL ULGHS from $275; a comparison site says $300 to $500), but SDS Studio sells €59 per SDS, SDS Manager $23 to $71 a month, NextSDS $59 a month, Data Sheet Solutions listed at $4 per SDS. Cheap AI-assisted tools already exist.
2. iXBRL tagging for Companies House: PDF2iXBRL £99 to £249 per set, PKF £320 to £380 (2018). Software-only filing moved to April 2028 (TaxCalc, Azets, ICAS summaries). A cheap product already does the job and accounts software tags natively.
3. Supplier statement reconciliation: Dext ships it (statement credits in its plans), and AutoEntry does it for Sage.
4. UK parcel carrier refund claims: LateShipment (claims for Royal Mail, UK Mail, FedEx, UPS) and Claimit's AI courier invoice audit launched September 2026 (ChannelX).
5. Forecourt competitor pricing under Fuel Finder: no public fee, but myAutomate (bought Portland Pricing; Gulf FuelSense), Forecourt Eye, EdgePetrol and PetrolPrices data services already serve it, and Fuel Finder data has quality errors (RAC Foundation, CMA warning letters).
6. Outsourced hotel revenue management: £700 to £1,000 a month (Priory Hotel case study), Otterly Booked from £100 per property; but Lighthouse from €69 a month, PriceLabs, RoomPriceGenie and others already sell the software.
7. AI inventory and check-out reports for letting agents: The Property AI, Inspecti, Wooma, Property Inspect and Kaptur (No Letting Go) already compare check-in and check-out photos.
8. Cosmetic product safety reports: £70 to £220 per product (one vendor, June 2026), £200 to £800 (another); Cosmetri (Registrar Corp), EUverify and others sell CPSR tools; the assessor's signature is a liability the studio would not take.
9. Supermarket supplier deductions: Salitix (UK, no-upfront-cost recovery service) and SPS Commerce Revenue Recovery already sell it.
10. Offshore statutory accounts and CT600 preparation: only an onshore price list (HaysMac: accounts from £1,500, tax returns from £1,200); Xero's streamlined accounts production and IRIS/TaxCalc cover the production step, and PCRT guidance keeps the accountant liable.
11. Biodiversity net gain small-site metric: the official metric tool is free; one pay-per-use provider is capped at £995 incl. VAT (undated); no ecologist fee data found. Not pursued.
12. SAP and Home Energy Model assessments: no per-plot price found; drawing-to-model input is a hard build. Not pursued.
13. Foreign VAT reclaim for UK hauliers: agent fee percentages not found; not pursued.

## Lessons for the validator
- Starting from a priced job fixed the Pay problem less than expected: staff roles give a salary ceiling (about £25k), and per-item outsourcing prices (SDS, iXBRL, CPSR) are the same ones cheap tools already undercut. A job with a public price is usually a job with a cheap product.
- Both survivors have a close incumbent (RemitClear, TableFlow) whose gap is the ledger or ERP, which the vendor can add. Expect Competition 3 to 5.
- Both depend on a UK ERP or ledger route (Sage 50, BisTrack, Merlin). A free or cheap test route for those systems is the first thing to check at G1 and decides Build.
- Neither idea is expected to reach 70. If the validator agrees, the pattern across 42 ideas is that the SME back-office "documents into the ledger" space is closed, and the next round should look at jobs where the output is a judgement or a recommendation (pricing, forecasting, exception detection), not extraction.
