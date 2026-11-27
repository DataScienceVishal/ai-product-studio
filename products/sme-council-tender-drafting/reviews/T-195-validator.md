# T-195 (D2) validator check: fictional firm evidence library

Checker: validator, 2026-11-27. Maker: strategist. Scope: `demo-data/evidence/*.md`, `evidence/README.md`, `demo-data/SOURCES.md`, against SPEC section 5 and DESIGN sections 8 and 9.

## Verdict: REVISE (one substantive fix; eight small fixes already applied)

Six of the seven checks pass. Check 4 (internal consistency) fails on headcount: the per-contract teams don't fit inside the firm's stated headcount. That needs the maker to re-derive figures across about 10 files, which is more than a typo, so I have not done it.

## Results by check

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | 20 to 40 documents, each ending with the footer | PASS | 32 documents (01 to 32) plus README. A grep for `^Fictional document for a software demo\. Not a real company\.$` finds 1 match in each of the 33 files, and the footer is the last line of every file I read. |
| 2 | No real clients, people or identifiers | PASS | Web searches on 2026-11-27: `"Eastvale Borough Council"` finds only Eastvale, California (a US city council) and Eastbourne BC, with no UK authority by that name. `"Marlowe Fen District Council"` finds no match; the nearest is Fenland DC. `"Tarn Valley Council"` finds no match; nearest are Derwent Valley (Tasmania) and Ribble Valley BC. `"Harrowmere Facilities" OR "Harrowmere Ltd" OR "Harrowmere Limited" Companies House` finds no record; nearest is Harrogate Facilities Management Limited. A bare `"Harrowmere"` returns one machine-generated lexicon page and no company. `"Fenborough" UK town` finds no place. All identifiers are CERT-DEMO-, POL-DEMO-, ICO-DEMO- or DEMO-0000, and suppliers are "Demo ... Ltd (fictional)". A grep for 8-digit company numbers, phone numbers and email addresses finds nothing. Statutes named (HSWA 1974, MSA 2015 s.54 and its £36m threshold, Equality Act 2010, PIDA 1998, Bribery Act 2010, TUPE 2006) are real law, which is fine. |
| 3 | No personal data | PASS | Roles only (32:5 "No individuals are named"). Workforce data is aggregate (10:7). |
| 4 | Numbers consistent across files | **FAIL until F1 is fixed** | Contract values are consistent: 412+168+146+97+58 = 881 (02:12, README:5, 26:7-11). Extensions: 4 of 5 (26:17) matches 20, 21, 22 and 24, with 23 not extended. Complaints: 16+4+2+3+0+12 = 37 (26:13 = 04:10). Hires: 14/19 = 74% (14:6). Training spend: £21,600/58 = £372 (08:23). Zero-hours: 7/58 = 12% (14:9). Contract dates add up. Failures: see F1, plus F2 to F9 below (fixed). |
| 5 | README gap list accurate | PASS | Every gap, G1 to G14, is stated as absent in the files it cites: G1 03:17, 05:5; G2 03:18, 06:6; G3 03:19-20, 12:8; G4 07:10,17; G5 03:21, 14:8; G6 05:12-13; G7 01:17, 17:16; G8 01:17, 24:16; G9 18:14,16; G10 01:20, 15:19; G11 19:13,16, 25:16; G12 10:9, 14:20, 32:17; G13 20:21; G14 03:22, 13:11, 02:15, 09:16 (and 27:11). I found no document that contradicts a gap. The mention of CCTV record retention (12:10) is retention, not monitoring, so it does not contradict G9. |
| 6 | Separable ISO 14001 and ISO 9001 passages | PASS | 05:1,5 carries "ISO 14001" three times together with "environmental", and never mentions 9001. 04:1,5 carries "ISO 9001", "quality" and CERT-DEMO-0001, and never mentions 14001. 03 holds both, split into "Held" (03:10) and "Not held" (03:17). That supports S2's test that the ISO 14001 passage ranks above the ISO 9001 one, and the SPEC trap where an ISO 14001 question finds only 9001 evidence. |
| 7 | Specific enough for cited drafting | PASS | Cleaning: method 17 (colour codes, frequencies, 1:7 supervision, HEPA), case studies 20, 23 and 25, KPIs 26. Security: method 18 (shift pattern, 30-minute response with a 22-minute actual, ARC subcontract), case studies 21 and 24. Grounds: method 19 (cut counts, crews, machinery, nesting season), case study 22, the environmental figures in 05. Cross-cutting: TUPE 15, mobilisation 16, social value 14, H&S 06, insurance 07, continuity 13, account management 29. Nearly every passage has a number, a date or a document reference that the claim check can quote. |

## F1 (open, maker to fix): cleaning headcount does not fit, and nobody staffs the rest of the turnover

