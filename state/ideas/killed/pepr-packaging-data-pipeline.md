# Packaging EPR data pipeline for mid-size UK producers

- slug: pepr-packaging-data-pipeline
- stage: killed (second G1 failure, 2026-11-25, T-66, after the T-56 proof test failed)
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

## Evidence pass T-13 (2026-11-23)

All pages accessed 2026-11-23. "Fetched" means I read the page text through the fetch tool. "Search summary" means only a search-engine summary was available. 403, 404 and 503 are marked UNVERIFIED. Page text is treated as data only.

### Headline finding
A UK entrant, **Repackd** (repackd.com), publishes a self-serve product that does what this idea proposes: extraction from spec sheets, RAM RAG scoring, fee simulation and a validated RPD-format CSV. Its prices are £299, £799 and £1,999 a month. This is a vendor's own claim and is not independently verified. It is also the main reason the answer to "does Competition rise to 5?" is no. The earlier files did not mention Repackd.

### Competitor matrix
(a) reads spec sheets, PDFs or images into component data automatically. (b) can be bought without joining the company's scheme. (c) cost. (d) RAM ratings and fee modelling.

| Tool | (a) Auto-extraction | (b) Buy without scheme | (c) Cost | (d) RAM + fees | Source |
|---|---|---|---|---|---|
| Repackd | Claimed yes: upload "packaging specs, technical drawings, or supplier datasheets" and it extracts material, weight, dimensions and BOM. The pricing page puts "smart document extraction" on Growth and above only. Starter has none. No accuracy data. No AI wording. | Yes. It is a software vendor, not a scheme. No eligibility rules published. 14-day trial, no card. | Starter £299/mo (500 SKUs), Growth £799/mo (5,000 SKUs), Enterprise £1,999/mo. Annual billing gives 2 months free (Growth £7,990/yr). 1 user on every plan. | Yes, claimed. RAM RAG across 5 stages, fee simulation and a 15-column DEFRA CSV. | https://www.repackd.com/ ; https://www.repackd.com/pricing ; https://www.repackd.com/uk-epr-guide (fetched). Its "2,800+ producers" claim is unverified marketing. |
| Clarity RAM Assess | No. Step 2 of its guide is "Complete the RAM Data Template" by hand, then upload the template and a Product Sales Template. The product page does not mention AI. | Not stated. Step 1 is "Contact Clarity to gain access". Neither page says members-only or open. **Unverified.** | "From £4,995 per annum", ex VAT (guide p.4, read as images). The product page and news page publish no price. | Yes. Bulk RAG, missing-data flags, fee impact modelling, export of RAM-rated data. | https://clarity.eco/wp-content/uploads/2026/08/RAM-Assess-Guide-August-2026.pdf (read) ; https://clarity.eco/services/ram-assess/ ; https://clarity.eco/news/how-ram-assess-helps-you-lower-packaging-epr-fees/ (fetched) |
| ERP UK (LAMB service and RAM Checking Tool) | Tool: user runs assessments on data they already hold, so no extraction. Extraction is by people, through the "Full RAM Data Service", where ERP gathers supplier information and checks the evidence. | Not stated. The tool is "subscription-based" (LAMB). Whether non-members can subscribe is **unverified**. | Not published. | Tool runs RAM assessments. Fee modelling not confirmed. | https://erp-recycling.org/uk/news-and-events/2026/10/ram-assessment-what-to-ask-your-packaging-suppliers/ (body did not load; search summary only). /uk/services/ram-data-service/ returned 404. |
| OPRL Recyclability Assessment Tool | Not stated. It takes packaging type, materials, size, weight, coatings and laminations. | **No.** "Exclusive to OPRL members". | Not published. | Being aligned to RAM; the page does not say it outputs RAG. No fee modelling described. | https://oprl.org.uk/blog/pepr-recyclability-assessment-methodology-impact-on-your-business-and-how-oprl-can-help/ (fetched) |
| PackTotal EPR | **UNVERIFIED.** packtotal.com returned 503 again. No source mentions AI extraction. | UNVERIFIED. It is a software vendor. | UNVERIFIED. No price found. | UNVERIFIED. A third-party directory (search summary) lists import/export and cost-driver analytics but lists fee calculation as missing. Treat with caution. | https://www.packtotal.com/ (503) ; https://netzerocompare.com/software/packtotal-epr (search summary) |
| Valpak RAM Data Service and Supplier Data Hub | No by software. Valpak staff collect supplier data and use "tested RAM automation processes" to score components. No AI wording. | Probably yes. The page says Valpak can onboard clients who do not use the Supplier Data Hub. It does not mention scheme membership. | Not published. Enquiry or brochure. | Yes, RAG with rationale reports. The Global Data Insights Platform (BRC release) models pEPR cost but does not mention UK RAM or RPD. | https://www.valpak.co.uk/insights/ram-data-service-suppliers/ (fetched) ; BRC release as cited above |
| Ecosurety | No. Its data service ingests supplier uploads, raw files and syncs and runs 220+ automated checks. No spec-sheet extraction, AI or RAM tool is mentioned. | Not stated. | Not published. | RAM tool not mentioned. | https://www.ecosurety.com/ (fetched) |
| Comply Direct | UNVERIFIED. Site returned 503. | UNVERIFIED | UNVERIFIED | UNVERIFIED | https://www.comply-direct.com/ (503) |
| Kite Packaging, Smurfit Westrock | UNVERIFIED. Not reached this pass. Kite showed no relevant tool in the earlier validator pass. | n/a | n/a | n/a | not checked |
| Shopify EPR apps (for example PackPilot EPR) | No UK pEPR coverage. The app lists German, French, Italian, Spanish and Austrian schemes. Not a competitor. | n/a | Free listing | No RAM or RPD | https://apps.shopify.com/packpilot-epr (fetched) |

