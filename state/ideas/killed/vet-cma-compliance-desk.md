# Vet CMA compliance desk

- slug: vet-cma-compliance-desk
- stage: KILLED (2026-11-26, T-108, second G1 failure, score 50)
- market and segment: UK independent veterinary businesses with 14 or fewer practices (small-business track of the CMA Order), running Provet, ezyVet or other practice management systems (admin and price data only; no clinical content)
- one-line pitch: Pull a practice's price items out of its practice-management export, build the Order's 36-service price list and pet-care-plan pages, then keep watching bills and estimates for the Order's £500 estimate, itemised bill, prescription-fee and complaint-log duties, with a practice manager signing off everything.

## Kill (validator, 2026-11-26, T-108)

**Reason.** This was the second G1 attempt, and it scored 50, below the first attempt's 53. So the pipeline kill rule applies. Each part of the product already has someone serving it, and most of them are free or cheap:
- The price list is free on Pricebook.vet ("free forever"). Xonvet sells it for £189 one-off plus £19 a month. Provet exports item lists.
- The complaint log is covered too. The Veterinary Defence Society, the indemnity body most UK vets already belong to, is launching VetResolve. It is a complaints platform built for the CMA reforms, with a dashboard, tracking, reminders and categorisation (Vet Times, 30 July 2026). Xonvet's £449 tier also includes a complaint log and management system.
- Provet is building prescription-fee automation and own-brand flagging "ahead of the first fee cap deadline".

The only thing nobody covers is an alert when a treatment pathway reaches £500. That is a deterministic threshold rule a practice-system vendor can add in a sprint. It can only flag after the event, because judging whether a pathway was "reasonably likely" to cost £500 is clinical. The one real price in the market (Xonvet, £19 a month after setup) caps a subscription at tens of pounds a month. The AI part (mapping item names to the 36 services) is a one-off job that a free tool already does in about 30 minutes.

