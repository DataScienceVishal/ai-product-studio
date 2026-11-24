# UK-EU origin evidence desk for small manufacturers

- slug: uk-eu-origin-evidence-desk
- stage: killed (T-49 validator, 2026-11-24, score 53; the Studio Lead should git mv this file to killed/)
- market and segment: UK manufacturers and food/drink producers (about 5 to 250 staff) that export to the EU under the Trade and Cooperation Agreement (TCA) and must prove origin from their bill of materials (BOM) and suppliers' declarations. Seller is a UK business.
- one-line pitch: Upload the BOM and supplier invoices; the desk maps each part to a commodity code, finds the TCA product-specific rule, runs the tariff-shift or non-originating-materials test, chases and files long-term supplier declarations, and keeps a dated origin file per product that an exporter can show HMRC or a customer.

## Problem and who has it

Exporters can only claim zero tariff if each product meets its product-specific rule, and they must hold evidence (supplier declarations for components, valid for set periods and withdrawn when they stop being true). The accuracy burden sits with the exporter, not the broker. Today this is done in spreadsheets, a paid workbook, a consultant's day, or enterprise trade-preference software (AEB, MIC, SAP GTS, DBH, Ecovium). Job: product-by-product origin determination plus a supplier-declaration register, re-run whenever a BOM line, supplier or price changes. Scope is administrative evidence, not customs or legal advice; the exporter signs the origin statement.

## Cheap kill test (done first, 2026-11-24)

