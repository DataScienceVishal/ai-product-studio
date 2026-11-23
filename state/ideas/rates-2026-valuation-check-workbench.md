# Rates 2026 valuation check workbench

- slug: rates-2026-valuation-check-workbench
- stage: G0
- market and segment: England and Wales businesses with 3 to 30 sites and rateable values (RV) mostly under £30,000 per site (the band the percentage-fee agents skip), plus small rating practices and accountants who file check cases for them.
- one-line pitch: Compares each site's 2026-list rateable value with the Valuation Office's own list for similar properties, finds the likely over-assessed sites, and drafts the Check case with the evidence attached, for a surveyor or the owner to sign off.

## Problem and who has it
- The 2026 revaluation took effect on 1 April 2026 and sets values for April 2026 to March 2029. Pubs and pub restaurants rose 29% on average against 19% across all English properties. Owners of many small sites have no cheap way to test whether each one is over-assessed.
- A challenge must start with a Check case, then Challenge, then Appeal to the Valuation Tribunal. Agents are the usual route. Some are rogue: the VO has refused to deal with named firms.
- Agent economics leave small sites unserved. Eddisons only takes appeals above £30,000 RV. Contingent fees on small RV reductions are tiny, so firms either decline or charge up front.
- Sellable to: multi-site SMEs (pubs, salons, dental and vet groups, small retail chains), rating practices who want a faster workflow, and accountants who already hold the client relationship.

