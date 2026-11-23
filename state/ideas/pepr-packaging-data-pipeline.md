# Packaging EPR data pipeline for mid-size UK producers

- slug: pepr-packaging-data-pipeline
- stage: G0
- market and segment: UK brands, manufacturers and importers that are "obligated" under packaging EPR (pEPR), mainly large producers (turnover over £2m and over 50 tonnes) and upper-band small producers. Typically 20 to 250 staff, hundreds to thousands of SKUs, no sustainability team.
- one-line pitch: Turns a producer's SKU, bill-of-materials and supplier spec exports into a validated Report Packaging Data (RPD) upload and a fee forecast, and flags errors before the producer pays a resubmission fee.
- forcing function: Packaging EPR is live. Large producers file H2 2026 data (1 July to 31 December) by **1 April 2027**, and small producers file full-year 2026 data by **1 April 2027**. H1 data is due 1 October each year. Source: https://www.gov.uk/guidance/packaging-data-check-reporting-periods-and-submission-deadlines (accessed 2026-11-23). Changing data after submission can cost a resubmission fee of £807 (direct) or £512 (through a compliance scheme). Source: same page. Regulator: PackUK and the four UK environment agencies. Legislation: The Producer Responsibility Obligations (Packaging and Packaging Waste) Regulations 2024, https://legislation.gov.uk/uksi/2024/1332/schedules/made (appeared in search results 2026-11-23; schedule text not read).

## Problem and who has it

Every obligated producer must report packaging by activity, class, material and weight in kg, plus nation of sale, on a fixed cycle. The data sits in ERPs, Shopify exports, supplier spec sheets in PDF and spreadsheets in mixed units. Large producers also pay per-tonne disposal fees, and data accuracy drives the fee. The producer stays legally responsible even when a scheme or consultant files for them.