Searched for an SMB or self-serve tool doing the same job. Found enterprise or demo-led vendors only; one free official tool (EU ROSA, which is a rule lookup, not a BOM test); a paid workbook; consultancy days. No self-serve SME BOM-to-origin-and-declaration tool found in three searches. Not proof of absence: iCustoms (below) is demo-led and the strongest threat.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.aeb.com/en/origin-preferences (fetched) | 2026-11-24 | AEB origin-preference software: request quote only, no price, only named customer is "a large European building paints manufacturer" (51,353 materials, 1,902 supplier declarations). Enterprise positioning. |
| https://www.aeb.com/en/supplier-declaration-exchange/ (search summary) | 2026-11-24 | Separate AEB product for supplier-declaration exchange with portal and reminders; tiers sized by material count (Business tier from 50,000 materials), price on request. |
| https://www.mic-cust.com/products-services/trade-compliance-software/free-trade-agreement-management/ and https://www.sap.com/uk/products/scm/partners/altea-up-srl-origine-preferenziale-e-made-in-manager.html (search summaries) | 2026-11-24 | MIC, DBH, Ecovium and SAP GTS all sell origin calculation and supplier-declaration solicitation; no public prices. |
| https://www.icustoms.ai/blogs/rules-of-origin-uk-product-specific-rules-and-tca-guide/ (fetched) | 2026-11-24 | iCustoms has a Rules of Origin module: maps commodity code to TCA rule, takes BOM with HS heading and origin per component, runs CTH/CTSH/MaxNOM test, keeps the calculation as evidence. Call to action is a demo booking, no price. |
| https://www.softwareadvice.com/scm/icustoms-profile (search summary) | 2026-11-24 | Aggregator lists iCustoms "Basic" at £1,000 a month; vendor page not found, SaaSworthy says quote-based (last updated 2022). Treat as unverified. |
| https://www.gov.uk/guidance/using-a-suppliers-declaration-to-support-a-proof-of-origin (search summary) | 2026-11-24 | Long-term supplier declarations cover many consignments only while the origin stays the same; the supplier must tell the buyer immediately if one stops being valid. Creates a standing tracking duty. |
| https://www.gov.uk/guidance/general-rules-to-determine-the-origin-your-products-for-trade-between-the-uk-and-eu (search summary) | 2026-11-24 | Official rule basis for the test; the applicable rule is found by HS heading in the TCA annex. |
| https://www.gov.wales/sites/default/files/statistics-and-research/2023-03/rules-of-origin-exploratory-research-with-businesses.pdf (search summary only; PDF not readable) | 2026-11-24 | Welsh Government-commissioned study says lack of awareness and guidance disproportionately affects smaller companies (qualitative). Pain signal; no proportions. |
| HMRC "Estimating Customs Costs and Burdens" via https://assets.publishing.service.gov.uk/media/684bf705df3ce2ce31e3f956/Estimating_Customs_Costs_and_Burdens.odt (search summary) | 2026-11-24 | 42% of importers aware of rules of origin say they have had to supply proof of origin to a supplier. Importers, not exporters; weak. |
| https://www.icaew.com/insights/viewpoints-on-the-news/2025/nov-2025/itw-how-to-nail-customs-compliance-as-an-sme (search summary) | 2026-11-24 | SME customs compliance commentary; says the broker often submits declarations without checking, so accuracy falls on the SME. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Spreadsheet built from the BOM | Staff hours, unpriced | Manual rule lookup; no declaration chasing; breaks when suppliers change |
| goexporting.com Rules of Origin guide and workbook (https://goexporting.com/rules-of-origin-guide-workbook/, fetched) | Price not shown on page | Static workbook; calculates MaxNOM share; no supplier workflow or evidence file; 2020-21 era rules to be checked |
| EU ROSA (free, search summary) | Free | Rule lookup, not a BOM test or evidence file; EU-side framing |
| Export.org.uk "1 day rules of origin checker" consultancy (https://www.export.org.uk/store/products/consultancy-1-day-rules-of-origin-checker/, search summary) | From £1,462.50 + VAT per day | One-off; covers a handful of products |
| Business West international trade consultancy (https://www.businesswest.co.uk/export/international-trade-consultancy, search summary) | £120 per hour members, £180 non-members, + VAT; £1,000 to £1,250 + VAT per day for 8+ hours | One-off; consultant gathers data on site |
| iCustoms Rules of Origin module (above) | Unverified £1,000 a month (aggregator) | Demo-led; built for broker and trader workflows; SME fit unknown |
| AEB, MIC, SAP GTS, DBH, Ecovium | Price on request; AEB tiers start at 50,000 materials | Enterprise ERP-scale |

## Why AI is essential (and the moat)

Honest view: the test itself (find the rule, compute the share) is deterministic, and iCustoms already does it. AI is needed for the messy front half: reading supplier invoices, spec sheets and supplier declarations in many layouts; matching free-text part names to commodity codes with a confidence flag; drafting and chasing supplier declaration requests; and spotting that a supplier's declaration has lapsed or contradicts the BOM. Candidate moat: SME price and onboarding (self-serve, per-product pricing), an evidence file in a form HMRC and EU customers accept, and a declaration inbox that works by email for small suppliers. None of that is a month-proof gap if iCustoms or AEB chose to go down-market; the validator must test that.

## Rough build plan and Azure cost

- Inputs: BOM CSV or Excel export, supplier invoices and declarations as PDF.
- Data: UK Trade Tariff (public API) for commodity codes; TCA product-specific rules from the published treaty annex (confirm licence and currency before use; gov.uk guidance is OGL, the annex text licence needs checking); customer's own BOM and supplier documents. No scraping.
- Pipeline: extraction (LLM with schema, human review queue), code suggestion with confidence, deterministic rule engine for CTH, CTSH, MaxNOM and tolerance, evidence file as PDF, supplier-declaration register with expiry reminders by email.
- Demo with synthetic data: a synthetic BOM and invented supplier declarations for two fictional products (a food product and a metal assembly) run against the real published rules. Fully demoable without a paid service; email chasing can be mocked.
- Azure estimate: not costed. Small: Container Apps, Postgres, Blob, one extraction model call per document. Likely under £50 a month at demo load; confirm against the $80 credit.

## Risks, and what would prove this wrong

- Competition: iCustoms module exists and a broker or ERP could add a self-serve tier. Proof of wrong: iCustoms or another vendor shows a public SME price below about £150 a month with BOM upload.
- Pay: only consultancy day rates found; no software price paid by an SME. Need evidence that exporters re-do this repeatedly (new products, supplier changes) rather than once.
- Reach: no count of UK exporters who claim TCA preference from their own origin determination. Needs HMRC or ONS counts (public).
- Risk: a wrong origin claim is the exporter's liability; positioning must be "evidence and calculation for the exporter to sign", not advice.
- Forcing function is weak: TCA is five years old; check whether the UK-EU reset or Pan-Euro-Mediterranean (PEM) changes create a re-assessment wave (gov.uk PEM call for evidence).
- Cross-check against killed ideas: customs-entry-prep and uk-export-classification-workbench lost to free AI drafting tools and existing vendors; this idea shares the commodity-code step.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|
| 11 | 8 | 7 | 6 | 10 | 4 | 7 | 53 |

## Validator, round 12 (T-49, 2026-11-24)

**Verdict: KILL (53/100, first attempt, ceiling about 62).** There is no red flag. The idea is killed because no realistic evidence gets it to 70.

| Line | Score | Why |
|---|---|---|
| Pain /20 | 11 | The pain is real and it recurs: a supplier or BOM change forces a new assessment (gov.uk), and declarations must be held when the proof is issued, with retrospective requests possible. The independent signals are qualitative only: the Welsh Government study (no proportions), a World Customs Journal paper saying origin compliance is "very costly... especially for smaller companies", and ICAEW commentary. None of them says how often or how many hours. The HMRC burdens figure covers importers. No job ads were found. |
| Pay /20 | 8 | The only SME-side prices are one-off consultancy (Export.org.uk from £1,462.50 + VAT a day; Business West £120-£180 an hour). Chambers also sell per-invoice origin validation (Business West Genesis, launched July 2024, price not shown). Enterprise software prices are on request, and iCustoms' £1,000 a month is still unverified, from an aggregator. Nobody shows an SME paying a subscription for this. One-off consultant days are evidence against a subscription. |
| AI /15 | 7 | The core is a deterministic rule engine (CTH, CTSH, MaxNOM, tolerance). The AI part is reading supplier documents and suggesting HS codes, and AI classification is already sold (iCustoms lists iClassification; the killed export-classification idea found Trademo and others). A free chatbot with the TCA annex is a credible substitute for one product at a time. |
| Reach /10 | 6 | Chambers of commerce, the Institute of Export, Make UK and the FDF are findable. But the chambers are themselves the competing channel (consultancy and Genesis), and no count of SME exporters who claim TCA preference was found. |
| Build /15 | 10 | A synthetic demo is possible. But a correct rule engine for TCA Annex 3 across chapters, with alternatives, tolerance and cumulation, is hard to get right in four weeks, and a wrong answer is a false origin claim. A narrow set of chapters would be needed. The cost fits the $80 credit. |
| Competition /10 | 4 | iCustoms has a TCA Rules of Origin module (BOM, CTH/CTSH/MaxNOM, kept as evidence). Its homepage targets importers, exporters and forwarders and has a "Start Now" register button, so it is not enterprise-only. The free GOV.UK trade tariff "rules of origin" check and EU ROSA (which covers the TCA) do the per-product rule test. AEB, MIC, SAP GTS, DBH and Ecovium cover the declaration register at scale. The only gap left is a cheap SME declaration register plus BOM upload, which iCustoms could ship in a month. |
| Risk /10 | 7 | No personal data. A wrong claim is the exporter's liability and leads to post-clearance duty demands, so the product carries real reputational risk even when positioned as evidence rather than advice. |

**Why killed.** The scout's "enterprise only" premise does not hold. iCustoms already sells the same BOM-to-TCA test to SMEs and forwarders. The per-product rule test is free on GOV.UK and EU ROSA. Chambers of commerce, which are the natural channel, sell origin validation and consultant days themselves. What is left is a supplier-declaration register with a deterministic core. Its AI is document extraction, which incumbents already ship, and its only Pay evidence is one-off consultancy. There is no forcing function: the TCA dates from 2021, and the PEM and reset changes have no confirmed re-assessment date for UK-EU trade.

**Lessons.** "Enterprise-only" has to be tested against the mid-market vendor's homepage (look for a register or "Start Now" button) and against free government tools, not only the vendor's article. Chambers of commerce are competitors in trade-document jobs, not just a channel. Consultant day rates show the pain but argue against a subscription.

**What would revive it.** A dated UK-EU change that forces every exporter to reassess origin, such as the UK joining PEM with diagonal cumulation for UK-EU trade under a set date. Or a public SME price from iCustoms or a rival above about £300 a month showing weak declaration handling. Plus job ads showing staff hours spent chasing supplier declarations.

Evidence, all accessed 2026-11-24:
- https://www.icustoms.ai/ (fetched: importers, exporters and forwarders; "Start Now" register; iClassification, iCalculator; no prices). https://www.icustoms.ai/pricing returned 404.
- https://www.icustoms.ai/blogs/rules-of-origin-uk-product-specific-rules-and-tca-guide/ (scout fetch: Rules of Origin module).
- https://www.businesswest.co.uk/blog/blog-posts/exciting-news-genesis-launching-on-1st-july/ (fetched: Genesis origin validation tool, article dated May 2024, no price).
- https://www.gov.uk/guidance/sending-goods-to-an-overseas-customer-using-rules-of-origin (search summary: the trade tariff tool's "rules of origin" option checks whether goods meet the rules; a supplier or part change can change origin).
- https://trade.ec.europa.eu/access-to-markets/en/content/presenting-rosa (search summary: free ROSA, covers the EU-UK TCA).
- https://www.gov.uk/guidance/using-a-suppliers-declaration-to-support-a-proof-of-origin (search summary: declaration timing, retrospective requests).
- https://www.worldcustomsjournal.org/article/144236 (search summary: origin compliance costly for smaller firms; automation via ERP and long-term declarations).
- https://www.aeb.com/en/origin-preferences (enterprise tiers, price on request).
- https://www.gov.uk/government/calls-for-evidence/pan-euro-mediterranean-convention-on-rules-of-origin-pem/annex-a-rules-of-origin-and-pem-explainer-web-accessible-version (search summary: PEM explainer; no dated UK-EU re-assessment trigger found).
- Freight forwarder and broker bundling: the search found no published origin-check fee. Brokers quote per declaration, and the exporter keeps legal responsibility (https://www.gov.uk/guidance/check-what-you-need-to-consider-before-getting-someone-to-deal-with-customs-for-you, search summary). Not a cheap bundled substitute, but not a buyer of software either.
- Not reached: the trade-tariff.service.gov.uk rules-of-origin pages (403).

## Gate log
- 2026-11-24 T-49 scout round 12: written at G0. Scores left for the validator.
- 2026-11-24 T-49 validator: KILL, 53/100 (Pain 11, Pay 8, AI 7, Reach 6, Build 10, Competition 4, Risk 7). The idea is not enterprise-only: iCustoms sells the TCA module to SMEs and forwarders, the rule test is free on GOV.UK and ROSA, chambers sell validation, and the only Pay evidence is one-off consultancy. Ceiling about 62.
