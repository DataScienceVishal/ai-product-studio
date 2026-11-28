# T-194 validator gate: 12 synthetic tender packs (D1 via Q-20 option B)

Checker: validator (opus). I did not write these packs. Date: 2026-11-28.

## Verdict: REVISE

The packs are good: they read like small UK public-sector ITTs, the arithmetic is right, and the formats vary well. Fix 8 items and they pass. Six are small text edits in the packs, one is a documentation update (SOURCES.md and a dated SPEC/EVAL amendment), and one is a set of key conventions qa must write down before D3. None needs a rewrite. After the fixes I need to re-check only the changed lines, plus the `build_docx.py --check` output.

What I read: SPEC sections 3, 5 and 6; DESIGN section 7 (personal data), section 8.1 and the D1 line in section 9; EVAL "Run configuration"; all 12 sources S01 to S12; `build_docx.py`; `parse_worker.py parse_docx`; `packs/manifest.json`; `evidence/README.md` (for item 6 only). I did not open `eval/keys/`.

Limitation: I had no shell in this run, so I could not run `build_docx.py --check` or `parse_worker.py`. I read the builder and parser code instead (see item 4). MUST-FIX 2 asks for the real page counts to be recorded.

## Summary per pack

| Pack | Role | Scored Qs | Weights add up | Dates | Safety | Main issue |
|---|---|---|---|---|---|---|
| S01 Brackenhall DC, cleaning | drafting held-out | 18 (+1 P/F) | yes, 60+10+30 | coherent (weekday names correct) | **real place name** | MF-1, MF-8; "six" high-use sites vs 5 in App. A |
| S02 Cinderwick TC, leisure cleaning | held-out | 9 | yes, 70+30 | coherent | ok | clean |
| S03 Wrenbourne AT, schools | held-out | 9 | yes, 60 (SV 10 inside) +40 | coherent | ok | per-case-study page limit (MF-7) |
| S04 Pellwick PC, halls/toilets | demo | 9 (+1 P/F) | yes, 60+40 | coherent | ok (01632 960417) | shared limit (fine for demo) |
| S05 Brackenmere DC, guarding | drafting held-out | 16 (+1 P/F), 17 if Q15(a)/(b) split | yes, 25+13+22=60, +40 | **29 Feb 2027** | ok | MF-6; asterisk mismatch |
| S06 Oakhallow Homes, concierge | held-out | 8 | yes, 60 marks +40 | coherent | ok | MF-3, MF-4 |
| S07 Thornbeck College, events | held-out | 10 | yes, 70+30 | coherent | ok | clean |
| S08 Halden Vale Trust, CCTV/keyholding | demo | 10 (+1 P/F) | yes, 50+10+40 | coherent | ok | site counts (nit, fix before R1) |
| S09 Brackenholt TC, grounds | drafting held-out | 19 (20 if 2.4(a)/(b) split) | yes, 60+10+30 | coherent | ok | MF-5 |
| S10 Ashenmere PC, cemetery/play | held-out | 8 (+Q0 P/F) | yes, 50+10+40 | coherent | ok (01632 960214) | unnumbered P/F bullets (MF-7) |
| S11 Quillbrook DC, pitches | held-out | 13 | yes, 60+10+30 | coherent | ok (01632 960417, duplicate of S04) | 20-page global limit (MF-7) |
| S12 Hallowby TC, grounds/FM | demo | 11 | yes, 40+10+50 | coherent | ok (01632 960655) | "recommended length" wording (nit) |

I checked every date's weekday against the 2027 calendar. All are right except the impossible 29 February 2027 in S05.

## 1. Safety

