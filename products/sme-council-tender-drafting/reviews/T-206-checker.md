# T-206 checker: held-out pack answer keys (independent check)

**Verdict: REVISE.** One limit is wrong in a way that would mark a correct extraction as wrong (S07 Q6). Two items break the README's own rules (S05 Q5 text, S06 deadline). One scoring gap needs a recorded decision before the keys are frozen. Everything else checks out line by line against `demo-data/pack-sources/*.md`: refs, weights, marks, page limits, shared and general-rule limits, mandatory rows and deadlines.

Method: I read all 9 pack sources in full and compared every key item with its pack line. I also read `eval/keys/README.md` (rules 1-19), `eval/score.py` (`match_items`, `score_extraction`) and `app/backend/tests/test_tender_pack_keys.py`. I did not open `demo-data/evidence/`. I had no shell in this session, so the tests were not run and the similarity figures below are hand estimates of `difflib` ratios on `_norm` text.

## Per-pack table

| Pack | Questions keyed (pack) | Mandatory keyed (pack) | Weight/marks total | Deadline | Errors found |
|---|---|---|---|---|---|
| S01 | 18 / 18 | 11 / 11 (M1-M10 + 2.4) | 70% (l.396) | Fri 30 Apr 2027, 12:00 noon (l.24) | none |
| S02 | 9 / 9 | 10 / 10 (C1-C10) | 70% (l.268) | Thu 14 Oct 2027 14:00 (l.21) | none (nit N3) |
| S03 | 9 / 9 | 11 / 11 (PF1-PF11) | 60% (l.266) | 12 noon Mon 10 May 2027 (l.21) | none (nit N3, N6) |
| S05 | 16 / 16 (Q11 keyed as mandatory) | 16 / 16 (M1-M15 + Q11) | 60% (l.335) | 12:00 noon 14 Apr 2027 (l.35) | **MF2**: Q5 text cut off mid-word |
| S06 | 8 / 8 | 11 / 11 (PF1-PF11) | 60 marks (l.167) | 14:00 Fri 23 Apr 2027 (l.31) | **MF3**: deadline prefix; nit N2 |
| S07 | 10 / 10 | 10 / 10 (PF1-PF10) | 70% (l.241) | 12:00 midday Fri 21 May 2027 (l.29) | **MF1**: Q6 word_limit null, should be 400 |
| S09 | 20 / 20 (2.4(a)/(b) split, parent not keyed) | 11 / 11 (M1-M11) | 70% (l.94-96) | 12:00 noon Fri 19 Mar 2027 (l.25) | none (nit N4) |
| S10 | 8 / 8 | 9 / 9 (Q0 + 1.4-1..1.4-8) | 60% (l.175) | 14:00 Thu 11 Feb 2027 (l.23) | none (nit N5) |
| S11 | 13 / 13 | 10 / 10 (P1-P10) | 70% (l.73-74) | 12:00 Fri 30 Apr 2027 (l.23) | none |

