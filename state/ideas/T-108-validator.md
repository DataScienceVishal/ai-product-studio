# T-108 validator: vet-cma-compliance-desk, second G1 attempt (2026-11-26)

**Verdict: KILL, 50/100 (first attempt REVISE 53). Second G1 failure, so pipeline.md's kill rule applies.**

## Spot-checks (5 tool calls, all accessed 2026-11-26)

| Claim | Source | Result |
|---|---|---|
| Xonvet prices | https://xonvet-website.pages.dev/ | Confirmed. "Compliant" £189 setup + £19/month (36 services across 6 weight bands, parasiticides, care plans, audit log). "Confident" £449 setup + £19/month (adds estimate template and escalation process, prescription and own-brand disclosures, complaint procedure and templates, a "complaint log and management system", audit checklists, responsibility matrix). Nothing reads invoices or monitors bills automatically. Says it is a setup service, not a law firm. |
| Provet gaps | https://www.provet.com/uk-cma-reforms | Confirmed. "There is no dedicated complaints module planned". "Nothing prompts you when a pathway reaches the threshold". Prescription fee automation in development, expected "ahead of the first fee cap deadline". Own-brand flagging in development. Item lists export; bundles need the Customer Success Manager. |
| Order dates and thresholds | https://www.gov.uk/guidance/small-veterinary-businesses-complying-with-the-cmas-order | Confirmed. Price list and complaints from the next working day after 22 Mar 2027. Estimates, itemised bills and fee caps from the next working day after 22 Sep 2027. £500 inc VAT with 20% not yet chosen. Re-estimate when the cost is likely to exceed the last estimate by 20% or £500, whichever is lower. Caps £21.40 / £12.70 inc VAT until 31 Mar 2028. Page published 13 Oct 2026, updated 15 Oct 2026. |
| Falsification: anyone selling CMA complaints or monitoring software? | Web search, then https://www.vettimes.com/news/business/practice-developments/vds-to-launch-purpose-built-complaint-management-platform | New finding. The Veterinary Defence Society (VDS) is launching VetResolve, a complaints management platform designed for the CMA reforms: dashboard, progress tracking, automated reminders, categorisation by species, type and outcome (Vet Times, 30 Jul 2026). No price or date published. |

New finding that the scout missed: VDS VetResolve. VDS is the profession's own indemnity and defence body, so it already has a relationship with nearly every practice and a reason to give this tool to members. It shuts the complaints-log part of the wedge from the channel owner's side.

## Score (second attempt)

| Criterion | Score | Reasoning |
|---|---|---|
| Pain /20 | 11 | The duty is real and dated (gov.uk). There are vendor admissions (Provet) and the "250 to 300 compliance checks" quote. Still no UK job ad or time-cost figure. A free tool does the list in about 30 minutes, which weakens the frequency and cost of the pain. |
| Pay /20 | 7 | The first real price is Xonvet at £189 to £449 one-off plus £19 a month, alongside a free price tool. That is evidence of willingness to pay, but the anchor caps a subscription at about £19 a month per practice. Nobody prices monitoring. |
| AI /15 | 4 | Mapping item names is one-off, and Pricebook.vet already does it free. What remains (complaint log, £500 trigger, itemisation and fee-cap checks) is deterministic rules. The monitor can only flag after the event, because judging a pathway "reasonably likely" to cost £500 is clinical. |
| Reach /10 | 7 | The segment is countable (76% of vet businesses are single-practice, per CMA). Channels exist: BVA, Vet Times, SPVS. But the channel owners (VDS, BVA) are now competitors, and the UK sales partner's sector is unknown. |
| Build /15 | 12 | CSV importers, rules, a log and a review screen. Synthetic data works and no paid service is needed. Real PMS invoice export formats are still undocumented. |
| Competition /10 | 2 | No evidenced wedge. Pricebook.vet (free) and Xonvet (£19/month) cover the price list. VDS VetResolve and Xonvet cover the complaint log. Provet is closing fee-cap and own-brand gaps before Sep 2027. Lupa builds estimates and invoices. The only unserved item is the £500 pathway alert, a rule any PMS can add, and the studio can't show it's better or cheaper for any segment. |
| Risk /10 | 7 | Admin only and kept clear of clinical data. Not legal advice if outputs are signed-off drafts. Flags can start the 14-day self-report clock, which is a liability design issue. |
| **Total** | **50** | Below the first attempt (53) and the scout's pass-first 55. The extra drop comes from VetResolve and the AI role shrinking to rules. |

Red flags: none. It isn't off-limits, needs no paid service and doesn't depend on scraping, and synthetic data can show the core. It dies on score, not on a red flag.

## Why no proof test

Pipeline.md allows a proof test only for scores of 63 to 69. At 50, and with Competition at 2, even a perfect benchmark cannot reach 70.

## Files changed
- `state/ideas/killed/vet-cma-compliance-desk.md`: full file with the kill reason, lessons, revival triggers, score and gate log.
- `state/ideas/vet-cma-compliance-desk.md`: replaced with a pointer stub. The lead should `git rm` it (the validator had no shell).
- `state/ideas/RANKING.md`: row removed, Killed entry added, header counts adjusted.