- Synthetic banner: present at line 3 of all 12 sources and at the top of every source page (`(Synthetic demo document - fictional buyer)`). The builder also writes it as a Word footer, but `parse_docx` does not read footers. Pages the builder splits off automatically (about every 450 words) therefore carry no banner in the text the app reads (nit N-X3).
- Every buyer is marked "(fictional)" on first use: S01 l.5, S02 l.5, S03 l.5, S04 l.5, S05 l.9, S06 l.9, S07 l.9, S08 l.9, S09 l.5, S10 l.5, S11 l.5, S12 l.5.
- Real place names: **"Brackenhall" is a real district of Huddersfield in Kirklees** (Wikipedia "Brackenhall"; ONS MSOA E02002295 "Deighton and Brackenhall"). It is used as the buyer name in S01 (MF-1). "Aldermoor" (S04 site names, l.58 and l.60) is a real neighbourhood of Southampton (ONS E02003550). It is only a hall and toilet site name, so I list it as a nit. Searches for Brackenholt, Brackenmere, Cinderwick, Pellwick, Ashenmere, Quillbrook, Hallowby, Thornbeck, Wrenbourne, Oakhallow and Halden Vale found no UK place or council. Generic names (Millbrook, Market Square, Station Road, Riverside, Foxcote, St Aldwyn's, St Wulfric's) are acceptable.
- Personal data: none. Contacts are roles only. Emails are role addresses on `.example` domains (grep: every `@` is `*.example`). There are no `http` or `www` links. Phone numbers are all in the Ofcom drama range 01632 960xxx: S04 960417, S10 960214, S11 960417 (a duplicate of S04, nit), S12 960655. TUPE tables give counts or letters A to D, never names.
- Copied text: I found no sign of it. The prose is generic and reads as original paraphrase. Two exact-phrase web searches on distinctive sentences found no source. Nothing is copied from the P01 to P12 notices, which were never downloaded.

## 2. Internal consistency

Weightings and marks add up as stated in every pack (table above). Inconsistencies found:

- S01 l.159 "the six highest-use sites identified in Appendix A", but Appendix A (l.454 to l.459) marks only five as "High use" (C01, C02, C03, C05, C06). Nit.
- S01 l.23 says the site visit is "compulsory", but l.84 says "Failure to attend will not exclude a bidder". This affects the A3 key: MF-8.
- S05 l.231 says the asterisked questions are Q2, Q5 and Q15, but Section 6 puts asterisks on Q2 (l.255), Q5 (l.267) and **Q12** (l.299), and Q15 (l.311) has none. Nit, but a buyer would issue an addendum.
- S05 l.36 "Weeks commencing 22 and 29 February 2027": that date does not exist. MF-6.
- S05 l.39: a standstill ending 15 June after a 4 June notice is 7 working days, not "minimum 8" (8 would end on 16 June). Nit.
- S05 l.117: "31,500 static guarding hours, 9,800 mobile patrol hours ... above the baseline staffing" does not match the posts in 3.3, which give about 12,000 static hours and about 5,600 patrol hours a year. Nit.
- S06 l.162 (and S08 l.179): the sub-parts of Q5 are labelled "5.1(a)/5.1(b)", but no question 5.1 exists. MF-3 for S06; nit for S08, which is a demo pack.
- S06 l.112: PF11 sits outside the pass/fail table and is discretionary. MF-4.
- S06 R1/R2 (l.187 to l.188): 75,000 concierge hours a year, against about 22,100 from the block hours in 3.1. R3 is 5,800 pair-hours against about 2,950. Both are also out of line with the £780k to £960k value. Nit.
- S08 site counts (known issue). The text has 19 alarm sites and 11 CCTV sites with 138 cameras. Categories (l.77 to l.79) are 4+6+9=19. Appendix 1 (l.226 to l.230) lists 3+1+1+5+4 = **14 sites**, though its cameras do sum to 138. Halls are given as "four" (3.1, l.57), "8" (3.4, l.85) and 4 (App. 1). Category 3 needs 9 "halls and other sites". Nit, because S08 is a demo pack with no key, but fix it before the R1 recording: it is the pack people will see.
- S08 l.186 "Total 60%": the arithmetic is right (50 quality + 10 social value; price is 40 in section 7). Nit: say "Section 6 total 60%; price 40% in section 7".
- S09 l.64 says "(a) and (b) are scored together under the weighting of the parent question", but 2.4(a)/(b) (l.317, l.319) carry separate weightings [2%]/[1%] and limits 200/150. MF-5.
- S10 l.137 says salting is "up to 10 call-outs a year", but the comparison price (l.219) uses 20 call-outs over 3 years. Nit.
- S12 l.79 says Appendix 2 holds "age, salary and notice"; it holds hours and service only. Nit (and better without age).
- TUPE totals check out: S01 23 (16+4+1+2; hours 544.5 against "about 560", nit), S03 41 / 880 h, S05 34, S06 21, S07 6, S11 9, S12 3.

