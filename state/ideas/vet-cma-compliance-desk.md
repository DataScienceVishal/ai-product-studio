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
| 11 | 6 | 5 | 8 | 12 | 4 | 7 | 53 |

## Validator notes (2026-11-23)

**Off-limits decision: clear of the medical-advice ban, with conditions.**

The product covers pricing, price-list publication, pet care plan pages, cremation prices, complaint logging and checking bills against published thresholds. That is administration and consumer-law compliance, not medical advice: the product never says what treatment or medicine a pet should have, and animal health records aren't special-category data under UK GDPR. It stays clear only under these conditions:
1. Imports exclude clinical notes and histories. Only price items, invoice lines (code, description, amount, date and a pseudonymous transaction id) and complaint records come in.
2. The product never writes clinical content, including any wording about prescription alternatives. Where the CMA and RCVS publish standard text, it uses that text verbatim.
3. The £500 estimate monitor only flags invoice-value patterns after the event. It never judges whether a treatment pathway was clinically "reasonably likely" to cost £500.
4. Every output is a draft checked against the published Order, cites gov.uk and is signed off by the practice manager. That also keeps it outside the legal-advice ban.

Legal point for G2: a practice that "becomes aware" of non-compliance must report it to the CMA or RCVS within 14 days, so every flag the tool raises can start that clock. The wording and design need legal review.

**Red-flag check: none.** No paid service is needed. Synthetic data credibly demos the value: the 36 services and the weight categories are public, and an invented messy price list plus a year of synthetic invoice lines is enough to show mapping and monitoring.

**Dates confirmed on gov.uk** (https://www.gov.uk/guidance/small-veterinary-businesses-complying-with-the-cmas-order, first published 13 October 2026, updated 15 October 2026; covers businesses with 14 or fewer practices). The scout's dates are correct.
- **From the next working day after 22 March 2027:**
  - a price list covering "all of the 36 services listed in Schedule 1", and a parasiticide price list;
  - ownership and practice information, pet care plans and cremation prices;
  - an in-house complaints process, a complaint log and mediation.
- **From the next working day after 22 September 2027:**
  - written estimates where the treatment pathway "is reasonably likely to cost £500 or more, including VAT" and at least 20% of that cost is not yet chosen;
  - itemised bills, prescription duties and own-brand rules;
  - prescription fee caps of £21.40 for the first prescription and £12.70 for each extra medicine, until 31 March 2028.
- **Find a Vet submission to the RCVS:** by 22 September 2027 or three months after the RCVS is ready, whichever is later.
- **Self-reporting:** non-compliance must be reported within 14 days.
- **Segment size:** 76% of vet businesses have a single first-opinion practice (20% of practices), and six large groups own over 60% of practices (https://www.gov.uk/government/publications/veterinary-services-for-household-pets-final-decision-report/summary-of-the-final-report-html).

**Falsification findings** (all accessed 2026-11-23)
- **A free tool already builds the price list.** Pricebook.vet was launched on 1 June 2026 by an independent practice (Nightingale Vets) and its co-owner's AI company.
  - Vet Times says it takes 30 minutes and is "easy, quick and free" (https://www.vettimes.com/news/business/finance/free-cma-pricing-compliance-tool-offered-to-amazingly-supportive-community).
  - Its own page offers a CMA template with every mandated category, "compliance guardrails", practice details entered once and an embed script. It says "Free forever. No trial. No subscription." (https://pricebook.vet/)
  - That meets the scout's own falsifier ("practice managers say they do the list in an afternoon") and makes AI mapping close to decorative for the price list.
- **Booking and practice-management vendors bundle the rest:**
  - Vetstoria shows "routine service pricing using standardised pet and weight categories" and adds a price-transparency section to booking confirmations (https://www.vetstoria.com/?p=102329).
  - Lupa says data held in Lupa is "the source of truth for your price list publication", and builds estimates and itemised bills in (https://lupapets.com/blog/cma-pricing-transparency-compliance-guide/, 9 July 2026).
  - Digital Practice ran a free closed beta of a CMA plug-in (https://www.vettimes.com/news/business/practice-developments/digital-practice-unveils-plan-to-help-practices-meet-cma-requirements, 22 December 2025).
  - BVA offers guides and videos to members (https://www.bva.co.uk/news-and-blog/news-article/cma-next-steps-bva-publishes-practical-resources-to-help-vet-teams-get-ready-and-compliant-with-upcoming-changes/, 23 May 2026).
- **Provet's own page confirms the remaining gaps** (https://www.provet.com/uk-cma-reforms). "There is no complaints module in Provet", none is planned, and nothing alerts at the £500 trigger. But Provet already exports item lists, links estimates to the consultation, produces line-item invoices and e-signed prescriptions, and is building prescription-fee automation and own-brand flagging.
- **Agilio sells no CMA tooling.** Its page links CMA compliance only to iLearn training records and iTeam policy storage (https://agiliosoftware.com/veterinary/insights/cma-final-decision/, 24 March 2026).
- **ezyVet:** a site search found no CMA page.
- **What is left has no price point.** A complaints log needs no AI and is cheap to build. After-the-fact monitoring of estimates, bills and prescription fees from September 2027 is mostly deterministic rules. I found no one charging for either.
- **The pain is real but has no cost figure.**
  - The tool's developer says a 36-item list involves "close to 250 to 300 compliance checks" (Vet Times, above).
  - Digital Practice says practices code their prices differently.
  - A consultation response warns of accidental breaches when the practice system, website and printed list are kept separately (https://assets.publishing.service.gov.uk/media/6ab234d04c0f475de0a66b26/Summary_of_Responses.pdf, search summary only).
  - I found no UK job ad and no time cost.

**What would change my mind (re-score on this evidence)**
1. A published price for CMA monitoring or complaints-log software sold to UK vets, or paid monitoring tiers on Pricebook.vet. That would be the first evidence of willingness to pay.
2. Pages from ezyVet, Covetrus (RxWorks, Robovet), VetIT and Merlin showing no £500 estimate alert, no complaints log and no own-brand flagging.
3. Public practice-system documentation of invoice-line export formats (at least Provet and ezyVet), so the monitor is built for real exports.
4. Trade-press, CMA or RCVS evidence that practices are struggling with the September 2027 duties.

With all four I'd expect 60 to 65. It's still the cleanest build of the five (web and CSV only, no paid service), so a desk check of points 1 and 2 is cheap.

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half). Closest to a rules-with-deadline idea; included because the vendor's own page documents the gaps. Validator to decide on off-limits boundary.
- 2026-11-23 | validator | G0→G1 | REVISE 53 | Not medical advice (pricing and complaints admin, kept clear of clinical data), and the dates and Provet's gaps check out on gov.uk and Provet's own page, but Pricebook.vet already gives practices a CMA price list free forever in about 30 minutes, Vetstoria and the practice-system vendors bundle the rest, and what's left (complaints log, after-the-fact monitoring) is mostly rules that nobody is yet paying for.
