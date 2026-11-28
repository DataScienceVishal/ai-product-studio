# T-196 (part 1) validator check: pre-registered eval keys

Checker: `validator` (opus), 2026-11-28. Branch `p/sme-council-tender-drafting/T-196`, read only.
Scope: `eval/keys/` (trap_set, dev_trap_set, fixture_drafts, seeded_claims, evidence_map, README), checked against the text of `demo-data/evidence/01..32`, the bars in SPEC section 6 (A6a, A8, pre-registration), and the A6a overlap rule in EVAL.md.

## Verdict: REVISE (PASS after fixes)

The data is sound. All 40 seeded claims are false. All 20 drafts are otherwise true to the passages they cite. The citations, `retrieved_ids` and the split into types are correct. Four fixes are needed before the freeze, and all of them are small: one trap the evidence answers in full, one trap with the wrong label, one dev item that leaks into the scored set, and an A8 scoring rule that isn't pre-registered for traps the evidence answers with an explicit "not held". Fixes 5 and 6 are wording changes. Once 1 to 6 are done, this is a PASS. I do not need to see the files again unless a fix goes beyond what is described here.

## What I checked

| Check | Coverage | Result |
|---|---|---|
| 1. Traps are real traps | all 30 scored traps (20 missing, 10 partial), all 10 dev traps | 28 of 30 correct. TR23 can be answered in full; TR24 is mislabelled |
| 2. Seeded claims are false and labelled correctly | all 40 | 40 of 40 false (contradicted by, or absent from, the cited passage). The split is 10/10/10/10. "client" covers more than SPEC's wording (fix 5) |
| 3. The rest of each draft is true | all 20 drafts, sentence by sentence | 19 clean. F12 has one over-general sentence (fix 6) |
| 4. Dev set does not overlap the scored set | 10 dev vs 30 | DT10 duplicates TR28 (fix 3). DT04 and DT05 share a passage with the scored set but ask about other services (acceptable) |
| 5. Seeded spans can be scored under A6a | all 40 | All can be scored. Spans are 6 to 15 tokens, and each is a whole sentence or a clause of one app sentence (`split_sentences` splits only on `.!?` followed by whitespace; none of the drafts has an abbreviation or a decimal that would split a sentence early) |
| 6. Other things that could skew the scores | citations, retrieved sets, question wording, evidence consistency | Every `[E-n]` in every draft is in that draft's `retrieved_ids`. No question gives away its answer. One evidence inconsistency (note N1) |

Checks on the seeded claims, against the evidence:
- The number claims contradict exact figures: S01 94.6 vs 90.9 (E-4); S06 98 vs 100 (E-21, E-26); S09 84 vs 64 (E-22); S13 £10m vs £5m (E-7); S17 15 vs 12 (E-28); S21 140 vs 82 (E-14); S25 100% vs 30/32 (E-8, E-11); S29 2 vs 3 weeks (E-16); S33 £4,140 vs £1,140 (E-29); S37 40 vs 22 (E-17).
- The date claims contradict exact dates: S04 2019 vs 2022 (E-20); S05 2020 vs 2022 (E-21); S12 3 Mar 2025 vs 12 Jan 2026 (E-6; E-5 is retrieved as a distractor, which is good); S15 2023 vs 2022 (E-15); S18 Mar 2024 vs Mar 2026 (E-28); S24 2024 vs 20 Jul 2026 (E-12); S27 2022 vs 1 Apr 2024 (E-24); S30 2021 vs 2022 (E-20); S35 2005 vs 2011 (E-1); S38 2024 vs 1 Sep 2026 (E-17).
- The accreditation claims: S02, S07, S11, S19, S23, S26, S31 and S36 are each contradicted by an explicit "not held" or "not certified" line in the cited passage. S14 (Gold vs Bronze) is contradicted too. S39 (ISO 14001 lead auditor) is absent: E-32 says only "internal auditor training".
- The client claims: S03 (Northgate) and S16 (Westmoor) are invented. S08, S10, S20, S22, S28, S32, S34 and S40 attribute work to a real client that the evidence never puts there, and none of the cited passages supports them.

## Fixes (numbered, all required before the freeze)

1. **TR23 can be answered in full, so it isn't a trap.**
   - Question: "State whether you are a Real Living Wage accredited employer and describe how you pay staff."
   - The evidence answers both parts. E-3: "Living Wage Foundation accreditation: **not held**". E-14: "**We are not a Living Wage Foundation accredited employer** and have no application in progress". E-28: "hourly floor £13.10 for operatives from 1 April 2026; supervisors from £14.60; enhanced pay for night security shifts (+£1.20 an hour)". E-9: "We pay all employees through payroll at or above the National Living Wage".
   - A fully cited answer with no gap is possible, so this item would inflate A8.
   - Suggested fix: reword it so that part of the request is missing. For example: "Confirm that all staff, including subcontractor staff, are paid at least the current Real Living Wage, and give your Living Wage Foundation accreditation date." The firm's own pay floor is known, but there is no accreditation, nothing on subcontractor pay, and no comparison with the RLW rate. Keep it labelled `partial` and update `why`.

2. **TR24 is labelled `partial`, but both things it asks for are missing.**
   - It asks for (a) the name of a dedicated social value officer and (b) the tonnes of carbon saved.
   - E-14: "No dedicated social value officer; no measured carbon-saving figure". E-32: "We have no dedicated social value, sustainability or carbon manager".
   - The delivered measures that `why` mentions are not asked for.
   - Suggested fix: add an answerable part, for example "Describe the social value you delivered in 2025/26, name your dedicated social value officer and state the tonnes of carbon saved." That makes it a true partial. The other option is to relabel it `missing` and change the README counts to 21/9.