Limits: in every held-out pack a careful person can work out each question's limit. Some formats need a recorded convention (MF-7).

## 3. Realism

Overall this passes. Every pack has the parts a real small UK public-sector ITT for the sector would have. These include pass/fail SQ items, EL, PL and PI insurance levels, and SSIP/CHAS. The sector accreditations are there: BICSc; SIA, ACS and BS 7858/7984/7958/5979; PA1/PA6 and BS EN 1176. So are TUPE tables, Living Wage indexation, open-book price build-ups, service credits, pricing baskets and social value. Things a council buyer would find odd (all nits):

- TUPE pay rates of £11.80 to £13.20 (S05 l.398 to 401, S06 l.222 to 224, S07 l.292) are below the 2026 National Living Wage (£12.71) and certainly below 2027 rates. That would be unlawful for a 2027 contract. Raise them to about £13.50 to £15.
- S01 l.471: "14 days annual leave plus bank holidays" is below the statutory 5.6 weeks.
- S09, S11 and S12 cite "PPN 03/24" (the SQ under PCR 2015) in packs otherwise run under the Procurement Act 2023. S12 l.93 also mentions ESPD, which is post-Brexit odd. S09 l.10 calls Contracts Finder "(fictional)", but it is a real service; say "the national notice service" instead.
- S09 l.82: "RoSPA/ROSPA-registered or ADIPS-accredited play inspector". ADIPS covers fairground rides; the real register is RPII. S10 l.149 also says "RoSPA-registered". S09 l.211 "Control of Pesticides Regulations" was superseded by the Plant Protection Products (Sustainable Use) Regulations 2012.
- S05 l.137: the Surveillance Camera Commissioner role no longer exists as such; say "Surveillance Camera Code of Practice". S05 l.191: a £3m turnover minimum for a contract worth about £0.5m a year is well above the usual cap of 2x the contract value. S05 has no Appendix D. S05 l.324 "people furloughed from long-term unemployment" is garbled, as are l.109 (A1 hours) and l.133 (keyholder numbers).
- S06 l.102 says a door supervisor licence is not acceptable for concierge work, but an SIA DS licence also covers guarding. S06 l.169 says social value is "included in the price and quality marks" yet not scored.
- S01 and S10: the site visit comes after the clarification deadline. S09: a grounds contract starting 1 June with a 2-week mobilisation is unusual (they normally start before the growing season).
- S01 and S05 both use ref "BDC/.../2027/014" and "Millbrook Depot". All three drafting held-out buyers start with "Bracken-". This is harmless, but renaming S01 (MF-1) also fixes it.

## 4. Eval fitness

- Drafting held-out packs: S01 has 18 scored quality questions, S05 has 16 and S09 has 19. All three meet the bar of at least 15. `manifest.json` names them correctly as `drafting_heldout` (exactly 3, all in `heldout`). Demo packs are S04, S08 and S12.
- Pages: the builder breaks at every `---pagebreak---` and about every 450 words, and never splits a table. From the source lengths (the largest, S05, is about 5,500 words), every pack should be roughly 6 to 16 pages, well under 40. Every page has text by construction: a break is only written when the current page holds content. Note that `parse_docx` drops empty pages, so it would hide an empty page rather than reveal one. The real counts must be recorded (MF-2).
- Format variety is good:
  - Tables: S01, S04, S06, S08, S10, S12. Headed paragraphs: S02, S03, S05, S07, S09, S11.
  - General-rule limits: S02 500, S05 400, S10 350 (with a "-" column).
  - Heading-borne limits: S01 5.1, S03 sections, S05 sections A and B, S09 4.x.
  - Combined limits: S04 4.1 to 4.3, S06 Q4 to Q6, S09 2.1 to 2.3, S05 Q15, S08 Q5.
  - Page limits: S03, S06 Q8, S07, S09 1.4, S10 Q7. Whole-response page budgets: S11 (20 pages), S12 (12 sides).
  - Pass/fail mixed into quality: S01 2.4, S04 4.7, S05 Q11, S08 PF-Q, S10 Q0.
  - Scoring scales: 0 to 5, 0 to 4 marks, 0 to 10, 0 to 100.
  - Unnumbered pass/fail bullets: S10, S12.

