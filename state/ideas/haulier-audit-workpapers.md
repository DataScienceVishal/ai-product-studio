# Operator-licence compliance audit workpapers for haulage auditors

- slug: haulier-audit-workpapers
- stage: G0
- market and segment: Independent audit providers and transport consultants who carry out operator-licence compliance audits for UK goods-vehicle operators (including those told to commission one by a Traffic Commissioner), plus operators doing a pre-audit self-check. Fleet sizes of 2 to 50 vehicles.
- one-line pitch: Reads an operator's maintenance (PMI) sheets, driver defect reports, tachograph and driver files, builds the sample the DVSA/Traffic Commissioner Standard Audit Framework asks for, and drafts the audit working papers and findings for the human auditor to verify and sign.

## Problem and who has it
- Traffic Commissioners often require an independent compliance audit as an undertaking, and the audit must meet the government's framework: independent of the operator, payment not linked to the outcome, minimum evidence per topic, sample sizes for vehicle, trailer and driver records, and an auditor declaration (gov.uk guidance, fetched).
- Audits that do not meet the standard are rejected. In a Traffic Commissioner decision dated 28 July 2026 the earlier undertaking to lodge an independent audit "was not met" because the consultant's report was not "sufficiently independent"; the licence was curtailed by half, to four vehicles (decision page, fetched).
- The failings listed in that decision (maintenance intervals, driver defect reporting, incomplete maintenance records, drivers' hours and tachograph records, unsigned infringement reports) are the records an auditor has to sample by hand.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/government/publications/operator-compliance-audits/operator-compliance-audits | 2026-11-24 | Fetched. Standard Audit Framework: topics, minimum evidence, sample sizes (section 1.3), auditor declaration (1.4). Auditor must be independent and cannot be paid by outcome. No template required: "Different audit providers will use different templates." Audits generally in person; parts can be remote if documents are accessible. |
| https://www.gov.uk/traffic-commissioner-regulatory-decisions/decision-for-pioneer-transport-ltd-of2056573 | 2026-11-24 | Fetched. Decision 28 July 2026: audit undertaking not met, consultant's report not independent enough, licence curtailed by half, to four vehicles, maintenance and driver-record failings listed. |
| https://www.gov.uk/government/publications/traffic-commissioners-annual-report-2025-to-2026/traffic-commissioners-for-great-britain-annual-report-2025-2026 | 2026-11-24 | Fetched. Public inquiries listed within 12 weeks: 77% against a 95% target. The Commissioners say AI "cannot replace human judgement in regulatory decision-making" and warn AI-drafted hearing documents can contain incorrect caselaw references. DVSA and the Commissioners are trialling technology to read bank statements. Licence and inquiry counts are in a linked spreadsheet not read. |
| https://www.gov.uk/traffic-commissioner-regulatory-decisions/ (the decisions listing; Benticks, RG Removals, Sauka Groundworks and other decision pages from the search) | 2026-11-24 | Search results. Published Traffic Commissioner decisions are a public corpus for failure patterns. Only the Pioneer decision was read. |
| https://logistics.org.uk/services/excellence-schemes/operator-licence-audit and https://www.rha.uk.net/Services/ComplianceServices/ComplianceAudits/LGVOperatorsLicenceComplianceAudit | 2026-11-24 | Search summaries only. Logistics UK's audit covers 9 sections with a report within 7 working days; the RHA sells HGV, coach and van audits. No prices published. (The Logistics UK page returned 404 on direct fetch.) |
| https://trans.info/en/automatic-driver-follow-up-inspection-ready-tachograph-compliance-what-roadsoft-s-ai-is-giving-uk-hauliers-in-2026-478698 | 2026-11-24 | Search summary only. Roadsoft's AI add-on automates driver follow-up for tachograph compliance in the UK in 2026. A records tool, not audit workpapers. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Legal-firm audit: a Fieldfisher fixed-fee operator audit for trade members, £2,500 (small), £4,000 (medium), £5,500 (large) ex VAT | 2020 article, search summary: https://www.route-one.net/operators/fixed-fee-legal-services-for-trader-annual-members/ | Dated and from a law firm, not a transport consultant. Shows what a full audit has cost |
| Logistics UK Van Excellence audit £654.50 ex VAT for a whole organisation | 2022 form via search summary (https://logistics.org.uk/files/events/vans-today-2022/van-and-membership-flyer-a5-web); not the operator-licence audit | A cheaper audit product, different scope. Shows the low end |
| FleetCheck: £3 (Driver), £4 (Essential), £6 (Professional) per vehicle per month, minimum 10 vehicles, 36-month contract; "O licence compliance features" on the Professional plan; document reading by OCR, no AI claim (page fetched: https://www.fleetcheck.co.uk/pricing) | £30 to £60 a month for 10 vehicles | A records and defect platform. No audit workpapers or framework sampling described |
| Compliance Control (HGV and PSV records, walkaround checks, audit-ready reporting) | Not published; a Capterra snippet shows "199" with no unit (unverified) | Records, not the audit itself (search summary) |
| Roadsoft (tachograph, AI driver follow-up) | Not published | Tachograph follow-up only |
| Transport consultants and RHA, Logistics UK audits | Not published | Manual sampling; the likely first buyer of a workpapers tool |

## Why AI is essential (and the moat)
- Inputs are scanned PMI sheets, handwritten or typed defect reports, tachograph analysis exports and driver files in inconsistent layouts. Mapping each document to the framework topic, checking dates against inspection intervals, linking defects to repairs and spotting gaps needs document understanding, not a rules table.
- Sample selection and sign-off stay human. The tool drafts workpapers with page references; the auditor verifies. That fits the guidance (independence, auditor declaration) and the Commissioners' stance on AI.
- Moat: the Standard Audit Framework turned into a checklist, plus a labelled set of failure types from published Traffic Commissioner decisions.

## Public data the studio would use to prove the gap and build the demo
- The gov.uk Standard Audit Framework and DVSA earned-recognition audit standards (https://www.gov.uk/government/publications/dvsa-earned-recognition-vehicle-operator-standards/heavy-goods-vehicle-hgv-operator-audit-standards-dvsa-earned-recognition, search result), published Traffic Commissioner decisions (gov.uk), the DVSA guide on maintenance standards.
- Proof test: take 50 published decisions, extract the failure types, build synthetic operator records that contain those failures, and measure whether the tool finds them with the framework reference. Pass: at least 85% found, at most 10% false alarms.
- Mock mode loses nothing; no paid telephony or messaging.

## Add-on check (does the incumbent already do it?)
- Read: FleetCheck pricing page (no AI, no audit workpapers). Search only: Compliance Control, Roadsoft. Not read: their help pages.
- The DVSA/Traffic Commissioners themselves say AI is not to replace judgement, which supports a "human signs" design but also means an AI-led audit would not be accepted.
- Free community tools: none found. Logistics UK and the RHA provide audit templates to members (not read).

## How the selling partner could reach buyers
- Audit providers: RHA and Logistics UK audit teams, independent transport consultants, transport law firms (company-level lists from their own websites). One sale to an audit provider reaches many operators. The number of independent auditors is small, perhaps in the low hundreds (estimate, no source), so Reach is limited. Channel unknown.

## Rough build plan and Azure cost
- Document intake (scans and exports), framework checklist, sampler per the framework's section 1.3, workpaper and findings drafts with citations, signed-off report export. About 4 weeks for a narrow version (maintenance and driver defect records). Azure about £15 to £30 a month (estimate); model cost depends on Q-7.

## Risks, and what would prove this wrong
- Few buyers: if only a few hundred auditors exist and most use their own templates, revenue is capped. Test: count consultants and audit providers on the RHA, Logistics UK and Traffic Commissioner decision pages.
- Independence rule: operators cannot self-certify, so the tool sells to auditors; if auditors resist software, there is no demand.
- Pay is unproven: only one dated legal-firm price and one older audit product price; no current consultant fee. An RHA or Logistics UK price would help.
- Operator and driver personal data in records (driver names, licence numbers): pseudonymise.
- A records platform (FleetCheck, Compliance Control) adds an "audit pack" export in a month. Test: read their help pages.

## Score (validator)
Draft self-score by the scout (validator to re-score):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 12 | 9 | 8 | 5 | 10 | 6 | 8 | 58 |

Rationale: Pain 12 (a regulator-rejected audit and curtailment shown in one decision; no volume data); Pay 9 (dated prices only); AI 8 (document reading, but sign-off is human and templates are loose); Reach 5 (small auditor base); Build 10 (clear framework, messy scans); Competition 6 (records platforms exist, none shown to produce audit workpapers); Risk 8 (some personal data, low advice risk).

## Gate log
- 2026-11-24 scout round 6 (T-36): G0 drafted. Needs a current audit price and a count of audit providers.