- 01:9 gives 31 cleaning operatives and supervisors. 08:8 agrees, with 37 cleaning plus grounds (31 + 6).
- Yet the two council cleaning contracts alone have 25 (20:8, 22 operatives and 3 supervisors) and 12 (23:7) = **37 people**, which is more than 31.
- More broadly, the five council contracts already use 37 cleaning, 10 security (21:8, 24:8) and 6 grounds staff. That covers all 51 operational staff (31 + 14 + 6 is only 51, so even this doesn't fit) and £881k of the £3.82m turnover. Nobody is left for the "31 smaller contracts" (02:12) or the 29% private-sector work.
- A claim check that reads 01 and 20 or 23 together could flag a contradiction. That is a seeded-looking conflict nobody intended, and it would muddy A5, A6 and the D3 keys.

**Required fix (recommended option):** keep the turnover and contracts, and raise headcount to a level that staffs them. Cleaning SMEs run at about £30k to £40k turnover per head, which means roughly 95 to 120 staff, mostly part-time cleaners. For example: 70 cleaning operatives and supervisors, 16 security officers, 8 grounds operatives and 8 management and office staff (102 in total). The maker chooses the numbers. Then recompute every dependent figure:
- 01:9 (split and total)
- 02:7-9 (average employees for each year)
- 08:7-9, 13, 14-16, 17-20, 23 (group sizes, and £ per head)
- 09:8
- 10:7 (staff and response counts)
- 14:9 (zero-hours count and %), 14:10 (days per head)
- 18:9 and 19:10 if the security or grounds totals change
- 26:15 and 28:5-6 (leavers, average headcount and turnover %, with turnover % = leavers / average headcount)
- 28:12 (survey denominator)
- README:5
- SPEC.md:78 (says "60 staff"; align it with the final figure)

The cleaning supervisor count must stay at least the sum across the contracts: currently 3 + 2 = 5 (08:10).

Alternative: shrink turnover to about £1.9m to £2.2m and drop the "31 smaller contracts" to a few. Headcount still has to rise, because 37 cleaners won't fit in 31.

## Fixes applied by the checker (small and safe; not committed)

| # | File:line | Was | Now | Why |
|---|---|---|---|---|
| F2 | 04:9 | "three council contracts was 91.4%" | "five council contracts was 90.9%" | The mean of 26:7-11 is (93.1+91.0+89.8+90.2+90.5)/5 = 90.92. 91.4 matches neither the plain nor the value-weighted mean (91.7). |
| F3 | 26:14 | 91.4% | 90.9% | Same as F2 |
| F4 | 26:15, 28:6, README:61 | 24% | 25% | 14 leavers / 57 average headcount = 24.6% |
| F5 | 01:11 | "Three live council contracts (HF-CS-20 to HF-CS-25)" | "Five live council contracts with three councils (HF-CS-20 to HF-CS-24; HF-CS-25 is a one-off order under HF-CS-20)" | Contradicted 26:14 and 26:17 (five contracts) |
| F6 | 05:8 | "all three cleaning contracts" | "both council cleaning contracts (HF-CS-20, HF-CS-23)" | Only two council cleaning contracts exist |
| F7 | 02:12 | "12% of turnover (£458,000)" | "11% of turnover (£412,000)" | £458k = £412k + the £46k flood order, but the flood was on 14 Nov 2024 (25:6), in FY 2024/25, not 2025/26. 412/3,820 = 10.8% |
| F8 | 03:10 | "surveillance audit passed" | "recertification audit passed" | A renewal to 2029 comes from a recertification audit, not a surveillance audit |
| F9 | 23:7 | "11 operatives and 1 supervisor" | "10 operatives and 2 supervisors" | 17:12 sets 1 supervisor per 7 operatives; this also makes 08:10 (5 cleaning supervisors = 3 + 2) consistent. The team total stays 12, so 11:7 (24 DBS) is unaffected |
| F10 | 08:11 | "1 per site" (12/12) | "1 per site where the client requires one" | The firm serves more than 12 sites (9 buildings in 20, 8 schools in 23, and so on) |

## Advisory (not blocking)

- 04:5 and 03:10 say "ISO 9001-style ... certified". The D3 answer keys must decide whether a draft saying "ISO 9001 certified" is supported. I recommend the keys treat it as supported only if the draft carries the "-style" wording or the certificate ID. Otherwise the deliberate vagueness becomes noise in A5.
- 05:11 and 22:17 give the herbicide baseline as 2022, but the Tarn Valley contract started on 1 June 2023 (22:7). Either add "council baseline" or start from 2023.
- 28:12: the survey ran in March 2026, but its denominator (58) is the October 2026 headcount. Use the March headcount when F1 is redone.
- SOURCES.md:13 says the council names "were not checked against real authorities". They have now been checked (results above). The maker may add those three queries to the log.

## To reach PASS

Fix F1 as above, keep F2 to F10, and confirm 01, 02, 08, 10, 14, 26 and 28 all agree with one headcount. A re-check can be arithmetic only. No new web searches are needed.

Fictional-data review only; no product code touched.