## 5. Answer-key feasibility (held-out packs only; demo packs need no key)

| Pack | Can qa key it without guessing? | Ambiguous refs or items |
|---|---|---|
| S01 | yes, after MF-8 and MF-7 | 5.2 "400 words per case study" (×2); 2.2(a)/(b) separate rows (fine); 2.4 P/F with 100-word limit; site visit l.23 vs l.84; 3.3 information requests (not mandatory) |
| S02 | yes | none (default 500 applies to Q2, Q3, Q5, Q6, Q7, Q9) |
| S03 | yes, after MF-7 | 4.3 "one side per case study" (×2); refs 2.1 to 5.1(b) sit under section headings 5.1 to 5.4 (deliberate, but a ref/heading collision for A1) |
| S05 | yes, after MF-6 and MF-7 | Q15 combined 500 across 15(a)/(b); Q12 falls to the 400 general rule; l.198 "standard SQ ... two references" (mandatory or not?) |
| S06 | **no, until MF-3 and MF-4** | Q5 "5.1(a)/5.1(b)"; PF11 discretionary; Q4 to Q6 combined 1,200; Q8 one side plus "diagram counts as 100 words" |
| S07 | yes | none |
| S09 | **no, until MF-5**; then MF-7 | 2.4(a)/(b) weights vs l.64; 2.1 to 2.3 combined 800; Section D Parts 1 to 7 "pass/fail except where noted" (separate mandatory items, or covered by M11?) |
| S10 | yes, after MF-7 | pass/fail bullets in 1.4 have no refs; 1.6a items (mandatory or information?); EL exemption alternative |
| S11 | yes, after MF-7 | Q2, Q4, Q5, Q7 and Q11 have no limit of their own (20-page global only); "Mandatory pitch briefing" (l.22) is conditional per l.50; 1.6 SQ parts; Q13 500 words plus an optional one-page table |

## 6. Leakage

No leakage. No pack names Harrowmere, its fictional clients (Eastvale, Marlowe Fen, Tarn Valley) or its identifiers or figures. The questions are normal for the sector, and many of them run into the library's deliberate gaps naturally:

- G4, £10m public liability, as pass/fail: S01 M2, S05 M8, S06 PF5, S07 PF4, S09 M1, S11 P1, S12 A3.
- G2, ISO 45001: S05 M6.
- G9, CCTV, ARC and door supervision: S05 M5 and D1, S07 door staff, S08 M1.
- G11, play inspection: S09 M7 and 5.1, S10, S11.
- G10, TUPE over 17 staff or a contract over £500k a year: S01, S02, S03, S05, S06.

That is the intended pattern. Observation for the strategist, not a defect: the firm fails a pass/fail item in most packs, including demo pack S12 (PL £10m). That could be a good honest "no-bid" demo moment, or a reason to swap S12's PL to £5m. It is a demo choice, not a validity issue.

## MUST-FIX

