# NHS supplier carbon reduction plan and Scope 3 evidence pack

- slug: nhs-supplier-scope3-crp-pack
- stage: G0
- market and segment: UK mid-size suppliers to the NHS and, secondarily, central government (50 to 500 staff): medical consumables distributors, facilities and cleaning firms, catering, IT resellers, construction and fit-out contractors that bid on NHS frameworks and high-value contracts.
- one-line pitch: Builds the Scope 1, 2 and 3 inventory from the supplier's own ledger and purchase data, screens all 15 GHG Protocol Scope 3 categories with documented justifications, and produces the NHS-format carbon reduction plan for board approval and publication.
- forcing function: From **April 2027** NHS England will require suppliers on in-scope contracts (the NHS says £5 million or more a year, plus all new frameworks and dynamic markets regardless of value) to publicly report targets and emissions and publish a carbon reduction plan covering all relevant global Scope 1, 2 and 3 emissions, assess all 15 Scope 3 categories and justify omissions. Product-level carbon footprinting follows in April 2028 (per Valpak's summary). Lower-value contracts stay under the 2024 CRP requirement. Sources: https://www.england.nhs.uk/long-read/2027-nhs-carbon-reduction-plan-requirements-for-the-procurement-of-nhs-goods-services-and-works/ (page body did not load when fetched; wording taken from the search-result excerpt, accessed 2026-11-23); https://www.valpak.co.uk/?p=50155 (2026-11-23); https://www.penningtonslaw.com/insights/enhanced-carbon-reduction-plan-requirements-for-nhs-suppliers-time-to-get-ready/ (search summary). Central government: PPN 006 requires a carbon reduction plan for contracts over £5m a year, net zero by 2050 commitment, plan reviewed within 6 months of year-end, https://www.gov.uk/government/publications/ppn-006-taking-account-of-carbon-reduction-plans-in-the-procurement-of-major-government-contracts/ppn-006-taking-account-of-carbon-reduction-plans-html (search summary, 2026-11-23). Legislation: Procurement Act 2023 and Provider Selection Regime.

Verify before G1: the VAT basis of the £5m threshold differs between sources, and the tier boundaries for SMEs are not stated in anything I read. Also note that Seedling's page says "net zero aligned to 2045" for NHS, while Valpak and PPN 006 say 2050; the NHS roadmap PDF (https://www.england.nhs.uk/greenernhs/wp-content/uploads/sites/51/2026/06/nhs-net-zero-supplier-roadmap-june-2026.pdf) did not parse and should be read by the validator.

## Problem and who has it

Suppliers lose bids or evaluation marks without a compliant, published plan. Scope 3 is the hard part: the NHS market sounding says up to 95% of a company's carbon impact sits in supply chain and other Scope 3 (search excerpt, https://www.england.nhs.uk/long-read/market-sounding-findings-net-zero-supplier-requirements-from-april-2027/, 2026-11-23). For mid-size suppliers the data lives in an accounting ledger, purchase orders, fuel cards and travel claims, with no carbon team.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| NHS England 2027 CRP requirements (URL above) | 2026-11-23 | Date and content of the new requirement; tiered; "irrespective of value" for new frameworks. Pain signal 1: regulatory step-up in data scope. |
| https://www.valpak.co.uk/?p=50155 | 2026-11-23 | A compliance consultancy markets NHS supplier ESG services; shows 2022 to 2030 NHS milestones; says plans need board approval and public availability. Pain signal 2: advisers sell this as a service. No prices. |
| https://www.penningtonslaw.com/insights/enhanced-carbon-reduction-plan-requirements-for-nhs-suppliers-time-to-get-ready/ | 2026-11-23 | Law firm alert (search summary): subcontractor emissions may form part of the prime supplier's Scope 3; estimates acceptable where data is missing (stated for pharma). Pain signal 3: prime suppliers must chase data from their own suppliers. |
| https://www.england.nhs.uk/greenernhs/get-involved/suppliers/ | 2026-11-23 | NHS notes that SMEs and VCSEs struggle to gather emissions data (search summary). |
| https://www.gov.uk/government/publications/ppn-006-taking-account-of-carbon-reduction-plans-in-the-procurement-of-major-government-contracts | 2026-11-23 | Government points SMEs to free tools before paying a provider (search summary). Cuts against willingness to pay. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Gaia Carbon Accounting (own pricing page) | Start-Up £300, Pro £650, Enterprise £1,500 per organisation per month excl. VAT. Pro adds PPN 006 Carbon Reduction Plan, Xero integration and supplier surveys. All plans cover all 15 Scope 3 categories (https://gaiacompany.io/carbon-accounting-software/pricing/, 2026-11-23). A search summary quoted different prices (£165, £415, £1,695); the own page is used. | Page does not mention NHS templates. Generic PPN 006 plan. |
| Seedling (own site, via search summary) | Quote on request; third-party listings range £80 to £290 a month (Capterra, Net Zero Compare, conflicting) | Own pages offer a free PPN 006 template, an NHS Evergreen guide and say the platform generates a board-signed plan. This is the closest competitor and already covers much of the plan generation. |
| Carbon Manager via Xero | From about £15 a month (Xero app listing, search summary) | Spend-based Scope 3 only. |
| Valpak, Carbon Trust style consultancies | Quote-based; no prices found | Service-led; scoped per client. |
| Free government templates and tools for SMEs | Free | The default for the smallest suppliers. |

Gap that survives: thin. Plan generation and Xero-linked footprints are already sold from about £15 to £650 a month. What I could not find on any own page is NHS 2027-specific handling: the 15-category screening log with written justifications for exclusions, the board-approval and publication workflow, and a prime-supplier subcontractor data request flow tied to the 2028 product-level footprint step. That is a feature gap, not a structural one, and Seedling or Gaia could close it in a release. Expect Competition to score low.

## Why AI is essential (and the moat)

- Classify ledger lines and purchase orders into Scope 3 categories and emission factors, and draft the justification text for each excluded category, with the factor and source cited from the public DESNZ and DEFRA conversion factors.
- Subcontractor data requests: draft, send and chase questionnaires, then normalise the replies.
- Moat: a ledger-classification benchmark for UK SME accounts and a rules set tracking NHS wording. Moderate; incumbents have the same data access via Xero.

Demo with public or synthetic data: a synthetic 120-employee facilities company ledger (about 3,000 lines), public conversion factors, produce the inventory and the screening log. No real customer data needed.

## Rough build plan and Azure cost

- Weeks 1 to 2: ledger import (CSV, Xero export), category classifier, factor library.
- Week 3: Scope 3 screening log and plan document generator.
- Week 4: subcontractor questionnaire flow (email behind an adapter with mock mode), audit trail.
- Azure: default stack, estimate under $25 a month. Paid email or LLM providers behind adapters. Not yet in BUDGET.md.

## Risks, and what would prove this wrong

- Competition is the main risk: Seedling and Gaia already target PPN 006 plans, and cheap Xero apps exist.
- The £5m a year threshold may exclude most mid-size suppliers directly; the buyers would then be primes that pass obligations down. Unverified.
- Emissions numbers are estimates and will be published by the supplier. Carbon claims need human review and, where the buyer demands it, assurance. Not legal advice. Legal review needed on any wording about meeting a procurement requirement.
- Would prove wrong: ten NHS suppliers in the segment say a free template plus their accountant is enough, or NHS publishes its own tool or template for 2027.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 2: G0 file written. Own-page checks: Gaia (full), Seedling (search summary of own pages only). NHS primary page and roadmap PDF did not load; validator to read them.
