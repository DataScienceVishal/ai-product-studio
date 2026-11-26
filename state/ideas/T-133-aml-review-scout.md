# T-133 scout: AI first-pass AML file review for small UK accountancy practices

Date: 2026-11-26. Desk check, 12 searches/fetches. All pages accessed 2026-11-26. Several fetches failed (OPBAS PDF encrypted, AccountingWEB 403, Learnsignal 429, ICAEW page body not read), so some figures are from search summaries and are marked.

## Verdict: DROP (no idea file written)

Reason: no price for the review job exists in public sources (the exact hole round 20 named), the penalty data shows fines are mostly for late registration rather than file-quality failures, and the main buyer class (sole practitioners) is exempt from the independent-review duty. A forcing function exists (FCA takeover) but its date is unconfirmed.

## 1. Pain signals
1. HMRC penalty list, 1 Apr to 30 Sep 2025: about 113 accountancy service provider entries, about £495,220 total, range £1,050 to £52,000. Reg 56 (late registration) is about 106 of 113 (manual tally by fetch tool, verify). Reg 18/19 (risk assessment, policies) appears in only one case (TAG Accountants (N.I.) £10,000). Source: https://www.gov.uk/government/publications/businesses-not-complying-with-money-laundering-regulations/businesses-that-have-not-complied-with-the-money-laundering-regulations-2025-to-2026. Reading: fines are real but are not about file quality, so a file reviewer would not have prevented most of them.
2. AccountingWEB (search summary, page 403 on fetch): 1 Oct 2024 to 31 Mar 2025, 336 businesses fined, 91 ASPs, ASPs £538,916 of £3,208,333. https://www.accountingweb.co.uk/practice/general-practice/hmrc-hits-businesses-with-ps32m-in-aml-fines
3. HM Treasury AML/CFT supervision report 2024-25 (published 8 Dec 2025). Learnsignal blog says HMRC outcomes were 19% compliant, 21% generally compliant, 60% non-compliant, across all HMRC sectors (MSBs, HVDs, ASPs), not confirmed against the official 95-page PDF: https://www.learnsignal.com/blog/hm-treasury-aml-supervision-report-2024-25-accountancy-sector-findings-guide/ ; official page https://www.gov.uk/government/publications/anti-money-laundering-and-countering-the-financing-of-terrorism-supervision-report-2024-25 (no sector numbers on page). Signal is weak: HMRC population, not ICAEW/ACCA practices.
4. OPBAS 2024/25 report (3 Mar 2026), via search summaries: PBS supervisors broadly compliant and "more effective than at any time since 2018", onsite visits across 22 supervisors not back to pre-pandemic levels, enforcement weakest area, some rely on firms self-certifying after problems. https://www.fca.org.uk/publication/corporate/opbas-report-progress-themes-supervisory-work-2024-25.pdf (PDF unreadable by fetch), https://fintech.global/2026/03/13/opbas-findings-highlight-need-for-stronger-aml-controls/. Fewer visits and rising effectiveness cut against urgency.
5. ICAEW has a "perform a regular compliance review" page in its AML top insights, implying reviews are a common weakness, but I did not read the figures: https://www.icaew.com/regulation/aml-supervision/anti-money-laundering-supervision-report/aml-top-compliance-insights/perform-a-regular-compliance-review

Net: 3 signals with numbers, none measures file-review failure rates for small practices.

Forcing function: HMT chose a single professional services supervisor (FCA). Per AAT's Sept 2026 update, the FSM Bill is expected to get Royal Assent between Sept 2026 and Mar 2027 and FCA guidance for professional services from Mar 2027 (https://www.aat.org.uk/files/aml-supervisory-reform-update-for-members-september-2026.pdf, via search summary). Current supervisors stay until transition; no go-live date for accountants found (HMT response June 2026 per https://www.lewissilkin.com/en/insights/2026/06/26/aml-ctf-supervision-reform-what-law-firms-and-accountancy-practices-need-to-know-102n6f4). Real but dated 2027 or later.

