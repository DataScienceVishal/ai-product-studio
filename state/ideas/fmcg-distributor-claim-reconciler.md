# FMCG distributor scheme-claim reconciler (India)

- slug: fmcg-distributor-claim-reconciler
- stage: G0
- market and segment: India. Small and mid-size FMCG distributors and stockists (one to several brands, typically running Tally, Busy or Marg for billing) who must claim trade-scheme reimbursements, damage claims and price-difference credits from brands. AICPDF says it represents 4 to 4.5 lakh such distributors.
- one-line pitch: Forward the brand's scheme circulars (PDF, Excel, WhatsApp images) and export your sales register. The tool reads each scheme, computes what you are owed line by line, matches it against the credit notes you actually received, and produces a claim pack plus a list of shortfalls and ageing claims.

## Problem and who has it

Brands run many overlapping consumer and trade schemes (slab discounts, free goods, display incentives) and announce them in circulars. Distributors pass these on to retailers at the time of sale, then claim reimbursement from the brand. Claims are computed by hand from billing data, submitted, and often settled late, partly or not at all, then offset against credit notes. Damage and expiry claims age for months. Distributors' working capital is locked in unsettled claims, and disputes become public fights between AICPDF and brands. This is a messy-data reconciliation problem (unstructured scheme terms × invoice lines × credit notes) plus document understanding, and it is GST-adjacent (credit notes) without being bookkeeping or tax filing.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://storyboard18.com/how-it-works/tata-consumer-products-distributors-allege-mismanagement-call-for-non-cooperation-movement-82179.htm | 2026-11-23 | (8 Oct 2025) Distributors of Tata Consumer Products allege damage settlement claims pending for more than 15 months and blocked investments, and call for non-cooperation. |
| https://www.angelone.in/news/colgate-distributors-halt-purchases-maharashtra-may-12 | 2026-11-23 | (May 2025) Maharashtra distributors suspend Colgate purchases. Trade credit notes issued without GST led to GST demands of "around Rs 200 crore" on distributors. Mis-documented scheme credit notes become real liabilities. |
| Search-result summary of https://cwv.yourstory.com/2024/11/honasa-clarifies-quantum-unsold-inventory-distributors-body (host not reachable from this session) | 2026-11-23 | (Nov 2024) AICPDF cited about Rs 50 crore of distributor claims against Honasa (Mamaearth). The company said scheme claims pending were Rs 4.73 crore as of 30 Sept 2024. The two sides' numbers differ by 10x, which is exactly a reconciliation failure. Not verified on the page itself. |
| https://jobs.weekday.works/finance-executive-contract-role-at-monin-india-wkdy4wicah (from search summary) | 2026-11-23 | A brand hires staff to "verify and process distributor claims" and "reconcile claims with the sales register". Both sides spend labour on the same matching. |
| https://tallysolutions.com/business-guides/tallyprime-for-fmcg-distributors/ (from search) | 2026-11-23 | Tally publishes a guide on scheme management for FMCG distributors in TallyPrime. Shows schemes are run inside generic billing software and claim computation is left to the distributor. Page not opened. |
| Search-result summary of https://www.outlookbusiness.com/news/fmcg-distributors-association-warns-of-protests-over-margins | 2026-11-23 | AICPDF represents over 4.5 lakh distributors across 25 states (press-reported, no official count). Shows segment size and a reachable association. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| SalesOn DMS/sales app (https://saleson.co.in/pricing.html) | Rs 250 per user per month (Pro) or Rs 400 (Enterprise) monthly. Rs 2,500 / 4,000 per user per year. Minimum 2 users. | Order-taking and distribution management. Scheme-claim computation from brand circulars is not advertised. |
| Brand-side DMS (Bizom, Channel Konnect), per https://www.aiaccountant.com/blog/distribution-management-software-india | Rs 1,000 to 5,000 per distributor per month (blog estimate, self-contradictory, unverified) | Paid for and configured by the brand. The distributor sees the brand's view of claims, not an independent check. |
| Marg ERP (aggregator figures via search, e.g. https://www.techjockey.com/detail/margerp-9) | Roughly Rs 8,100 to 26,000 one-time licence by edition, plus AMC about Rs 2,000 to 5,000 a year (conflicting reseller figures) | Billing with scheme fields. Does not read circulars or reconcile received credits against entitlement. |
| Claims staff | AmbitionBox "Claims Executive" Rs 1.4 to 4.5 lakh a year, all industries (https://ambitionbox.com/profile/claims-executive-salary, from search) | Manual Excel. Bigger distributors employ one, small ones do it themselves. |

## Why AI is essential (and the moat)

- Scheme circulars are unstructured: PDFs, Excel sheets, WhatsApp images, often bilingual, with conditions like "buy 10 cases of SKU group A between dates, get 2% on invoice value, max per outlet". An LLM extracts these into machine-checkable rules. A human confirms them once, and then rules run deterministically on every invoice line. That is the RAG/agent plus data-engineering combination.
- Reconciliation engine: entitlement vs claimed vs credit notes received, with ageing, partial-settlement detection and duplicate checks.
- Moat: a growing library of parsed scheme templates per brand (brands reuse formats), and Tally/Busy/Marg export adapters. The distributor side is underserved because DMS vendors sell to brands.

## Rough build plan and Azure cost

- Week 1: Import adapters for Tally/Busy/Marg sales register and credit note exports (Excel/XML), canonical invoice-line schema.
- Week 2: Scheme extraction (Azure OpenAI, structured output into a rule DSL) with a human confirmation screen. Rule engine.
- Week 3: Reconciliation and ageing reports, claim-pack generator (Excel/PDF per brand format), mock WhatsApp intake.
- Week 4: Evaluation on synthetic circulars and invoices (extraction accuracy, rupee-accurate computation tests), handover docs.
- Azure (estimate: Container Apps scale-to-zero, Blob for documents, Document Intelligence free tier or LLM vision for images, small DB): about USD 5 to 20 a month during build. Confirm in state/BUDGET.md.

## Risks, and what would prove this wrong

- Real scheme circulars are brand-confidential and not public. Realistic synthetic ones can be written, but accuracy on real ones is unproven (red-flag watch: "core value can't be shown without real customer data").
- Disputes are often commercial (the brand simply refuses), not computational. A correct claim pack may not get paid.
- Credit notes and GST treatment: the product must stay a calculator and evidence pack, with no tax advice. Flag for legal review.
- Proves it wrong: distributors say their claims are computed by the brand's DMS and the money is the dispute, not the maths; or extraction accuracy on varied circulars stays below about 90% after the confirmation step.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
