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
| 12 | 9 | 10 | 2 | 10 | 5 | 7 | 55 |

**Verdict: REVISE** (55, no red flag). (validator, 2026-11-23)

### Validator notes (2026-11-23)

Spot-checks
- Tata Consumer (Storyboard18, 8 Oct 2025): the federation alleges damage claims pending for more than 15 months, with no amounts given. The article describes delay and non-payment, not a calculation error.
- Colgate (Angel One, 8 May 2025): credit notes were issued without GST, and distributors now face GST demands of about Rs 200 crore (the federation's figure). That is a tax-treatment dispute, not a maths error.
- Terra Insight, a brand-side vendor (25 June 2026), says more than half of stuck slab claims arise because the brand counts primary sales while the distributor counts secondary sales. It expects these disputes to be settled on the brand's figures. So even a correct distributor-side calculation can go unpaid.

Falsification
- Brand-side DMS already computes and settles claims:
  - Botree DMS has workflow claims and claim top sheets.
  - Botree MyDMS (Oct 2024, used by Nestle) shows multi-company distributors their company schemes and credit notes.
  - A Havells scheme document says a 3% scheme is "settled monthly via credit note to the distributor, based on DMS sales" (snippet).
  - Also in play: Eazy DMS (Tally-integrated, "manage distributor's claims"), ClaimDS (an SMB claims and rebates tool on Product Hunt, no price), and Excel plus an accountant.
- The structural gap is real. Brands pay the DMS vendors, so those vendors won't build tools that help distributors dispute their own customers. That is the defensible angle.
- Copyable in a month: brand DMS vendors could add LLM circular parsing for brands. An independent distributor-side check is unlikely from them.
- Why buyers won't pay or switch:
  - Margins are under pressure (the federation's margin-support calls, June 2026).
  - Distributors fear antagonising brands.
  - A correct claim pack doesn't force payment.
- Regulatory traps:
  - GST treatment of credit notes and input tax credit is the live issue, so the product must stay a calculator and evidence pack and never give tax advice.
  - Distributor agreements may make circulars confidential, so flag for legal review before users upload them (unverified).

Data red flag: could synthetic or public data credibly demo the value? Partly yes, and enough to clear the flag for now.
- Real circulars are public in at least one channel business. Havells publishes scheme decks openly. I read its 37-page "July Promotional Schemes" PDF (July 2025), which is mostly images and tables. It contains:
  - credit notes at 3.5%, plus a 3% extra payout on named lines;
  - free goods ("27 + 3 pcs");
  - conditional slabs ("2% (on monthly sale > 2 lakhs)");
  - per-invoice conditions ("Rs 10/pc on purchase of 100 Pc ... in single invoice", "master packs only").
- That is exactly the extraction problem, and it can be measured on real documents. It is electricals rather than FMCG, but the structure is the same. I found no public HUL, Dabur, ITC, Marico or Emami circular.
- The reconciliation maths (what is owed, what was claimed, which credit notes arrived, how old each claim is) is deterministic and demos credibly on synthetic Tally exports.
- Public data can't show whether a computed shortfall actually gets paid. That counts against pain and willingness to pay, not as the red flag.
- Check robots.txt and the site terms before downloading the Havells files, and take only a small evaluation set.

Studio limits
- Reach scores 2. Distributors are traditional, relationship-led and served through Tally partners, and a UK-based seller has no way in. AICPDF gathers many of them in one place, but it is a lobby group, not a sales channel.
- The build fits four weeks for TallyPrime exports plus 3 or 4 scheme types. Vision extraction costs more tokens but fits the budget with caching. No paid services are needed.

What would change my mind
1. Public evidence that a meaningful share of distributor shortfalls is computational (mis-applied slabs, missed free goods, credit notes that don't match), not only commercial or tax disputes. Trade press, federation statements or vendor case studies with rupee figures would do.
2. An evaluation set of 20+ real public circulars from 3+ brands, with extraction accuracy of 90% or better after one confirmation pass on gpt-5-mini, within the token budget.
3. Any distributor-side price point: a distributor paying for claim software or a claims consultant, by fee or by percentage recovered. Public pricing for ClaimDS or Eazy DMS would count.
4. A route to distributors for a UK-based seller (a Tally partner, an association or a reseller). Without this, reach limits the score to the low 60s.

Sources checked (accessed 2026-11-23)
- https://storyboard18.com/how-it-works/tata-consumer-products-distributors-allege-mismanagement-call-for-non-cooperation-movement-82179.htm
- https://www.angelone.in/news/colgate-distributors-halt-purchases-maharashtra-may-12
- https://www.terra-insight.com/insights/slab-discount-distributor-claim-recovery-fmcg/
- https://havellspowerplus.havells.com/NotificationUpload/295_flashAttachment.pdf (read directly)
- https://www.trustradius.com/products/botree-dms/details (search summary)
- https://www.theweek.in/wire-updates/business/2024/10/23/dcm35-botree-software-international-pvt.-limited.html
- https://www.slideshare.net/eazyerp/eazy-dms-distributor-management-software (search summary)
- https://www.producthunt.com/p/claimds-b2b-rebates-tpm-claims-for-smb/what-faster-claim-settlement-is-worth-claims-cash-and-working-capital-2
- https://www.business-standard.com/industry/news/experts-flag-tax-credit-blockage-for-fmcg-distributors-despite-gst-relief-125092800121_1.html (search summary)
- https://businesstoday.in/india/story/give-us-margin-support-or-risk-rural-stockouts-distributors-warn-indias-fmcg-giants-535639-2026-06-08 (search summary)

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 55 | Strongest AI angle in this batch and testable on real public circulars, but the evidence says stuck claims are mostly commercial and tax disputes rather than maths, there is no distributor-side price point yet, and a UK-based seller can't reach Indian distributors.
