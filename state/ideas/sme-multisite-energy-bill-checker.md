# SME multi-site energy bill checker

- slug: sme-multisite-energy-bill-checker
- stage: G0
- market and segment: UK businesses with 5 to 50 sites (care homes, retail and hospitality groups, schools trusts, small property managers) on electricity and gas contracts, below the size where bureau providers quote.
- one-line pitch: Reads supplier PDF invoices for every meter, recomputes them from the contract rates and published pass-through charges and reads, and lists the likely overcharges with a ready-to-send query to the supplier.

## Problem and who has it
- Bills for each meter (MPAN or MPRN) bundle commodity, network (DUoS, TNUoS), levies, Climate Change Levy and VAT. Errors come from wrong rates, estimated reads, wrong VAT or CCL treatment, or a meter linked to the wrong site.
- Team Energy (vendor figure) says 3 to 4% of utility bills have errors.
- Bureaux and software firms serve large estates. A 10-site operator mostly pays and hopes.
- Back-billing: Ofgem's rules apply to domestic customers and microbusinesses (12-month limit), so a larger SME may be exposed to longer back bills.

## Forcing function
- None official. Soft forcing: high business energy costs and the end of fixed deals. Honest note: this idea has no hard deadline, which counts against Reach and Competition.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.teamenergy.com/services/energy-management-software/utility-bill-management-and-cost-recovery/ | 2026-11-23 | Sigma runs 100+ automated checks at MPAN/MPRN level; vendor claim 3 to 4% of bills have errors; no price shown |
| https://www.socotec.co.uk/our-services/utility-bill-validation | 2026-11-23 | SOCOTEC checks bills against agreed rates, CCL and VAT; bureau service; no price |
| https://tridentutilities.co.uk/services/invoice-validation | 2026-11-23 | Portfolio database of sites, tolerance thresholds; no price |
| https://www.mrisoftware.com/uk/products/energy-management-software/invoice-validation/ | 2026-11-23 | eSight invoice validation, quote only |
| https://claverton-energy.com/?p=4200 | 2026-11-23 | Chellow, free open-source bill checker; imports EDI and CSV, not PDF; built-in DUoS only for three DNO areas; page dated 2012 |
| https://www.ofgem.gov.uk/electricity/retail-market/market-review-and-reform/energy-backbilling-project | 2026-11-23 | Back-billing rules scope (domestic and microbusiness), from search summary; my direct fetch of a different Ofgem URL returned 404 |
| https://findajob.dwp.gov.uk/details/17469263 | 2026-11-23 | Brownlow Utilities Validation Analyst job in bureau services (salary shown as €35,000, probably a listing error) |
| https://internaljobs.coop.co.uk/job/manchester/senior-utility-analyst/26772/85727383840 | 2026-11-23 | Co-op Utility Analyst, £24,570 to £25,500, validating utility bills (closed Feb 2026, per search summary) |
| https://mycareers.yorkshirewater.com/job/bradford-senior-energy-analyst-bd6-2sz/1428571033/ | 2026-11-23 | Senior Energy Analyst (Billing), £43,792 to £54,740 |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| SOCOTEC bureau (https://www.socotec.co.uk/our-services/utility-bill-validation) | Not published | Enterprise bureau |
| Team Energy Sigma (https://www.teamenergy.com/services/energy-management-software/utility-bill-management-and-cost-recovery/) | Not published | Enterprise software; rules-based |
| Trident, Ameresco, MRI eSight | Not published | Same |
| Chellow (https://claverton-energy.com/?p=4200) | Free | Needs EDI or CSV and custom scripts; no PDF; documentation dated 2012 |
| Staff analyst | £24.5k to £55k salary per the job ads above | One analyst per bureau; SMEs cannot afford one |
| Older trade article: bureaux cost under 0.5% of spend | Search summary only, URL not confirmed | Treat as unverified |

Gap that survives (provisional): PDF-first, self-serve checking for SMEs with no price barrier. Weakness: none of the pages above says they refuse SMEs, and several do not publish a price, so the real gap could be only a sales-process gap. Not checked: brokers (e.g. via energy brokers' own bill-check offers) and whether any supplier portal flags errors. Validator should treat Competition as at best 4 to 5.

## Why AI is essential (and the moat)
- PDF layouts differ by supplier; extraction into half-hourly or period line items is the cost that keeps bureaux human. Recalculation is deterministic. AI also drafts the supplier query. Moat: the library of supplier layouts and a validated rules engine, but incumbents can add extraction in weeks.

## Public dataset for the demo
- DESNZ and gov.uk CCL rates (OGL v3.0): https://www.gov.uk/guidance/climate-change-levy-rates (not opened).
- Network charge statements from distribution network operators and Elexon data: licence not verified; the validator must check before building. Synthetic invoices for 8 meters with seeded errors are the demo, so no customer data is needed.

## How the selling partner could reach buyers
- Facilities managers and finance leads in care groups, school trusts, franchisees; accountants. Energy brokers could resell but conflict with their commission model. Named channel to be confirmed.

## Rough build plan and Azure cost
- PDF extraction, tariff and pass-through rule engine for 3 suppliers, error list and query letters. About 4 weeks. Azure £20 to £40 per month (estimate).

## Risks, and what would prove this wrong
- Biggest: the incumbent gap is price opacity, not capability; Sigma, SOCOTEC or a broker could add a self-serve tier.
- Each supplier layout is its own project; three suppliers may not cover buyers' mix.
- Test that would kill it: obtain 20 real-world bill samples (published case studies or user-shared) and see if recomputation finds errors at above 3%.
- No hard deadline, so no urgency.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted. Scout expects Competition 3 to 5; flagged as the weakest of the five on gap.
