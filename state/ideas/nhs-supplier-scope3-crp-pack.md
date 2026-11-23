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
| 12 | 13 | 6 | 7 | 11 | 1 | 7 | 57 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area. The product handles suppliers' business emissions data, not health data.
- No paid service or scraping is needed. The DESNZ conversion factors are free, and email runs through the mock adapter.
- Public and synthetic data can credibly demo the value. A synthetic ledger for a 120-employee facilities firm plus the public conversion factors is enough to show the inventory, the category screening log and a draft plan.
- Legal risk: the supplier publishes the emissions and targets, and its board approves them. Misleading environmental claims are a legal exposure for the supplier (my inference; legal review needed). Sign-off design:
  - The tool drafts figures and justifications, each citing its factor source.
  - The board approves, and the supplier publishes.
  - No "meets NHS requirements" wording appears without legal review.

**Forcing function: confirmed, with corrections**
- The NHS Net Zero Supplier Roadmap (June 2026, PDF read):
  - From April 2027: "new proportionate requirements for suppliers to publicly report targets, emissions and publish a Carbon Reduction Plan for all of their relevant global scope 1, 2 and 3 emissions".
  - From April 2028: product-level carbon footprinting, with the scope and method still to be set.
- The NHS long-read returned an empty page on three tries. Pinsent Masons (11 June 2026, fetched) quotes the guidance:
  - It covers new procurements after 1 April 2027 of £5m a year and above "including VAT", plus "all new framework contracts where proportionate". That settles the scout's VAT question.
  - Suppliers must commit to net zero by 2050; 2045 is only encouraged. Seedling's "2045" is the NHS's own target, not the supplier requirement.
- On the 15 categories, the guidance asks for "all relevant" Scope 3 categories. Screening all 15 and justifying omissions comes from Penningtons and the NHS market sounding (search summaries). Under PPN 006, a plan that leaves out a scope without explanation fails.
- The scout missed one point: the £5m plan rule has applied since April 2023 and was extended proportionately to all new procurements from April 2024 (roadmap). So suppliers in the 2027 tier mostly already publish a plan. The 2027 change widens Scope 3 and the reporting boundary; it doesn't create a new buyer.

**Falsification findings**
- **Seedling** is the strongest competitor (own site, fetched).
  - It has a free "Seedling Starter" tier and says "Get prepared for government and NHS bids".
  - It has already published an article, "What counts as relevant Scope 3 for a 2027 NHS Carbon Reduction Plan?", so it markets this exact wedge.
  - Each client gets a dedicated carbon specialist, and it claims "500+ businesses".
- **Gaia** (own pricing page):
  - Start-Up £300, Pro £650 and Enterprise £1,500 a month, ex VAT.
  - All plans cover the 15 Scope 3 categories.
  - Pro adds the PPN 006 plan, Xero, QuickBooks and Sage integrations, and supplier surveys. There is a free trial.
- **ClimatePartner** (own NHS page): "all relevant scope 3 categories", over 50,000 emission factors, an "audit-ready CRP" on the government template, board-level documentation and annual refreshes.
- **Cheap tools** (search summaries): Sage Earth £9 a month for Sage users, EcoHedge Express £97 a month, Certified Carbon £199 a year, and Seedling at £80 to £290 a month on listings.
- **Consultancies:** TeamEnergy sells NHS plan consultancy and Evergreen support (fetched); Valpak and Auditel also sell services.
- **Cheapest substitute:** Seedling's free tier, or the government plan template with spend data from the accountant.
- **What an incumbent could add in a month:** a 15-category screening log with justification text and a board-approval step. Seedling and Gaia already have most of it.
- **Job ads are weak** (search summaries): a Vita Health Group Sustainability Officer for a Scope 3 supplier-engagement project, and a Sopra Steria net zero manager for NHS SBS. I found none from mid-size NHS suppliers hiring for plan work.

**Scoring rationale**
- **Pain 12.** The rule binds from April 2027 and Scope 3 is genuinely hard. But most in-scope suppliers already have a plan and a provider, and the 2028 product-footprint step is undefined.
- **Pay 13.** Many paid tools and consultancies exist, but the low end runs from free to £9 a month.
- **AI 6.** Spend-based Scope 3 classification is commoditised (Sage Earth, Xero apps), and justification text is easy to generate.
- **Reach 7.** Suppliers can be found through NHS framework award lists, Contracts Finder and Find a Tender.
- **Build 11.** Straightforward on the default stack.
- **Competition 1.** At least six products already target NHS or PPN 006 plans.
- **Risk 7.** Public carbon claims, and buyers may demand assurance.

**What would change my mind**
Only a segment the carbon tools don't serve, backed by evidence. For example: primes that must collect subcontractor and product-level data for the April 2028 step, once NHS publishes the method, plus own-page checks showing that Seedling, Gaia and ClimatePartner have no subcontractor data-request workflow. Even then I'd expect a ceiling of about 60. Recommend parking it.

**Sources** (all accessed 2026-11-23)
- https://www.england.nhs.uk/greenernhs/wp-content/uploads/sites/51/2026/06/nhs-net-zero-supplier-roadmap-june-2026.pdf (PDF read)
- https://www.england.nhs.uk/long-read/2027-nhs-carbon-reduction-plan-requirements-for-the-procurement-of-nhs-goods-services-and-works/ (empty on fetch; search excerpts only)
- https://www.pinsentmasons.com/out-law/news/nhs-england-net-zero-requirements-suppliers (fetched)
- https://www.penningtonslaw.com/insights/enhanced-carbon-reduction-plan-requirements-for-nhs-suppliers-time-to-get-ready/ (search summary)
- https://www.teamenergy.com/discover/insights/market-briefings/nhs-carbon-reduction-plan-requirements-2027-suppliers/ (fetched)
- https://seedling.earth/ (fetched)
- https://gaiacompany.io/carbon-accounting-software/pricing/ (fetched)
- https://www.climatepartner.com/en/nhs-carbon-reduction-plan (fetched)
- https://www.compareyourfootprint.com/en-au/blog/sage-earth-vs-dedicated-carbon-accounting-software, https://netzerocompare.com/software/ecohedge and https://www.capterra.com/p/10036555/Certified-Carbon/ (search summaries)
- https://www.scope.org.uk/jobboard/sustainability-officer-190226 and https://onestopesg.com/esg-jobs/net-zero-and-sustainability-manager-ftc (search summaries)

## Gate log
- 2026-11-23 scout round 2: G0 file written. Own-page checks: Gaia (full), Seedling (search summary of own pages only). NHS primary page and roadmap PDF did not load; validator to read them.
- 2026-11-23 | validator | G0→G1 | REVISE 57 | The April 2027 rule is real (£5m a year including VAT, all relevant Scope 3), but Seedling (free tier, NHS 2027 content), Gaia (from £300 a month, all 15 categories, PPN 006 plans) and ClimatePartner already sell it, and most in-scope suppliers have had a plan since 2023.
