# Tour operator contract rate loader

- slug: tour-operator-contract-rate-loader
- stage: G0
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
| | | | | | | | |

## Gate log
- 2026-11-23: G0 spotted by scout (T-31). Open checks before scoring: Tourplan and Sembark help pages, verified job ads with salaries, UK operator count and systems used.
