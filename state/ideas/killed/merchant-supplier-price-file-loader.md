# Supplier price-file loader for UK builders' merchants and trade wholesalers

- slug: merchant-supplier-price-file-loader
- stage: killed (G0, 2026-11-24, 53)
- market and segment: UK independent builders' merchants, plumbing and electrical wholesalers and similar trade distributors (roughly 10 to 150 staff) that load manufacturers' price lists into their ERP several times a year
- one-line pitch: Reads each manufacturer's price update (Excel with merged cells, PDF, email body), maps it to the merchant's own item codes and discount structure, shows a change summary and anomalies (price jumps, missing lines), and exports a file in the ERP's import format.

## Problem and who has it
Each manufacturer sends price changes in its own layout, with different discount codes and effective dates. A pricing administrator or buyer re-keys or reformats them, and wrong prices cost margin or lose quotes. This is a staffed job, not a tool purchase today.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.payscale.com/research/UK/Job=Pricing_Coordinator/Salary (search summary) | 2026-11-24 | Pricing coordinator: average about £25,000, typical range £20k to £40k (modelled estimate, not a merchant survey) |
| https://www.tpplccareers.co.uk/job/pricing-administrator-jobid-17049 (search summary) | 2026-11-24 | Travis Perkins advertises a Pricing Administrator role in the buying team; no salary figure given |
| https://tableflow.com/blog/electrical-distributor-pricing-automation (search summary) | 2026-11-24 | A US vendor case study: an electrical distributor with 40+ suppliers cutting 15+ hours a week (vendor claim) |
| https://tableflow.com/use-cases/supplier-pricing (fetched) | 2026-11-24 | TableFlow ships supplier-price ingestion pushing to NetSuite, SAP, Epicor and Prophet 21; no price shown; no mention of UK, Sage or BisTrack; Portola Labs, Inc. |
| https://www.cloverdx.com/blog/supplier-data-integration-for-distributors (search summary) | 2026-11-24 | A single supplier update can be a million-line Excel file; supplier part numbers differ from the distributor's, so a crosswalk is the hard step |
| https://www.fixradio.co.uk/fix-feed/construction-news/post/bmf-launches-universal-product-data-template-to-achieve-standardisation (search summary) | 2026-11-24 | The Builders Merchants Federation launched a universal product data template, which could reduce the format problem over time (adoption not checked) |

Pain signals so far: (1) the pricing administrator role exists at the largest merchant; (2) a US vendor case study with an hours-per-week figure; (3) a data-engineering article naming the SKU crosswalk as the hard step. Thin: all three are indirect, and none are UK merchant-specific.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Pricing administrator or buyer's time | Pricing coordinator about £25k a year (Payscale, estimate) | The cost to beat; the share spent on loading files is unknown |
| TableFlow | No price shown; demo required | US; ERPs named are NetSuite, SAP, Epicor Prophet 21; UK merchant ERPs (BisTrack, Merlin, Profit4) not named on the fetched page |
| Parabola vendor price-list template | Not checked | Generic no-code; no UK ERP formats |
| CloverDX or integration consultants | Not checked | Project work, not a subscription |
| ERP's own price-file import (Epicor BisTrack, Merlin) | Not found | Not confirmed either way; BisTrack and Merlin help pages must be checked |
| BMF universal product data template | Free | A standard format, not a reader of legacy formats |

## Why AI is essential (and the moat)
Layout reading and column inference ("LP", "Catalog Price", net vs list) is where rules fail and models succeed; anomaly checks (a 40% jump) and SKU crosswalk suggestions are the second use. The moat is weak against a funded TableFlow; the studio's possible edge is UK merchant ERP import formats and the BMF template, which a US vendor may not prioritise.

## Rough build plan and Azure cost
Upload or inbox intake, table extraction, a mapping memory per supplier (so the second file loads faster), change summary, export CSV in two ERP formats. Azure about £30 to £60 a month at pilot scale (estimate, not costed).

Demo with synthetic data: generate five invented manufacturer price files in awkward formats plus a merchant catalogue with planted code mismatches. Fully demoable with no paid service.

## Risks, and what would prove this wrong
- No public price for the job beyond a modelled salary: Pay is unproven.
- Overlaps merchant-whatsapp-order-desk and wholesale-email-order-entry-sage (both REVISE); the same merchants, same ERP-access problem. Merge or park.
- Biggest unchecked fact: whether BisTrack and Merlin already import supplier price files from standard layouts. If they do, the manual job is only reformatting and the idea collapses.
- What would prove this wrong: BisTrack or Merlin help pages showing scheduled supplier price imports that accept the BMF template; or TableFlow naming UK merchant customers.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 10 | 7 | 8 | 6 | 9 | 3 | 10 | 53 |

