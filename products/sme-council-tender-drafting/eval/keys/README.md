# Pre-registered eval keys (T-196, part 1)

| File | What it is |
|---|---|
| `trap_set.json` | 30 trap questions (20 `missing`, 10 `partial`) for A8 and the gap-marker check. Each `why` names the evidence file that shows the gap. |
| `dev_trap_set.json` | 10 tuning-only trap questions (DT01 to DT10). Different topics from the 30; the only trap data prompt tuning may use. |
| `fixture_drafts.json` | 20 hand-written drafts (F01 to F20) with `[E-n]` citations and the `retrieved_ids` the checker is given. |
| `seeded_claims.json` | The 40 seeded false claims (2 per draft; 10 each of number, client, accreditation, date). Each `span` occurs exactly once in its draft. Used by A6a. |
| `evidence_map.json` | How each `[E-n]` was derived (file, passage index, sha256, first 80 characters), from the app's own chunker. |
| `retrieval_labels.json` | qa's hand labels for the 3 demo packs: per question, the relevant E-numbers (`relevant`), the ones that must be found (`primary`), and why. A diagnostic, not a bar. Run `python -m eval.run retrieval` on a freshly seeded demo tenant: Recall@8 (no model call, writes `eval/results/retrieval.json`). Below 0.8, the first fix is query expansion. |

E-numbers assume a fresh demo tenant seeded by `eval/seed.py`. seed.py skips `demo-data/evidence/README.md` (it lists the deliberate gaps and would leak the traps), so E-1 to E-32 are files 01 to 32.

## Rules
- Keys are frozen at the pre-registration commit. Do not edit any file here after any live model run. A change after that is a dated amendment in SPEC.md, never a silent edit.
- `tests/test_tender_eval_keys.py` fails if the evidence or the chunker changes so that the numbering or passage text moves.

## Still to come (once the tender packs exist, Q-20)
- Answer keys for the 9 held-out packs.

## Definitions and scoring rules (pre-registered)
- Seeded claim type `client`: an invented client (S03, S16), or a real library client credited with work it never had (the other 8). `number`, `accreditation` and `date` are a wrong figure, an accreditation not held, and a wrong date.
- A8 (gaps honest): a trap answer passes if it shows a gap marker, OR states an honest negative that cites the passage saying so (for example "we do not hold a parent company guarantee [E-2]"). It fails if it asserts anything in that item's `must_not_claim`. `score.py`'s script half counts gap markers only, so honest-negative answers go to the human check.
- `must_not_claim` is a non-empty list of short strings on every trap and dev-trap item, for that human check.

**Fresh tenant only.** E-n numbers come from a per-tenant counter that only goes up. The keys hold only for a demo tenant seeded once, from empty, by the current `eval/seed.py`. A tenant seeded before README.md was skipped (or re-seeded after deletes) has different numbers: create a new demo tenant before any live eval run.

## Key conventions (pre-registered, T-206 / D3 part 2)

These apply to the pack answer keys `S*.json` (`{"pack": "<file>.docx", "items": [...]}`, in this order: questions in pack order, then mandatory items in pack order, then the deadline; except that a pass/fail question inside the quality section sits at its pack position (S05 Q11 between Q10 and Q12, S10 Q0 first). Order does not affect scoring). Keys are written by hand from the pack text, never from a model run or from `demo-data/evidence/`. A key field is null unless the pack states it unambiguously, because A2 compares every non-null field exactly. A null `word_limit` or `page_limit` means "this item has no limit of its own": an extracted word or page limit against a null key is scored wrong in A2 (an invented limit). A null `marks` or `weight_pct` is "not unambiguous": an extracted value there is not scored, only listed by `score.py` as `invented_unscored` (T-213).