Small producers have to report: packaging activities, class (single sales unit or grouping), material and weight in kg per material, and a few special cases (bags in England, drinks containers coded SP and HDC). Source: https://www.gov.uk/guidance/epr-for-packaging-what-you-must-do-as-a-small-producer (2026-11-23).

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.gov.uk/guidance/packaging-data-check-reporting-periods-and-submission-deadlines | 2026-11-23 | Deadlines (1 Oct, 1 Apr), resubmission fee £807 or £512, 2025 resubmission deadline was 1 Sep 2026. Pain signal 1: a regulator-set cost for getting the data wrong first time. |
| https://www.gov.uk/guidance/epr-for-packaging-what-you-must-do-as-a-small-producer | 2026-11-23 | Data fields required; 2027 registration fee £1,303 direct or £696 via a scheme; late registration fee £386; scheme fees extra. Gov.uk also tells producers they may use a scheme, a consultant, or do it themselves. |
| https://erp-recycling.org/uk/news-and-events/2026/08/poor-packaging-data-could-be-increasing-your-epr-costs/ | 2026-11-23 | Compliance scheme's own article titled "Poor Packaging Data Could Be Increasing Your EPR Costs". Only the title was retrievable; the body was not read. Pain signal 2 (unverified detail). Validator to read it in full. |
| https://www.gov.uk/government/news/new-resubmission-deadline-for-2025-packaging-data | 2026-11-23 | Appeared in search results: PackUK set a 1 September 2026 resubmission deadline for 2025 data from producers who pay pEPR fees. Pain signal 3: the regulator is pushing producers to correct data. Page itself not opened. |
| https://www.valpak.co.uk/knowledge-hub-post/packaging-extended-producer-responsibility-epr-frequently-asked-questions | 2026-11-23 | Valpak (a scheme) offers a data collection service "where data is not sufficient". Shows producers are paying for data collection. No price on the page. |
| Job-ad signal | not collected | TODO for validator: search job boards for "packaging compliance" or "EPR data analyst" roles. Not done in this round. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Compliance schemes (Valpak, ERP, Ecosurety) with data services | Not published. Small-producer registration via a scheme is £696 to the regulator, scheme fee on top (https://www.gov.uk/guidance/epr-for-packaging-what-you-must-do-as-a-small-producer, 2026-11-23). | Service-led and priced by quote. Schemes sell fee-bearing compliance, not a self-serve data tool. |
| Valpak by Reconomy Global Data Insights Platform | Not stated (https://brc.org.uk/news-and-events/news/associate-insight/2026/valpak-by-reconomy-launches-global-epr-platform/, 2026-11-23). Centralises packaging, component and supplier data, models pEPR cost, claims 60m SKUs referenced. | The page does not say it covers UK pEPR specifically, and does not mention RPD submission. Aimed at "brands and retailers". The closest competitor. |
| PackTotal EPR | Price not published; third-party listing says "No data available" (https://netzerocompare.com/software/packtotal-epr, search summary only; page returned 403). | SKU and bill-of-materials model plus import/export for UK EPR and PPT. I could not open its own pricing page. Validator must check packtotal's own site. |
| Lappa (EU-oriented) | Published tiers in euros; extra packaging report €70 (https://lappa.org/epr-pricing/, search summary only) | Not UK-first. |
| Excel plus a consultant | Staff hours; resubmission £807 | The status quo. |

Gap that survives: unproven. On features, PackTotal and Valpak overlap. The only gaps I can name are price transparency for mid-size producers and a pre-submission validator (unit errors, missing nation split, mismatches against purchase volumes) tied to a fee forecast. An incumbent could close that quickly. Expect Competition to score low unless the validator finds a stronger angle.

## Why AI is essential (and the moat)

- Extraction and normalisation: read supplier spec sheets, pack drawings and mixed-unit spreadsheets into materials and weights per component, with a confidence score and a human review queue.
- Reconciliation: compare declared packaging weight against purchase volumes and sales volumes by SKU to catch errors that would trigger a resubmission.
- Fee modelling from the published fee tables, so the producer sees what a design change saves. Needs the Year 2 fee figures from gov.uk (I did not read them; the validator should).
- Moat is the validation rule set plus the evaluation set of messy inputs. It is not the chat layer.

Demo with public or synthetic data: build a fictional brand with about 300 SKUs, synthetic supplier spec PDFs and a messy ERP export. Use the public gov.uk reporting rules and fee tables. No real customer data is needed. Pass criterion: the pipeline produces an RPD-format CSV and a list of seeded errors found.

## Rough build plan and Azure cost

- Weeks 1 to 2: SKU and BoM schema, rules engine for RPD fields, CSV export in the RPD format (spec to be taken from gov.uk "report packaging data" guidance).
- Week 3: LLM extraction from spec sheets and a review UI.
- Week 4: reconciliation checks, fee forecast, audit trail and seven-year record retention.
- Azure: App Service or Container Apps on a scale-to-zero plan, Postgres on a burstable tier, Blob storage. Estimate under $25 a month on the default stack. Not yet written to BUDGET.md.
- The studio does not file on the producer's behalf. It produces a file for a human to upload and sign off.

## Risks, and what would prove this wrong

- Thresholds are quoted inconsistently across sources (£1m to £2m and 25 to 50 tonnes). Use gov.uk as the authority.
- Not legal advice. Output is a data file and a checklist. Producers remain responsible. Legal or compliance-consultant review needed before any wording about "compliant" appears in the product.
- Gap may not exist. If PackTotal's own site shows RPD CSV export and validation at SME prices, kill on Competition.
- Reachability: producers buy through schemes. A scheme could be the channel or the competitor. The selling channel is a UK business, so UK buyers fit.
- Small producers (the easiest to reach) pay no disposal fees, so willingness to pay may be low. Target is large and upper-band producers.
- Would prove wrong: three or more mid-size producers say a scheme's free data service is enough; or RPD changes its upload format often enough to make a file generator a maintenance burden.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 16 | 14 | 9 | 7 | 10 | 3 | 9 | 68 |

## Validator notes (2026-11-23)

**Scored as the merged idea.** I agree with the scout: ppt-recycled-content-ledger merges into this file. Both need the same per-component material weights and supplier evidence, the buyers overlap (brand owners and importers with plastic packaging), and the same incumbents (Valpak, ERP, Clarity, PackTotal) sell both. Scored alone, PPT gets 51. The merged scope is pEPR data and RAM evidence first, with a PPT recycled-content module after G4. Keeping PPT out of the first build is what makes four weeks realistic.

**Red-flag check: none.**
- Not an off-limits area. It handles packaging and supplier business data only.
- No paid service is needed: Azure OpenAI through the default deployment, with the Document Intelligence free tier as an option. No scraping is needed either. The RPD file spec, the RAM methodology and the fee tables are all published on gov.uk.
- Public and synthetic data can credibly demo the value. The demo would use a fictional brand with about 300 SKUs, synthetic supplier spec sheets in varied layouts (some missing the polymer, colour, label or closure details), the public RAM v1.1 and RAM 2027 guidance, the fee tables, and gov.uk's RPD file spec. It shows which components would default to red, what that costs, and a valid RPD file. Accuracy on real supplier documents stays unproven until a pilot.
- Legal and tax advice: this stays a data tool if built this way. The tool drafts each RAM rating with the evidence it used and the methodology version. A named person at the producer approves every rating and the final file. The producer or its scheme uploads to RPD; the tool never submits. No "compliant" wording appears without legal review. The later PPT module touches a tax return, so it shows recycled-content figures and evidence per component, never a tax liability, and a tax adviser reviews any tax figure before it appears.

**Forcing function: confirmed on gov.uk, and stronger than the file says**
- Deadlines (updated 19 Aug 2026): large producers' H2 2026 data and small producers' 2026 data are due 1 April 2027; H1 data is due 1 October every year. The resubmission fee is £807 direct or £512 through a scheme.
- Missing evidence is costly: "If you cannot provide evidence for your household packaging unit or component, it is an automatic red", and RAM records must be kept for 7 years (RAM supplementary guidance, updated 20 Apr 2026).
- The red penalty grows: the modulation factor is 1.2 in 2026-27, 1.6 in 2027-28 and 2.0 in 2028-29 (modulation statement, updated 17 Feb 2026).
- The method changes every year: RAM 2027 (published 1 July 2026) applies to packaging supplied in 2027, with H1 due 1 Oct 2027. Change requests for RAM 2028 are due by 31 Dec 2026 (search summary).
- Year 2 fees (open item). Confirmed fees were not on gov.uk: the large-producer fees page (updated 28 Oct 2026) still links only the illustrative table, and PackUK's 6 July 2026 news story says fees come "later this calendar year". The illustrative table (19 Dec 2025, "likely to change significantly") gives red / amber / green in £ per tonne:

| Material | Red | Amber | Green |
|---|---|---|---|
| Plastic | 545 | 455 | 415 |
| Fibre-based composite | 630 | 525 | 475 |
| Wood | 540 | 450 | 410 |
| Steel | 345 | 290 | 260 |
| Aluminium | 325 | 270 | 245 |
| Paper and board | 250 | 210 | 190 |
| Glass | 245 | 205 | 185 |
| Other | 270 | 225 | 205 |

- Worked example (my estimate from the illustrative fees): 200 tonnes of household plastic reported red instead of amber costs about £18,000 more in 2026-27 (200 × £90). At factor 1.6, with the base near £455, the gap is about £273 a tonne, or about £55,000 a year.

**Pain signals checked**
- The PackUK annual report 2025-26 (updated 30 Sep 2026) says many producers resubmitted data after the first Notices of Liability (£1.46bn). That cut obligated tonnage and forced a recalculation in March 2026, to £1.411bn. So the data was wrong at scale in year one.
- When PackUK set the illustrative Year 2 fees, RAM data covered only 45% of submitted H1 2025 tonnage (illustrative fees page).
- ERP's article "Poor Packaging Data Could Be Increasing Your EPR Costs" (18 Aug 2026) is the scout's open item. Its body would not load. The search excerpt says missing or incomplete RAM data gets a red rating, and the green-to-red gap is material for producers with large plastic or fibre-composite volumes. ERP's July piece, "Packaging EPR Data Mistakes Costing Producers Thousands", also would not load. Both are vendor sources.
- Valpak (10 June 2026, fetched) lists misclassified RAM scores, packaging-class errors, double reporting, and weight and RAM gaps as causes of overpayment. Also a vendor source.
- Job ads (open item):
  - Valpak EPR Data Consultant, £27,000 to £29,500 (fetched): collating weights, checking customer data, supporting suppliers.
  - Ecosurety Data Specialist, £30k to £34k, and Senior, £42k to £45k (search summary via itjobswatch).
  - Kite and Beyondly packaging-compliance data analyst posts were seen in search only; Kite's page shows no live ad and Beyondly's returns 404.
  - Almost every ad is on the scheme side. The work is done by hand, but mostly by the schemes, who are the competitors.
- Not found: complaints or reviews written by producers themselves.

**Competitors (own pages where reachable)**
- **Clarity RAM Assess** is the strongest competitor and the best price anchor (own guide, Aug 2026, PDF read).
  - Price: "From £4,995 per annum", ex VAT.
  - Features: bulk component RAG ratings, "identification of incomplete or missing data" to avoid default red, analysis by SKU, component or material, fee impact modelling, documented methodology, RAM-rated data for EPR reporting, multiple users and expert support.
  - Input is a RAM data template that the producer fills in by hand and uploads. Step 5 of the guide submits through the Clarity dashboard, so it looks built for Clarity's scheme members (not confirmed).
- **Valpak** (own page, 10 June 2026): Data Management services cover weight gaps and RAM gaps, chase suppliers for missing data, run weighing exercises, and enrich data from "65+ million SKU records". Its Global Data Insights Platform (BRC release, 7 May 2026) is multi-country and does not mention UK RAM or RPD. No prices.
- **ERP UK**: a LAMB Data Service with a RAM Checking Tool, plus a fully outsourced option (search summary; ERP's pages would not load).
- **OPRL**: its Recyclability Assessment Tool is for members only. It is aligned to RAM v1.1, with a RAM 2027 update promised (OPRL help centre and blog, search summary).
- **PackTotal** (open item): still unverified. The site returned 503 on both www and the bare domain, and Net Zero Compare returned 403. Verdantix (6 Nov 2025, fetched) says it "automates EPR data categorization, calculations and reporting for UK and EU EPR".
- **Free substitute:** gov.uk's packaging data file generator (Excel, v5.2, 19 Aug 2026) "contains built-in validation rules", produces a pre-validated RPD CSV, and can check a file built elsewhere. The RPD file is a simple 15-column CSV. So the scout's "validated RPD upload" is not a selling point. The value is upstream, in getting correct component weights and RAM evidence.
- **Cheapest substitute overall:** the scheme's own data service, which comes with membership, plus Excel and the free file generator.
- **Why buyers won't switch:** large producers sit inside a scheme relationship, and the scheme's tool feeds the scheme's own submission flow. A neutral tool adds a vendor and a data handoff.
- **What an incumbent could add in a month:** Clarity or Valpak could add LLM reading of supplier spec sheets into their templates.
- The gap that survives is turning supplier specs, pack drawings and ERP exports into component data with an evidence vault, independent of any scheme. It is real on the pages I could read, but not confirmed and easy to copy.

**Market and reach**
- About 5,250 producers are registered with the Environment Agency in England (data.gov.uk dataset updated 6 July 2026, search summary; no large/small split).
- The public register on Report Packaging Data lists producers with size and Companies House number (search summary). That is a good company-level lead source with no personal data.
- The PPT module would add overlap with 5,142 PPT registrants (HMRC statistics, fetched).

**Scoring rationale**
- **Pain 16.** Official sources show wrong or missing data costs money, twice a year. The red penalty rises to 2.0 by 2028-29 and the method changes every year. Not higher, because almost all job-ad and complaint evidence comes from schemes, not producers.
- **Pay 14.** Clarity's £4,995 a year is a published software price, EPR data roles pay £27k to £45k, and regulator fees are at stake. There is no second published software price; PackTotal, Valpak and ERP all quote.
- **AI 9.** Reading varied supplier spec sheets and pack drawings into components and RAM attributes is where AI is essential. The RAM rules themselves are deterministic, and Valpak's 65 million SKU records are a data advantage the studio can't match.
- **Reach 7.** The public producer register has size flags, and there are trade bodies. But most large producers deal through a scheme, which is both channel and competitor.
- **Build 10.** It fits four weeks only if RAM rules cover a subset of materials first (plastics, paper and board, glass, metals) and PPT waits until after G4. Two RAM versions add work (v1.1 for 2026 data, RAM 2027 for 2027 data). The extraction benchmark can't run until T-1 (Azure OpenAI) is unblocked.
- **Competition 3.** Clarity sells the core rating and fee software, schemes sell the data work, and gov.uk gives the file tool away.
- **Risk 9.** Business data only, with human approval of every rating.

**What would change my mind (re-score on this evidence)**
1. **The upstream gap confirmed.** Check Clarity RAM Assess, ERP's RAM Checking Tool, OPRL's RAT and PackTotal on their own pages, help docs or public demo videos. Find out whether each needs hand-filled templates or reads supplier documents, and whether a producer outside the scheme can buy it. If none extracts from documents and at least two are members-only, Competition rises to 5.
2. **A segment the schemes don't serve, sized from public registers.** Candidates are producers registered directly with the regulator (not through a scheme), or smaller compliance schemes without their own RAM tool that might license one; gov.uk keeps a register of schemes. This would lift Reach and Competition.
3. **Official data on red or unevidenced tonnage** in 2025 and 2026 submissions (PackUK publications or Notice of Liability commentary). A large defaulted share lifts Pain to 17 or 18.
4. **Producer-side evidence of the manual work**: brand owners or manufacturers (not schemes) advertising packaging data or EPR roles, or producer complaints in the trade press.
5. **A desk benchmark once T-1 is unblocked.** Run 30 synthetic supplier spec sheets in varied layouts, extracting the RAM fields (polymer, colour, component weights, labels, closures, inks, coatings). It needs at least 90% field accuracy at a cost per page that fits the Azure budget. That lifts AI to 10 and Build to 11.

With items 1, 3 and 5 the score would be about 73 (17+14+10+7+11+5+9). Without item 1 it can't reach 70, because Competition stays at 3. A second G1 failure kills the idea, so re-score only after items 1 and 5 are in.

**Sources** (all accessed 2026-11-23)
- https://www.gov.uk/guidance/packaging-data-check-reporting-periods-and-submission-deadlines (fetched)
- https://www.gov.uk/government/news/new-resubmission-deadline-for-2025-packaging-data (fetched)
- https://www.gov.uk/government/publications/year-2-illustrative-waste-disposal-fees-extended-producer-responsibility-for-packaging/year-2-illustrative-waste-disposal-fees-extended-producer-responsibility-for-packaging (fetched)
- https://www.gov.uk/guidance/waste-disposal-fees-for-large-producers-under-epr-for-packaging (fetched)
- https://www.gov.uk/government/publications/extended-producer-responsibility-for-packaging-modulated-disposal-fees/packuk-extended-producer-responsibility-epr-for-packaging-producer-disposal-fees-modulation-statement (fetched)
- https://www.gov.uk/guidance/recyclability-assessment-methodology-supplementary-guidance (fetched)
- https://www.gov.uk/government/news/packuk-publishes-recyclability-assessment-methodology-ram-2027 (fetched)
- https://www.gov.uk/government/publications/packuk-annual-reports/packuk-annual-report-1-april-2025-to-31-march-2026 (fetched)
- https://gov.uk/government/publications/extended-producer-responsibility-for-packaging-generate-a-packaging-data-file and https://www.gov.uk/guidance/report-packaging-data-create-your-reporting-file (fetched)
- https://clarity.eco/wp-content/uploads/2026/08/RAM-Assess-Guide-August-2026.pdf (PDF read)
- https://www.valpak.co.uk/pepr-data-accuracy-reduce-risk-cut-costs/ and https://brc.org.uk/news-and-events/news/associate-insight/2026/valpak-by-reconomy-launches-global-epr-platform/ (fetched)
- https://www.verdantix.com/insights/blog/from-burden-to-strategy--mastering-packaging-epr-compliance (fetched)
- https://erp-recycling.org/uk/news-and-events/2026/08/poor-packaging-data-could-be-increasing-your-epr-costs/ (body not loaded; search excerpt only)
- https://www.valpak.co.uk/careers-at-valpak/epr-data-consultant-uk/ (fetched); https://www.itjobswatch.co.uk/jv/Ecosurety/Data-Specialist-Job-Bristol-UK-51okb7 (search summary)
- https://help.oprl.org.uk/en/knowledge/is-the-recyclability-assessment-tool-rat-included-as-part-of-my-membership (search summary)
- https://www.data.gov.uk/dataset/8a8af563-188a-414f-80c7-482e2f3da652/packaging-regulations-producers-registered-entities-only and https://report-packaging-data.defra.gov.uk/public-register (search summary)
- https://www.packtotal.com/ (503) and https://netzerocompare.com/software/packtotal-epr (403)

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor own-page check done for Valpak (via BRC release) only; PackTotal own page not reachable (403 on aggregator). Open items listed above.
- 2026-11-23 | validator | G0→G1 | REVISE 68 | Scored as the merged pEPR and PPT data layer: the studio's strongest official pain so far (automatic red for missing evidence, red factor rising to 2.0 by 2028-29), but Clarity already sells bulk RAM ratings, missing-data flags and fee modelling from £4,995 a year and gov.uk gives the RPD file generator away, so only an unverified upstream extraction gap is left.
