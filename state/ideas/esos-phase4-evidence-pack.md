# ESOS Phase 4 energy data and evidence pack

- slug: esos-phase4-evidence-pack
- stage: G0
- market and segment: UK groups that are "large undertakings" for ESOS (250 or more employees, or turnover over £44m and balance sheet over £38m) and have no in-house energy team: multi-site retail, hospitality, logistics, care, manufacturing, education groups.
- one-line pitch: Collects utility invoices, meter reads and fleet fuel records across entities and sites, reconciles them to a 95% coverage test, and builds the evidence pack for the ESOS lead assessor and the board.
- forcing function: ESOS Phase 4 qualification date is **31 December 2026**; notification of compliance is due **5 December 2027**; action plan 5 December 2028; progress updates 2029 and 2030. Source: https://www.gov.uk/government/publications/comply-with-the-energy-savings-opportunity-scheme-esos-phase-4/how-to-comply-with-the-energy-savings-opportunity-scheme-esos-phase-4 (accessed 2026-11-23; first 100,000 of 221,000 characters read, penalties section not read). Regulator: Environment Agency, via the MESOS online system (same page). Legislation: The Energy Savings Opportunity Scheme Regulations 2014, https://legislation.gov.uk/uksi/2014/1643 (appeared in search results; not read).

## Problem and who has it

Qualifying organisations must measure total UK energy consumption over a 12-month reference period spanning buildings, transport and industrial processes, cover at least 95% of it by a compliance route, appoint a lead assessor (unless an ISO 50001 or under-40,000 kWh exemption applies), get board-level review, submit through MESOS and keep an evidence pack. Source: gov.uk page above. A commercial guide describes the hidden cost as staff time "locating invoices, extracting utility meter data and engaging operational teams". Source: https://www.3blmedia.com/news/are-you-budgeting-esos-2027 (2026-11-23).

