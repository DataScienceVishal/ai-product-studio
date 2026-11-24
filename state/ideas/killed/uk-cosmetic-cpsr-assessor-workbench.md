# UK cosmetic CPSR assessor workbench

- slug: uk-cosmetic-cpsr-assessor-workbench
- stage: KILLED (validator, T-50, 2026-11-24, score 47)
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
| 11 | 11 | 7 | 4 | 7 | 2 | 5 | **47** |

Validator checks (T-50, 2026-11-24; vendor pages are marketing, so their claims are unverified):
- **Pain 11.** The per-product fees on bureau pages (£220-£465, "from £70") show that a CPSR costs money and that assessor labour is the bureau's margin. Two problems: there are no complaints, job ads or reviews about the drafting work itself, and the price war cuts the hours a tool can save on each report. CTPA's notice on non-compliant and possibly fraudulent UK CPSRs (https://www.ctpa.org.uk/news/important-non-compliant-cpsrs-in-the-uk-7866, search summary) shows quality problems, not a bureau that wants a tool.
- **Pay 11.** Brands pay bureaus per report, but the bureau's own spend on software sets the ceiling. Third-party listings put Cosmetri Product Manager at €49 a user a month (Capterra, https://www.capterra.com/p/233732/Cosmetri-Product-Manager/) and $58-$345 a month (SoftwareSuggest, https://www.softwaresuggest.com/cosmetri). Both are search summaries, they disagree, and neither is from the vendor. The incumbents and OrAIsi publish no prices.
- **AI 7.** Reading supplier SDS, specs and CoAs is real AI work. The MoS (NOAEL or PoD divided by SED) is arithmetic. The incumbents' moat is a curated toxicology database (Ecomundo says 4,000+ profiles; Coptis Tox), not the model. The Part B reasoning has to stay with the assessor, so the AI share of what the buyer values is small.
- **Reach 4.** There is no public register or count of UK qualified safety assessors (CTPA and gov.uk searches found none). The only routes are the CTPA and Society of Cosmetic Scientists networks, DGK certificate courses and freelancers on Fiverr and Upwork, and none of them gives a count.
- **Build 7.** The stack is standard and the Azure cost is fine, but a credible MoS needs a NOAEL or PoD for every ingredient. SCCS opinions, CosIng and CIR reports are free, but they cover a minority of INCI names. ECHA dossier data is uneven and its reuse terms need checking. The studio can't get a lawful, comprehensive free toxicology source in four weeks, and a demo restricted to SCCS-covered ingredients is a narrow one. This is close to the data red flag but doesn't reach it.
- **Competition 2.** The same job is already sold, in some cases to the same buyer:
  - **OrAIsi** (fetched): AI for "safety assessors, regulatory affairs managers, and cosmetic manufacturers". It reads formulas, supplier lists and SDS "in any source format", calculates SED, NOAEL and MoS per ingredient and route, and assembles the PIF "with Part A and Part B structured for audit". EU only, with no UK mention, but UK Annexes mostly mirror the EU's, so UK coverage is a content update, not a moat.
  - **Ecomundo COSMETIC Factory** (fetched): "Automate your MoS calculations in one click", PIF smart-fill templates, a toxicology profile database, AI modules for document conformity (EcoMarket) and document management (EcoGed), and EU/UK compliance with a London office.
  - **Coptis Tox / Coptis Lab** (vendor page, search summary): generates toxicology profiles for whole formulas automatically and calculates MoS from validated ingredient data.
  - **Cosmetri (Registrar Corp)**: assessors complete and sign Parts A and B inside the PIF.
  - **Also:** ToxTool (Cosmetica Italia), ChemComply.io (CPSR and PIF platform) and Biorius MyApps.
  - **Left over:** UK wording and per-bureau style memory, which any of these can copy within a month.
- **Risk 5.** This is not off-limits. A CPSR is a product-safety regulatory deliverable, not medical or legal advice to a person, and the signature and liability stay with the qualified assessor. It is health-adjacent, though: consumer toxicology, where a wrong MoS harms end users. A drafting tool also lowers the cost of the "signature mill" reports CTPA warns about. No personal data.

**Verdict: KILL (47, first attempt; ceiling about 55).**

## Kill reason
The workbench is already a product category. OrAIsi sells the same pitch (read supplier documents and SDS, compute SED, NOAEL and MoS, assemble Part A and B for the assessor to sign) to the same buyer, and Ecomundo, Coptis Tox and Cosmetri already automate MoS, toxicology profiles and assessor sign-off. Their real moat is curated ingredient toxicology data, which the studio can't lawfully assemble from free sources in four weeks. The only gap left is UK wording, and EU vendors can copy that in a month (the UK Annexes largely mirror the EU's). The buyer pool is uncountable (no assessor register), and a per-report price war from £70 caps what a bureau would pay for a seat. The idea is admin, not medical advice, so it isn't off-limits, but it is health-adjacent and could help low-quality report mills.

## Lessons
- In regulated-document niches, the "AI drafts, professional signs" pattern is already the default pitch of every vertical vendor. Read the comparison table on the nearest AI vendor's page: OrAIsi named Coptis, Ecomundo and Cosmedesk, which settled Competition in one fetch.
- When the deterministic core depends on a reference dataset (toxicology values), the data owner is the incumbent. Check who curates the data, and its licence, before scoring AI and Build.
- A bureau price war is evidence against Pay for a bureau-side tool, not for it.

## What would revive it
A lawful, broad and free (or cheaply licensable, with approval) per-ingredient toxicology source, plus evidence that UK bureaus avoid OrAIsi, Ecomundo and Coptis for a reason those vendors can't fix quickly, such as price (a published price above about £300 a seat a month) or UK-specific failures. Or a UK licensing regime for safety assessors (the committee recommendation) that creates new required records the incumbents don't produce.

## Gate log
- 2026-11-24 T-50 second pass (bureau-side): written at G0, scores blank. Weak-to-moderate survivor; strongest evidence is two bureaus' own per-product prices and 24,112 Responsible Persons.
- 2026-11-24 T-50 validator: KILL, 47/100, first attempt (Pain 11, Pay 11, AI 7, Reach 4, Build 7, Competition 2, Risk 5). OrAIsi sells the same assessor workbench (SDS reading, SED/NOAEL/MoS, Part A/B assembly); Ecomundo, Coptis Tox and Cosmetri already automate MoS, tox profiles and assessor sign-off; tox data is the incumbents' moat; no assessor count. Not off-limits (product-safety compliance, not medical advice; assessor keeps liability), but health-adjacent. Ceiling about 55.
