# UK export classification workbench

- slug: uk-export-classification-workbench
- stage: G0
- market and segment: UK electronics, sensors, software and advanced-manufacturing SMEs (10 to 250 staff) that export dual-use goods, software or technology and have no in-house export-control specialist
- one-line pitch: Classifies each product against the UK Strategic Export Control List from its datasheet and spec, shows which control-entry parameters were checked and which are missing, and produces a dated rating record for the export file, now that ECJU has stopped giving classification advice.

## Problem and who has it
Exporters must self-classify. Until October 2026 an SME could ask ECJU's Control List Classification (CLC) service. On 12 October 2026 ECJU paused it, with no end date and an update promised "before the end of 2026". Exporters now rely on their own expertise or paid advice. A wrong "not controlled" call means an unlicensed export, and HMRC publishes compound settlements (for example £374,326.07 for unlicensed dual-use exports, NTE 2025/05). Software and technology are controlled too, including electronic transfers.

Who pays: the operations or compliance manager at an SME exporter, today through an export-control consultant, a law firm or by guessing.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.squirepattonboggs.com/insights/publications/two-significant-updates-for-uk-exporters-pause-in-uk-classification-advice-and-wider-open-licences-for-dual-use-and-military-exports/ | 2026-11-24 | ECJU paused CLC on 12 Oct 2026, will not process new requests, no end date; reason: "increasingly complex cases"; exporters remain responsible for classifying. A single law-firm source: confirm on GOV.UK |
| https://www.gov.uk/government/publications/notice-to-exporters-202505-compound-settlement-offer-for-breaches-of-export-control/nte-202505-compound-settlement-offer-for-breaches-of-export-control | 2026-11-24 | UK company, £374,326.07 compound settlement for unlicensed dual-use exports (offer Oct 2024; published 4 Mar 2025). The notice does not say why the goods were unlicensed |
| https://www.gov.uk/government/publications/notice-to-exporters-202428compound-settlement-for-breaches-of-export-control-august-2024/266de0dc-bd25-4ecb-a976-5180143e7a75 | 2026-11-24 | Three exporters, about £1.9m in Aug and Sep 2024; mostly military goods (£1.48m and £402k), one dual-use £37,743.34. No misclassification mentioned |
| https://crowe.com/uk/insights/uk-export-controls (search result, not fetched) | 2026-11-24 | Summary reports £4.7m in settlements Jan to Sep 2024 |
| https://gov.uk/guidance/export-controls-dual-use-items-software-and-technology-goods-for-torture-and-radioactive-sources (search result) | 2026-11-24 | Controls cover software and technology and electronic transfers; list and CLC are the official routes |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| ECJU CLC service via SPIRE | Free; paused since 12 Oct 2026 | Gone for now; may return |
| Export-control consultants and law firms | No UK price found in public sources | Per-product, slow, one-off |
| Trade-compliance classification software (GingerControl ECCN Classifier, Thomson Reuters, MIC Customs Info) | Not published | US EAR (ECCN) focus; MIC covers EU dual-use list; no UK SME-priced UK-list classifier found (not verified on the vendors' own UK pages) |
| Free consolidated list and OGEL checker on GOV.UK | Free | Keyword lookup; no parameter-by-parameter reasoning |

## Competitor search done (2026-11-24)
Queries: "dual-use export control classification software SME UK strategic export controls HMRC compound settlements AI classification tool"; "export control classification software dual-use self-classification tool small exporters AI control list classification product 2026"; "export control classification consultancy cost UK SME..." No UK-list AI classifier found, no consultancy price found. Vendor pages for MIC, Descartes, Livingston, Sanction/trade-compliance suites were not read: do this before G1.

## Evidence the studio can collect itself
- UK Strategic Export Control List (OGL, https://assets.publishing.service.gov.uk/media/69415ba1f065108822537524/uk_export_control_list_2025.pdf) plus ECJU guidance; the EU dual-use annex as a cross-check.
- Public product datasheets from named manufacturers (cameras, FPGAs, lidar, encryption modules) as test inputs.
- ECJU's published notices and rating examples (if any) for ground truth. Gap: no public labelled set of "correct" ratings; the studio would build one by hand and the validator should treat accuracy as unproven.

## Demo plan on public or synthetic data
Take 30 public datasheets and write a labelled expected rating from the list text. The tool outputs, per product: the candidate control entries, each technical parameter found with page citation, missing parameters to ask the manufacturer, a confidence band and a record sheet. Report accuracy on candidate-entry recall and on correctly flagged "need more data". No paid service needed.

## Why AI is essential (and the moat)
Control entries hinge on numeric thresholds and exclusions buried in datasheets and notes; a keyword search misses them. RAG over the list plus parameter extraction with citations, and a calibrated "I cannot decide" are the product. Moat: a UK-list evaluation set and a rating-record workflow; a reseller of US-oriented tools can add the UK list, so the gap is thin; unconfirmed.

## Rough build plan and Azure cost
Index the list and notes; extractor over PDF datasheets; entry matcher with threshold checks; rating-record export. Azure about £30 to £90 a month; estimate.

## Risks, and what would prove this wrong
- Pay: no price found; the CLC was free, so buyers may wait for it to return.
- Liability: a wrong "not controlled" call is the buyer's offence; the studio must not give assurance, only evidence for the exporter's decision. Near the legal-advice line.
- Settlements named so far are mostly military goods and not linked to misclassification, so classification pain is inferred, not proven.
- Small buyer population; count exporters using ECJU annual-report licence data (https://assets.publishing.service.gov.uk/media/687910bc7ea2091686363947/UK_Strategic_Export_Controls_Annual_Report_2024.pdf) before G1.
- Wrong if ECJU restores CLC in December 2026 or a trade-compliance vendor already sells a UK-list classifier.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-24 T-42 scout round 7: written as G0. The pause, the NTE 2025/05 and NTE 2023/28 pages were fetched; vendor claims are from search summaries.
