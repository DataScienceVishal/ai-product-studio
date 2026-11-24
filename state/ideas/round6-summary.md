# Round 6 scout summary (T-36, 2026-11-24)

Brief: Q-6 default A. Scout only ideas where the studio can collect the decisive evidence itself (public datasets, open APIs, regulator and ombudsman publications) and run a credible demo on public or synthetic data. Each candidate got a "<problem> software/tool 2026" and "AI <problem>" search and an add-on check. Most checks rest on search summaries; where a page was fetched the idea file says so. No injection attempts seen in fetched pages.

## Written (4 files, all draft self-scores below 70; validator to re-score)

| Slug | Pitch | Draft score | Strongest evidence | Biggest doubt |
|---|---|---|---|---|
| housing-complaint-response-qa | Checks a social landlord's draft complaint response against the statutory Code and Housing Ombudsman guidance and published decisions | 60 | Ombudsman upheld 62% of 8,783 determinations (2025-26), called Stage 2 reviews "too often inadequate"; Aareon's own page shows complaints = workflow and templates, no AI | Ombudsman decisions carry no reuse licence; system vendors can add a checker; channel unknown |
| apprenticeship-evidence-preaudit | Reads apprentice evidence packs against ILR and DfE funding rules and lists learners at clawback risk | 59 | DfE says off-the-job evidence is the main cause of funding errors; mock audits sold by Mazars and RSM; APAR CSV lists the buyers | Aptem has AI and an audit-readiness story (not fully read); learner data risk |
| mot-advisory-dealer-risk-score | Turns official MOT advisory text into a repair-risk score for used-car dealers before auction bids | 59 | DVSA bulk data under OGL lets the studio backtest the model itself; no dealer-side predictor found | Pay: no dealer tool price found; HPI and Auto Trader sit next door |
| haulier-audit-workpapers | Drafts operator-licence audit workpapers for haulage auditors from maintenance and driver records | 58 | A July 2026 Traffic Commissioner decision rejected a consultant's audit as not independent and halved the licence | Small auditor market; only dated prices |

## Dropped (16), with one-line reasons

1. Forecourt fuel pricing from the Fuel Finder open data (RL edge): EdgePetrol (1,000+ forecourts), myAutomate FuelSense, CBE, TSG, Kalibrate and OPIS PriceCast already sell it.
2. Estate agent material-information packs from public data joins: Sprift, AVRillo, iamproperty and Street already ship them.
3. Digital waste tracking and EWC classification: Defra's approved-software list and Access, Wasters and WasteMatrix cover it; carriers' duty is not yet in force.
4. HMRC penalty appeals grounded in tax tribunal decisions: pain is real (32,258 automated-penalty appeals in six months, about 62% won), but a £100 penalty and a free letter kill Pay, and it sits near legal advice.
5. AML client-file review for accountancy practices: Digita AML (AI document analysis), AMLCC (ICAEW-accredited) and IRIS cover it.
6. CQC mock inspection for home care: Access, Birdie and ShiftCare sell it, and the CQC framework is mid-change.
7. Ofsted nursery inspection prep: Ofsted's own toolkit, consultants and vendors; no decisive public data for the AI part.
8. SFI26 parcel and action finder: the government's free "Find funding for land or farms" tool shows eligibility per parcel.
9. Biodiversity net gain for small sites: Joe's Blooms (£495 to £959) is listed on Planning Portal and the statutory tools are free.
10. Product recall matching: RecallStream ($0 to $49 a month), Recalert, Shopify apps and Apify actors exist.
11. CIL liability for small developers: no developer tool found, but no price evidence and a narrow market (vendors sell to councils).
12. CITB grant claim service: no consultant price found, grants are discretionary and the provider-led route removes the claim.
13. Deposit-dispute evidence for letting agents: inventory software vendors already add AI comparison; the schemes publish only guidance.
14. HMRC letter triage for accountants: no product found, but no public data to prove value and HMRC's January 2026 AI guidance demands human review.
15. HSE enforcement-notice readiness: public register exists, but no price evidence found and H&S is bought as a bundled retainer (not verified).
16. Garage MOT-advisory upsell: Motasoft "Opportunities" and MOT Manager already do advisory follow-up (idea 3 above reframes the same data for dealers).

Not pursued without a check: social-landlord regulatory benchmarking from Regulator of Social Housing judgements and Tenant Satisfaction Measures data (likely a benchmarking-incumbent category; not searched).

## Lessons for the validator and next scout
- The one extra thing this round added is a self-run proof test per idea (labelled public decisions, seeded synthetic packs, an MOT backtest). The validator should hold each idea to its test, not to the draft score.
- All four scored 58 to 60, which matches the earlier rounds. Pay is the weakest score in every file: public sources rarely show a software price for the job, only salaries or one-off audit fees. A price-quote step (needs Vishal's OK to contact) may be the only way to lift Pay.
- Reach is capped at 5 or 6 everywhere until Q-6's channel question is answered.
- Evidence gaps left open: Aptem's AI ebook (PDF fetch failed), 2026 DfE investigation PDFs, NEC, Civica and Mobysoft product pages, the MOT bulk-file format page, and any 2026 price for an operator-licence audit.