## 2. Price
No public price for the review job found. Deloitte (mock inspections), Weightmans (remote independent AML audits), Crowe (gap analysis), Kingsley Napley (AML audits) all list the service with no fee: https://www.deloitte.com/mt/en/services/consulting-risk/services/fincrime-review-and-assure.html, https://www.weightmans.com/services/regulatory/anti-money-laundering/anti-money-laundering-audits/, https://www.crowe.com/uk/services/advisory/anti-money-laundering-compliance-service, https://www.kingsleynapley.co.uk/services/specialist-group/aml-compliance/aml-audits. Substitute and adjacent costs only:
- AMLCC subscription: £346.40 a year new, MLRO plus 3 staff, extra staff £30 each, ex VAT (own page, https://www.aiaworldwide.com/amlcc). Sets the anchor for what a small practice pays for AML software.
- Per-check software: £2.00 to £6.00, IRIS Elements from £2.50 plus licence (IRIS page https://www.iris.co.uk/products/anti-money-laundering-aml/, summary).
- One anecdotal £250 charge to a client for an AML check (HMRC community forum, https://community.hmrc.gov.uk/customerforums/bt/5891c64b-f674-ef11-a4e5-6045bd0c8ae7).
- Free: AccountingWEB vendor 7-step health check; AAT annual compliance review checklist (https://www.aat.org.uk/files/aat-anti-money-laundering-annual-compliance-review-checklist.docx).
Hours evidence: none. Counter-evidence: ICAEW says a sole practitioner with no relevant employees need not have regular independent reviews unless ICAEW requires it (https://www.icaew.com/technical/tas-helpsheets/anti-money-laundering-helpsheets/anti-money-laundering-for-smaller-practices). The reg 21 buyer is a practice with staff, and the independent function need not be external, so it can be done in-house for free.

## 3. Incumbents (own pages where fetched)
- AMLCC: no AI feature; audit trails, document storage, read-only supervisor dashboard; no independent review service on page. Not a file reviewer.
- Digita AML (Thomson Reuters): AI claims cover ID document analysis and screening false positives only; periodic reviews and monitoring are not described as AI. https://europe.thomsonreuters.com/solutions/digita/aml-id-verification
- IRIS Elements AML: per-check and biometric ID, MLRO notified on SARs (search summary, page not fetched).
- Legl, Xama, SmartSearch, Credas, Amiqus, Tickd, Ignition AML: not checked on own pages (time box). Search found no AI file-review feature for Legl or Xama; Legl price on request.
- Precise statement: of the vendors whose own pages I read (AMLCC, Digita), none does AI review of existing files against MLR 2017 or AMLGAS. Not verified for Legl, Xama, SmartSearch, Credas, Amiqus, Tickd, Ignition, IRIS beyond summaries. No AI AML review tool found for accountants. Adjacent: the SRA publishes a manual AML file review form for law firms (https://www.sra.org.uk/globalassets/documents/solicitors/aml-file-review.pdf), a model of what the task is, and a free substitute for solicitors. Caveat: absence in about 12 searches, and incumbents (Digita, IRIS, Legl) already hold the files so adding a "gap check" is a prompt-level feature.

## 4. Wedge, recurring, data, proof test
- Wedge: none evidenced. Possible wedge is "independent" status (review by a party outside the firm), but a software tool cannot give supervisor-recognised independence, and no supervisor statement accepts an AI review as the reg 21 audit. Competition would score 0 to 3.
- Recurring: annual review per practice, one job a year at an unknown price. A subscription needs a monthly use case, which is absent. Spike before 2027 FCA handover is one-off.
- Data red flag: real files hold client ID and CDD, personal data. A proof test can only use synthetic files, so it shows format and rule citation, not real-file messiness (same weakness as round 20). Integration with IRIS/Digita exports is closed.
- Score a pass first: a benchmark pass leaves Pay about 4 to 6, Competition 2 to 3, so the total cannot reach 70. Do not spend on the benchmark.
- Proof test design (not run): 60 synthetic client files (20 compliant, 40 each seeded with 1 to 3 known gaps from the ICAEW/AAT checklists and MLR regs 18, 19, 28, 33, 35), run on a cheap model, cost under $3. Fix model, effort and a generous output cap, one retry at a larger cap on truncation. Pass: at least 80% recall on seeded gaps, at most 10% false-positive rate on compliant files, and the correct regulation cited on at least 85% of findings.
- Revisit only if: a practitioner or consultancy states a fee for a reg 21 review and a supervisor says an AI-assisted review is acceptable, or the FCA publishes a go-live date and an inspection regime.

## Injection note
No instructions embedded in fetched pages were observed.