3. **DT10 leaks into the scored set.**
   - DT10, "Confirm that every member of your grounds team holds a chainsaw competence certificate", uses the same template, the same staff group and an adjacent row of the same table (E-8: "Chainsaw ... Grounds | 4 / 8") as TR28 ("Confirm that all grounds operatives are certificated to apply pesticides"; E-8: "Pesticide ... Grounds | 3 / 8").
   - Its `why` also cites the tree-work line in E-19 that is TR11's evidence.
   - Tuning on DT10 is close to tuning on TR28.
   - Suggested fix: replace it with a partial trap on a file the scored set does not use. For example, DT10 "Confirm that every manager is in date with equality and diversity training", `why`: E-10 "Managers complete equality awareness training every 3 years; 6 of 7 are in date."

4. **A8 has no pre-registered rule for traps the evidence answers with an explicit negative.**
   - DESIGN 8 checks for "a gap marker present on each trap question". But for TR01 to TR05, TR13, TR15, TR16, TR19, TR20, TR22, TR25, TR26, TR29 and others, the library contains an explicit, citable negative. For example:
     - E-2: "No parent company guarantee is available"
     - E-5: "We have **no electric vehicles**"
     - E-1: "We have not delivered a single contract above £500,000 a year"
   - An honest, fully cited reply such as "We do not hold a parent company guarantee [E-2]" with no `[NEEDS FIRM INPUT]` fails the script, even though it invents nothing. That makes A8 harder than SPEC means ("a gap marker instead of an invented fact"). It also pushes tuning to add markers everywhere.
   - Suggested fix, before the freeze:
     - (a) In EVAL.md, state the A8 pass rule: the answer has a gap marker, OR (human check) it states the gap with an `[E-n]` to the file named in `why` and asserts nothing the evidence lacks.
     - (b) Add a `must_not_claim` list to each trap in `trap_set.json` for the human check. Examples:
       - TR21: any tonnes CO2e figure, including one converted from the 14,800 litres;
       - TR27: "100%" or "all", including where it leans on E-23 "safeguarding awareness for all staff", which does not say "in date";
       - TR10: any count of door supervisor licences;
       - TR22: £10m public liability;
       - TR26: a mobilisation under 3 weeks.

5. **The "client" type is broader than SPEC's wording.**
   - SPEC A6a lists "invented clients". Only S03 (Northgate City Council) and S16 (Westmoor Borough Council) are invented.
   - The other 8 (S08, S10, S20, S22, S28, S32, S34, S40) are real clients given work they never had. These are valid false claims, and harder than invented names, but the label doesn't match the bar.
   - Suggested fix: one line in `eval/keys/README.md` defining `client` as "an invented client, or a real client credited with work not done for them (8 of 10)". This makes the A6a misses-by-type report read correctly. No data change.

6. **F12, first sentence, over-generalises and could be counted as a false flag.**
   - "We process personal data as a data processor under UK GDPR ... [E-12]."
   - E-12 says only: "We process personal data of our employees and, on some sites, hold key-holder lists and incident reports for clients as a data processor under UK GDPR." For employee data, the firm is a controller.
   - A strict checker could correctly flag this unseeded sentence as unsupported. That raises the false-flag rate, and since it overlaps no seeded span it can't be scored.
   - Suggested fix: "On some sites we hold client key-holder lists and incident reports as a data processor under UK GDPR, and we are registered with the data protection regulator [E-12]." Check that S23 and S24 still appear exactly once.

## Notes (no fix required)

- **N1 (evidence consistency).** E-22 says the parks team is "6 operatives (5 TUPE transferees, 1 apprentice)". E-15 says "5 grounds staff transferred in; 4 remain".
  - F05 states "5 of whom transferred in under TUPE [E-22]". That is true to E-22, and E-15 is not in F05's retrieved set, so it doesn't affect A6a.
  - It could confuse A5 reviewers on live drafts. The optional fix is to change E-22 to "(4 remaining TUPE transferees, 1 apprentice, 1 new hire)" and regenerate `evidence_map.json` and the test hashes. That is fine before the freeze.
- **N2.** DT04 and DT05 draw on the same "do not do" and "not provided" lines (E-1, E-18) as TR06 to TR10, but they ask about other services (catering, cash-in-transit). This is acceptable as the same trap pattern with different facts. DT01, DT07 and DT08 are acceptable on the same basis.
- **N3.** TR17 (Northgate City Council) and S03 use the same invented client. That is harmless because the A8 and A6a runs are separate, but a different name for one of them would keep the two keys independent.
- **N4.** `evidence_map.json` lists 26 of the 32 entries (only the E-n the drafts cite) while `total_passages` is 32. That works for the drafts, but listing all 32 would let the test also pin E-9, E-10, E-23, E-25, E-30 and E-31, which the trap `why` fields rely on.
- **N5 (difficulty).** 9 of the 10 accreditation claims are contradicted by an explicit "not held" line, which makes that type easy. The number, date and client types include harder cases (S12 with a distractor date in the retrieved E-5, S20, S32, S40), so overall difficulty is reasonable. EVAL.md should report misses by type, as it already plans to.
- Every seeded span appears exactly once in its draft, and every draft has exactly 2 seeded claims.