Things I checked and found correct:
- General-rule limits (rule 5/17) are applied correctly: S02 Q2, 3, 5, 6, 7, 9 = 500 (Part 1 s.3, l.49). S05 Q12 = 400 (2.4, l.68). S10 Q2, Q3, Q5 = 350 (1.3, l.49).
- Section-heading limits are applied correctly: S01 5.1 = 300 (l.376). S03 2.1/2.2 = 2 pages, 3.1/3.2 = 300, 5.1(a)/(b) = 500. S05 Q1-Q6 = 500, Q7-Q10 = 350. S09 4.1/4.2 = 400.
- Shared limits are right: S06 Q4-Q6 (1,200 words) and S09 2.1-2.3 (800 words).
- The combined limit is right: S05 Q15 = 500.
- Per-item limits are right: S01 5.2 = 400 with case_studies 2, and S03 4.3 = 1 page with case_studies 2.
- The page budget is right: S11 has a 20-page whole-response budget and no question carries it.
- Pass/fail questions inside the quality sections are keyed as mandatory with their word caps: S01 2.4 = 100, S05 Q11 = 150 (it overrides the section's 350), S10 Q0 = 100.

## MUST-FIX

| # | Pack | Ref | Field | Key value | Correct value | Pack line |
|---|---|---|---|---|---|---|
| MF1 | S07 | `6` | `word_limit` | `null` | `400` | S07 .md l.211: "Word limit: 400." under "Question 6: Supervision, welfare and lone workers (7%)". S07 has no general rule (2.2, l.43: "Each question shows its own limit"), so this is the question's own limit. With null, A2 never checks an extractor that gets this limit right or wrong, and A7 would not cap the draft. |
| MF2 | S05 | `Q5` | `text` | ends "...the Council's duty officer, and the re" (cut off mid-word) | end at "...the use of the police and the Council's duty officer, and the reporting that follows." | S05 .md l.269. This breaks rule 13 (the pack's own words, first one or two sentences). It does not affect matching today (estimated ratio against the full sentence is about 0.97), but a frozen key should not hold a broken word. |
| MF3 | S06 | `""` (deadline) | `text` | "Tender return deadline: 14:00 on Friday 23 April 2027" | "Tender submission deadline: 14:00 on Friday 23 April 2027" | Rule 11 says the text starts "Tender submission deadline:". S02 (l.21, "Tender return deadline") and S10 (l.23, "Return of tenders") already follow this rule, so S06 is the only key that does not. The date and time are correct. |
| MF4 | rules / `score.py` | all | `word_limit`, `page_limit` | — | decision needed before freeze | `score_extraction` only scores fields that are non-null in the key, so an extractor that invents a limit is never penalised. Under rule 7 (shared limits null), an extractor that puts 1,200 on each of S06 Q4-Q6, or 800 on each of S09 2.1-2.3, passes A2. Under rule 8, copying S11's 20 pages onto every question also passes, and so does inventing a limit for S11 Q2/Q4/Q5/Q7/Q11. Each of these errors would wrongly let the drafter write up to 3x the real allowance, or wrongly cap a draft. Either (a) score a non-null extracted `word_limit`/`page_limit` against a null key as wrong (my recommendation: these are exactly the cases rules 7 and 8 exist for), or (b) write in the README that false-positive limits are deliberately not scored under A2, and say where they are caught instead. Option (a) changes `score.py`, not the keys, but it must be pre-registered before the freeze. |

## Rule coherence (point 3)

The rules are coherent and the 9 keys apply them consistently, apart from MF1-MF3. My notes on individual rules:

- **Rule 1 vs rule 19 and the test.** Rule 1 says "a pack that gives both uses both fields". The test (`assert all(i["marks"] is None ...)` for percent packs) and rule 19 forbid that. No held-out pack gives both, so nothing breaks today. Reword rule 1 or drop that sentence.
- **Rule 3 vs S03 PF11.** Rule 3 lists "references" as information-only and not keyed, but S03 PF11 ("Two references", a pass/fail row) is keyed as mandatory. That is right under rule 4. Add "unless it is a pass/fail row (rule 4)" to rule 3 so the two rules do not appear to clash.
- **Rule 6 covers words only.** S03 4.3 applies it to pages ("one side of A4 per case study", so 1 page with case_studies 2). Say so in rule 6.
- **Rule 17 mentions "S11 per-question limits" as a general rule.** S11 has no general per-question rule. Every S11 limit is printed with its own question, and the only general limit is the 20-page budget, which rule 8 keeps out of the key. Delete that example, or replace it with the right one.
- **Ordering (README l.30: questions, then mandatory, then deadline).** The keys do not follow it. S05 Q11 sits between Q10 and Q12, and S10 Q0 comes first. Order does not change scoring (pairing is by ref, then best similarity), but either reorder the keys or relax the sentence.
- **Deadline is not scored.** SPEC step 2 lists the deadline as something to extract, but `score_extraction` ignores `kind == "deadline"`. Rule 11 is fine. This is a coverage gap in the scorer, not in the keys; the Studio Lead should note it in EVAL.md or add a check.

## Nits (no score impact expected)

- **N1 (test).** `test_tender_pack_keys.py` checks structure and totals but no individual limits. A small table of spot assertions per pack would have caught MF1, for example S07 `6` = 400, S05 `Q12` = 400, S10 `Q2` = 350 and S06 `Q8` page 1.
- **N2 (S06 Q5 text).** The key keeps only part (a) (l.162). The estimated ratio against a full extraction is about 0.68, so it passes only through the ref match (needs 0.5), not the 0.8 text fallback. S05 Q15 keeps both parts, so for consistency include (b) and "Describe the escalation steps and what is reported afterwards."
- **N3 (S02 C1-C10, S03 PF1-PF11 texts).** These are written as "<Requirement>: <Pass mark>", joining two table cells, so they are not verbatim as rule 13 says. That is reasonable, but an extractor that returns only the first cell drops below the 0.5 ref gate on short labels. Estimates: S02 C9 "Equality" about 0.31, C10 "Exclusion grounds" about 0.49, S03 PF7 "DBS" well below 0.5. If that should count as a miss (I think it should, because the pass mark is the requirement), say so in the README.
- **N4 (S09 1.4 text).** It keeps the limit sentence "Maximum two A4 pages." Rule 13 says to remove limits. Matching is unaffected.
- **N5 (S10 Q0 vs S01 2.4).** S01 keeps the "PASS/FAIL:" prefix in its text and S10 drops "Pass/fail:". Pick one.
- **N6 (refs with sub-parts).** `_norm("2.2(a)")` gives "2 2 a" and `_norm("2.2a")` gives "2 2a", so an extractor that writes `2.2a` misses the ref match and falls back to 0.8 text similarity. That is probably fine, but worth knowing for S01 2.2(a)/(b), S03 5.1(a)/(b) and S09 2.4(a)/(b).

## To reach PASS
Fix MF1-MF3 in the keys. Record the MF4 decision in the README (and change `score.py` if option (a) is taken). Rerun `pytest app/backend/tests/test_tender_pack_keys.py`. A re-check would only need to look at those four items.
