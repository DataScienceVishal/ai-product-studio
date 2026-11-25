# Round 17 scout summary (T-54, 2026-11-24)

Brief: geographic arbitrage. Find UK-proven AI-able SMB document jobs that exist under Irish, Australian, NZ or Canadian rules with no local AI tool. Time box about 15 minutes. Evidence is search-result summaries only (12 searches, 2026-11-24); no page was fetched in full, so every drop is "search evidence", not page-verified. No prompt-injection attempts seen. Nobody contacted, nothing signed up for.

## Written (0 files)
No candidate met the bar (3 pain signals, 2 prices, official count, a gap confirmed on local vendor pages). Zero is the honest result.

## Dropped at the cheap kill test (candidate, evidence, reason)
1. Australia award interpretation and underpayment audit: Employment Hero award interpretation (https://employmenthero.com/solutions/award-interpretation-software), Deputy (Xero AU listing, $5 per user a month, min $25), Payroo, Tanda, KeyPay; audit side WageSafe (April 2026 release, per-pay-cycle award check), Yellow Canary (AI compliance audit platform), McGrathNicol consulting. FWO is also exploring AI award guidance (DEWR regulatory technology roadmap proposes an API for the Modern Awards Pay Database). Intentional underpayment has been a criminal offence since 1 Jan 2025 (Xero AU guide), a real forcing function, but the space is full and a government API would commoditise it.
2. Ireland tender writing: BidReview.ai (Irish, self-service draft review, launched 2026, won an SME IT award) plus UK tools sold in Ireland (BidWriter, mytender.io, BidPal, Remporte on Capterra IE). Same loss as CleanTender.
3. Ireland rent setting under the 1 March 2026 national rent control: the RTB gives a free Rent Calculator and a free Rent Register of comparables (https://rtb.ie/rtb-rent-calculator/, https://rtb.ie/?p=55258). Landlords must attach the printouts to the notice. The government supplies the work free, and the UK equivalent (MarketRent) was already killed.
4. NZ healthy homes compliance statement: free government template, decision tool, insulation and ventilation tools (https://tenancy.govt.nz/healthy-homes/compliance-statement); the 1 July 2025 deadline has passed; the penalty is up to $500 a tenancy; only an old Tenancy.co.nz and All Clear integration was found. Deterministic form, no forcing function left, no price found.
5. Australia NatHERS: assessor software is accredited by the Administrator against AccuRate; CSIRO RapidRate (AI) and Cotality already estimate existing-home ratings; NatHERS says "user interface" tools are due in 2026 (https://nathers.gov.au/news). The scheme owner is steering this itself.
6. Ireland auto-enrolment (MyFutureFund, from 1 Jan 2026): Xero IE, Sage IE and payroll vendors build it into payroll; employers send a payroll instruction. No document job.

## Watch-list (not written: evidence too thin)
Ireland BER assessment. No third-party AI or survey-capture tool found in three searches, and Irish BER assessors must publish inside SEAI's own DEAP 4 software (https://www.seai.ie/ber/support-for-ber-assessors/deap). Volume is real: 162,799 domestic BERs in 2025 (CSO, cited by Engineers Ireland, https://www.engineersireland.ie/Engineers-Journal/More/Sponsored/the-growing-need-for-ber-assessors-in-irelands-energy-transition), a 500,000-home retrofit target by 2030 (each retrofit needs a pre- and post-works BER), and assessor fee about EUR 150-300 (Bord Gais, 2024, https://www.bordgaisenergy.ie/home/ber-certs). But I found no assessor-side pain evidence, no assessor count, no assessor software prices, and the UK proof (Specvo) was killed as Elmhurst-scheme bound. Reach for a UK business is also weak. Cheap next test: ask whether any Irish vendor (search "BER software" vendor names, Irish assessor forums, SEAI assessor member login pages) sells survey capture, and count active assessors from the SEAI register.

## Lessons for the validator and next scout
- The arbitrage thesis mostly fails because the destination market has the same incumbents as the UK (Employment Hero, Deputy, Xero and Sage local editions) and often a stronger regulator tool (RTB, Tenancy Services, NatHERS Administrator), which supplies the job free or is building it.
- Where the regulator makes the document free (RTB register, NZ template), there is no Pay.
- Search-engine summaries returned no Irish or NZ price points for any job. Pay evidence would need page fetches (bureau price lists) that this 15-minute round did not make.
- Only Ireland is plausibly reachable via a UK business; AU and NZ Reach should be scored low.
- Next, if the thesis continues: fetch the Irish BER vendor and forum pages, and test Canada (EnerGuide, provincial rules), which this round skipped.

## T-79 follow-up (2026-11-25): Ireland BER assessor desk, DROPPED (no idea file written)
Method: 4 WebFetch attempts and 6 searches, about 15 minutes. No injection attempts seen. Nobody contacted, nothing signed up for. Page-verified items are marked.

| URL | Accessed | What it shows | Page-verified |
|---|---|---|---|
| https://ndber.seai.ie/PASS/Assessors/Search.aspx | 2026-11-25 | Public assessor register, searchable by name, company, county, area; shows NO total count | yes (fetched) |
| https://www.oireachtas.ie/en/debates/question/2024-05-21/146/ | 2026-11-25 | Parliamentary answer: about 940 domestic and 225 non-domestic BER assessors (May 2024) | no (search summary only) |
| https://www.engineersireland.ie/Engineers-Journal/More/Sponsored/the-growing-need-for-ber-assessors-in-irelands-energy-transition | 2026-11-25 | CSO 162,799 domestic BERs in 2025, 5,476 non-domestic; 1.7m certs to date; 500,000-home retrofit target needs pre- and post-works BER; sponsored (training firm), no fees, no assessor count | yes (fetched) |
| https://www.seai.ie/ber/support-for-ber-assessors/deap | 2026-11-25 | DEAP page returned HTTP 403 to fetch; content from search summary only: DEAP free, anyone can run it, only registered assessors publish | no |
| https://seai.ie/sites/default/files/publications/Publishing-a-Domestic-BER.pdf | 2026-11-25 | Search summary: publishing is done wholly inside DEAP software | no |
| https://www.seai.ie/publications/Roadmap-for-DEAP-4.2.0.pdf | 2026-11-25 | Search summary: DEAP 4.2.0 produces no XML (PDF dwelling report only); only import is heat pump data from HARP. So no public pre-fill route | no |
| https://www.seai.ie/sites/default/files/2025-02/BER_QA_Audit_FAQ.pdf | 2026-11-25 | PDF fetched but text unreadable by the tool (21 pages); failure rates not obtained. Saved at /root/.claude/projects/-home-user-ai-product-studio/f8cc0a7f-9156-5ae2-b09e-56e61e18744f/tool-results/webfetch-1795594894665-x9ac4p.pdf if someone wants to extract it | partial |
| SEAI Schedule_of_fees.pdf (redirect chain, last hop not fetched) | 2026-11-25 | Fee figures not retrieved | no |

Findings against the four questions:
1. Count and volume: volume is official (162,799 in 2025). Assessor count is about 940 domestic as of May 2024 (unverified summary), so about 170 BERs per assessor a year if all are active (my estimate: 162,799 / 940; not all are active). A small pool of roughly 1,000 buyers.
2. Assessor-side pain: none found. No forum thread, no audit or disciplinary statistic, no time-per-BER figure. SEAI says only that time depends on complexity. Zero independent pain signals.
3. Tools: no third-party DEAP companion, survey-capture app or Irish version of Elmhurst, Stroma, Specvo or Quidos found in any of the 9 searches this round and last. SEAI supplies a paper/PDF/Excel survey form and guide, and photos are uploaded inside DEAP. Publishing happens only inside DEAP, and DEAP 4.2.0 has no XML output and no known import. A pre-fill therefore has no integration point: the assessor would still re-key every field into SEAI's closed tool (the gap is real, but it also removes the product's value, since a tool that only produces a filled-in PDF survey form saves little).
4. Prices: no third-party tool price, no fee figure, no one-stop-shop BER paperwork price found. The earlier EUR 150-300 consumer fee (Bord Gais 2024) is the only price. Zero tool price points.

Why dropped: 0 of 3 pain signals, 0 of 2 tool prices, assessor count only from an unverified summary, and the closed-system gap that would be our moat (no import) cannot be bridged without SEAI's cooperation. Reach is also weak (about 1,000 Irish buyers, no UK channel named). Not worth an idea file; it would score under 40.

What would revive it: SEAI announces a DEAP import/API or XML; or a forum thread or SEAI QA report shows high audit-failure rates driven by evidence/photo gaps (extract the QA FAQ PDF and the "Review of BER QA" PDF at https://www.seai.ie/home-energy/building-energy-rating-ber/support-for-ber-assessors/Review-of-BER-QA.pdf first); or a named Irish one-stop-shop firm publishes a per-BER cost. If revived, a numeric proof test would be: at least 20 public or synthetic survey photo sets, with the tool pre-filling at least 80% of DEAP Survey Form fields correctly and cutting data-entry time at least 30% against a hand-keyed baseline.
