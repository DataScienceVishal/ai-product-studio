# UK export classification workbench

- slug: uk-export-classification-workbench
- stage: killed (T-42 validator, 2026-11-24, 50)
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
Validator score, 2026-11-24 (T-42):

| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 9 | 5 | 11 | 5 | 9 | 5 | 6 | 50 |

**Verdict: KILL (first attempt; ceiling below 70).**

**Falsification findings** (all accessed 2026-11-24; "fetched" means the page itself was read)
- **The pause is real, but only a law firm reports it.** Squire Patton Boggs (October 2026, fetched) quotes "Notice to Exporters 2026/22: temporary pause of the Control List Classification (CLC) service", dated 12 October 2026: ECJU "will not process new requests", "has not set a date for it to resume", promises an update before the end of 2026, and says "increasingly complex cases have made it harder to provide classification advice". I could not find NTE 2026/22 on gov.uk; the indexed notices collection stops at 2026/13 (search results). Treat it as confirmed by one reputable secondary source.
- **The pause has happened before, and no product market followed.** ECJU suspended CLC from June 2014 and reinstated it on 25 June 2018 (gov.uk "Notice to exporters 2018/15: control list classification service to return on 25 June", and IOE&IT "Control list classification service reinstated", search results). For four years exporters coped with consultants, in-house expertise and the free goods checker, and the service came back. The likeliest outcome now is the same: a December update, and either a restored or a narrowed service. Buyers have reason to wait.
- **Pain is inferred, not shown.** The named settlements (NTE 2025/05, £374,326.07; NTE 2024/28, about £1.9m, mostly military) don't say misclassification caused them (scout read). No job adverts, complaints or reviews were found for the classification task itself.
- **AI classification vendors already cover dual-use lists, some claiming the UK.**
  - Trademo sells an "AI Export Control & Dual-Use Classification Engine" over "technical specifications, and engineering attributes", with confidence scores and logged rationale, drawing on a database that includes "UK strategic controls"; aimed at compliance teams with large SKU catalogues; no price ("View Plans", "Talk to Sales") (https://www.trademo.com/ai-export-control-dual-use-classification, fetched).
  - Digicust: uploads "product descriptions, technical specifications", and the AI "analyzes ... performance parameters" for dual-use characteristics against EU, German, US and Chinese lists; the UK appears only in sanctions screening; free first-pass ECCN tool (https://digicust.com/en/solutions/ai-export-control/, fetched).
  - traide AI (EU dual-use with BAFA correlation), EC Compliance (AI mass classification, European and US rules) and Thomson Reuters ONESOURCE, which already loads ECJU changes such as the 25 June 2026 consolidated dual-use OGEL into its content (search results; ONESOURCE help page title).
  - Because the UK dual-use list is largely the EU Annex I list (both come from the Wassenaar and other regimes; the UK list marks regime-origin entries with a code letter, per the consolidated list summary), an EU classifier covers most UK dual-use entries already. Adding the UK-only national entries is weeks of work for any of these vendors.
- **Cheapest substitutes:** the free gov.uk goods checker and consolidated list; the manufacturer's own published rating (many component makers publish ECCN and EU ratings for their parts; validator's knowledge, not verified this run); an export-control consultant; an Institute of Export or trade-association helpline. No price was found for any of them.
- **Off-limits check: not legal advice as scoped, but close.** A control rating is a technical assessment that consultants and in-house engineers make, not a legal opinion. But the buyer's offence if it is wrong (unlicensed export) puts the liability on a two-person seller who can't insure it, and dual-use goods add an ethics angle. No red flag; a heavy Risk deduction.

**Scores in brief**
- Pain 9: a real loss of a free service, but a temporary one with a precedent of return, and no evidence that misclassification drives fines.
- Pay 5: no consultant or software price found; the free CLC is the anchor buyers know.
- AI 11: the strongest AI case of the round. Thresholds, notes and exclusions buried in datasheets need parameter extraction and judgment. But accuracy is unproven and there is no public labelled set of correct ratings.
- Reach 5: a small, specialist buyer base (count it from the ECJU annual report licence data); reached through the Institute of Export, ADS and techUK, which the partner may not know.
- Build 9: indexing the list is easy; proving accuracy to a Sellable bar without ground truth is not, and a wrong "not controlled" output is the worst failure the studio could ship.
- Competition 5: Trademo claims UK coverage; EU-list classifiers cover most of it; no UK SME-priced product confirmed on a vendor's own page.
- Risk 6: −3 for liability on a criminal-offence decision, −1 for dual-use ethics.

**Reason (one paragraph).** The gap rests on a free government service paused on 12 October 2026 with an update promised within weeks, and the same service came back after a four-year suspension in 2018 without a software market forming in between. AI classification engines (Trademo, which claims UK strategic controls, Digicust, traide AI, EC Compliance, ONESOURCE) already read technical specifications against dual-use lists that are largely the same as the UK's. There is no price for the job, and no evidence that classification errors cause the settlements. The product would also put a two-person seller between an exporter and a criminal offence. Best plausible re-score if ECJU doesn't restore CLC and a consultant price is found: Pain 12, Pay 9, AI 12, Reach 6, Build 10, Competition 6, Risk 6 = 61.

**Lessons**
- A "free official service just closed" gap is only worth chasing if the closure is permanent and the service's past behaviour is known. Search the service's history ("<service> suspended / reinstated") before writing the G0 file.
- In regulated lists harmonised across regimes (UK and EU dual-use, Wassenaar), check the vendors for the larger jurisdiction first; their coverage nearly always includes the smaller one.
- Ideas where a wrong output is the buyer's criminal offence carry a Risk ceiling of about 6, whatever the framing.

**What would revive it**
- ECJU's year-end update says CLC stays closed for good, plus two published prices for UK classification work (consultant day rates or per-item fees), plus a vendor-page check showing Trademo and the EU tools don't cover UK national entries. Even with all three, the ceiling is about 61.

## Gate log
- 2026-11-24 T-42 scout round 7: written as G0. The pause, the NTE 2025/05 and NTE 2023/28 pages were fetched; vendor claims are from search summaries.
- 2026-11-24 | validator | G0→G1 | KILL 50 | The gap is a free ECJU service paused on 12 Oct 2026 with an update due by year end; CLC was suspended 2014-2018 and came back with no product market in between. Trademo (claims UK strategic controls), Digicust, traide AI and EC Compliance already sell AI dual-use classification from specs; no price for the job; a wrong rating is the buyer's offence. Ceiling about 61.
