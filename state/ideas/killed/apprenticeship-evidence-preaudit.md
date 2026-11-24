# Apprenticeship evidence-pack pre-audit checker

- slug: apprenticeship-evidence-preaudit
- stage: KILLED at G0 (validator 53, 2026-11-24, T-36)
- market and segment: England apprenticeship training providers (independent training providers, employer-providers and colleges) funded through the DfE, roughly 2,588 organisations on the register as at August 2026. Sweet spot: providers with 100 to 2,000 apprentices that have no in-house funding assurance team.
- one-line pitch: Reads each apprentice's evidence pack (signed agreement, training plan, progress reviews, off-the-job logs, eligibility documents) and the provider's ILR extract, and lists the learners whose evidence does not support the funding claimed, citing the DfE rule for each gap, before the DfE or a mock auditor finds it.

## Problem and who has it
- The DfE's own assurance findings put off-the-job training first: "Off-the-job training (OTJT) was the main cause of apprenticeships funding errors, audit delays and control recommendations." It also flags signatures not robust enough, so "all funds for that learner may be at risk", missing monthly learning activity, unreliable end dates and inaccurate negotiated price (TNP2) values (fetched).
- DfE investigation outcome reports published in 2026 repeat the pattern: ILR data not matching the evidence held, progress reviews not held or not retained (search summaries of the Woodspeen and other reports; PDFs could not be read by the fetch tool).
- Providers pay for assurance twice: an audit and, often, a mock audit. One provider reported being quoted "up to £12k for an audit" and also paying for a mock DfE audit (provider forum, via search summary; URL not shown, so unverified).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/publications/esfa-assurance-work-on-post-16-funding/common-findings-from-funding-assurance-work-on-post-16-education-providers-2024-to-2025-assurance-year | 2026-11-24 | Fetched. Ranked common findings (OTJT, agreements and signatures, learning activity, end dates, TNP2, start dates, co-investment, eligibility, English and maths). Clawback: "we will seek to recover the funding, including funding overclaimed in previous years". No counts or amounts given. |
| https://assets.publishing.service.gov.uk/media/6a6209e8243ee000f7127e96/PDSAT_review_notes_2025_to_2026.pdf | 2026-11-24 | Search summary only. Review notes include checks 26A-215, 26A-216 and 26A-217 reconciling planned and actual off-the-job hours. A public, rule-by-rule test list. |
| https://assets.publishing.service.gov.uk/media/6a68cabe229c578debc1a78c/Funding_Rules_2627_Version_3_Final.pdf | 2026-11-24 | Search result. 2026 to 2027 funding rules, with an off-the-job training section. Not read. |
| https://assets.publishing.service.gov.uk/media/6a9ed802f36e1f225ecb7eb4/Evidence_requirements_for_New_Apprenticeships_-_procedure_process_flow_diagram_v0.1.pdf | 2026-11-24 | Search result title only: evidence requirements for the new apprenticeships, process flow v0.1. Possible forcing function; not read. |
| https://assets.publishing.service.gov.uk/media/69ca6df4b111d64c49bb3d22/DfE_investigation_outcome_report_Woodspeen_Training_Limited.pdf | 2026-11-24 | Fetch returned the compressed PDF only; content not read. A search summary says 2026 investigations found ILR data not matching evidence. A real-failure corpus the validator can read. |
| https://forvismazars.com/uk/en/industries/public-social-sector/public-and-social-sector-insights/mock-funding-assurance-reviews-in-practice | 2026-11-24 | Search summary only. Mock funding assurance reviews examine ILR data, enrolment and delivery records and PDSATs. Providers buy this from audit firms. |
| https://mazars.co.uk/services/audit-assurance/independent-assurance-reviews/education-funding-assurance and https://www.rsmuk.com/insights/advisory/mock-funding-compliance-review | 2026-11-24 | Search results: Mazars and RSM sell mock funding reviews. Prices not published. |
| https://download.apprenticeships.education.gov.uk | 2026-11-24 | Search result: the apprenticeship provider and assessment register (APAR) can be downloaded as a CSV. Gives the studio a company-level list of buyers to size and target. |
| https://feweek.co.uk/?p=156557 (and related FE Week items) | 2026-11-24 | Search summary only: 2,588 organisations on the register (27 August 2026 item); figures across items are inconsistent, so size from the APAR CSV instead. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Aptem Apprentice and Aptem Enhance (AI virtual assistant, checkpoint, marking aid, enhanced reviews); eBook "Using Aptem to prepare for an ESFA Audit"; webinar "Preparing for DfE audit" (https://aptem.co.uk/wp-content/uploads/2023/04/Aptem-eBook-Using-Aptem-to-prepare-for-an-ESFA-Audit.pdf, https://support.aptem.co.uk/hc/en-gb/articles/34823483925906-Webinar-Preparing-for-DfE-audit) | Not published | Search summaries only; the PDFs could not be read. Aptem already positions its system as the audit record and has AI. The gap is providers whose evidence lives across several tools, or who use another LMS |
| OneFile (features list: evidence mapping and audit trail; G-Cloud listing: AI engagement insights) https://onefile.co.uk/features | Not published | Search summary: audit trail and engagement monitoring, no evidence-vs-ILR check found |
| Smart Assessor (now an ePortfolio under OneAdvanced) | Not published | No AI audit-readiness feature found in search |
| Mock funding assurance from audit firms (Mazars, RSM) | Not published. One provider reports "up to £12k" for an audit (unverified, forum) | Sampling, slow, annual |
| Cost of failure | Clawback of funding for any learner whose evidence fails, including prior years (DfE common findings, fetched) | The whole value of an apprenticeship funding claim for that learner |
| In-house quality or compliance staff | Not priced here. Look for provider job ads naming ILR audit and evidence-pack checks (not yet searched) | The staff hours a tool would cut |