### What the matrix says about validator item 1
Validator's test: "If none extracts from documents and at least two are members-only, Competition rises to 5."
- The first condition fails, on the vendor's own claim. Repackd says it extracts from documents. The incumbents (Clarity, ERP, Valpak, Ecosurety) do not, or use people.
- The second condition is not met on evidence. Only OPRL is confirmed members-only. Clarity and ERP are unverified either way.
- Clarity's input is a hand-filled template, which confirms the validator's reading. But a cheaper rival now sells the upstream step Clarity leaves manual.

### Size evidence (direct registrants)
- **No public count of large producers registered directly under pEPR was found.** The public register shows large or small and the Companies House number, but no direct or scheme field (https://gov.uk/guidance/find-large-producers-on-the-report-packaging-data-service, fetched). The data.gov.uk dataset covers about 5,250 producers registered with the Environment Agency, last updated 18 Sep 2026. It also does not show the route, and it is licensed for internal use for one year (https://www.data.gov.uk/dataset/8a8af563-188a-414f-80c7-482e2f3da652/packaging-regulations-producers-registered-entities-only, fetched). That 5,250 may include legacy-regime registrants.
- The only direct-registrant figure found is **344 UK direct registrants** under the older recycling-obligation regime in the Environment Agency's 2025 compliance report (330 met their obligations). It is not a pEPR large-producer count and it is old-regime data. Page: https://www.gov.uk/government/publications/packaging-producer-responsibility-monitoring-plan-2025/compliance-monitoring-and-enforcement-activity-2025 (fetched). I treat 344 only as a rough upper-order marker for the direct segment. It is not a market size.
- Direct registration is a legal option for large producers (registration fee £2,842 direct against £1,803 via a scheme, and resubmission £807 against £512; search summary of gov.uk guidance https://www.gov.uk/guidance/how-to-register-for-epr-for-packaging-as-a-large-producer--2 and the deadlines page already cited). Direct registrants pay about £1,039 more to register. Even so, some will keep their data in-house, so they are the likeliest buyers of a data tool.
- The PackUK annual report 2025-26 gives no producer totals, no direct or scheme split and no resubmission count. It says only "large numbers" resubmitted and that about 11% of obligated producers were affected by a direct-debit incident (fetched). The PackUK operational plan 2026-27 gives no producer counts either (fetched). **No figure exists in the sources I could read for how many producers resubmitted or paid resubmission fees.**
- The segment can be counted only by working through the register by hand, or by asking the Environment Agency (not allowed here). Until then the segment is unsized.
- The two compliance-scheme registers (2025 and 2026 Excel files) are linked on https://www.gov.uk/government/publications/extended-producer-responsibility-for-packaging-register-of-packaging-compliance-schemes . I did not open them. Counting smaller schemes without a RAM tool is still open.

### Risks (things that make it worse)
1. **Repackd** sells the same workflow at £299 to £799 a month, which is below Clarity's £4,995 a year only at Starter. At Growth it is about £9,600 a year, or £7,990 on annual billing. Extraction is paywalled to Growth. The claim "no UK AI-native entrant" no longer holds.
2. **No regulator tool is announced.** The PackUK operational plan 2026-27 mentions no supplier-data or RAM tool, and says future digital work is "constrained by funding". The gov.uk file generator remains the only free tool (fetched).
3. **No scheme was found bundling free AI extraction.** Valpak uses staff plus automation, ERP offers a managed service, and Clarity needs hand-filled templates. Clarity could add document reading quickly, as the validator said.
4. Several competitors' own pages could not be read (PackTotal, Comply Direct, ERP body). A claim that none of them extracts is unproven for those.
5. The direct segment is small and unsized, and it carries buyers who chose not to use a scheme, so they are likely to be price-sensitive.

### Bottom line
The evidence does **not** support moving Competition from 3 to 5. The upstream-extraction gap that the validator named is claimed as already filled by Repackd, a UK self-serve vendor with a free trial and published prices from £299 a month. The members-only part is only partly true (OPRL yes, Clarity and ERP unverified). The direct-registrant segment cannot be sized from public sources and the only figure (344, old regime) is small. With nothing to lift Competition, the idea cannot reach 70 even if the T-14 benchmark gives AI 10 and Build 11 (about 68 to 70 at best, and Competition might drop to 2). I recommend **parking the idea**, not spending the second G1 attempt now. Revive it only if (1) a hands-on check of Repackd's extraction shows it is weak on messy spec sheets, which would need a trial sign-up that Vishal must approve first, and (2) PackTotal, Comply Direct and Clarity's access terms are read on their own pages. Running T-14 alone would only prove a capability that a rival already sells, and a second G1 failure kills the idea.

## Proof test (T-56): kill test, written before any run

Written 2026-11-24, before any extractor exists and before any run. Per `playbooks/pipeline.md` (Proof-test route). Public or synthetic data only.

**Question.** Can AI read messy supplier packaging spec sheets into UK pEPR RAM fields accurately enough, with every value traceable, that a producer could trust it without re-keying?

**Fields extracted, per packaging component**
1. component name (for example "bottle", "cap", "label", "outer carton")
2. material and polymer (for example PET, HDPE, PP, kraft paper, glass, aluminium)
3. colour (including clear, natural, black, carbon-black flag where stated)
4. weight in grams (units normalised to g)
5. recyclability-relevant features: labels (type, material, coverage), closures (material, liner), inks and coatings, sleeves, adhesives, barrier layers
6. RAM material category (plastic, paper and board, glass, aluminium, steel, wood, other), taken from the material, not guessed

**Metric.** Field-level match against a hand-written ground truth (`products/pepr-packaging-data-pipeline/benchmark/truth/*.json`). A field scores 1 if it is an exact match or matches after documented normalisation (case, whitespace, synonyms such as "polyethylene terephthalate" = PET, unit conversion to g within 1% or 0.1 g, whichever is larger). Components are matched to truth by name and material before fields are scored; an extracted component with no truth match counts as one wrong field per field, a missed truth component counts as missed. Every extracted value must carry a page reference (page number plus a short source quote) that the scorer checks actually contains the value. Fields absent from the sheet are labelled `missing` in truth; the extractor must return `missing`, not a guess.

**Dataset**
- 30 synthetic spec sheets, generated by a script with a fixed seed, with hand-written truth files. Layouts: tables, prose paragraphs, scanned-look (rasterised, noise, skew), mixed units (g, kg, oz, mg), multi-component packs, missing fields, contradictory values (for example a table says 24 g and the notes say 26 g; truth records the rule for the expected answer, normally "flag as conflict, report both").
- Messiness tiers: 10 clean, 10 moderate, 10 messy. "Messiest third" means the 10 messy sheets.
- Plus any genuinely public supplier spec PDFs found that licence permits using; these are reported separately, hand-labelled, and do not change the pass mark.

**Pass mark (all must hold)**
1. Overall field accuracy >= 90% across all 30 sheets.
2. Field accuracy >= 80% on the 10 messy sheets.
3. 0 untraced values: every non-missing value has a page reference whose quote contains it.
4. Missing-field handling: >= 95% of truth-`missing` fields returned as missing; any fabricated value for a missing field is counted wrong and reported separately. Contradictory values must be flagged as conflicts, not silently chosen, in at least 80% of conflict cases.
5. Cost: at most GBP 0.25 per sheet in Azure OpenAI tokens (about GBP 7.50 for the full set).

**Time box and budget.** Slice 1 (this section and benchmark plan): 15 minutes. Slices 2 to 4 together: at most 3 runs of about 45 minutes. Azure OpenAI token cap for the whole proof test, including prompt iteration: 3 million tokens, with a hard budget guard in the extractor that stops the run at the cap. Prompt tuning is allowed only on 5 held-out tuning sheets generated with a different seed; the 30 test sheets are run once for the score, and a rerun after tuning on them does not count.

**What pass and fail mean**
- **Pass:** the validator re-scores the idea with the result as evidence. Expected effect is AI 9 to 10 and Build 10 to 11, but the 70 bar is unchanged and Competition stays as the validator scores it, given Repackd (see Evidence pass T-13). A pass proves capability, not market room.
- **Fail:** counts as a failed G1 attempt (the idea has already had one REVISE at 68, so a fail kills it under the two-attempt rule). Lessons and what would revive it go in this file, then it moves to `state/ideas/killed/`.
- No pass mark is changed after seeing results. Any change needs a new dated entry here before the next run.

### Amendment, 2026-11-24 (before any run)

Made before any extractor exists and before any run. Pass marks are unchanged.

1. **Ground truth.** Truth is written by the generator from the same data model that renders each sheet, not by hand. It lives at `benchmark/data/truth/` (tuning sheets: `benchmark/data/tuning_truth/`). It was spot-checked by hand against the PDFs. Every present value carries a page and a quote that is tested to appear on that page.
2. **Scoring rules (fixed before any run).**
   - (a) A conflict weight scores 1 only if the extractor flags a conflict and reports both truth values, each within tolerance (1% or 0.1 g, whichever is larger). A silent pick scores 0.
   - (b) The value-in-quote check parses number and unit from the quote (g, kg, mg, oz), converts to grams and applies the same tolerance. Strings must match after case and whitespace normalisation and listed synonyms. Feature quotes must be the canonical value or a listed paraphrase.
   - (c) Image-only (scanned) sheets are checked against the page text the generator rendered onto the raster, stored in `benchmark/data/manifest.json`. Whitespace and case normalised substring match. No OCR in scoring.
   - (d) Components are matched by normalised name first (listed name variants), with material as a tie-break only when the truth material is present. One-to-one, greedy.
3. **Missing features.** Every feature key that is plausible for a component type (map in `benchmark/taxonomy.py`) is labelled in truth as present or `missing`. The extractor must return all plausible keys for every component, using `missing` when the sheet does not state one. Only plausible keys are scored. Features are returned as one value from a closed vocabulary; sheets use paraphrases.
4. **Budget counting.** The 3M token cap counts input + output + reasoning + image tokens, tuning included. Model: Azure OpenAI deployment `gpt-5.4-pro`. Price basis: USD 15 per 1M input and USD 120 per 1M output (incl. reasoning), from `state/BUDGET.md`; GBP at 0.79 per USD. The GBP 0.25 per sheet check is computed on that basis. Added hard cap: USD 12 of model spend for the whole proof test (tuning + test run), enforced by the extractor guard; it stops at whichever cap comes first.
   - *Correction 2026-11-24 (run 591a, T-58; original text above unchanged):* the real gpt-5.4-pro price is USD 30 per 1M input and USD 180 per 1M output (OpenAI model page; Microsoft Foundry launch post). The guard and cost check now use 30/180; the GBP 0.25 per sheet mark and the USD 12 cap stand, read as real money. Tuning cost USD 3.09 at the real price (mean USD 0.62 a sheet, about twice the mark). See Q-12 for how the test will run.
5. **Conflict count.** The test set has 22 conflict cases (7 in the moderate tier, 15 in the messy tier). The 80% conflict bar therefore needs at least 18 of 22. The test set has 68 components and 457 scored slots (307 present, 128 missing, 22 conflict; ram_category counted only where material is present; corrected by amendment 2).
6. **Tuning set.** The 5 tuning sheets (different seed) cover one clean sheet, one multi-component sheet with missing fields, one mixed-units sheet, one scanned sheet with a conflict and one contradictory sheet.
7. **Public PDFs (realism check).** Slice 4 must search for genuinely public supplier spec PDFs whose licence permits use and report the extractor's result on them separately (hand-labelled), or state that none were found and where it looked. They do not change the pass mark.
8. **Wording fix.** "Hand-written ground truth (`benchmark/truth/*.json`)" in the Metric and Dataset paragraphs above is superseded by item 1.

### Amendment 2, 2026-11-24 (before any model call, including tuning)

Made before any extractor exists and before any run. Pass marks are unchanged. Answers the re-review (`reviews/T-56-slice2-rereview.md`, items 1, 2, 6, 7, 9). The full rules are in `benchmark/README.md` and `benchmark/taxonomy.py`.

1. **Closed vocabularies for material and colour.** Material and colour are scored like features. The extractor is given the closed canonical lists (`MATERIAL_VOCAB`, `COLOUR_VOCAB` in `taxonomy.py`) and returns one canonical value. A value scores 1 only by exact match, after case and whitespace normalisation, to the truth canonical value or a listed wording of it (for example "BOPP", "PP film" and "polypropylene film" all mean PP; "jet black" means black). No containment matching: "PETG" is not PET, and `black` for truth `black (carbon black)` is wrong (a missed carbon-black flag).
2. **Quote rule.** After normalisation (case, whitespace, and the `|` cell separator treated as whitespace, on both sides) the quote must appear in the stated page's text, and it must name exactly the extracted value: it contains the canonical value or one listed wording of that value (longest match wins) and no wording of another canonical value for the same key. Whole-row or whole-sentence quotes are allowed. For weights, the quote holds a number and unit (g, kg, mg, oz) that converts to grams within tolerance (1% or 0.1 g, whichever is larger) of the value. Implemented as `taxonomy.quote_ok()`.
3. **Page text.** Text sheets: pypdf `extract_text()`. Image-only sheets: the page text recorded by the generator in `manifest.json`. Both go through the same normalisation. No OCR.
4. **ram_category.** Scored only when the truth material is present, so a missing material costs one slot. Test set slots: 457 (307 present, 128 missing, 22 conflict).
5. **Features are one canonical value each.** Label type, material and coverage, and closure material and liner, are collapsed into one value per feature key. Label coverage is not modelled, so a pass says nothing about coverage.
6. **False conflict.** Flagging a conflict on a weight whose truth is present scores 0.

### Amendment 3, 2026-11-24 (before any model call, including tuning)

Made before any run. Pass marks, the 30 test sheets, the 5 tuning sheets and their truth are unchanged (regenerated data is byte-identical; reviews/T-56-realism.md).

1. **Gram spellings.** The weight unit rule in Amendment 1 (2b) and Amendment 2 (2) reads "(g, kg, mg, oz, and the gram spellings gm, gms, gram, grams)". Reason: real supplier sheets write "37.00gm" (benchmark/REALISM.md). No current sheet uses these spellings, so no score on the existing sets can change.
2. **Realism supplement.** benchmark/REALISM.md (13 public sheets, verdict MIXED) found the synthetic set easier than real sheets on layout and wording. A separate realism supplement set (about 10 sheets, new seed) may be added and is reported separately. It never changes the pass marks or the result on the 30 test sheets.

### Amendment 4, 2026-11-24 (before any model run, including tuning)

Studio Lead decisions D1 to D4, made before any model call. Pass marks, the 30 test sheets, the 5 tuning sheets, their seeds and truth are unchanged (the committed data is byte-identical; the reproducibility test passes).

1. **D1 Blends.** A material cell naming a blend of PET and rPET with shares (for example "rPET 30% + PET 70%") has truth = the canonical material with the largest stated share; a tie goes to "PET". Scorer: `quote_ok` for key `material` accepts a quote naming several canonical materials only if it names exactly PET and rPET, every one carries a percentage, the shares are all read in one direction (share before every name, or after every name; "70% rPET - 30% PET" is rPET), the shares sum to 100 +-1, and the value is the unique largest (tie goes to PET). "rPET + PET" without shares, joined cells ("PET 100% | PP 100%"), three-material quotes and mixed directions are rejected. Mixed-family blends are not generated. Recycled content on one material ("rPET (PCR 100%)", "minimum of 25% PCR kraft paper") is not a blend.
2. **D2 Unit in the label.** `quote_ok` for `weight_g`: a quote that is exactly one row, a label containing weight/wt/mass with a unit in parentheses "(g)", "(gm)", "(gms)", "(grams)", "(kg)" or "(oz)", then a bare number that ends the quote (an optional "+-" or "+/-" tolerance after it is allowed), is accepted; the number is converted with that unit. "Weight 25.5", "Weight (g) 25.5 mm", "Weight (g) 25.5 x 30", "Gauge (g) 25" and "Height (mm) 120 Weight (g) 25.5" are rejected. The extractor prompt gains a line: when the unit is only in the row label, the quote is "label cell | value cell" for that one row. This does not conflict with the rule against joining both columns of a two-column row, which is about side-by-side products; the prompt says so.
3. **D3 Areal and case weights.** A component that gives only gsm, micrometres, gauge or a case, pallet or board weight has `weight_g` truth `missing`. The existing scorer already counts any predicted present value on a truth-missing slot as fabricated (rule: missing -> value is a fabrication); a test shows it. No scorer redesign.
4. **D4 Supplement.** `benchmark/supplement.py`, seed 20261126, 12 sheets S801 to S812 under `benchmark/supplement/` (`data/sheets`, `data/truth`, `manifest.json`), truth in the same schema (optional field `target_item`, new layout value `supplement`, new template values `catalogue`, `two_block`, `unit_header`). Reported separately with the same pass marks (no messy-10 mark, no conflicts in it). It does not decide the kill test; its result goes into the idea file next to the test result.

Truth decisions made while building the supplement:
- S805 "WhiteSolid" with "Colour ID: W1229": truth colour is `white`, quote "WhiteSolid". The wording is accepted only on that slot through the truth file's `accepted_values` (the scorer passes non-vocabulary `accepted_values` of the matched truth field to `quote_ok`, and only for the truth's own value); `COLOUR_VOCAB` is unchanged and the test and tuning data are byte-identical.
- "Variable Coloured" (S804) is out of vocabulary: colour `missing`.
- "Finish: Clear" with no Colour row (S804): colour `clear`, quote "Clear".
- Weight with unit only in a table header cannot be quoted contiguously, so S810 keeps units in the weight cells and puts header units on distractor columns (Height (mm)). A header-unit weight column needs its own decision.
- Prompt lines added besides D2 (needed so the supplement is answerable; no model has seen the prompt yet; they are part of the prompt used on the kill-test set too): blend rule, "gsm/micrometre/case weight means weight_g missing", "catalogue: extract only the item named in the title", and a packing-notes line: lines under a packing or palletisation heading that have no rows of their own are not components, while anything listed as a component with its own rows (for example "Component: outer case", Material n/a, as on S019) stays a component.
- Component names on S804/S808 ("Shipper", "Pouch film", "Label stock") rely on the prompt's name-mapping instruction.
- French page (S811) uses vocabulary wordings ("transparent") and a decimal point; a decimal comma ("4,2 g") is not parsed by `parse_weight` and is not generated.
- The encrypted sheet (S812) is AES-128 with an empty user password; `cryptography` is pinned in `benchmark/requirements.txt`.

5. **Run order and budget.** The supplement runs only after the test-set run, never before it, so it cannot use budget the `--set test` preflight needs. `extractor.run --set supplement` exits 6 unless the ledger already holds test-set (S001-S030) entries. It spends against the same USD 12 / 3M-token caps.

### Amendments 5 and 6 (record copied here at the kill, 2026-11-25)

These two were written on the product branch, not in this file. The branch will not be merged, so they are summarised here so the record is complete.
- **Amendment 5** (`benchmark/KILL_TEST_AMENDMENT_5.md`): a proposal from tuning run e08c to accept whole-word sub-span quotes in `quote_ok`. It is marked "NOT applied". It was never used, and the scorer that produced the result is the scorer reviewed before any run.
- **Amendment 6** (`benchmark/KILL_TEST_AMENDMENT_6.md`, dated 2026-11-24, before any test-set call; also in `state/DECISIONS.md` at 23:30Z, run bb8d): moved the re-tune and the test run from gpt-5.4-pro to gpt-5-mini (USD 0.25 / 2.00 per 1M). After one re-tune on the five tuning sheets, effort and max output tokens could be chosen, provided the choice was recorded before the test run. Prompt changes were not allowed. Pass marks 1 to 5, the test set, the truth, the scorer, the cost mark (USD 0.316 a sheet, which is GBP 0.25 at 0.79) and the USD 12 cap were all unchanged.

## Kill (T-66, 2026-11-25)

Validator, run 20261125T001943Z-run-cf06. Evidence: the pre-registered kill test above; the result file `products/pepr-packaging-data-pipeline/results/test1/score.json` and `NEXT.md` ("Run bb8d test1 result") on branch `p/pepr-packaging-data-pipeline/T-56`; `state/DECISIONS.md` (lines for runs bb8d and 4500); `state/BUDGET.md`. This run had no shell, so I read the branch files through their public raw URLs. `results/test1/score.json` is the scorer's own output and was not retyped by anyone.

**Verdict: KILL.** Final score 68 (unchanged; the proof test gives no lift because it failed). This is the second failed G1 attempt.

**Result against the pass marks.** One test run on 30 sheets: gpt-5-mini, reasoning effort medium, max output 6000 tokens. It was resumed once after a connection reset at S017, and no finished sheet was re-run.

| Mark (written before any run) | Needed | Got | |
|---|---|---|---|
| 1. Overall field accuracy | >= 90% | 89.3% (408/457) | **FAIL** |
| 2. Messy-10 field accuracy | >= 80% | 88.8% (174/196) | pass |
| 3. Untraced values | 0 | 0 | pass |
| 4a. Missing fields returned as missing | >= 95% | 90.6% (116/128); 1 fabricated (S026) | **FAIL** |
| 4b. Conflicts flagged | >= 80% (18 of 22) | 90.9% (20/22); 0 false conflicts | pass |
| 5. Cost | <= USD 0.316 a sheet mean | USD 0.0074 a sheet (USD 0.223 for 30; max USD 0.026) | pass |

**Is this a Fail under the Fail line? Yes.** The pass mark says "all must hold", and two marks (1 and 4a) do not hold. The Fail line says a fail "counts as a failed G1 attempt", and the first attempt was REVISE 68 on 2026-11-23, so the two-attempt rule in `playbooks/pipeline.md` kills the idea.

**Did any pass mark change after results? No.** I checked four things:
- The thresholds in `score.json` (90 / 80 / 0 / 95 / 80 / 0.316) match the original text and Amendments 1 to 4, which were all written before any model call.
- Amendment 6 changed the model, not the marks, and it is dated before the test call.
- Amendment 5 was never applied.
- The resume after the crash re-ran no finished sheet. S016, which was incomplete before the crash, was not retried (DECISIONS, run bb8d).

**One process gap, which doesn't change the verdict.** The test text says amendments go "here". Amendment 6 was recorded on the branch and in `state/DECISIONS.md`, not in this file, before the run. It touched no mark, so the result stands.

**Why the run missed.** Two sheets, S016 and S021, used up the 6000-token output budget (mostly on reasoning) and returned nothing. Under the rules they scored 0 on all 41 of their slots, including 11 missing slots and both of the unflagged conflicts.
- Without those two sheets, the other 28 score 98.1% accuracy (408/416) and 99.1% missing handling (116/117).
- Completing S021 alone would probably have passed both marks. Completing S016 alone would still miss mark 4a (at most 121/128, 94.5%).
- So the failure is a truncation failure, not a reading failure. This is the honest reading, but it does not change the result: the rules written before the run score an incomplete answer as missing, and the single-run rule forbids a re-run on these sheets.

**Lessons**
1. **The output budget decided the test, and this is the second time.** T-12 (mtd-quarterly-prep) lost its image runs when reasoning used all 8,000 output tokens. Here two of 30 sheets ran out at 6000.
   - Amendment 6 allowed a larger cap. The plan was to repeat with 16000 only if tuning showed incomplete sheets.
   - Five tuning sheets can't reveal a failure that happens on about 1 sheet in 15: with that rate, 5 clean tuning sheets happen about 70% of the time.
   - Rule for future proof tests: on a cheap model, set the output cap generously before the run (16000 on gpt-5-mini costs about 3 cents a sheet at worst). Alternatively, pre-register how truncation is handled, for example one retry at a larger cap or chunking by component, decided before the run.
   - Also log output tokens per sheet in tuning so the headroom is visible.
2. **Cost is not the problem.** gpt-5-mini cost 0.74 cents a sheet, about 2% of the USD 0.316 mark, and the whole proof test used USD 3.35 of USD 12. The expensive model was the cost trap: gpt-5.4-pro tuning averaged USD 0.62 a sheet, about twice the mark. For extraction, start with the mini model and move up only if accuracy needs it.
3. **Even a pass needed a wedge.** Repackd already sells spec-sheet extraction, RAM scoring, fee simulation and a DEFRA CSV (Growth £799 a month; Evidence pass T-13).
   - A pass would have given about AI 10 and Build 11, which is about 70 at best with Competition at 3. It could have been 69 if Competition fell to 2.
   - The test could prove capability, not market room.
   - Rule: before spending runs on a proof test, write down the score a pass would produce. If a pass can't clear 70 on its own, get the wedge evidence first (here, a Repackd trial; Q-9 A now allows free, no-card trials with test data).
4. **What pre-registration taught the studio.**
   - It worked as intended. Marks, data, truth and scorer were fixed before any model call, every amendment was dated, and the studio held the line on a 0.7-point miss instead of rationalising a re-run.
   - It also showed the cost. About eight runs went into benchmark engineering (generator, scorer, quote rules, supplement, spend guard) for one pass-or-fail number.
   - The fixed parts of a kill test should cover run configuration (output cap, truncation handling, model) as well as marks. Configuration chosen informally ("6000 was the default") is where this test was lost.
   - Keep every amendment in the idea file, not only on a branch.
5. **The benchmark kit is reusable.** The synthetic sheet generator with truth from the same data model, the page-quote traceability check, the conflict and missing-field scoring and the ledger spend guard all live on branch `p/pepr-packaging-data-pipeline/T-56`. Reuse them for any future "documents into structured fields" proof test, but don't merge them as a product.

**What would revive it (all three are needed)**
1. **A wedge against Repackd, with evidence.** Use a Repackd free trial (allowed under Q-9 A: no card, test data only, nothing in Vishal's name, the sign-up logged) on the 12 realism-supplement sheets and a few licence-cleared public spec PDFs.
   - The trial must show that its extraction is weak on messy sheets: field accuracy under about 80%, no source trace, or invented values for missing fields, documented with screenshots of test data.
   - Or a priced segment Repackd doesn't serve must be shown, for example smaller compliance schemes licensing a tool, sized from the gov.uk scheme register.
2. **A new kill test, written and committed before any run.**
   - Same pass marks.
   - A **fresh held-out set**: a new seed, at least 30 sheets, including the realism-style forms from Amendments 3 and 4 (gm and oz, unit only in the label, gsm-only films, blends, catalogues).
   - Run configuration fixed in the text: an output cap of at least 16000 or per-component chunking, and a written truncation rule.
   - The new test must pass. **A re-run on the 30 T-56 test sheets cannot count.** Their results are known, and any change to the budget or prompt would be tuned on them.
3. **A validator re-score of 70 or more** under the wedge-scored Competition row (Q-10), with Competition backed by the evidence in item 1.

**Realism supplement (about USD 0.1): recommend yes, for lessons only.** Run the 12 sheets once at the same settings (gpt-5-mini, medium, 6000) and log output tokens per sheet. It costs about USD 0.1 of the USD 8.65 left in the cap. It shows whether the truncation rate and mini-model accuracy hold on real-sheet weight forms and wording, which any future extraction idea (including a revival) needs to know. It cannot change this verdict.

## Gate log
- 2026-11-23 scout round 2: G0 file written. Competitor own-page check done for Valpak (via BRC release) only; PackTotal own page not reachable (403 on aggregator). Open items listed above.
- 2026-11-23 | validator | G0→G1 | REVISE 68 | Scored as the merged pEPR and PPT data layer: the studio's strongest official pain so far (automatic red for missing evidence, red factor rising to 2.0 by 2028-29), but Clarity already sells bulk RAM ratings, missing-data flags and fee modelling from £4,995 a year and gov.uk gives the RPD file generator away, so only an unverified upstream extraction gap is left.
- 2026-11-24 | studio lead | proof test T-56 run (bb8d) | FAIL | field accuracy 89.3% (needs 90%) and missing handling 90.6% (needs 95%); the other four marks passed; S016 and S021 ran out of the 6000-token output budget and scored 0.
- 2026-11-25 | validator | G0→G1 (second attempt, T-56 proof test) | KILL 68 | Second failure. The pre-registered test failed 2 of 6 marks with no mark changed after results, and two sheets that hit the output cap decided the miss. Cost (USD 0.007 a sheet) was never the issue, and even a pass would only have proved what Repackd already sells. Lessons and revive conditions are in "Kill (T-66, 2026-11-25)".

## Realism supplement (T-67, 2026-11-25, lessons only; does not change the kill)
Ran once at test1 settings (gpt-5-mini, medium, 6000 output tokens) on the 12 supplement sheets: field accuracy 92.6% (162/175), missing handled 100%, 0 fabricated, 2 untraced values (S807, S809), USD 0.004/sheet, USD 0.050 total. No sheet came near the output cap (max 3,494 tokens), so truncation came from the test set's hardest sheets, not from realistic layouts. The one real weakness: on a catalogue sheet listing many SKUs (S807, REALISM item 3) the model extracted every row instead of only the target item (40.9%). Any future documents-to-fields product needs an explicit target-item step. Results: branch `p/pepr-packaging-data-pipeline/T-56`, `results/supplement/`.