## Validator, round 8 (T-44, 2026-11-24)

**Verdict: KILL at G0 to G1 (53; ceiling about 60).**

The idea's own falsification test fails. The merchant ERPs already import supplier price files, and the sector already has industry data services that deliver manufacturer prices straight into ERPs. That leaves only odd-format reformatting, for a job whose cost has never been measured.

Evidence (accessed 2026-11-24):
- https://merlin3.knowledgeowl.com/help/price-update (search summary; the help site now redirects to merlin3.vetspace.cloud): Merlin's "Price Update" screen imports pricing from each wholesale supplier's own file format and shows warnings, for example on zero-price items. The fetched pages are written for the vet wholesale variant, so the builders' merchant version is likely but not confirmed.
- https://ondemand.epicor.com/courseResources/r2244_ImportProductsTipsTricks_2.pdf (search summary): BisTrack's spreadsheet product import has an Update mode, a Validate-only pass, and supplier price and branch cost import.
- https://www.ogl.co.uk/profit4-erp-integration-for-luckinslive (fetched): with LUCKINSlive, "all data for each product is immediately and automatically imported into Profit4" and pricing is updated automatically. Trimble says most UK MEP wholesalers are connected to LUCKINSlive by API to their ERP (https://mep.trimble.com/en-gb/resources/mep-blogs/five-reasons-wholesalers-need-integrated-product-pricing-information, search summary). Intact iQ and OrderWise advertise the same integration. For electrical, plumbing and HVAC wholesalers, this is the job already sold as a subscription.
- https://www.nmbs.co.uk/bmf-and-nmbs-to-launch-industry-data-pool/ (search summary): BMF and NMBS run Data Yard, an industry-owned data pool with more than 140 supplier members. Manufacturers publish once and merchants and buying groups consume the data. Whether it carries prices was not confirmed, but it is the sector's own fix for the format problem, alongside the BMF template.
- https://tableflow.com/use-cases/supplier-pricing (scout, fetched): a funded US AI vendor already sells the extraction itself.
- https://desktophelp.sage.co.uk/sage200/sage200standard/content/Screens/Stock/Import%20supplier%20prices.htm (search summary): Sage 200 imports supplier price lists from CSV, one supplier at a time.

How each score was reached:
- Pain 10: all the pain signals are indirect. There is one Travis Perkins job title with no salary and no UK merchant complaints.
- Pay 7: the only figure is a modelled Payscale salary, and the share of that job spent loading files is unknown. Luckins is an existing paid substitute, but its price was not found.
- AI 8: reading layouts and suggesting SKU crosswalks does need a model, but TableFlow already ships it.
- Reach 6: the BMF and NMBS membership lists can be found, but the partner sector is unknown.
- Build 9: synthetic data is enough for the demo, and CSV export to ERP import formats is plausible.
- Competition 3: Luckins, Data Yard, the ERP import utilities and TableFlow.
- Risk 10: product data only.

**Near-duplicate:** partly, of merchant-whatsapp-order-desk (REVISE 56): the same buyers, the same ERP route (BisTrack, Merlin, Kerridge) and the same unknown partner sector. Merge the useful findings into that file rather than keeping a separate idea: the ERPs have import utilities, and Luckins and Data Yard sit in the data supply chain. Do not run a separate G1 attempt.

**What would revive it:** a UK independent merchant segment that is not served by Luckins or Data Yard (for example, timber and landscaping suppliers whose manufacturers send PDFs), with a measured number of hours per month spent on price loading, plus a Luckins or Data Yard price showing that the substitute is expensive.

**Lessons:**
- Before scoring a "documents into a vertical ERP" idea, search for the sector's data pool or aggregator (Luckins, Data Yard, GS1, buying-group feeds). Industries with many suppliers usually standardised supplier price files years ago.
- A salary taken from a job title is a ceiling on the saving, not the cost of the task.

## Gate log
- 2026-11-24 T-44 scout round 8: G0 written. Pay evidence is only a modelled salary; no UK price-file product found in one search (not conclusive). Biggest doubt: Pay and ERP import support.
- 2026-11-24 | validator | G0→G1 | KILL 53 | Merlin's Price Update and BisTrack's import already load supplier price files; LUCKINSlive auto-feeds prices into wholesaler ERPs (Profit4, Intact, OrderWise); BMF and NMBS run the Data Yard pool; TableFlow sells the AI extraction. The only evidence on Pay is a modelled salary. Fold the findings into merchant-whatsapp-order-desk. The file should move to `killed/` (git mv by the lead).
