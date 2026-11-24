# SAP design-stage input desk for small SAP assessors

- slug: sap-design-stage-input-desk
- stage: G0
- market and segment: UK domestic energy assessors and small SAP/Part L consultancies (1 to 10 staff) who produce design-stage and as-built SAP calculations for small builders and architects
- one-line pitch: Reads the architect's plans, elevations and spec sheet and pre-fills the assessor's SAP input sheet (areas, U-value build-ups, openings, thermal-bridge junctions, heating spec) with every value traced to a drawing page, so the assessor only checks and keys it.

## Problem and who has it
SAP assessors price new-build SAP work per plot at very low public prices (about £75 to £100 a plot at the low end). Margin depends on how fast the assessor turns drawings into inputs in accredited software. The input step (measuring areas from PDFs, reading build-up notes, matching junction details) is repetitive. This is a "per-unit bureau" job: builders pay per plot, the assessor's cost is input time.

Why now: the Home Energy Model is due to replace SAP for new homes (DESNZ consultation Jan to Mar 2026), so assessors face a re-tooling cycle. Whether that helps (new inputs everyone must re-learn) or hurts (vendors rebuild their input flows with automation) is unknown.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://ukbc-website.pages.dev/pricing (search result; low-trust, unverified site) | 2026-11-24 | "SAP calculations start from £75 + VAT for a single new-build dwelling"; multi-plot discounted |
| Search result for a second assessor page, "from £99 per unit, no VAT" (URL not fetched; the search engine listed the same host as above) | 2026-11-24 | Second public per-plot price, unverified |
| https://forum.buildhub.org.uk/topic/2651-sap-costs/ | 2026-11-24 | Self-builders quoted £90 + VAT (design and as-built SAP) and £120+ VAT with EPC. Posts are from May 2017, so only a lower bound on history |
| https://stroma.com/built-environment-consultants/built-environment-services/energy-performance/sap-calculations (fetched) | 2026-11-24 | A large assessor sells the service by quote only. The page asks clients for plans and drawings; no automation mentioned |
| https://www.socotec.co.uk/our-services/sap-calculations (search result) | 2026-11-24 | Design-stage assessment is done in accredited software "based on architectural drawings and technical specifications" (manual input) |
| https://www.gov.uk/government/consultations/home-energy-model-energy-performance-certificates/home-energy-model-hem-methodology-for-assessing-existing-dwellings-and-producing-new-energy-performance-certificates-metrics-accessible-webpage (search result) | 2026-11-24 | HEM methodology is replacing SAP-based EPCs (existing dwellings); new-build transition date not confirmed |
| https://www.elmhurstenergy.co.uk/blog/2026/06/03/government-epc-accuracy-research-highlights-opportunity-to-strengthen-energy-assessment/ (search result) | 2026-11-24 | Accreditation body says input accuracy is a live quality issue (EPC accuracy research) |
| Fiverr SAP gigs, e.g. https://fiverr.com/fisched/prepare-sap-reports-and-energy-calculations-for-building-regulations (search result) | 2026-11-24 | Offshore freelancers already sell SAP reports cheaply, a ceiling on price |

Pain signals so far: (1) per-plot prices low enough that input time decides profit (inferred, not measured); (2) accreditation body flags input accuracy; (3) Fiverr undercutting. None is a direct independent complaint from assessors about drawing-to-input time. That is the first thing to find.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Accredited SAP software (Elmhurst, Stroma and others) | licence prices not checked | Manual input from drawings; no AI import found on Stroma's page. Elmhurst release notes NOT checked |
| Offshore freelancers (Fiverr) | gig prices not recorded | Not a subscription tool; assessor still carries liability |
| General CAD or BIM-to-energy tools (Cambridge research highlight, not a product) | n/a | Research only |
| A free chatbot given the PDF | free | Cannot be trusted with geometry; still a substitute for the notes and spec-reading part |

## Why AI is essential (and the moat)
Extracting geometry and build-up text from varied architects' PDFs is a vision and layout task, with a traced source for each input so the accredited assessor signs off. The moat is thin: liability stays with the assessor (a plus: the tool never certifies), and the accredited software vendors could add import. Accreditation rules around who "calculates" the SAP could also limit what a pre-fill may do.

## Rough build plan and Azure cost
- Synthetic demo from public planning-portal drawings (householder and small-scheme PDFs are public) with a self-made answer key.
- Pipeline: PDF page classification, dimension and area extraction, U-value build-up parsing, input sheet export (CSV or the software's import format if one exists; unknown).
- Azure: Document Intelligence plus a vision model; estimate under £50 a month at demo scale (to be costed by the architect).

## Risks, and what would prove this wrong
- Pay: the only per-plot prices are from a low-trust page and 2017 forum posts. At about £75 to £100 a plot an assessor may not pay £100+ a month. Needs two named bureau price pages.
- Accredited software vendors may already ship or plan drawing import (check Elmhurst and Stroma release notes and help pages).
- HEM replaces SAP and changes inputs; a tool built now could be obsolete in 12 to 24 months.
- Drawings vary; extraction accuracy on messy architects' PDFs may not reach "faster than keying".
- Kill test (cheap): extraction benchmark on 10 public planning PDFs for floor area and window area against hand measurement; plus a search of Elmhurst/Stroma help pages for "import", "DXF", "AI".

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |

## Gate log
- 2026-11-24 T-50 round 13 scout: written at G0. Kill test passed only partially: no AI drawing-to-SAP tool found in two searches, but vendor release notes were not checked and the Pay evidence is weak.
