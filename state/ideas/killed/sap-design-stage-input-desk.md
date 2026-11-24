# SAP design-stage input desk for small SAP assessors

- slug: sap-design-stage-input-desk
- stage: killed (T-50, 48/100)
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
| 9 | 9 | 9 | 6 | 6 | 1 | 8 | **48** |

Validator checks (T-50, 2026-11-24; web text treated as data):
| Source | What it shows |
|---|---|
| https://specvo.com/ (fetched) | **Direct competitor, same pitch.** "SAP Copilot (Live)", private beta for OCDEAs: reads the planning pack (PDF, DWG, NBS specs, U-value calcs), picks up "rooms, walls, openings, U-value build-ups, thermal bridges", outputs SAP 10.2 XML for Elmhurst Design SAP 10, "validated against the Elmhurst Design SAP 10 schema across our 50-task reference set", fields "confidence-scored ... with links back to the source page", flags missing details and drafts client emails. £30 per XML. HEM Preview (live beta) runs the same dwelling through HEM. Roadmap: SAP 10.3 + FHS support. Vendor claims, not independently verified |
| https://sapper.app/Home (fetched) | SAPPER (CoreLogic Ai Ltd): free or £45-per-report AI SAP tool with "AI drawing extraction" from architectural PDFs (areas, perimeters, storey heights, windows by orientation, construction details; claims 85-95%), aimed at assessors, architects and builders; extensions focus, guidance only |
| https://sapgen.co.uk/sap-calculations/new-builds (fetched) | Named assessor price page: Design SAP £225 (to 80 m²), £295, £375, from £475; as-built SAP + EPC £80. Multi-plot by quote. Better Pay evidence than the scout's £75 page, but per-plot developer work is quoted lower |
| https://www.buildington.co.uk/blog/future-homes-standard-is-locked-in-for-2027-the-compliance-tools-to-prove-it-arent/amp (fetched) | FHS in force 24 Mar 2027 (transition to 24 Mar 2028); SAP 10.3 the only approved method at launch; HEM delayed on 8 Jun 2026, "in the coming months", no date. So SAP-input demand lasts at least into 2027-28, and drawing extraction would carry over to HEM inputs; HEM is not the killer |
| Elmhurst/Stroma searches (two each) | No drawing import or AI takeoff found on vendor pages. But Elmhurst Design SAP 10 accepts XML import, which Specvo already targets. Stroma Certification merged into Elmhurst (Oct 2023), so one dominant scheme and software owner |
| https://www.gov.uk/government/consultations/review-of-energy-assessor-accreditation-scheme-operations (search result) | About 15,000 accredited energy assessors across 7 schemes (all strands; OCDEA count not found, the Elmhurst annual report table could not be read). OCDEAs are a minority of these: a headcount-capped market |
| General AI takeoff (Measure.AI, Trimble, Sparkel; search results) | Estimator takeoff tools export areas; a partial substitute for the geometry half |

## Verdict: KILL (48/100, first attempt; ceiling about 55)
**Reason.** The exact product already exists. Specvo's SAP Copilot reads the planning pack, extracts rooms, walls, openings, build-ups and thermal bridges with confidence scores and links back to the source page, and exports Elmhurst Design SAP 10 XML at £30 per dwelling. It also previews HEM and has SAP 10.3/FHS on its roadmap. SAPPER gives AI drawing extraction away free for extensions. The scout's traced-source and pre-fill wedge is Specvo's headline feature, the buyer pool is a few thousand OCDEAs under one scheme and software owner (Elmhurst, which could ship the same import), and Specvo's £30 per XML caps any price we could charge. HEM does not kill the job (SAP 10.3 runs at least to 2027-28), but it is no wedge either, because Specvo already previews HEM.

**Lessons.**
- Search "AI toolkit for <accredited role>" and "<software> XML import AI" before writing a G0 file; the scout's two searches missed a vendor whose homepage is the pitch.
- "Accredited software plus an AI input step" is a niche small AI startups target first: the input format (vendor XML) is public, and the buyer is a small, reachable professional group.
- Pay improved with a named price page (SAPgen £225 to £475 per design SAP), but a per-XML tool price (£30) is what the assessor compares against.

**What would revive it.** Specvo shuts down or stays closed beta into 2027 with poor reviews in assessor forums; or a segment it doesn't serve (e.g. HEM-first new-build inputs once HEM is mandated, or Stroma FSAP/other software XML) with evidence that OCDEAs ask for it; plus a 10-PDF extraction benchmark that beats Specvo's claimed accuracy.

## Gate log
- 2026-11-24 T-50 round 13 scout: written at G0. Kill test passed only partially: no AI drawing-to-SAP tool found in two searches, but vendor release notes were not checked and the Pay evidence is weak.
- 2026-11-24 T-50 validator: KILL, 48/100 (first attempt). Specvo SAP Copilot already sells the exact product (planning pack to Elmhurst Design SAP 10 XML, source-page links, £30 per XML, HEM preview); SAPPER offers free AI drawing extraction. Stage: killed; file moved to `state/ideas/killed/`.