## Forcing function
- 2026 list live since 1 April 2026. Appeals against the 2026 list can be made from 1 April 2026 (council pages). The gov.uk challenge page gives no separate deadline for the 2026 list; I could not verify the end date of the window. UNVERIFIED: the validator must confirm the time limit (and backdating to 1 April 2026) before scoring.
- The pubs and hotels valuation methodology review (call for evidence, August 2026) may change values for a segment, which creates a second wave of checks.
- Nearly half of appeals took over 12 months in early 2026 (law-firm summary of a Property Week piece), so early, well-evidenced cases matter.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://gov.uk/guidance/challenge-the-valuation | 2026-11-23 | Check then Challenge then Appeal; challenge within 4 months of check decision; all evidence must be submitted together; no separate 2026-list deadline stated; page does not mention agents or fees |
| https://www.eddisons.com/valuations-and-advisory/business-rates/business-rating-appeals | 2026-11-23 | No-win-no-fee, percentage of saving, appeals only above £30,000 RV, no AI or self-service tool mentioned, enquiry form and phone only |
| https://www.allsop.co.uk/professional-services-management/business-rates/business-rates-appeals-deadline/ | 2026-11-23 | Contingency basis; says appeals can be backdated, up to three years of savings depending on case; 31 March 2026 deadline referred to the old list |
| https://www.gov.uk/government/news/be-wary-of-rogue-business-rates-agents | 2026-11-23 | VO warns about rogue agents (page surfaced in search, not opened in full) |
| https://www.gov.uk/guidance/choosing-a-business-rates-agent | 2026-11-23 | VO says you can manage rates yourself in a business rates valuation account; some agents do not meet standards |
| https://www.westnorthants.gov.uk/business-rates/appealing-your-rateable-value | 2026-11-23 | Council warns of contracts taking a percentage of the RV reduction rather than the saving; cites RICS free helpline (from search summary) |
| https://findajob.dwp.gov.uk/details/17741679 | 2026-11-23 | Business Rates Surveyor advertised at £35,000 to £40,000 plus commission (closing 15 Feb 2026), a staff-cost signal for the manual work |
| https://www.cobaltrecruitment.co.uk/careers/business-rates-surveyor-senior-surveyor-greater-london-jn-042026-85222_1786965697-29864 | 2026-11-23 | Business Rates Surveyor / Senior Surveyor, City of London, £60,000 to £75,000 plus bonus |
| https://www.gov.uk/government/calls-for-evidence/valuation-methodology-review-for-pubs-and-hotels/business-rates-review-of-valuation-methodology-for-public-houses-and-hotels-call-for-evidence | 2026-11-23 | Government review of pub and hotel valuation after the 2026 revaluation; 29% vs 19% average RV rise (from search summary) |
| https://www.tax.service.gov.uk/view-my-valuation/terms-and-conditions | 2026-11-23 | VO data terms: use restricted to Non Domestic Rating purposes; onward disclosure prohibited; Crown copyright |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Eddisons rating appeals (https://www.eddisons.com/valuations-and-advisory/business-rates/business-rating-appeals) | No win no fee, % of saving; RV £30,000+ only | Skips small sites; no self-service; people-led |
| Allsop (https://www.allsop.co.uk/professional-services-management/business-rates/business-rates-appeals-deadline/) | Contingency; free appraisal | Same: service, not a tool |
| Appeal Business Rates (via Trustpilot listing, https://nl.trustpilot.com/review/www.appealbusinessrates.co.uk) | Reported as 5% of RV non-refundable plus 25% of year-one savings above £24,000 RV (search summary only; page not opened) | Upfront fee on small sites is what customers complain about; check before citing |
| VO "Find a business rates valuation" and Check case (https://gov.uk/guidance/challenge-the-valuation) | Free | Owner must find comparables and write grounds alone |
| Apify "UK Business Rates" actor (https://apify.com/spookyweb/uk-business-rates.md) | Pay per run (not opened in full) | A scraper, not a case builder; scraping the VO service may breach its terms, so the studio will not use it |
| Nimbus comparables (https://www.nimbusmaps.co.uk/features/the-complete-comparables-tool) | Quote | Built for property deals, not rates |
| RICS free helpline (council page above) | Free | Advice, no case preparation |

Gap that survives: no tool or agent serves the sub-£30,000 RV multi-site owner with a cheap, evidence-first Check case. Not checked: whether VOA/VO itself will ship comparables in its valuation account (the account is described at https://www.gov.uk/guidance/choosing-a-business-rates-agent). Agents' own software (Ryan, Altus, Gerald Eve) is internal and not public.

## Why AI is essential (and the moat)
- Properties are rated on 'scheme' price per m2 by use and area. The value is in matching the owner's site to comparables correctly (use class, floor area, zone, split of areas) and writing grounds in the VO's expected format. LLMs read lease, floor plans and photos to correct area and use; deterministic code does the comparable maths.
- The moat is a tested pipeline of how successful challenges are argued, not the chat layer. Incumbents are people firms with percentage models that do not suit small cases. A rating agent could copy it but loses fee income on small sites, so the gap is economic, not technical.

## Public dataset for the demo
- VO rating list: bulk download and per-property view at https://www.tax.service.gov.uk/business-rates-find/search (the VO terms limit use to NDR purposes and bar onward disclosure; footer says OGL v3.0 except where stated). The licence on the bulk file is unclear (a University of Liverpool article says OGL does not apply to the bulk file: https://www.liverpool.ac.uk/geographic-data-science/news/stories/title,986082,en.php). Needs a written answer from the VO (ccaservicevo@hmrc.gov.uk), which only Vishal can send.
- Statistics and background: https://www.gov.uk/government/statistics/non-domestic-rating-change-in-rateable-value-of-rating-lists-england-and-wales-2026-revaluation-draft-list/non-domestic-rating-reval-2026-draft-list-and-background-information (OGL).
- Demo fallback: a synthetic estate of 12 sites built from published scheme rates and published statistics, so the demo never needs a redistributed VO file. Customer data is the owner's own leases; the demo needs none.

## How the selling partner could reach buyers
- Through accountants and bookkeepers serving pubs, salons and small retail groups; trade bodies and franchise networks; the partner's own client base if it is a UK SME service business. Channel to confirm with Vishal's friend.

## Rough build plan and Azure cost
- Ingest the VO list for a customer's postcodes, compute scheme comparables, rank sites by implied saving, generate a Check case pack (PDF) and a tracker for deadlines. Estimate: 4 weeks; Azure about £20 to £40 a month (storage, small database, one app service, LLM calls per case). Estimate, no method beyond typical small-app sizing.

## Risks, and what would prove this wrong
- Biggest: saving per small site may be too low to justify a subscription. Test: take 50 sites below £30,000 RV from the public list and compute the likely saving range; if the median annual saving is under about £150 per site, kill.
- VO licence may bar commercial reuse of the bulk list.
- Over-assessment can be wrong in either direction: valuations can rise on appeal (Eddisons page warns this), so the tool must show downside risk.
- Advice boundary: RICS-regulated valuation advice; frame as evidence preparation, surveyor or owner signs.
- The 2026-list challenge deadline is unverified.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 3 (T-22): G0 drafted.