## Why AI is essential (and the moat)
- Evidence is unstructured: scanned signed agreements, progress review notes, off-the-job logs in free text. The checks are judgement calls, for example whether a logged activity is eligible off-the-job training, whether reviews are tripartite and dated, whether the signature meets the standard, and whether the hours reconcile with the ILR.
- A rules engine on structured ILR data already exists (PDSAT, provider software). The gap is reading the evidence behind the ILR and reconciling the two.
- Moat: an evaluation set built from the DfE's published failure patterns and investigation reports, and a library of rule references (funding rules, PDSAT checks) mapped to findings.

## Public data the studio would use to prove the gap and build the demo
- DfE funding rules 2026 to 2027, evidence-requirements guides and flow diagrams, PDSAT review notes, the ESFA/DfE common-findings publications, investigation outcome reports (all gov.uk, Open Government Licence unless stated; validator to confirm), the APAR CSV, and the Skills England off-the-job minimum volumes by standard.
- Proof test the studio can run itself: write 60 synthetic evidence packs from the published failure types, with known defects seeded, and measure detection per rule. Pass: at least 85% of seeded defects found with the right rule cited and at most 10% false alarms.
- No real learner data is needed for the demo. Mock mode loses nothing.

## Add-on check (does the incumbent already do it?)
- Aptem: has AI and an audit-readiness story (search summaries). Whether Aptem Enhance checks evidence packs against funding rules is not confirmed: the eBooks could not be read. The validator should read Aptem's AI ebook (https://www.aptem.co.uk/wp-content/uploads/2026/05/Aptem_AI_and_data_in_apprenticeship_providers_ebook.pdf) in a PDF-capable tool.
- OneFile and OneAdvanced: nothing found on AI evidence checks.
- Free tools: DfE's own PDSAT is free and deterministic (ILR data only).

## How the selling partner could reach buyers
- The APAR CSV gives named organisations. Trade bodies: the Association of Employment and Learning Providers (AELP; not researched here, membership lists are not public data; name the channel before scoring). Press: FE Week. Channel unknown for the partner; if there is no education contact, Reach is about 4.

## Rough build plan and Azure cost
- Document ingestion (PDF and scans), checklists per funding rule, ILR extract reader, reconciliation report with rule references, per-learner exceptions list. About 4 weeks for a narrow version (agreement, OTJ hours, progress reviews). Azure about £20 to £40 a month (estimate); document OCR and model costs depend on Q-7.

## Risks, and what would prove this wrong
- Learner personal data at scale, including 16 to 18 year olds and right-to-work documents: high Risk. Pseudonymise, UK region, short retention; the first MVP can skip identity documents.
- Aptem or another LMS ships "evidence check" in a month, or already has it. Test: read Aptem's pages; if found, Competition falls to 2.
- The funding rules are in flux (new apprenticeship evidence requirements v0.1, Growth and Skills Levy), so rule maintenance is ongoing cost.
- Providers may expect the checker to carry audit liability. It must say "evidence gap against rule X", never "will pass audit".

## Score (validator)
Scout draft: 59 (Pain 14, Pay 11, AI 11, Reach 6, Build 8, Competition 4, Risk 5).

Validator score, 2026-11-24 (T-36):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 14 | 10 | 10 | 5 | 7 | 3 | 4 | 53 |

