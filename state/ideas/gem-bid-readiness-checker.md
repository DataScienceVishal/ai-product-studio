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
| 10 | 11 | 7 | 3 | 12 | 3 | 7 | 53 |

**Verdict: REVISE** (53, no red flag). (validator, 2026-11-23)

### Validator notes (2026-11-23)

Spot-checks
- The segment holds. More than 11 lakh MSEs are registered, and they won over 51 lakh orders worth Rs 2.36 lakh crore in FY26 (PIB factsheet; GeM CEO, April 2026). MSEs took 47.1% of FY26 GMV (Devdiscourse).
- GeM bids are shorter and more structured than the pitch implies. I read a public 2026 GeM bid (GEM/2026/B/7203534, 7 pages, Hindi and English):
  - It has fixed fields for "Document required from seller": experience criteria, past performance, bidder turnover, certificate requested in ATC, OEM authorisation and OEM turnover.
  - It also has fixed fields for minimum turnover, OEM turnover, years of experience, MSE relaxation, EMD amount, ePBG, and MSE and MII preference.
  - After those come free-text "Buyer Added Bid Specific Terms and Conditions" and linked specification and GTC files. The AI work is in that buyer-added text (ATC), the linked specifications and the corrigenda.
- MSE status is checked through GeM's link to the Udyam database (GeM training material; Parliament answer, March 2025). So "expired MSE certificate" is less of a failure mode than this file says. The buyer still grants the EMD exemption bid by bid.

Falsification
- Competitors:
  - Tenders Agent: a free plan with 3 AI summaries a month, then ₹2,999 to ₹29,999 a year with AI eligibility checks (Capterra and GetApp).
  - BidShakti: eligibility checks, Go/No-Go and a bid pack. Listed prices conflict, from USD 2 to 49 a month.
  - Zelmier: covers 250+ portals.
  - Tender247: agentic AI and a national celebrity campaign (Oct 2026), so it is well funded.
- Cheapest substitute: paste the bid PDF into a general AI chatbot and ask for the checklist, or read the "Document required from seller" field on page 2 of every bid.
- Copyable in a month: a document vault with expiry dates and a gap check against the criteria that incumbents already extract.
- Why buyers won't switch: small sellers often buy a bundled consultant who handles registration, catalogue and bidding (Fiverr and IndiaMART listings). A checker covers only part of that job.
- Neither the scout nor I found public data on how often bids are rejected.
- Regulatory traps:
  - The output must not read as legal advice on eligibility.
  - A false "ready" costs a bid, so findings need clause citations and human sign-off.
  - Company folders can hold directors' Aadhaar and PAN, which the vault must mask or reject.
  - Bids name consignee officers, which is personal data.

Data red flag: none. Buyer organisations host public GeM bid PDFs (a Delhi department, IIT Kanpur, NITI Aayog, GIC Re), so the studio can build a real evaluation set without automating any portal. Download a small set by hand from sites that allow it, and stay off GeM's bidplus site (its robots.txt returned 503).

Studio limits
- The build is the easiest in this batch: RAG plus OCR on the default stack, and cheap on tokens.
- Reach scores 3. GeM sellers are reachable online and many work in English, but a UK-based seller has no presence there. With rivals charging from ₹2,999 a year, paid customer acquisition is hard to make pay.

What would change my mind
1. Public data on the share of GeM bids rejected at technical evaluation for document reasons, from CAG or GeM reports, RTI disclosures, or counts of High Court writs.
2. Public docs, demo videos or reviews showing that Tenders Agent, BidShakti and Tender247 don't check the bidder's own documents (validity dates, turnover against criteria, OEM authorisation scope, corrigenda). No sign-ups, because creating accounts is on the ask-first list.
3. A head-to-head on 30+ public bids with their ATC and corrigenda, where the checker finds mandatory conditions that a plain general-LLM prompt misses (95% or better recall on mandatory items).
4. A route to GeM sellers for a UK-based seller. Without items 2 and 3, competition and AI advantage stay low and the score can't get near 70.

Sources checked (accessed 2026-11-23)
- https://hjbhabhaiti.delhi.gov.in/sites/default/files/hjbhabhaiti/tender/gem-bidding-8945415.pdf (read directly)
- https://pib.gov.in/FactsheetDetails.aspx?Id=150812 (search summary)
- https://www.devdiscourse.com/article/law-order/3863894-gem-surpasses-184-lakh-crore-gmv-emerges-as-backbone-of-indias-digital-public-procurement-ecosystem (search summary)
- https://lms.gem.gov.in/resources/upload/webinar_archive/archived_webinar_4Mf5_5VRu.pdf (search summary: MSE checks through Udyam)
- https://www.commerce.gov.in/wp-content/uploads/2025/03/LS-USQ-No.2860-dated.-18.03.2025.pdf (search summary)
- https://www.capterra.com/p/10056461/Tenders-Agent/pricing/ and https://www.getapp.com/all-software/a/tenders-agent/ (search summaries; pages returned 403)
- https://sourceforge.net/software/product/BidShakti/ and https://www.saasworthy.com/product/bidshakti/pricing (prices conflict)
- https://india.entrepreneur.com/?p=100307 (Tender247, Oct 2026)
- https://yourstory.com/ai-story/government-tender-bidding-zelmier-ai-procurement (search summary)

## Gate log
- 2026-11-23: G0 spotted by scout.
- 2026-11-23 | validator | G0→G1 | REVISE 53 | Easy to build on public bid PDFs, but GeM bids are short and largely structured, several AI tender tools already sell eligibility checks at ₹2,999 to ₹29,999 a year, a general chatbot is a near-free substitute, and a UK-based seller can't reach Indian MSEs.
