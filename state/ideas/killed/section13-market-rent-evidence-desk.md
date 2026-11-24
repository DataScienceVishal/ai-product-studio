# Section 13 market-rent evidence desk

- slug: section13-market-rent-evidence-desk
- stage: killed (G1 attempt 1, 57, T-46)
- market and segment: England letting agents and self-managing portfolio landlords (about 5 to 300 tenancies) that must justify every rent increase under the Renters' Rights Act from 1 May 2026
- one-line pitch: For each tenancy due a review, recommends the rent to put in the Section 13 notice, ranks the comparables, and writes the evidence pack that would stand up at the First-tier Tribunal. A person signs it off.

## Problem and who has it
Since 1 May 2026 rent review clauses are void and a Section 13 notice (Form 4A, two months' notice, once per 52 weeks) is the only way to raise rent on an assured periodic tenancy. A tenant can send the figure to the tribunal, which sets the market rent. Agents now need a defensible number per tenancy, not a letter. Today the number comes from an agent's gut, Rightmove or Zoopla listing searches and a phone call. The output is a judgement: what rent to ask, and why.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.nrla.org.uk/news/landlord-warning-appeals-hit-record-high (fetched) | 2026-11-24 | 3 Sep 2026: Hamptons counted 166 tribunal market-rent decisions in July, the highest on record and about four times July 2025. 42% of August decisions involved self-managing landlords, many without solid evidence. About a quarter of decisions cut the figure because the property was below standard (EPC, carpets, white goods). |
| https://www.propertyreporter.co.uk/rightmove-adds-section-13-rent-review-tool-to-tenancy-manager.html (fetched) | 2026-11-24 | Rightmove Tenancy Manager now creates and serves the notice from the tenancy record. The page does not say it recommends a rent or builds comparables (the page is silent, not a confirmed absence). |
| https://blog.goodlord.co/your-guide-to-section-13-and-rent-increases-in-the-private-rented-sector (fetched) | 2026-11-24 | Goodlord has a Section 13 workflow (Form 4A from the tenancy record, review alerts, audit trail). No rent recommendation or comparables feature, no price, "Book Demo" only. Its FAQ tells landlords to gather comparables themselves. |
| https://england.shelter.org.uk/professional_resources/practical_resources/tools_and_guides/how_to_challenge_a_rent_increase_in_the_tribunal/gather_evidence_for_the_tribunal (search summary) | 2026-11-24 | Tenant-side guidance says the evidence pack should show comparable properties; tenants are now being coached to bring one. |
| https://www.landlordstudio.com/uk-blog/proving-open-market-rent-for-rental-increase (search summary) | 2026-11-24 | A landlord-software vendor publishes how-to advice on proving open-market rent ("three to five strong comparables beat ten weak ones"). The job is done by hand today. |
| https://www.property118.com/landlords-hit-with-new-letting-agent-fees-claim/ (search summary) | 2026-11-24 | Goodlord survey: nearly a quarter of landlords report higher agent fees since the Act. Agents are charging for Section 13 work. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Agent's per-review fee, Cluttons Section 13 rent review | £250 inc VAT per review (search summary of the 2026 landlord fee PDF; the PDF was unreadable when fetched, so verify) | This is the public price of the human decision. At roughly 12% of rent as letting fee, the review is a small add-on. |
| Your-Move and Reeds Rains landlord fee schedules (May and June 2026) | Review fee charged only when the review ends in an increase (amount not read) | Outcome-based fees show agents treat the review as billable work. |
| Savills landlord fees | Review folded into a letting fee with a £1,200 to £1,800 minimum | Large agents absorb it. |
| Rightmove Tenancy Manager Section 13 tool (Sept 2026) | Not priced on the page | Notice workflow only. Rightmove holds the listings data and could add a rent suggestion. |
| Goodlord Section 13 workflow | Quote only | Same: notice and audit trail, no rent figure or evidence pack found. |
| Free ONS Price Index of Private Rents and Shelter and NRLA guidance | Free | Area index, not a per-property figure. |
| RICS rental valuation by a surveyor | Not priced in this round (not found) | Costly per property, so not used for routine reviews. |

## Why AI is essential (and the moat)
Choosing comparables is a judgement over messy text: matching on size, condition, EPC, furnishings and the tenancy start, then adjusting. An LLM can read the agent's own tenancy records and inspection notes, apply condition adjustments, explain the choice in tribunal-ready language and flag tenancies whose proposed rent is likely to be cut. Deterministic code can't write the reasoning. The moat is the evidence pack and the audit trail kept per tenancy, which the notice-serving platforms don't offer. It is not a moat against Rightmove adding a suggestion.

## Rough build plan and Azure cost
- Inputs: a CSV export of the agent's tenancies, plus the agent's own comparables (let agreed rents they manage) and listings the agent pastes in. Public data: ONS PIPR by local authority (OGL), VOA rental stats, EPC register (open data).
- Output: recommended rent with a range, a ranked comparables table, a condition-adjustment note, a tribunal-risk flag and a draft pack for sign-off. Notice serving stays in the agent's system.
- Demo with synthetic tenancies plus real ONS and EPC open data. No paid service is needed, so the whole demo works without mock mode.
- Cost: Container Apps plus Postgres plus one LLM call per tenancy. Estimate under £30 a month for a pilot (estimate: about 200 tenancies at a few thousand tokens each is cents per review).

## Risks, and what would prove this wrong
- Biggest doubt: Data. The best comparables are portal listings (Rightmove, Zoopla) that forbid scraping. Without them the figure is only as good as the agent's own let-agreed rents, so value falls for small agents. Test: can a benchmark of 30 tribunal decisions (gov.uk panel decisions are public) be matched within 5% from open data plus synthetic comparables?
- Rightmove or Goodlord may ship a suggested rent within a quarter. They hold the data.
- It must not become legal advice: the product recommends a market rent and evidence, not a view on notice validity. Keep out of the notice-validity checks.
- Pay unproven: £250 is a fee per review, but the agent may not pay extra for a tool. Likely price is £2 to £5 per tenancy a month (an estimate, no evidence).
- Hurts if the forcing function fades: the tribunal peak may settle once evidence habits form.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 16 | 11 | 6 | 7 | 8 | 2 | 7 | 57 |

## Gate log
- G0 written by scout, round 9 (T-46), 2026-11-24. Not scored.
- G1 attempt 1, validator, round 9 (T-46), 2026-11-24: **57, KILL** (ceiling about 62). See "Validator, round 9".

## Validator, round 9 (T-46, 2026-11-24)

**Verdict: KILL, 57/100.** The pain is real, but the product the scout describes already exists as a funded single-purpose UK startup.

**Reason.** MarketRent, founded by Rajeev Nayyar and Duncan Careless (the Fixflo co-founders), opened on 14 April 2026 as a "workflow and evidence platform" for rent reviews. It brings market data, comparables, ONS indexation and landlord approvals into one system, compiles a "tribunal-ready pack for landlords with a rent suggestion", generates the prescribed form, takes the tenant's counter-evidence and keeps an audit trail. It also gives away a free ONS indexation tool and already integrates with Veco Plus. That is the scout's whole pitch, sold by founders who already have a distribution network among letting agents. Around it: LonRes Rental Checker (April 2026) gives like-for-like comparables from *achieved* rents, an accuracy barometer and a branded report with the method, which is better data than the studio can lawfully get. PropertyData includes instant rental valuations with a confidence score in every plan from £15 to £60 a month. Rightmove Tenancy Manager (September 2026) and Goodlord serve the notice. Landlord Law sells a Market Rent and Tribunal Kit with a comparables assessment pack (29 August 2026). The data problem is close to a red flag: the only good comparables are achieved rents (LonRes, the agent's own book) or licensed portal-derived data (PropertyData's API from about £28 a month is a paid service that would need Vishal's approval). ONS PIPR is area-level only, so a demo on open data plus synthetic comparables can't show the figure is accurate. The AI is the weakest part: picking comparables is a data and statistics job, and MarketRent and LonRes do it without an LLM. Drafting the narrative is the only LLM step, and anyone can copy it in a week.

**Scores.**
- Pain 16: statutory forcing function on every periodic tenancy every year. Record tribunal volume (166 decisions in July 2026, NRLA/Hamptons). Tenants are being coached to bring evidence (Shelter).
- Pay 11: agents charge per review (the Cluttons £250 is still from a search summary and unverified; Your-Move and Reeds Rains charge on outcome). Data tools are priced at £15 to £60 a month. Nothing shows a separate subscription for the evidence pack.
- AI 6: mostly data retrieval plus arithmetic. The LLM narrative is easy to copy.
- Reach 7: letting agents are easy to find through Propertymark and the portals, but the channel already belongs to Fixflo's founders and Rightmove.
- Build 8: the core flow is easy, but showing that the figure is accurate needs licensed data.
- Competition 2: MarketRent, LonRes, PropertyData, Rightmove, Goodlord, MRI and the Landlord Law kit.
- Risk 7: tenancy personal data, and the output is used in tribunal proceedings, so it sits close to legal advice.

**Lessons.**
- A new statutory process ("Section 13 from 1 May 2026") is seen by every proptech founder. Search the trade press (The Negotiator, Letting Agent Today, Property Industry Eye) for "<process> platform launched" before writing the G0 file. Four launches came up in one search.
- For valuation or recommendation ideas, find out who owns the *achieved* (transaction) data first. If it is a data vendor or a portal, the studio's figure will be second-rate.

**What would revive it.** A lawful, free or approved source of achieved rents (for example a partner agent's own book under a data agreement), plus evidence that MarketRent and LonRes don't serve self-managing landlords outside London at a price they will pay. Even then, the ceiling is about 62.

**Evidence (accessed 2026-11-24).**
- MarketRent launch: https://propertyindustryeye.com/platform-launched-to-support-rent-reviews-under-renters-rights-act/ (fetched); "tribunal-ready pack ... with a rent suggestion": https://thenegotiator.co.uk/news/products-services-news/new-rent-review-platform-launches-ahead-of-renters-right-act/ (search summary). No price was found.
- LonRes Rental Checker: https://www.propertyreporter.co.uk/lonres-launches-rental-compliance-tool-ahead-of-renters-rights-act.html (fetched, 24 Apr 2026)
- PropertyData plans, £15 to £60 a month, rental valuations included: https://propertydata.co.uk/pricing (fetched). API pricing: https://propertydata.co.uk/api/pricing (search summary, about £28 a month)
- Landlord Law Market Rent and Tribunal Kit: https://landlordlaw.co.uk/introducing-the-landlord-law-market-rent-and-tribunal-kit/ (fetched; no price)
- Rightmove Section 13 tool: https://thenegotiator.co.uk/news/rightmove-adds-rent-review-tool-to-tenancy-manager/ (search summary)
- gov.uk process: tenant applies before the new rent's start date, £47 fee, tribunal outcome "might end up being lower or the same", two months' minimum notice from 1 May 2026: https://www.gov.uk/guidance/apply-for-a-market-rent-determination (fetched, page updated 10 Aug 2026)
- Process guidance: https://www.nrla.org.uk/resources/managing-your-tenancy/increasing-rent-during-tenancy-agreement (search summary)
