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
| | | | | | | | |

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor claims come from search summaries of provider pages, not full reads. Own-page check of Carbon Footprint Ltd and Catalyst still to do.
