# Surface water drainage rebate evidence

- slug: surface-water-drainage-rebate-evidence
- stage: G0
- market and segment: England and Wales multi-site non-household water customers (retail and care groups, warehouses, schools trusts, car parks, depots) paying surface water drainage charges, and the water-audit consultants who serve them.
- one-line pitch: Measures each site's roofs and hard surfaces from open map data, tests it against the site area on the water bill and the water company's published charge scheme, and prepares the site plan and rebate application for the owner or auditor to submit.

## Problem and who has it
- Surface water drainage is charged by site area or meter size, depending on the retailer and wastewater company. Companies estimate site areas, and estimates can be wrong. Rebates apply where rainwater does not drain to the public sewer, but usually the customer must apply.
- Thames Water's page says rebates can be backdated up to six years. Aquaswitch says overcharges can usually be reclaimed up to six years in England and Wales. Back-dating policy differs by company and time (a Consumer Council for Water case describes one year after April 2018 policy; treat as company-specific).
- Aquaswitch says the claim needs a detailed site plan showing boundaries, sewers, pipe routes, paved and built areas, and an estimate of the share of site connected to sewers, and recommends a business water auditor for it.

## Forcing function
- None official. Pressure: rising wastewater charges (sewerage £1.50 to £4.80 per cubic metre, per Aquaswitch) and six-year back-claim window that shrinks each year. I did not find a deadline, and I flag the lack of a forcing function.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.aquaswitch.co.uk/blog/sewerage-rebate-business/ | 2026-11-23 | Claim route (MOSL Form H 01 via retailer); evidence required including detailed site plan; recommends an auditor; sewerage charge range |
| https://www.aquaswitch.co.uk/water-bill-validation/ | 2026-11-23 | Validation checks surface water by property or meter size, estimated reads, trade effluent, SPID mislinks; fee models free review, share of savings, or fixed per site; claims six-year reclaim; no AI or automation mentioned; no minimum spend stated |
| https://www.thameswater.co.uk/help/account-and-billing/understand-your-bill/reduce-your-wastewater-bill/surface-water-drainage | 2026-11-23 | Rebate if not connected to public sewer; backdated up to six years; evidence such as plans; page does not cover business customers |
| https://www.ofwat.gov.uk/?p=234 | 2026-11-23 | Ofwat page on rebates for non-connection (search result, not opened in full) |
| https://www.cedr.com/wp-content/uploads/2020/07/WAT-1137-020119.pdf | 2026-11-23 | Dispute decision: one customer's backdating limited to one year while a neighbour got ten (from search summary; shows inconsistency) |
| https://www.environmental-expert.com/services/surface-water-drainage-services-890909 | 2026-11-23 | H2O Building Services sells surface water drainage audits (vendor listing; fee per case after a savings letter) |

Pain evidence is the weakest of the five: no job ad and no complaint-volume figure found. Next scout step: search for facilities-manager forum threads and water-retailer complaint data from the Consumer Council for Water.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Aquaswitch water audit and bill validation (https://www.aquaswitch.co.uk/water-bill-validation/) | Not published; free review, share of savings or fixed fee per site | Human experts 'recalculate each charge from scratch'; no tool |
| H2O Building Services (https://www.environmental-expert.com/services/surface-water-drainage-services-890909) | Proposes a fee after a savings letter | Same |
| Retailers' own forms (MOSL Form H 01, described at https://www.aquaswitch.co.uk/blog/sewerage-rebate-business/) | Free | Customer must produce the site plan |
| Wastewater company rebate pages (https://www.dwrcymru.com/en/help-advice/surface-water-rebate) | Free | Household-oriented; business rules set in each charges scheme |

Gap that survives (provisional): nobody offers a computed site-area evidence pack using open map data. Honest caveat: OS OpenMap Local building outlines are generalised and the site plan accepted by a water company may need more detail (requirements vary by company; not verified), so the pack supports, not replaces, a survey.

## Why AI is essential (and the moat)
- Reads the water bill, charge scheme PDFs (each wastewater company publishes its own scheme and phrases the rules differently, per Aquaswitch and the search results), and drainage plans; geospatial processing estimates roofs and paved area from open data. Moat is the library of company schemes and a geo pipeline, which is data engineering Vishal can build; a broker can copy slowly.

## Public dataset for the demo
- OS OpenMap Local (buildings, roads, free, Open Government Licence, no registration): https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local (accessed 2026-11-23; generalised geometry at 1:10,000 scale, updated twice a year).
- Water company charge schemes: published on each company's site, licence to confirm (not OGL by default). Demo: 10 synthetic sites placed on real open map tiles, synthetic bills, two real published charge schemes read as text.

## How the selling partner could reach buyers
- Water audit and facilities-management consultants (resale or white label), property managers, accountants to multi-site retail and care groups. Named channel to be confirmed.

## Rough build plan and Azure cost
- Geo processing of footprint area, charge-scheme reader for 3 companies, application pack generator. 4 weeks. Azure £20 to £50 per month (estimate; geo files add storage).

## Risks, and what would prove this wrong
- Biggest: per-site savings may be small, and OpenMap Local accuracy may be too coarse for a water company to accept; test by comparing outlines to known site areas for 20 public sites.
- Retailers submit claims, and the water company, not the tool, decides.
- Overlaps conceptually with the energy checker (utilities audit); the validator should consider merging if both score low.
- No forcing function found.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted. Weak pain evidence, no deadline; flagged.
