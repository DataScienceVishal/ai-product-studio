# Vet CMA compliance desk

- slug: vet-cma-compliance-desk
- stage: G0
- market and segment: UK independent veterinary businesses with 14 or fewer practices (small-business track of the CMA Order), running Provet, ezyVet or other practice management systems (admin and price data only; no clinical content)
- one-line pitch: Pull a practice's price items out of its practice-management export, build the Order's 36-service price list and pet-care-plan pages, then keep watching bills and estimates for the Order's £500 estimate, itemised bill, prescription-fee and complaint-log duties, with a practice manager signing off everything.

## Problem and who has it

The CMA's final Order (made September 2026) puts new duties on every vet business. For small businesses most start the next working day after 22 March 2027, with estimates, itemised bills, prescriptions and fee caps from the next working day after 22 September 2027 (see Evidence). Practice managers must turn messy internal price items into a standard list, publish it, and prove day-to-day compliance. Whether a pathway reached £500 with 20 percent of tests undecided is a judgement a human must sign off.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/guidance/small-veterinary-businesses-complying-with-the-cmas-order | 2026-11-23 | Small-business guide (14 or fewer practices): price list for 36 services, parasiticide prices, pet care plan details, cremation prices, written complaint process and log from the next working day after 22 March 2027; written estimates (£500 or more with 20 percent or more of tests or treatments not yet chosen), itemised bills, prescription duties and fee caps (£21.40 first, £12.70 each further, until 31 March 2028) from the next working day after 22 September 2027. Report non-compliance within 14 days. |
| https://www.provet.com/uk-cma-reforms | 2026-11-23 | Provet's own page admits gaps: bundle export needs a Customer Success Manager; no alert when a pathway reaches the £500 threshold; "There is no complaints module in Provet"; own-brand flagging, automatic prescription fee and price link in booking confirmations in development. |
| https://www.provet.com/blog/the-uk-cma-veterinary-ruling-what-every-practice-needs-to-know | 2026-11-23 | Provet blog (seen via search) says it is looking at easier export in the CMA's required format (by pet weight category). Vendor admission that the workflow is not finished. |
| https://www.gov.uk/government/news/cma-concludes-market-investigation-with-major-reforms-to-veterinary-sector | 2026-11-23 | CMA estimate of regulator cost charged per practice: £150 to £250 set-up and £450 to £550 a year (earlier estimate). Shows scale of compliance cost to a practice. |
| https://stealthagents.com/research/veterinary-practice-staffing-costs-2026 | 2026-11-23 | US staffing blog: wages 38 to 48 percent of gross revenue (VHMA 2025). Not UK; context only. |

No UK job ad for a vet admin role citing this work was found. Pain signals are regulatory duty plus Provet's admissions plus the cost of regulator fees; a practice-level time cost estimate is missing.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Provet Cloud (page above) | From about £99 a month for a one-vet practice (https://whito.co.uk/for/vets/best-software-for-uk-vets/, via search summary; Capterra lists US$99) | Own page lists the gaps above; it is building them, so the vendor will close some within months. |
| ezyVet | Capterra lists from US$260.50 a month (https://www.capterra.com.au/compare/99977/137569/ezyvet-cloud-vet-software/vs/provet-cloud) | No CMA feature list found; not checked on its own pages. |
| Agilio Software CMA page (https://agiliosoftware.com/veterinary/insights/cma-final-decision/) | Not captured | Another vendor publishing CMA commentary; not checked for product features. Must check before G1. |
| Manual spreadsheet by practice manager | Staff hours (no UK estimate yet) | The substitute. |

Gap claimed: a vendor-neutral layer that works from exports of any practice system, covers the monitoring duties, and has a manager sign-off trail. Each PMS vendor may close its own part, and the compliance date is a one-off, so recurring revenue depends on the monitoring and plan-update duties.

## Why AI is essential (and the moat)

Item names in practice systems are free text ("Cons 1", "Vacc booster inc kennel cough"). Mapping them to the Order's 36 defined services, pet weight bands and cat or dog variants needs language matching with a human confirming each mapping. Monitoring invoice lines for the estimate trigger and own-brand wording is classification across messy line items. The moat is the mapping memory and the export parsers; thin on its own.

## Rough build plan and Azure cost

- Importers for CSV exports (mock mode: synthetic export in the same shapes as a PMS price list and an invoice-lines file). Live PMS API access is a later, optional step.
- Mapper to the 36 services with confidence and a review screen; generates a publishable HTML and PDF price list and a plan page.
- Monitor over invoice-line exports: flags pathways near £500, bills missing itemisation, prescription fee above cap; complaint log form with export.
- Sign-off trail (who approved what, when).
- Azure: Static or small App Service plus Postgres burstable; under about £20 a month. No paid third-party service needed to demo.
- Demo with synthetic data: invented practice price list with 300 messy item names and a year of synthetic invoice lines; the 36 services are public in the CMA Order. Measure mapping accuracy and flagged exceptions.

## Risks, and what would prove this wrong

- Off-limits boundary: this is pricing and compliance admin, not medical advice, but vet data sits next to clinical records. Keep clinical fields out of imports.
- Not legal advice: the product presents drafts for the practice to confirm; legal review of wording needed.
- Forcing date is real but one-off; PMS vendors, groups and RCVS templates may cover the need. The RCVS may publish tools.
- Small practices may not pay for a one-off; reach through vet-specific channels needs a named route via the UK sales partner.
- Wrong if: Provet, ezyVet and Agilio each show price-list export and monitoring on their own pages by Q1 2027, or practice managers say they do the list in an afternoon.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| pending | pending | pending | pending | pending | pending | pending | pending |

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half). Closest to a rules-with-deadline idea; included because the vendor's own page documents the gaps. Validator to decide on off-limits boundary.