1. **S01: real place name as the buyer.** "Brackenhall" is a real Huddersfield district. Rename the buyer everywhere in `demo-data/pack-sources/S01-cleaning-civic-offices-conveniences.md`: l.5, l.14 and l.15 (domain `brackenhall-dc.example` and the portal), l.43, l.125, l.128, l.393. Also change the ref "BDC/FM/2027/014" (l.9). Pick a name that does not start with "Bracken", web-search it for a real UK place or council before use, log the check in SOURCES.md, then rebuild the .docx.
2. **SOURCES.md and the pre-registration record still describe the real P01 to P12 packs.** `demo-data/SOURCES.md` D1 still says "0 of 12 packs verified" and lists P01 to P12. The EVAL drafting rule ("first of each sector in SOURCES.md order") and `manifest.json` refer to that order. Add an S01 to S12 table with: sector, fictional buyer, source .md, .docx SHA-256, page count from `build_docx.py --check` and from `parse_worker.py docx <file> 40`, the role (demo / held-out / drafting), and a line saying "synthetic, Q-20 option B, no licence needed". Mark P01 to P12 as superseded. Add a dated amendment to SPEC section 5 (and a line in EVAL "Run configuration") saying the packs are studio-written and synthetic, so their A1 to A3 numbers measure synthetic layouts, not real council PDFs. This must happen before the freeze.
3. **S06 l.162: wrong sub-part labels in a held-out pack.** Change "5.1(a)" and "5.1(b)" to "(a)" and "(b)" (or "5(a)/5(b)"). No question 5.1 exists, and the key ref would be ambiguous. Make the same change in S08 l.179 (demo pack).
4. **S06 l.112: PF11 status is ambiguous for A3.** Either move it into the pass/fail table as "PF11 ... (Pass/Fail)", or relabel it "Information only, not pass/fail; the Association may consider it under discretionary exclusion". As written, qa cannot tell whether it is a mandatory item.
5. **S09 l.64 contradicts 2.4(a)/(b) (l.317, l.319) in a drafting held-out pack.** Reword l.64 to: "Where a question has parts (a) and (b), each part carries the weighting and limit shown against it; together they make up the parent question's weighting." A2 needs weights to match exactly.
6. **S05 l.36: impossible date.** "Weeks commencing 22 and 29 February 2027" should be "Weeks commencing 22 February and 1 March 2027". A deadline-type key item cannot hold a date that does not exist.
7. **Key conventions, written in `eval/keys/README.md` before D3** (qa; if the README already covers these, confirm each one):
   - (a) Per-item limits ("400 words per case study" in S01 5.2, "one side per case study" in S03 4.3): record the per-item value plus a count of 2, never the doubled total, or the reverse, but one rule.
   - (b) Limits shared across questions (S06 Q4 to Q6, S09 2.1 to 2.3) and within one question (S05 Q15): one rule for `word_limit` on each item plus a shared-group id.
   - (c) Sub-parts with their own weight or limit (S01 2.2(a)/(b), S03 5.1(a)/(b), S09 2.4(a)/(b)) are separate items. Sub-parts without them (S05 15(a)/(b), S06 Q5) are one item.
   - (d) Whole-response page budgets (S11 20 pages, S12 12 sides): questions with no limit of their own get `word_limit: null`, and the budget is a pack-level item.
   - (e) Ref rules for unnumbered pass/fail bullets (S10 1.4), matched on text.
   - (f) Which SQ parts and information requests count as `mandatory` (S01 3.3, S05 l.198, S09 Section D, S10 1.6a, S11 1.6).
   - (g) Conditional requirements (S11 briefing, S10 EL exemption).
8. **S01 l.23 vs l.84: site visit "compulsory" vs "will not exclude".** Make them agree. Either change l.23 to "(one representative per bidder expected; see 1.6)", or make attendance pass/fail in 1.6. As written, A3 cannot say whether it is a mandatory item.

## Nits (fix if cheap; none blocks the gate)

- N-1 S08 site counts (App. 1 has 14 sites vs 19 alarm and 11 CCTV; halls are 4, 8 and 4; category 3 has 9) and the "Total 60%" wording at l.186. **Fix before R1 recording**, because S08 is a demo pack.
- N-2 S05 asterisk list (l.231) vs the marks on Q12 and Q15. S05 standstill date (l.39). S05 hours "above the baseline" (l.117). S05 garbled lines l.109, l.133, l.324. S05 has no Appendix D. S05 £3m turnover vs value. S05 Surveillance Camera Commissioner (l.137).
- N-3 S01 "six highest-use" vs 5 (l.159). TUPE hours (l.229). 14 days' leave (l.471). Site visit after clarification deadline. The invented "Association for Cleaning and Hygiene Excellence style" (l.178).
- N-4 TUPE pay below the 2026/27 minimum wage in S05, S06 and S07. Raise to about £13.50 to £15.
- N-5 S06 hour quantities vs posts and value (l.187 to l.189). DS licence statement (l.102). Appendix order 1, 2, 4, 5, 3. Unscored social value (l.169).
- N-6 S09 RPII not RoSPA/ADIPS (l.82, and S10 l.149). Pesticide regulations (l.211). "Contracts Finder (fictional)" (l.10). PPN 03/24 under the PA 2023 (S09, S11, S12). ESPD (S12 l.93).
- N-7 S10 salting 20 vs up to 10 a year (l.137 vs l.219). S12 A2 "recommended length" vs word limits (l.41): say limits are binding. S12 Appendix 2 contents (l.79). S04 pavilion not in the site list (l.34).
- N-8 Duplicate phone number 01632 960417 (S04 l.13, S11 l.13). Give S11 another 960xxx number.
- N-X1 "Aldermoor" (S04 l.58 and l.60) is a real Southampton neighbourhood. Rename the site (for example "Alderholt" is also real, so choose and search).
- N-X2 Three "Bracken-" buyers across the drafting held-out packs. MF-1 fixes one of them.
- N-X3 Pages the builder splits automatically have no in-body banner, and the parser ignores the footer. Optionally have `build_docx.py` repeat the banner line after each automatic break.
- N-X4 S11 l.43 says "including diagrams and tables", but S09 l.62 says tables count "only where the question says so". That is fine as variety, but make sure the keys record what each pack says.