**Falsification findings** (all accessed 2026-11-24; "fetched" means the page itself was read)
- The platforms where the evidence lives already flag the gaps:
  - **Bud.** Bud's funding and compliance page promises "Alerts, dashboards and reports that identify missing evidence, overdue reviews or unsigned documents early" and keeps agreements, plans, reviews, activity and off-the-job hours in one learner record (https://bud.co.uk/platform-capabilities/funding-and-compliance, fetched).
  - **Bud is moving to agents.** Bud's "Funding confidence" solution promises "Audit-ready evidence packs for every learner" and sits under the heading "Bud Agents: specialist agentic capabilities for funded delivery" (https://bud.co.uk/solutions/funding-confidence, fetched). Bud also publishes a 2026/27 funding-rules audit checklist (search result).
  - **Aptem.** Aptem Apprentice has a structured eligibility review, ILR sign-off controls, a full ILR audit history, "Validation warnings fire if inconsistent data is entered", and change-of-circumstance trackers mapped to DfE codes (https://www.aptem.co.uk/apprentice-training-providers/apprenticeship-compliance-management-aptem-apprentice/, fetched).
- Aptem already bundles the human version of this product. Its compliance assurance review (ACAR) is an annual two-day independent review by Lockhart Hawkins: a self-assessment against the core funding rules, a sample of five learners reviewed inside Aptem, and trend analysis. It is "included as part of their Aptem package" for eligible customers and sold as an add-on to others (https://www.aptem.co.uk/aptem-news/aptem-compliance-assurance-review/, fetched; no price). This proves the spend, but the system vendor owns both the data and the review.
- What's left is narrow: judging whether evidence that is already present is good enough (is the off-the-job activity eligible, is a review substantive?). That is a layer over data held in Aptem, Bud or OneFile. The studio can't test their export formats without a customer, and Bud is building agents on that same data.
- Pay is still unpriced:
  - Mazars and RSM don't publish prices for mock reviews (search results).
  - The "up to £12k" forum figure is unverified.
  - Aptem's ACAR and Bud's per-learner prices aren't on their pages (Bud's G-Cloud listing https://www.applytosupply.digitalmarketplace.service.gov.uk/g-cloud/services/423082446389131, fetched, puts its prices in a PDF).
- Data licence: no problem. The DfE funding rules, the common findings and the PDSAT notes are on gov.uk under the OGL.
- Risk:
  - The product processes learner personal data at scale, including 16 to 18 year olds, eligibility and right-to-work documents, and learning-difficulty information.
  - Its findings feed funding decisions about named learners.
  - The funding rules change every year, and apprenticeship units arrived in 2026.

**Scores in brief.**
- Pain 14: the DfE's own findings (fetched) and clawback.
- Pay 10: spend is proven (ACAR, mock reviews), but there is no price.
- AI 10: judging unstructured evidence is real AI work, but the residual layer is narrow.
- Reach 5: the APAR CSV names the buyers; the channel is unknown.
- Build 7: messy scans, many rules, yearly rule changes and untestable LMS exports.
- Competition 3: Bud's alerts and agents, Aptem's validation and ACAR, mock audits, and the free PDSAT.
- Risk 4: minors' data and eligibility documents.

**Verdict: KILL (first attempt; ceiling below 70).**
- The DfE itself documents the pain, but the systems that hold the evidence already alert on missing, unsigned and overdue evidence:
  - Bud describes "Funding confidence" as an agentic capability.
  - Aptem bundles an independent compliance review into its package.
- That leaves a standalone checker one narrow judgement layer, over data the studio can't reach without a customer's LMS export. It also carries minors' personal data and a rule set that changes every year.
- Even with the best plausible evidence (Pain 16, Pay 13, AI 11, Reach 6, Build 8, Competition 4, Risk 5), the score tops out at about 63.

**Lessons**
- In LMS-centred sectors, the LMS vendor owns the evidence and the "audit-ready" story, and now bundles a human review as well (Aptem ACAR). Check the vendor's news pages for bundled services as well as for features.
- Ideas whose input is "the customer's records held in a vertical system" inherit that system vendor as their main competitor. It is the same lesson as the tour-operator kill in round 5.

**What would revive it**
- Evidence that a large group of providers keeps evidence outside Aptem, Bud and OneFile (for example colleges using a general VLE plus spreadsheets), from 15 or more public job ads or tender documents that name that setup.
- And a published price for mock funding reviews or ACAR.
- And a selling partner with access to training providers.

## Gate log
- 2026-11-24 scout round 6 (T-36): G0 drafted. Aptem's AI ebook and the 2026 investigation reports still need reading with a PDF-capable tool.
- 2026-11-24 | validator | G0→G1 | KILL 53 | Bud already alerts on missing, unsigned and overdue evidence and sells "Funding confidence" under its agents line, Aptem bundles an independent compliance review (ACAR, Lockhart Hawkins), and the residual judgement layer sits on LMS data the studio can't reach; minors' data at scale; ceiling about 63.
