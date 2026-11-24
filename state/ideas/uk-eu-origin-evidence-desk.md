# UK-EU origin evidence desk for small manufacturers

- slug: uk-eu-origin-evidence-desk
- stage: G0
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
|  |  |  |  |  |  |  |  |

## Gate log
- 2026-11-24 T-49 scout round 12: written at G0. Scores left for the validator.
