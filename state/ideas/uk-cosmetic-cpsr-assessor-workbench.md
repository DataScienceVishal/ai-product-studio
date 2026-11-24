# UK cosmetic CPSR assessor workbench

- slug: uk-cosmetic-cpsr-assessor-workbench
- stage: G0
- market and segment: UK (and UK/EU) safety-assessor bureaus and Responsible Person services that write Cosmetic Product Safety Reports (CPSR Part A and B) for small cosmetics brands at a per-product fee
- one-line pitch: The bureau's AI workbench reads each brand's formulation, supplier specs, SDS and certificates, reconciles ingredients, runs the margin-of-safety arithmetic and drafts CPSR Parts A and B with every statement traced to a source, so the qualified assessor reviews and signs instead of writing (found in the bureau-side second pass of T-50; scores blank for the validator)

## Problem and who has it
Every cosmetic placed on the GB market needs a CPSR signed by a qualified safety assessor and a notification on SCPN. The bureau charges per product (about £220 to £465 + VAT on its own pages) and its cost is assessor hours. Fees are being pushed down (one bureau advertises "from £70", another has batch pricing down to about £98 a product per a vendor guide), so labour per report is the margin. The bureau keeps the client and the signature; the workbench does the extraction, lookups and first draft.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://euverify.com/cpsr/ | 2026-11-24 | Per-product price (excl. VAT): Basic £250 (1-9 ingredients), Standard £370 (10-29), Complex £465 (30+); variants +£10 to +£60; includes Part A and B, assessor sign-off, SCPN filing; "3,600+ verified brands"; 2-4 weeks; page does not mention AI or software (fetched in full) |
| https://oxbio-site.pages.dev/regulatory-compliance/uk | 2026-11-24 | Oxford Biosciences Ltd: £220 for a single product up to 20 ingredients, variants £40, batches of five from £875, "from £70" elsewhere on the same page; 2-3 working days; signed by a qualified assessor; no AI mention. Domain is a pages.dev preview, so treat as medium trust; the firm identity is stated on the page |
| https://www.gov.uk/government/news/new-data-on-uk-cosmetic-product-safety-notifications | 2026-11-24 | 861,686 notifications on SCPN since launch and 24,112 registered Responsible Persons as of 28 May 2026 (cumulative; no per-year split); OPSS acted on notified products with banned chemicals |
| https://www.itv.com/news/2026-11-03/hair-and-beauty-products-less-regulated-than-ballpoint-pens-report | 2026-11-24 | Independent pain/forcing signal: parliamentary committee report (early Nov 2026) calls the rules a "confusing mess", urges a licensing framework and commencement of marketplace safety duties within 12 months (secondary coverage; report itself not read) |
| https://committees.parliament.uk/work/9435/ | 2026-11-24 | The inquiry "The science and regulation of hair and beauty products and treatments"; OPSS gave evidence 3 June 2026 (search summary) |
| https://euverify.com/what-is-cps/ | 2026-11-24 | Vendor guide gives £180-£700 per product, lab tests extra, "Part A only" budget offers exist (vendor-authored; low weight) |

Honest gaps: no independent count of qualified UK safety assessors or of bureaus (there is no public register that I found); volume per year unknown; both price pages are vendor pages; the committee report is read only through news coverage.

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Bureau in-house (Euverify, Oxford Biosciences and similar) | £220-£465 + VAT a product (own pages), as low as £70 on one page | These are the buyers; no AI claimed on their pages |
| OrAIsi (AI platform for assessors, regulatory affairs and manufacturers; OrAIsi Tech S.L., Spain) https://oraisi-website.pages.dev/en/index.html | Not stated; "book a 30-minute conversation" | Page cites only EU rules (CosIng, SCCS, ECHA); no UK mention. Same product idea, so the main kill risk |
| Cosmetri Product Manager (Registrar Corp) https://www.registrarcorp.com/services/cosmetic-product-safety-report-cpsr/ and Capterra UK listing https://www.capterra.co.uk/software/1016188/cosmetri-product-manager | Not found | Generates a PIF from formulations stored in Cosmetri and lets assessors complete Parts A and B; US-owned, brand-side; no UK per-unit price found |
| SpheraCosmolife (free, research tool) https://doi.org/10.14573/altex.2010221 | Free | Does the toxicology arithmetic and in-silico NOAEL; no document reading, no report |
| Brand uses a general chatbot to prepare the ingredient table | Free to about £20 a month | Saves assessor time but not sign-off; that is the bureau's cost lever, not a substitute for the bureau |

## Why AI is essential (and the moat)
- The slow part is unstructured: supplier specifications, certificates of analysis, SDS, stability and packaging notes, purity and impurity statements, each in a different layout. Reading them and tying each ingredient to concentration, function, UK Annex status and exposure assumptions is document work; the margin-of-safety arithmetic is deterministic and stays in code.
- The assessor signs, so liability stays with the bureau and a human; a software vendor selling to brands will not take that sign-off, and a bureau will not hand its sign-off to a brand-side tool.
- Moat is thin on features, so it must come from (a) UK-specific rules content (UK Annex differences after Brexit, SCPN fields) that the EU-focused OrAIsi page does not show, and (b) fit to a small bureau's own past reports and wording (per-bureau style memory).

## Rough build plan and Azure cost
- Inputs: PDF/XLSX formulations and supplier documents. Outputs: ingredient table with INCI reconciliation, Annex flags, MoS sheet, drafted Part A and Part B with citations, reviewer queue, SCPN field export.
- Public data: CosIng and EU/UK annexes, SCCS opinions, public sample assessments (for example the Danish EPA's published baby-lotion safety assessment https://edit.mst.dk/media/egtfhsru/safety-assessment-dhivacosmetics-dhiva-baby-lotion_final.pdf, listed in search results, not yet read).
- Demo with synthetic formulations and public gold reports; no paid telephony or messaging, so the whole demo runs without mock mode.
- Azure: App Service, Blob, Postgres, one LLM deployment: about £60-£120 a month at demo load (estimate, not costed).

## Risks, and what would prove this wrong
- OrAIsi or Cosmetri adds UK coverage in a month: check both vendors' UK pages and release notes before scoring.
- Price war ("from £70" on one page) means each report is worth little and a bureau will pay little per seat; Pay may be the weak score again.
- Number of qualified assessors and bureaus unknown. Proof of wrong: fewer than about 50 UK assessor bureaus and no willingness to pay (cannot be tested without contact; selling is locked).
- Core is arithmetic plus lookup; AI share could be below the bar.
- Forcing function is only a committee recommendation, not law.
- Cheap kill tests: read OrAIsi and Cosmetri UK pages and release notes; read the committee report; find the CTPA or Society of Cosmetic Scientists lists of assessors; run a 10-formulation extraction test on synthetic and public examples.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

## Gate log
- 2026-11-24 T-50 second pass (bureau-side): written at G0, scores blank. Weak-to-moderate survivor; strongest evidence is two bureaus' own per-product prices and 24,112 Responsible Persons.
