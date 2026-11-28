# Review: T-216 slice 1, relative year/acronym boost (`p/sme-council-tender-drafting/T-216` @ 45ae98b)

**Verdict: PASS**

Reviewer: reviewer agent, 2026-11-28.
- Diff: `git diff 45ae98b^ 45ae98b`. It is one commit; its parent 9a1060e is on main.
- Files changed: evidence.py (19 lines changed), test_tender_ingest.py (+35), DESIGN.md, EVAL.md, NEXT.md and retrieval.json.

## Evidence (commands run on a detached worktree at exactly 45ae98b)

**Full backend suite.** I ran `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python -m pytest -o addopts="" -q`, without the hidden-summary flags, to get a real summary line:

```
1271 passed, 1 skipped, 1 warning in 234.77s (0:03:54)
exit 0
```

This confirms the builder's dot-counted 1271 / 1.

**Recall.** I ran `eval.run.retrieval_diagnostic` on the seeded demo tenant from the T-214 re-review. The seed has no schema change since then.

| | Recall@8 | primary hit @8 | k=5 recall | primary hit @5 |
|---|---|---|---|---|
| pooled | **0.745** | 0.964 | **0.626** | 0.929 |
| S04 | 0.669 | | | |
| S08 | 0.833 | | | |
| S12 | 0.733 | | | |

These match EVAL.md, NEXT.md and `retrieval.json`.

**Year/acronym tokens in the 30 labelled questions.** Only 4 questions contain one, and at most 2 appear in any one question. In 2 of those questions the boost moves a passage above the top-ranked one, and both are genuinely close candidates:
- E-18: rank 0.118 against a best of 0.119.
- E-12: rank 0.098 against a best of 0.128.

## Correctness

- **Order of operations** (`evidence.py:127-139`):
  1. `best` is the maximum absolute rank over **all** scored candidates (up to 300).
  2. It is computed **before** the boost, the floor and the per-document cap.
  3. Each hit's boost uses that `best`.
  4. The sort is by score.
  5. The loop then applies `min_score` and the per-doc cap.

  This is the right order:
  - The best candidate always survives the cap anyway, since it is first in its document.
  - Computing `best` after capping would make the boost depend on which passages the cap kept, which is circular.
  - The boost decides which passages of a document survive the cap, which is intended.
  - With no candidates the result is still [] (and `best` is 0).
- **Code boost:** unchanged and absolute. `w >= CODE_BOOST` picks out codes because the token weights are exactly 1.0 and 0.25. `test_the_code_boost_still_beats_any_rank_and_is_not_scaled` checks that `score - rank == 1.0`.
- **Tenant scoping and SQL:** untouched by this commit.

## Findings (all non-blocking)

1. **Several tokens add up, so "reorders close candidates only" holds only for one or two tokens** (`evidence.py:132`, DESIGN 4.2).
   - Each matching year or acronym adds 0.25 × best, summed up to MAX_BOOST 3.0. With k tokens, a passage overtakes the best (which holds none of them) once rank > best × (1 − 0.25k). At k=4, any matching passage overtakes it, however weak.
   - Tender questions that name four acronyms ("TUPE, COSHH, DBS and CCTV") are plausible. The demo labels max out at 2, so the eval does not exercise this.
   - Suggestion: cap the relative part, for example `min(sum_relative, 0.25 * best)`, or count each kind once. Alternatively, qualify the DESIGN sentence ("per token; several tokens add up").
2. **The boost can still lift a weak retrieval over `RETRIEVAL_FLOOR`.**
   - The floor applies to `score`, which is rank plus boost. The boost scales with `best`, so it lifts a weak search much less than the old +0.25 did. But a search whose best rank is just under the floor F still passes once best × (1 + 0.25k) ≥ F.
   - A code match (+1.0) passes any floor below 1, which is probably intended.
   - The floor is 0 today, so nothing changes yet. When L1 tunes it, decide whether the floor should test `rank` (or `best`) rather than `score`, and add a test. DESIGN 4.2 currently says only that the floor "applies to `score`", which is accurate but does not mention this.
3. **Tests:** the three new tests check behaviour and are well aimed. The second one pins the relative magnitude (`== 0.25 * best`), not just the order. Missing:
   - a test with several tokens (finding 1);
   - a test of the floor with a boosted weak hit (finding 2).
4. **Honesty of the docs: OK.**
   - EVAL.md and NEXT.md report 0.745 / 0.626 with the before figures and say in bold that recall is still below 0.8.
   - NEXT.md says plainly that this equals the "boost off" figure from T-214, so the relative boost adds nothing beyond removing the old absolute boost's cost.
   - "0.25 fixed a priori, not swept" is fair. The T-214 sweep was of the absolute form, and 0.25 is the value carried over, not one picked from that sweep.
   - The T-214 R2 doc fixes are superseded by the new DESIGN wording. The only overstatement left is "reorders close candidates only" (finding 1).
5. **Nit:** telling codes from other tokens by `w >= CODE_BOOST` silently breaks if anyone sets `TOKEN_BOOST` to 1.0 or more. Returning a kind flag from `must_have_tokens` would be clearer.

## Verdict
**PASS.** The change is correct, the ordering relative to the floor and cap is sound, the tests are green with a real summary line (1271 passed, 1 skipped), and the recall is reproduced. Findings 1 and 2 are worth folding into the next T-216 slice. Neither is a regression: both were worse with the old absolute +0.25.
