# Customs entry prep for small forwarders

- slug: customs-entry-prep-small-forwarders
- stage: G0
- market and segment: UK independent freight forwarders and customs agents (roughly 5 to 50 staff) that lodge import declarations on CDS for SME importers, where documents arrive as emailed commercial invoices and packing lists.
- one-line pitch: Turn the emailed commercial invoice and packing list into a checked, pre-filled CDS import entry, with suggested commodity codes and a list of queries for the client, so an entry clerk reviews it instead of keying it.

## Problem and who has it

Most UK traders do not lodge their own customs declarations. They pay an intermediary, usually a freight forwarder, express operator or customs agent. HMRC's own research found most outsourcing traders send their information by email without any software. The intermediary's entry clerk then reads the commercial invoice and packing list, researches commodity codes and duty rates, and keys the declaration into their CDS software. HMRC's survey puts traders' own preparation time at 1 to 2 hours per declaration, and the median intermediary charge at about £50 to £60 per declaration. HMRC research has also recorded intermediaries turning away new clients for lack of capacity, and stakeholders "frequently raised" incorrectly completed declarations as a quality problem. Errors mean overpaid duty or VAT, corrections and goods held at the border.

The buyer is the small forwarder or agent: its margin is the per-entry fee minus clerk time, so fewer minutes and fewer errors per entry go straight to profit.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://assets.publishing.service.gov.uk/media/684bfab8da3d1b49e6797020/HMRC_CAB_report_FINAL.odt (HMRC Customs Admin Burden research, Sept 2023) | 2026-11-23 | 78% of surveyed traders used only an intermediary for declarations. Among those outsourcing all declarations, 66% sent information online without software (including email), 18% via software. Time per declaration was typically 1 to 2 hours. Median intermediary cost per declaration was £51 for full import declarations and £60 overall among those who did not know the declaration type. |
| https://gov.uk/government/publications/research-into-the-customs-intermediaries-sector-waves-3-to-5/customs-intermediaries-wave-3-executive-summary (HMRC/Ipsos, fieldwork 26 Mar to 6 May 2021, 473 interviews) | 2026-11-23 | More than half of intermediaries had turned new customers away, most commonly for lack of capacity (29%). |
| https://gov.uk/government/consultations/introducing-a-voluntary-standard-for-customs-intermediaries/introducing-a-voluntary-standard-for-customs-intermediaries--3 (HMRC, updated 7 Dec 2023) | 2026-11-23 | Respondents "frequently raised" incorrectly completed declarations as a quality issue, causing overpaid duty/VAT, corrections and delays; linked to knowledge and quality-assurance gaps. Note: the same document says respondents felt sector capacity was sufficient by then. |
| https://www.gov.uk/government/publications/research-into-the-customs-intermediaries-sector-waves-3-to-5/customs-intermediaries-wave-8-executive-summary-2023 (fieldwork 5 Oct to 1 Dec 2023, 493 interviews) | 2026-11-23 | 52% of intermediaries price by declaration type and complexity; full import declarations take longer than exports and ENS; about 59% had a supply chain management system. |
| https://www.manpower.co.uk/en/job/administration-and-business-support/customs-clearance-clerk/438970 | 2026-11-23 | Job ad (now closed) for a Customs Clearance Clerk in Immingham at £12.71/hour, duties: complete customs declarations accurately, contact customers for missing information, manage documentation. Shows the task is staffed manually. |
| Search-result snippets for UK customs entry clerk adverts (Chelmsford £22,000 to £26,400; London forwarder £25k to £30k; Bradford £30k to £35k, "Experience with CDS is essential"), duties including researching commodity codes and calculating duty and VAT. Pages not fetched or closed, so unverified. | 2026-11-23 | Indicative only: entry preparation and code research are named duties in job ads. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Using an intermediary (trader's view; HMRC CAB report above) | Median £51 per full import declaration | This is the forwarder's revenue line; our tool cuts the cost of producing it. |
| customs-declarations.uk self-serve CDS filing (https://www.customs-declarations.uk/) | "£25 max per declaration", pay as you go, no monthly fee | Lodging software; the user still keys the data and picks codes. |
| In-house entry clerk (https://www.payscale.com/research/UK/Job=Customs_Clerk/Salary/82aef6e6/Documentation) | Average base £25,943/yr (page headline says 2026 but also "last updated Jan 09 2021", so treat as indicative) | Hard to recruit and train; throughput is limited by keying and code research. |
| Large CDS software suites (for example Descartes, named in job ads) | Not published; not verified | Built for lodging, not for reading messy invoices. |

## Why AI is essential (and the moat)

The core step is reading unstructured, varied commercial invoices and packing lists (PDFs, scans, spreadsheets, sometimes in other languages) and mapping free-text product descriptions to 10-digit UK commodity codes. That is document understanding plus classification, which rules and templates do badly across hundreds of suppliers. AI can also cross-check invoice totals, weights, origin and Incoterms against each other and draft the client query email for missing data.

Moat: a per-forwarder memory of past approved classifications for each client's products (accuracy improves with use), an evaluation set of real anonymised entries, and tight export to the forwarder's lodging software. The UK Trade Tariff is public, which keeps data costs at zero.

## Rough build plan and Azure cost

1. Upload or forward-to-inbox intake for invoice and packing-list PDFs.
2. Extraction to a structured entry (consignor, consignee, lines, values, weights, origin, Incoterms) with confidence flags.
3. Commodity-code suggestions with reasons, drawn from the public UK Trade Tariff and the forwarder's own past approvals; clerk confirms every code.
4. Consistency checks and a drafted query email for gaps.
5. Export as CSV/XML for the forwarder's lodging software (no direct CDS submission in the MVP).

Azure (estimate, method: default stack with scale-to-zero container app, a small database on a free or lowest tier, blob storage, and pay-per-token Azure OpenAI for a demo volume of a few hundred documents): likely under $15 a month in the build phase. The architect should confirm figures in `state/BUDGET.md` before anything is created.

## Risks, and what would prove this wrong

- Liability: a wrong commodity code means wrong duty. The product must only suggest; a human confirms every code, and the UI must say so. Not legal or tax advice.
- Integration: each forwarder uses different lodging software; if none accept an import file, value drops to "faster reading".
- Capacity pressure may have eased since 2021 (HMRC's 2023 consultation response says respondents felt capacity was sufficient), weakening the urgency.
- Demo data: real invoices contain business data; we need synthetic or public sample invoices to show value without customer data.
- Proven wrong if: small forwarders tell us keying is under 10 minutes an entry, or their lodging software already auto-extracts invoices well, or they will not pay more than a few pounds a month.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
