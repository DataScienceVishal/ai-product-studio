# Plastic Packaging Tax recycled-content evidence ledger

- slug: ppt-recycled-content-ledger
- stage: G0
- market and segment: UK manufacturers and importers of plastic packaging components registered for Plastic Packaging Tax (HMRC counted 5,142 registered businesses at 13 August 2026), plus their customers who need proof. Target the mid-size converters and importers with many product lines and several resin suppliers.
- one-line pitch: A per-product-line ledger of plastic weights, recycled content and supplier evidence that produces the quarterly return figures and re-tests every product line when the April 2027 rules change what counts as recycled.
- forcing function: Plastic Packaging Tax is live (quarterly returns). On **1 April 2027** pre-consumer plastic waste stops counting towards the 30% recycled-content threshold, and chemically recycled content may only be counted under a certified mass balance approach (3-month site accounting period, no negative balance, certification at every supply chain step, records kept six years). The rate is £228.82 a tonne from 1 April 2026 (disputed by one source that listed older figures). Sources: https://www.gov.uk/government/publications/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic (effective date 1 April 2027 confirmed on the page; the pre-consumer and rate details come from search summaries of https://www.gov.uk/guidance/preparing-to-use-a-mass-balance-approach-for-plastic-packaging-tax and https://www.pinsentmasons.com/out-law/news/mass-balance-shift-uk-plastic-packaging-tax, accessed 2026-11-23). HMRC technical consultation on mass balance launched 6 October 2026 (search summary). Regulator: HMRC. Record rules: https://www.gov.uk/guidance/record-keeping-and-accounts-for-plastic-packaging-tax (search result; not read).

## Problem and who has it

Records must be kept per product line and show the recycled content and its source. Recycled content is recycled weight divided by total plastic weight. A product line that falls under 30% pays the tax on the whole component weight. When the pre-consumer rule bites in April 2027, existing supplier declarations that counted pre-consumer scrap become wrong, and the line may flip from exempt to taxable. Source: gov.uk guidance via search summaries (2026-11-23).