Not all large undertakings have this solved. Group structure changes (acquisitions and disposals) alter who qualifies.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/publications/comply-with-the-energy-savings-opportunity-scheme-esos-phase-4/how-to-comply-with-the-energy-savings-opportunity-scheme-esos-phase-4 | 2026-11-23 | Thresholds, dates, 95% coverage, lead assessor, MESOS submission, evidence pack. Pain signal 1: statutory data-collection burden with a fixed deadline. |
| https://www.3blmedia.com/news/are-you-budgeting-esos-2027 | 2026-11-23 | Indicative cost bands (a service provider's guide, not fixed pricing). Pain signal 2: data collection is described as the large hidden cost. |
| https://www.carbonfootprint.com/esos_energy_savings_opportunity_scheme.html and https://www.catalyst-commercial.co.uk/services/esos-phase-4/ | 2026-11-23 | Providers sell managed ESOS including data collection and lead assessor sign-off (search summary; own pages not opened). Pain signal 3: paid services exist for exactly this task. |
| https://www.carbonfootprint.com/docs/2026-07-cfp-esos-phase4-briefing.pdf | 2026-11-23 | Vendor briefing on Phase 4 (appeared in search; not opened). |
| Job-ad signal | not collected | TODO for validator. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Managed ESOS service from a lead assessor (consultancy) | Indicative bands: smaller organisations £4,000 to £10,000; medium multi-site £10,000 to £25,000; large and complex £25,000 or more (https://www.3blmedia.com/news/are-you-budgeting-esos-2027, 2026-11-23). Labelled indicative by the source. | Service-led, repeated every four years. Data collection is partly done by the client. |
| Carbon Footprint Ltd, ESOS plus Sustrax software | No public price (search summary of own site) | Bundles lead assessor with software; a competitor owning both the sign-off and the tool. |
| Catalyst Commercial, ReEnergise, Socotec | No public prices (search summaries of own pages) | Lead assessor services that manage data collection through submission. |
| Energy management software (meter-connected) | Not priced in sources | Works where smart meters and integrations exist; weak for invoices and fuel cards across many entities. |
| In-house spreadsheet | Staff hours | Status quo. |

Gap that survives: unclear. Incumbents sell data collection bundled with the assessor, so they do not want a neutral tool, and the lead assessor sign-off is a human role that a software-only product cannot replace. A "bring your own assessor" data pack could be a neutral layer, but I have no evidence yet that buyers want that. Expect Competition to be weak to middling.

## Why AI is essential (and the moat)

- Extraction from messy invoices (gas, electricity, fuel card, fleet) across many suppliers and formats, with reconciliation to meter reads and a coverage calculation.
- Group mapping: which entities and sites sit in scope; flags for double counting.
- Anomaly detection (missing months, estimated reads, unit mix-ups).
- Moat: a validated extraction set for UK utility invoice formats, and the coverage and reconciliation rules. The audit analysis itself stays with the human lead assessor.

Demo with public or synthetic data: generate synthetic invoices for a fictional 40-site group using public UK conversion factors and tariff structures, seed errors, and show the coverage percentage rising as gaps are closed. No real customer data needed.

## Rough build plan and Azure cost

- Weeks 1 to 2: entity and site model, invoice ingestion, kWh normalisation.
- Week 3: reconciliation, 95% coverage test, evidence pack export (PDF plus CSV) for the lead assessor.
- Week 4: board summary, audit log, retention.
- Azure: default stack plus Document Intelligence or an LLM extraction adapter with a mock mode. Estimate $20 to $40 a month at demo load. Not yet in BUDGET.md.
- The studio does not submit to MESOS. The responsible person and lead assessor do.

## Risks, and what would prove this wrong

- Buyers are large (250+ staff) and buy through procurement; the target segment is those without energy teams, which may be small.
- The cycle is four-yearly; recurring revenue is weak unless the product also serves SECR and annual action-plan progress (SECR overlap is plausible but not verified here).
- Not legal advice: ESOS compliance is a statutory duty with a lead assessor sign-off. Product outputs are data packs. Legal review needed before any "compliant" claim.
- Would prove wrong: three target firms say their energy supplier or consultant gives them the data pack free; or MESOS or guidance adds a template that makes the pack trivial.
- Penalties not read. Check section 15 of the gov.uk page.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 10 | 12 | 7 | 7 | 11 | 2 | 9 | 58 |

## Validator notes (2026-11-23)

**Red-flag check: none.**
- Not an off-limits area: organisation-level energy data only.
- No paid service or scraping is needed. Conversion factors are public, and extraction runs on the Document Intelligence free tier or gpt-5-mini.
- Public and synthetic data can credibly demo the value. Synthetic utility invoices, meter reads and fuel-card exports for a fictional 40-site group are enough to show extraction, kWh normalisation, the 95% coverage test and the evidence pack.
- Legal advice: ESOS is a statutory duty, but the lead assessor signs off and the organisation submits through MESOS. The tool only produces data packs. The assessor reviews every figure and assumption, and the product makes no "compliant" claims.

**Forcing function: confirmed on gov.uk** (published 30 July 2026)
- Dates:
  - Qualification date: 31 Dec 2026, with a 12-month reference period that includes it.
  - Notification of compliance: by 5 Dec 2027. Action plan: by 5 Dec 2028. Progress updates: 2029 and 2030.
- Who qualifies: 250+ employees, or turnover over £44m and balance sheet over £38m.
- What's required: 95% coverage, and a lead assessor unless ISO 50001 covers 95% of use or use is under 40,000 kWh.
- Penalties (section 15, the scout's open item, now read):
  - Failure to notify: up to £5,000, plus £500 a working day for up to 80 days.
  - Failure to keep records: up to £5,000.
  - Failure to carry out an audit: up to £50,000, plus £500 a day.
  - False or misleading statement: up to £50,000.
  - The regulator may also publish the breach.

**Market size**
- DESNZ's post-implementation review (18 July 2025, PDF read): the Environment Agency believed 9,871 corporate groups qualified for Phase 3. 8,581 (87%) notified and 7,145 confirmed they had to comply.
- So the market is about 7,000 to 10,000 groups, once every four years.

**Falsification findings**
- **Assessors bundle the data work with the sign-off.**
  - Carbon Footprint Ltd's own page offers gap analysis, audits, lead assessor sign-off and submission help. Its Sustrax software takes bill uploads and provides a "digitised evidence pack" (fetched; no price).
  - Catalyst, ReEnergise, TEAM, Elmhurst and others sell managed ESOS (search summaries).
  - The indicative £4,000 to £25,000+ goes to the assessor, not to a data tool.
- **The data often already exists.**
  - SECR has required large companies (two of: 250 employees, £36m turnover, £18m balance sheet) to report annual energy use in their annual reports since April 2019 (gov.uk press release, fetched). Most ESOS groups therefore already compile a year's energy data.
  - Energy bureau and bill validation services hold invoice data for many multi-site groups. Examples are SER's Energy Bureau Analyst role and Veolia's energy data role with an invoice validation system (search summaries).
- **No ESOS-specific job ads found.**
- **Why buyers won't switch:** the assessor owns the method and the sign-off and prefers its own tool, and the client wants one supplier.
- **Recurrence:** one main cycle every four years plus two short progress updates. That is hard to sell as a subscription.

**Scoring rationale**
- **Pain 10.** It is statutory with real penalties, but it comes round every four years and SECR and bureau data partly solve it already.
- **Pay 12.** Organisations pay £4,000 to £25,000+ per phase, but to assessors who bundle the data collection.
- **AI 7.** Utility-invoice extraction is useful but commoditised.
- **Reach 7.** The Environment Agency publishes Phase 3 notification data, a public company-level lead list, and there are lead assessor registers. But buyers are large firms with procurement processes.
- **Build 11.** Straightforward on the default stack.
- **Competition 2.** Assessor bundles, Sustrax-type tools and bureau services already cover it.
- **Risk 9.** Business data, with the assessor signing off.

**What would change my mind**
1. Evidence that lead assessors, not end clients, would buy a data-collection tool: assessor complaints about client data quality, or an assessor-facing tool with prices and traction.
2. A recurring hook verified on gov.uk, for example the same data pack serving annual SECR reporting, with evidence that SECR filers buy tools for it.

Without a recurring hook the ceiling is about 62. Recommend parking it.

**Sources** (all accessed 2026-11-23)
- https://www.gov.uk/government/publications/comply-with-the-energy-savings-opportunity-scheme-esos-phase-4/how-to-comply-with-the-energy-savings-opportunity-scheme-esos-phase-4 (fetched, including section 15)
- https://assets.publishing.service.gov.uk/media/689c6b3cd2a1b0d5d1bb1260/esos-pir-2025.pdf (PDF read)
- https://www.carbonfootprint.com/esos_energy_savings_opportunity_scheme.html (fetched)
- https://www.gov.uk/government/news/new-digital-tool-enables-easier-energy-and-carbon-reporting (fetched; SECR thresholds)
- https://www.3blmedia.com/news/are-you-budgeting-esos-2027 (scout's source, not re-read)
- https://www.itjobswatch.co.uk/jv/SER-Limited/Energy-Bureau-Analyst-Job-Bristol-UK-4tqtpr and https://careers.veolia.co.uk/job/jr31197 (search summaries)
- https://www.teamenergy.com/discover/insights/guidance-and-market-research/esos-phase-4-readiness-checklist/ (search summary)

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor claims come from search summaries of provider pages, not full reads. Own-page check of Carbon Footprint Ltd and Catalyst still to do.
- 2026-11-23 | validator | G0→G1 | REVISE 58 | Dates and penalties are confirmed and 7,000 to 10,000 groups are in scope, but the job comes round every four years, lead assessors bundle data collection with the sign-off (Carbon Footprint's Sustrax already has a digitised evidence pack), and most groups already compile annual energy data for SECR.
