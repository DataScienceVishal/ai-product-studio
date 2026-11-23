# Tour operator contract rate loader

- slug: tour-operator-contract-rate-loader
- stage: KILLED (G0, first gate attempt, 2026-11-23)
- market and segment: UK specialist tour operators, DMCs and group-travel firms (about 5 to 100 staff) that load hotel and supplier contracts by hand into a booking or pricing system
- one-line pitch: Reads each hotel's contract PDF, rate sheet or email (seasons, room grids, supplements, child bands, allotments, cancellation tiers), builds a validated rate sheet with every figure traced to the contract line, flags gaps and overlaps, and exports it in the format the operator's system imports.

## Problem and who has it

Product and contracting teams at tour operators receive each supplier's rates as PDFs, Word contracts, Excel sheets and emails in no common layout, and re-key them into the booking system (or a costing spreadsheet) every season. The work needs judgment: season gaps and overlaps, supplements, child age bands, taxes outside the net rate, release periods, and cancellation clauses stated as dates or percentages. Errors become mispriced quotes or unrecoverable margin loss. Employers advertise this as a staffed job ("Contract Executive / Loader", "Hotel Contracting Executive"). The data is company-to-company commercial data, not personal data.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://jobs.travelweekly.co.uk/job/162522/contract-executive-loader-/ (title seen in search results; page not fetched, host blocked in this session) | 2026-11-23 | A UK job board lists a role titled "Contract Executive / Loader". Unverified beyond the title. |
| Search snippets from jobs.travelweekly.co.uk, hallo.co.uk, e.g. https://jobs.travelweekly.co.uk/job/162061/hotel-contracting-executive/ and https://www.hallo.co.uk/ads/jobs-in-travel-and-tourism/contract-executive/2864837 | 2026-11-23 | Snippet text: "loading and maintaining of hotel contracts"; salaries seen: £24,000 basic (plus bonus), £26,000 to £29,000, £24,000 to £28,000 (2024), up to £40,000 for a European Contracts Manager. Several ads date from 2019 to 2024. Unverified: only search snippets read, not the ads. |
| https://dmcquote.com/guides/hotel-contract-template | 2026-11-23 | Lists what a loading sheet needs: contract terms, seasons (with gaps/overlap checks), room grids, meal and child bands, allotment and release by season, blackout dates, cancellation tiers. Shows the task is multi-field and judgment-heavy. |
| https://developer.hotelbeds.com/documentation/hotels/cache-api/internal-inventory-process/additional-information | 2026-11-23 | Cancellation fees can be an amount or percentage, first night only, cumulative, with rate-specific fees overriding general ones. Seen in search snippet only (unverified). |
| https://www.wave-access.com/public_en/blog/2025/september/10/ai-powered-contract-extraction-for-a-travel-company.aspx | 2026-11-23 | A software house built a custom AI contract extraction pipeline (OCR, clustering, templates) for a B2B travel company. Shows the pain is real enough to fund bespoke builds. Snippet only; page not read. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| In-house contracting executive or loader (job ads above) | about £24k to £29k a year plus on-costs (snippets, unverified) | Seasonal peaks; manual re-keying; error risk. |
| TourConnect AI for Tourplan (https://tourconnect-ai.squarespace.com/resources/new-expired-rate-automation-for-tourplan) | not published | Page covers expired-rate fallback and rate choice during itinerary building. Page does not say it reads contract PDFs (checked 2026-11-23). |
| Sembark supplier contracting (https://sembark.com/travel-software/features/supplier-contracting) | not checked | Stores contracted rates and costs packages; snippet only, no sign of PDF-to-rate extraction. Needs a direct check. |
| Generic document AI (Contracko hotel-contract-to-CSV, https://contracko.com/contract-data-extraction/hotel-contract-to-csv/index.html.md) | not checked | Examples are hotel management contracts (fees, term), not trade rate grids. Free-form LLM chat is the real substitute. |
| Tourplan and other operator systems (https://www.capterra.com/p/2489/Tourplan-iS/) | page returned 403 | Not verified. Needs a check of Tourplan's own help pages for rate import and any AI features. |

## Why AI is essential (and the moat)

The input is unstructured and different for every hotel. Extraction must produce a fixed schema, resolve ambiguity ("child 2 to 11 sharing free, max 2"), compute the cancellation tiers as dates, and detect season gaps and overlaps. Validation (rule checks plus every figure linked to a source line) is what makes it safe for a human reviewer to sign off, and that review step is the product. Moat: a schema and test set of real contract patterns, plus import adapters for operator systems. Moat is moderate. Operator systems could add contract import themselves.

## Rough build plan and Azure cost

- Week 1: PDF/Word/Excel ingestion, LLM extraction into a rate schema, source-line tracing.
- Week 2: rule validator (season gaps, overlaps, occupancy, child bands, currency, tax flags), reviewer UI with side-by-side contract view.
- Week 3: exports (CSV/Excel in a generic layout, then one system's import format), year-on-year change report (new rates vs last season).
- Week 4: evaluation set of about 50 synthetic contracts in different layouts; demo with fictional hotels.
- Azure (estimate): Container Apps scale-to-zero, Azure OpenAI small model for extraction, Document Intelligence if OCR is needed: about $10 to $30 a month at demo volume (method: about 300 contracts of 10 pages a month). Check against BUDGET.md.
- Demo data: fully synthetic contracts that the studio writes in several layouts. No scraping and no personal data. Mock mode loses nothing; no paid telephony or WhatsApp.

## Risks, and what would prove this wrong

- Reach: the UK buyer pool (specialist operators, DMCs) is small and its systems differ (Tourplan, others). The channel owner is unknown; needs a named UK partner in travel.
- Competition not fully checked: Tourplan, Sembark and other travel systems' own help pages were not read; an import or AI contract feature may exist. TourConnect AI could add contract parsing quickly.
- Job ads are old or snippet-only, so the labour cost is unverified. Many operators have moved to dynamic or bedbank content, reducing contracted rate volume.
- Accuracy: a wrong rate is costly; the reviewer step must stay mandatory.
- Proved wrong if: three or more UK operators already use a contract-import tool, or Tourplan's help pages show AI contract import, or typical contracts are already supplied as structured files.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 13 | 12 | 10 | 4 | 9 | 2 | 9 | 59 |

## Validator notes (T-31, 2026-11-23)

**Red-flag check: none.** Not an off-limits area, no paid service is required, no scraping, and synthetic contracts can demo extraction. (The value of the export step does depend on proprietary import formats the studio can't test; see Build.)

**Falsification findings** (all accessed 2026-11-23; vendor pages and trade press, read by the fetch tool or seen as search results where stated)
- The tour-operator systems already ship AI contract loading inside the platform:
  - TravelBox (CodeGen, a UK/Sri Lanka tour-operator system): "Smart Contract Loading" uploads single or bulk contract PDFs, uses an LLM API to extract contract data, maps it to TravelBox templates and emails error logs. Published 17 July 2025 (https://codegen.co.uk/blog/smart-contract-loading-in-travelbox-simplifying-contract-management-with-ai/, fetched).
  - Juniper (which bought UK operator-system vendor Inspiretec in 2025) sells an "AI Contract Builder" for loading contracts, and has partnered with 247tpd, whose HERMES TDLP platform automates hotel contract processing with specialist validation, as an outsourced option inside Juniper (https://www.traveldailynews.com/technology/juniper-and-247tpd-partner-to-automate-hotel-contract-data-loading/, search result only; fetch returned 403).
  - Travel Compositor (Travelsoft group) launched Dante in February 2026: upload a contract and it reads rates, descriptions, seasons and conditions into a sellable product; first for closed tours, then accommodation and other engines (https://travelcompositor.com/en/travel-compositor-launches-dante-its-new-ai-based-patent-to-revolutionize-contract-loading/ and https://www.travolution.com/news/travel-compositor-launches-dante-a-new-ai-based-patent-that-converts-contracts-into-products/, search results).
  - TourConnect (the Tourplan partner) runs a Data Conversion Team that converts supplier rates into rate sheets for review, Enterprise plans only (https://intercom.help/tourconnect/en/articles/4446795-request-rate-conversion, fetched).
- Contract loading is an established outsourced service, and that is the cheap substitute: Coforge (https://coforge.com/resource-library/case-studies/contract-loading), WNS (https://www.wns.com/perspectives/case-studies/transforming-contract-loading-to-accelerate-speed-to-market-for-a-leading-travel-club) and Unire in India (https://www.unire.co.in/?p=534, fetched: bulk contract uploads for DMCs, OTAs and TMCs; no prices). This proves the pain and willingness to pay, but no prices are public, and offshore loading with human checking is what a small UK operator compares a SaaS tool against.
- Not checked on their own pages (time): Tourplan help, Sembark, Travelogix, Dolphin Dynamics, Lemax, Kaptio. Not needed for the verdict: three systems and one Tourplan partner already have it.
- Buyer pool: the CAA reports 1,616 ATOL holders after a March renewal (https://www.caa.co.uk/newsroom/news/1-616-businesses-in-the-travel-sector-licensed-under-the-atol-scheme/, search result; year not confirmed). Wikipedia cites about 900 ABTA tour-operator members (https://en.wikipedia.org/wiki/ABTA_(trade_association), not matched to an ABTA source). Estimate: only a few hundred of these hand-load hotel contracts at volume (many sell flight-plus-bedbank dynamic packages), and those with volume run TravelBox, Juniper/Inspiretec, Tourplan or similar, whose vendors are adding the feature.
- Reach via a small UK partner: weak. Selling means getting into the operator's booking-system workflow, and the system vendors control the import path. The partner's sector is unknown, and nothing suggests travel.
- Build: extraction and validation are feasible in four weeks on synthetic data, but the value is the load into the operator's system. Tourplan, TravelBox and Juniper import formats are proprietary and can't be tested without a customer's licence, so the G4 demo would end at a CSV.

**Scores in brief.** Pain 13: a staffed job plus a BPO industry, but the salaries are snippet-only. Pay 12: in-house and BPO spend are real, no public price. AI 10: genuinely AI-heavy, but now standard in the systems. Reach 4. Build 9. Competition 2: the incumbents' own systems and their partners already do it. Risk 9: commercial data, no personal data, the human reviewer stays.

**Verdict: KILL (first attempt; ceiling below 70).** By late 2026 the operator systems themselves (TravelBox Smart Contract Loading, Juniper AI Contract Builder with 247tpd, Travel Compositor Dante) and offshore contract-loading BPOs (Coforge, WNS, Unire) already turn hotel contracts into loaded rates. A standalone tool would end at a CSV, because it can't reach the proprietary import paths those vendors control. The UK buyer pool is a few hundred operators, and a small non-travel partner has no route to them. Even with the best plausible evidence (Pain 15, Pay 14, AI 11, Reach 5, Build 10, Competition 4, Risk 9) the score tops out near 68, so REVISE would waste a round.

**Lessons**
- "Documents into a system of record" is the first AI feature a vertical system vendor ships. Check the system vendors' own blogs and release notes before anything else.
- Where a BPO industry exists for a task, the pain is proven, but the buyer already has a cheap human-checked option and the system vendors partner with the BPOs.
- Value that ends in a proprietary import format the studio can't test caps Build and the demo.

**What would revive it**
- A large segment with no system vendor at all (for example group-travel or school-trip firms running costing spreadsheets), shown by 20+ public job ads that name Excel as the loading target.
- Or a UK partner already selling into tour operators, plus a sample of real contracts that TravelBox, Juniper and Dante demonstrably get wrong.

## Gate log
- 2026-11-23: G0 spotted by scout (T-31). Open checks before scoring: Tourplan and Sembark help pages, verified job ads with salaries, UK operator count and systems used.
- 2026-11-23 | validator | G0→G1 | KILL 59 | TravelBox, Juniper and Travel Compositor already ship AI contract loading in-platform, and offshore BPOs (Coforge, WNS, Unire, 247tpd) sell it as a service; a standalone tool can't reach the proprietary import paths, and the ceiling is about 68.
