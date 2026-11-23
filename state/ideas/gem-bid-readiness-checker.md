# GeM bid readiness checker (India)

- slug: gem-bid-readiness-checker
- stage: G0
- market and segment: India. Micro and small manufacturers and suppliers registered on the Government e-Marketplace (GeM) who bid on a few tenders a month without a dedicated bid team (e.g. regional makers of bags, furniture, lab equipment, water purifiers). GeM reports over 11 lakh registered MSE sellers.
- one-line pitch: Drop in a GeM bid document (plus corrigenda) and your company document folder. The tool extracts every eligibility condition, mandatory upload, EMD/MSE exemption rule and deadline, checks them against your documents (expiry dates, turnover, OEM authorisation, Make in India certificate), and returns a Hindi or English checklist of gaps before you submit.

## Problem and who has it

Government bid documents are long, and bids are often rejected on technicalities rather than price: missing uploads (GST, PAN, MSME/Udyam, experience certificates), expired MSE certificates for EMD exemption, ignored corrigenda, DSC problems, local-content certificates. Small suppliers either hire a tender executive, pay consultants by the hour, or do it themselves and get disqualified. Rejected bids end up in writ petitions at High Courts. The task is document-grounded checking (RAG over the bid + the company's own documents), not legal advice.

## Evidence
| Source (URL) | Accessed | What it shows |
|---|---|---|
| https://www.tendershark.com/blogs/why-your-gem-bid-gets-rejected-reasons-of-disqualification-in-government-tenders | 2026-11-23 | (May 2026) Lists 10 common GeM rejection causes. Incomplete documents are the most common, followed by spec mismatch, EMD/MSE exemption errors, ignored corrigenda, DSC issues and pricing errors. All of them can be caught by checking documents. |
| https://delhihighcourt.nic.in/app/showFileJudgment/59428102025CW162222025_144907.pdf (and related Delhi HC judgments in search) | 2026-11-23 (search summary; PDFs not opened) | Writ petitions over technical bids rejected for a Local Content (Make in India) certificate, a CA certificate and missing documents. Some bidders go to court over document rejections. |
| https://www.mncjobsindia.com/jobs/gem-executive-panipat-4100714 (from search summary) | 2026-11-23 | A bags manufacturer in Panipat hires a GeM Tender Executive at Rs 25,000 to 30,000 a month to prepare technical/financial bids per GeM requirements. Other postings (Vadodara, Bengaluru) show similar roles. Manual labour cost exists today. |
| https://www.newsonair.gov.in/gem-registers-11-lakh-mse-sellers-secures-over-%e2%82%b97-lakh-crore-in-orders (from search) | 2026-11-23 | Over 11.25 lakh MSE sellers registered on GeM (as of 30 Nov 2025). MSEs hold about 47% of FY26 GeM order value per several reports. Large reachable segment. |
| https://echai.ventures/startingup/selling-to-government/how-do-i-write-a-tender-bid-that-doesn-t-get-thrown-out-on-a-technicality (from search; not opened) | 2026-11-23 | A startup guide is devoted to bids "thrown out on a technicality". More evidence that this is a recognised pain. |

## Current alternatives and prices
| Alternative | Price | Gap |
|---|---|---|
| Tenders Agent (GetApp/Capterra listings; https://www.capterra.com/p/10056461/Tenders-Agent/pricing/ returned 403) | Free plan with 3 AI summaries a month. "Growth" plan about Rs 9,999 a year with 300 AI summaries and an AI eligibility check (GetApp snippet, conflicts with Capterra, unverified) | Summarises the tender. Not clear it checks the bidder's own documents and expiry dates. |
| BidShakti (https://www.saasworthy.com/product/bidshakti) | Freemium plus paid monthly/yearly plans, price not public | Claims Go/No-Go and bid-pack preparation. Direct AI competitor, quality unknown. |
| BidAssist (App Store https://apps.apple.com/us/app/id1374525306) | Pay per tender document USD 3.99 (in-app). Subscription prices not shown | Discovery and alerts, not compliance checking. |
| Tender consultants on IndiaMART (https://m.indiamart.com/impcat/e-tendering-services.html) | e.g. Rs 500 an hour, Rs 1,500 per "piece" (unverified listings) | Manual, variable quality. |
| In-house tender executive | Rs 25,000 to 30,000 a month (Panipat posting above) | Fixed cost. Still manual. |

## Why AI is essential (and the moat)

- RAG over long, semi-structured bid PDFs (ATC, GTC, corrigenda, BOQ) to extract conditions with clause citations, and comparing them with the bidder's document vault (OCR of certificates, expiry dates, turnover figures). Every finding links to the exact clause, and an evaluation set of real public GeM bids measures recall of mandatory conditions.
- Hindi and regional-language explanations for owner-operators.
- Moat: a curated corpus of public GeM bid documents and corrigenda (published openly by buyers, e.g. on cag.gov.in and iitk.ac.in), condition-extraction evals, and a per-supplier document vault that makes every next bid faster.

## Rough build plan and Azure cost

- Week 1: Collect 50 to 100 public GeM bid PDFs from government buyer sites that publish them (check robots/terms; download only, no portal login automation). Build a labelled eval set of conditions.
- Week 2: PDF parsing, chunking, extraction to a condition schema with citations (Azure OpenAI), plus Azure AI Search free tier or pgvector.
- Week 3: Document vault (upload certificates, OCR, expiry extraction), gap checker, checklist output in Hindi/English.
- Week 4: Eval report (recall/precision on mandatory conditions), DPDP handling for company documents (PAN, GST certs are business data, but director IDs may appear), demo.
- Azure (estimate: Container Apps scale-to-zero, Blob, AI Search free tier, LLM tokens for perhaps a few hundred long PDFs): about USD 10 to 25 a month during build, mostly tokens. Confirm in state/BUDGET.md.

## Risks, and what would prove this wrong

- Crowded: BidShakti, Tenders Agent, Zelmier (https://yourstory.com/ai-story/government-tender-bidding-zelmier-ai-procurement, from search) and others already sell AI tender analysis. The gap must be bidder-document checking and price, and the incumbents might already do it.
- Must not present output as legal advice on eligibility. Frame it as a checklist with citations and keep human sign-off.
- Proves it wrong: competitor trials show they already do document-vault gap checking well at low price, or MSE interviews show rejections are mostly price/L1 and not document gaps. No public data on rejection rates was found.

## Score (validator)
| Pain /20 | Pay /20 | AI /15 | Reach /10 | Build /15 | Competition /10 | Risk /10 | Total /100 |
|---|---|---|---|---|---|---|---|

## Gate log
- 2026-11-23: G0 spotted by scout.