**Lessons**
- Regulatory deadlines in small professional markets bring in the profession's own bodies, not only software vendors. Check the indemnity insurer, the defence society, the professional association and the regulator before scoring Competition. Here VDS's VetResolve and the BVA's guides were the channel owners.
- A vendor's own "we don't do X" page (Provet: no complaints module, no £500 alert) shows a gap in one vendor, not in the market. This repeats the round-4 lesson.
- Practitioner-built free tools (Pricebook.vet, by Nightingale Vets) appear within weeks of a rule that hits thousands of small practices. When the regulated parties are numerous and sociable, assume a free community tool exists.
- Compliance setup sold as one-off fee plus small monthly (Xonvet's £189 to £449 plus £19) is the market's price anchor. It is evidence of willingness to pay, but too low to support a two-person studio.

**What would revive it**
- VetResolve launches as a paid add-on or is withdrawn, and no practice system ships a £500 pathway alert by September 2027.
- The CMA, the RCVS or the trade press reports widespread September 2027 non-compliance in estimates, itemised bills or prescription fees, with enforcement or published breaches.
- A buyer-side price above about £50 a month per practice for monitoring software, or evidence that practice groups just above the 14-practice line buy cross-system monitoring.
- Even then, it needs a re-score of 70 or more with a real AI part, for example estimate-pathway monitoring across several practice-system export formats, proven on public format documentation.

## Problem and who has it

The CMA's final Order (made September 2026) puts new duties on every vet business. For small businesses most start the next working day after 22 March 2027, with estimates, itemised bills, prescriptions and fee caps from the next working day after 22 September 2027 (see Evidence). Practice managers must turn messy internal price items into a standard list, publish it, and prove day-to-day compliance. Whether a pathway reached £500 with 20 percent of tests undecided is a judgement a human must sign off.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/guidance/small-veterinary-businesses-complying-with-the-cmas-order | 2026-11-23, re-checked 2026-11-26 | Small-business guide (14 or fewer practices): price list for 36 services, parasiticide prices, pet care plan details, cremation prices, written complaint process and log from the next working day after 22 March 2027; written estimates (£500 or more with 20 percent or more of tests or treatments not yet chosen), itemised bills, prescription duties and fee caps (£21.40 first, £12.70 each further, until 31 March 2028) from the next working day after 22 September 2027. Report non-compliance within 14 days. |
| https://www.provet.com/uk-cma-reforms | 2026-11-23, re-checked 2026-11-26 | Provet's own page admits gaps: bundle export needs a Customer Success Manager; "Nothing prompts you when a pathway reaches the threshold"; "There is no dedicated complaints module planned"; own-brand flagging and prescription fee automation in development (fee automation expected "ahead of the first fee cap deadline"). |
| https://www.provet.com/blog/the-uk-cma-veterinary-ruling-what-every-practice-needs-to-know | 2026-11-23 | Provet blog says it is looking at easier export in the CMA's required format. |
| https://www.gov.uk/government/news/cma-concludes-market-investigation-with-major-reforms-to-veterinary-sector | 2026-11-23 | CMA estimate of regulator cost per practice: £150 to £250 set-up and £450 to £550 a year. |
| https://xonvet-website.pages.dev/ | 2026-11-26 (scout and validator) | Xonvet: "Compliant" £189 one-off + £19/month (36-service price module, audit log); "Confident" £449 one-off + £19/month (adds estimate template, complaint log and management system, audit checklists, own-brand and cremation disclosures). No automatic invoice or estimate monitoring. |
| https://www.vettimes.com/news/business/practice-developments/vds-to-launch-purpose-built-complaint-management-platform | 2026-11-26 (validator) | 30 July 2026: VDS to launch VetResolve, a complaints management platform designed for the CMA reforms (dashboard, progress tracking, automated reminders, categorisation). No price or launch date stated. |
| https://pricebook.vet/ | 2026-11-23, 2026-11-26 | Free-forever CMA price list tool. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Pricebook.vet | £0, free forever | Price list only |
| Xonvet | £189 or £449 one-off + £19/month | Templates and checklists, no invoice monitoring |
| VDS VetResolve | Not published | Complaints only; channel owner (defence society) |
| Provet Cloud | Core £139 per vet/month; Pro £159 per vet + £199 platform (https://provet.com/pricing) | No complaints module, no £500 alert; fee cap and own-brand in development |
| Lupa | Not published | Estimates and itemised invoices built in |
| Vetstoria | Not published | Standardised pricing on booking flow |
| Manual spreadsheet | Staff hours (no UK estimate) | The substitute |

## Why AI is essential (and the moat)

Item-name mapping to the 36 services is language matching, but it's a one-off and a free tool does it in about 30 minutes. Invoice monitoring for the £500 trigger, itemisation and fee caps is mostly deterministic rules. Moat: thin.

## Score (validator)

First attempt (2026-11-23): 53.

Second attempt (2026-11-26, T-108):
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 11 | 7 | 4 | 7 | 12 | 2 | 7 | 50 |

Evidence and reasoning: `state/ideas/T-108-validator.md`.

## Validator notes (2026-11-23)

Off-limits decision: clear of the medical-advice ban if imports exclude clinical notes, the product writes no clinical content, the £500 monitor flags invoice-value patterns after the event only, and every output is a signed-off draft citing gov.uk. Red-flag check: none. Falsification: Pricebook.vet (free), Vetstoria, Lupa, Digital Practice plug-in, BVA resources; Agilio sells no CMA tooling. See the first verdict in the Gate log.

## Desk check update (2026-11-26, T-108, scout)

Xonvet priced (£189/£449 one-off + £19/month); Pricebook.vet £0; Provet pricing and gaps unchanged; Lupa builds estimates and invoices; ezyVet, Covetrus, Merlin, VetIT showed no CMA material. Pass-first score 55, no path to 70. See `state/ideas/T-108-vet-cma-check.md`.

## Gate log
- 2026-11-23: G0 written by scout (round 2, second half).
- 2026-11-23 | validator | G0→G1 | REVISE 53 | Not medical advice; dates and Provet's gaps check out, but Pricebook.vet gives the price list free, vendors bundle the rest, and what is left is mostly rules nobody pays for.
- 2026-11-26 | scout | desk check T-108 | KILL-candidate, pass-first score 55 | Only priced offer is Xonvet; price tool is free; no path to 70.
- 2026-11-26 | validator | G0→G1 second attempt (T-108) | KILL 50 | Second G1 failure. Xonvet (£19/month after setup), Pricebook.vet (free), VDS VetResolve (CMA complaints platform from the vets' defence society) and Provet's in-development fee-cap and own-brand features leave only a £500 pathway alert, which is a rule a PMS vendor can add. Pay capped near £19/month; AI near decorative; no evidenced wedge.