1. **Units.** `word_limit` is words. `page_limit` is pages; one side of A4 is one page ("2 sides of A4", "two A4 pages" both give 2). A limit stated in words is never converted to pages or the reverse. `weight_pct` is a percentage of the whole tender score as printed (a "6%" gives 6). `marks` is used only where the pack gives points ("20 marks"); a percent is never copied into `marks`. A pack scores either in percent or in points, never both (rule 19).
2. **Refs** are written exactly as the pack prints them, without the critical-question asterisk: `1.1`, `2.2(a)`, `Q15`, `M3`. The deadline item has ref `""` (the pack prints none).
3. **Question items.** One per scored question the bidder must answer, including sub-parts that have their own weighting or limit (each is its own item, the parent is not keyed). Sub-parts with no weighting or limit of their own (S05 15(a)/(b)) are one item whose text holds both. Information-only items (SQ "provide your company details", references (unless it is a pass/fail row, rule 4: S03 PF11), "information requests (not scored)", Section D style information parts) are NOT keyed at all.
4. **Mandatory items.** One per pass/fail requirement row or bullet (M1..Mn), plus any pass/fail question printed inside the quality section (S01 2.4, S05 Q11). Such a pass/fail question is keyed once, as `mandatory`, not also as a `question`, and its `weight_pct` is null. If the pass/fail row states a word cap ("Word limit: 150", "no more than 100 words") that cap is its `word_limit`. A recommended or "expected" action that the pack says will not exclude (S01 site visit) is not mandatory. Conditional requirements are keyed as mandatory only if the pack says failure excludes the bid.
5. **Own limit versus general rule.** A limit printed with the question, in its table row, or in the heading of its section ("max 500 words per question", "each answer in 4.1 and 4.2 is limited to 400 words") is that question's `word_limit`. A pack-wide default ("unless otherwise stated, 400 words per question", S05 2.4) is also copied to every question that has no limit of its own, because the pack says it applies to each one.
6. **Per-item limits.** "400 words per case study" gives `word_limit: 400` (the per-item value, never the doubled total) with the extra non-scored field `"case_studies": 2`. The same holds for pages ("one side of A4 per case study", S03 4.3, gives `page_limit: 1` with `case_studies: 2`).
7. **Limits shared across questions** ("800 words in total across 2.1-2.3"): `word_limit` is null on each member, because no single item has a checkable limit. An extracted word limit on a member is therefore scored wrong in A2 (invented), and A7 does not score the member. The items carry the extra non-scored fields `"shared_group"` (for example `"2.1-2.3"`) and `"shared_words"`. A combined limit within a single keyed item (S05 Q15, 500 words for 15(a) and 15(b)) is that item's `word_limit`.
8. **Whole-response budgets** (S11 20 pages, S12 12 sides) are not copied into any question. Questions without a limit of their own keep `word_limit: null`, and `page_limit: null`. An extracted limit copied from the budget onto such a question is an invented limit and is scored wrong in A2. The budget is not a key item.
9. **Page limits** on a question go in `page_limit`; `word_limit` stays null unless a word limit is also printed.
10. **Scored by marks that are not printed** (a question with no weighting at all): `weight_pct` null.
11. **Deadline.** Exactly one `deadline` item per pack: the tender submission deadline. `score.py` reports whether the extractor found it (date, and time separately) but it is not a bar (EVAL.md). Text starts "Tender submission deadline:" and includes the date and time as printed. Other dates (clarifications, site visits, award) are not keyed.
12. **Unscored but required** items (S01 3.3 information requests, S05 references) are not keyed, per rule 3.
13. **Text.** The item `text` is the pack's own wording, the first one or two sentences of the question (limits in brackets removed). A key is faithful if a reader can find it verbatim in the pack.
14. **Extra fields** (`case_studies`, `shared_group`, `shared_words`) are ignored by `score.py` (which scores only `word_limit`, `page_limit`, `marks` and `weight_pct`, with null handled as in the A2 note above) and checked by `tests/test_tender_pack_keys.py`.
15. **Unnumbered items** (pass/fail bullets with no printed ref, S10 1.4) get a synthetic ref `<section>-<n>` in print order (`1.4-1` .. `1.4-8`). A ref match against the extractor will then fail (it cannot know the synthetic ref), so these items rely on text similarity >= 0.8, which is the intended test of whether the extractor reproduces the bullet's wording.
16. **Ref label.** A leading word "Question" is dropped (`Question 2.1:` gives `2.1`); a printed letter prefix stays (`Q1`, `PF3`, `M7`, `C4`, `P2`).
17. **Decision (Studio Lead, T-206 part B): general-rule limits stay copied to each question** (rule 5), because a careful human reads the pack that way. If the extractor misses a general rule (S05 2.4 for Q12, S02 Part 1 section 3, S10 1.3; S11 has no general per-question rule), that is an extraction miss and counts against A2. It is not fixed by editing the key.
18. **Selection questionnaires described as a whole** (S11 1.6 parts 1-7, S09 Section D, S10 1.6a) are information requests and are not keyed; only the pass/fail table or list is (S11 P9 covers "completed SQ"). A briefing that is mandatory only for a stated option (S11 pitch briefing, for storage-compound use) is not keyed.
19. **Marks packs** (S06: "10 marks") use `marks` and leave `weight_pct` null; percent packs leave `marks` null.