## Re-check 2026-11-28

Checked on branch p/sme-council-tender-drafting/T-194, in the working tree, against the source files. I still had no shell, so I did not re-run the parser myself. The page counts come from the SOURCES.md table: 7 to 15 pages, all under 40.

| Item | Result | Evidence |
|---|---|---|
| MF-1 S01 real place name | fixed | The buyer is "Fennickstead District Council (fictional)" (l.5). Ref FDC/FM/2027/014 (l.9). `fennickstead-dc.example` (l.14, l.15). l.43, l.125, l.128 and l.393 are renamed. A grep finds no "Brackenhall" left in any pack. My own web search for "Fennickstead" found no UK place. |
| MF-2 SOURCES and pre-registration | fixed | SOURCES.md l.17 to l.38: a synthetic status line, the S01 to S12 table with parser page counts and source SHA-256, and the roles. P01 to P12 are moved under "Earlier real candidates (not used)" (l.40). EVAL.md amendment l.54 and SPEC.md "Amendment 2026-11-28 (T-194)" (l.146 to l.148) both say the packs are synthetic and that results must say so. |
| MF-3 S06 Q5 labels | fixed | S06 l.162 reads "(a)" / "(b)". S08 l.179 has the same fix, and its limit now says "across parts (a) and (b)". |
| MF-4 S06 PF11 | fixed | l.112 "PF11 (Pass/Fail) ... fails PF11" is now plainly pass/fail. |
| MF-5 S09 sub-parts | fixed | l.64 "scored separately, each with its own weighting and limit as shown; together they make up the parent question". This matches 2.4(a) [2%] and (b) [1%]. |
| MF-6 S05 date | fixed | l.36 "Weeks commencing 22 February and 1 March 2027". |
| MF-7 key conventions | deferred to qa (T-206) | This is acceptable for this gate, because no key exists yet. **It is a precondition for D3**: the conventions (a) to (g) above must be in `eval/keys/README.md` before any held-out key is written, and the D3 checker should confirm them. |
| MF-8 S01 site visit | fixed | l.23 "(strongly recommended, one representative per bidder)" and l.84 "should attend ... will not exclude" now agree. |

Nits I spot-checked:
- S05 l.231 now names Q2, Q5 and Q12, which matches the asterisks.
- TUPE pay: S05 l.398 to 401 is £12.75 and up, S06 l.222 to 224 is £12.75 and up, S07 l.292 is £12.85 and up.
- S09 M7 (l.82) now asks for an RPII-registered inspector.
- S04 Aldermoor is now Pellwick Memorial Hall and Memorial Green (l.58, l.60).
- S08 now says 4 halls (l.57, l.85, l.232), and l.186 now reads "together 60%; price 40%".

Residual nits, which do not block:
- (i) The S08 Appendix 1 note (l.224) says "section 2", but the counts are in section 3.2. Its "counted per system" explanation still leaves keyholding at 19 sites (l.73, l.77 to l.79) against the 14 sites listed. Before R1 recording, either list 19 sites or change the categories.
- (ii) S01 l.159 still says "six highest-use sites", but Appendix A marks five.
- (iii) The source SHA-256 values in SOURCES.md are for the .md files, not the .docx. That is fine because the build is deterministic from source, but say so in the table header.

**Verdict: PASS.** All safety and eval-validity must-fix items are fixed. MF-7 carries over as a hard precondition on D3 (T-206).