Finance angle: this is a tax return, so the cost of error is an assessment and penalties. Penalty amounts were not found in this round.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/statistics/plastic-packaging-tax-ppt-statistics (via search summary of https://www.packaging-gateway.com and https://erp-recycling.org/uk/news-and-events/2026/09/plastic-packaging-tax-what-the-latest-figures-reveal/) | 2026-11-23 | 5,142 registered businesses at 13 Aug 2026; 2.970m tonnes of plastic packaging declared in 2025-26, of which 1.107m tonnes taxable; about 51% met the 30% recycled threshold; £250m accrued. The ERP article body did not load. |
| https://www.pinsentmasons.com/out-law/news/uk-plastic-packaging-tax-data-increases-scrutiny-on-supply-chains | 2026-11-23 | Law firm says the data increases scrutiny of supply chains; commentators cite HMRC concern over recycled content claim integrity (search summary). Pain signal 1. |
| https://www.valpak.co.uk/epr-drs/plastic-packaging-tax/ | 2026-11-23 | Valpak lists as manual burdens: component-level composition, collecting and reconciling recycled-content data per component, evidence per component. Pain signal 2. |
| https://cms.law/en/gbr/legal-updates/key-consultation-on-mandatory-third-party-certification-for-uk-plastic-packaging-tax-recycled-content-claims | 2026-11-23 | A consultation on mandatory third-party certification for mechanically recycled content (closed 10 Aug 2026 per a search summary). Pain signal 3: evidence requirements are tightening. Page not opened. |
| Job-ad signal | not collected | TODO for validator. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Valpak PPT service plus Data Insights Platform | "Contact us for a quote"; tax liability calculator is free and estimates tax, not fees (own page, 2026-11-23) | Service-led; the page does not say which steps are automated. |
| PackTotal PPT / EPR (UK packaging compliance software) | Price not published (third-party listing says no data; own site not reachable) | Covers PPT and EPR; the closest software competitor. I could not read its own page. |
| ERP Recycling managed calculation and reporting | No price found (search summary) | Managed service with audit-ready methodology records. |
| Free quarterly return template from Paperform | Free (search result) | A form, not an evidence ledger. |
| Tax itself | £228.82 a tonne of taxable plastic packaging (2026-11-23, one source disputes) | The cost of getting a product line wrong. |

Gap that survives: weak. Three vendors already sell the data-gathering and return workflow. The only angle I can see is the 1 April 2027 re-test of every product line against the new definitions, and evidence-chain tracking for mass balance certificates. That is a short window and incumbents are well placed to add it. This idea is more a feature of the pEPR idea than a stand-alone product. Consider merging both into one "UK packaging compliance data layer" at validation, since the SKU and bill-of-materials data is the same.

## Why AI is essential (and the moat)

- Extract recycled-content claims and certificates from supplier declarations and resin datasheets, and test them against the April 2027 definitions.
- Detect product lines whose status flips and quantify the tax change.
- Moat: rules tracking and a labelled set of supplier declarations. Moderate at best.

Demo with public or synthetic data: synthetic converter with 150 product lines, synthetic supplier declarations (some counting pre-consumer scrap), the public HMRC rules and rate. Show the before and after tax effect on 1 April 2027.

## Rough build plan and Azure cost

- Weeks 1 to 2: product-line ledger, recycled-content calculator, return figure export.
- Week 3: declaration extraction and evidence chain, April 2027 re-test.
- Week 4: mass balance certificate tracker, audit trail, six-year retention.
- Azure: default stack, estimate under $20 a month. Not yet in BUDGET.md.
- No HMRC submission integration assumed; a human files the return.

## Risks, and what would prove this wrong

- Not tax or legal advice. HMRC guidance decides what counts. A tax adviser must review before the product states a tax figure. Human sign-off on every return figure.
- Mass balance rules are still in consultation; guidance is due early 2027.
- Small market: 5,142 registrants, many already served by Valpak, ERP or PackTotal.
- Would prove wrong: PackTotal's own site shows evidence tracking and April 2027 re-testing already; or five target converters say their ERP already holds recycled-content evidence per line.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 10 | 9 | 7 | 5 | 11 | 2 | 7 | 51 |

## Validator notes (2026-11-23)

**Verdict: REVISE, merged into pepr-packaging-data-pipeline.** I agree with the scout's merge proposal, for three reasons:
- The data is the same: per-component plastic weights and supplier evidence.
- The buyers overlap: brand owners and importers with plastic packaging.
- The incumbents are the same: Valpak, ERP, Clarity and PackTotal sell both.

Alone it scores 51. It continues as a module that follows G4 of pepr-packaging-data-pipeline, scored there as part of the merged idea. Don't re-score it separately.

**Red-flag check: none.**
- Not an off-limits area. It does touch a tax return (see sign-off below).
- No paid service or scraping is needed.
- Public and synthetic data can credibly demo the value. A synthetic converter with 150 product lines, synthetic supplier declarations (some counting pre-consumer scrap) and HMRC's public rules are enough to show the 1 April 2027 re-test and its tax effect.
- Tax advice flag and sign-off design:
  - The module outputs recycled-content figures and evidence per component, never a tax liability statement.
  - The registrant signs off every return figure.
  - A tax adviser reviews before any tax figure appears.
  - There is no HMRC submission.

**Forcing function: confirmed on gov.uk**
- Policy paper (26 Nov 2025): from 1 April 2027, pre-consumer waste no longer counts towards the 30% threshold. Chemically recycled content counts only under a certified mass balance approach.
- Mass balance guidance (published 28 Aug 2026):
  - a 3-month accounting period with no negative balance;
  - certification at every step from the chemical recycler to the converter;
  - records kept for 6 years.
- Tax rate: £228.82 a tonne from 1 April 2026 (gov.uk rates page via search summary, matched by the Isle of Man government), and £236.56 from 1 April 2027 (Deloitte, search summary). The scout's "disputed" note is resolved: the other figure was a typo in a GWP guide.
- HMRC statistics (updated 27 Aug 2026, fetched):
  - 5,142 businesses registered at 13 Aug 2026.
  - 2.970m tonnes declared in 2025-26, of which 1.107m tonnes (37%) were taxable.
  - 1.506m tonnes (51%) were declared at or above 30% recycled content.
  - £250m accrued.

**Falsification findings**
- Valpak's platform already reports on recycled content and source certification (BRC release, fetched), and Valpak's PPT service is priced by quote (the scout's own-page check).
- ERP sells a managed calculation (search summary). PackTotal PPT is unverified: its site returned 503.
- No job ads for PPT compliance roles were found.
- The April 2027 re-test is a one-off event. The ongoing work is the quarterly return, which the incumbents already handle.
- Mass balance details are still being consulted on (a technical consultation launched 6 Oct 2026, per the scout's search summary; I didn't re-check it).

**Scoring rationale**
- **Pain 10.** The rule change is real, but it is a one-off for a subset of 5,142 registrants.
- **Pay 9.** The only price points are the tax itself and quote-only services.
- **AI 7.** Reading supplier declarations is useful.
- **Reach 5.** I found no public list of PPT registrants.
- **Build 11.** Straightforward on the default stack.
- **Competition 2.** Valpak, ERP and PackTotal already cover it.
- **Risk 7.** It produces tax figures.

**What would revive it as a standalone**
Evidence that many converters relied on pre-consumer scrap to pass 30% (for example a British Plastics Federation survey or HMRC impact figures), plus own-page checks showing no incumbent offers the 2027 re-test. I don't expect it. The module path is better.

**Sources** (all accessed 2026-11-23)
- https://www.gov.uk/government/publications/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic/plastic-packaging-tax-mass-balance-approach-and-removal-of-pre-consumer-plastic (fetched)
- https://www.gov.uk/guidance/preparing-to-use-a-mass-balance-approach-for-plastic-packaging-tax (fetched)
- https://www.gov.uk/government/statistics/plastic-packaging-tax-ppt-statistics/plastic-packaging-tax-ppt-statistics-commentary (fetched)
- https://www.gov.im/news/2026/mar/03/plastic-packaging-tax-rate-to-increase-from-1-april-2026/ and https://taxscape.deloitte.com/measures-budget-2026/plastic-packaging-tax.aspx (search summaries)
- https://brc.org.uk/news-and-events/news/associate-insight/2026/valpak-by-reconomy-launches-global-epr-platform/ (fetched)
- https://www.packtotal.com/ (503)

## Gate log
- 2026-11-23 scout round 2: G0 file written. Weakest of the five on Competition; included so the validator can decide whether to merge it with pepr-packaging-data-pipeline. Price points are thin: tax rate and one quote-only vendor.
- 2026-11-23 | validator | G0→G1 | REVISE 51 (merged into pepr-packaging-data-pipeline) | The 1 April 2027 change is confirmed, but alone it is a one-off re-test for a subset of 5,142 registrants that Valpak, ERP and PackTotal already serve, so it continues only as a module of the pEPR data layer.
- 2026-11-25 | validator | T-66 | parent killed | pepr-packaging-data-pipeline was killed after its T-56 proof test failed (`state/ideas/killed/pepr-packaging-data-pipeline.md`). This module goes with it and is not to be revived alone at 51.
