# Review: T-216 slice 2, boost cap, floor on rank, explicit token kind (`p/sme-council-tender-drafting/T-216` @ 97070f3)

**Verdict: PASS**

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff 64c5b4e 97070f3` (the commit message says "decisions: ..." but it also holds the slice-2 code). Files: evidence.py, test_tender_ingest.py (+4 tests, 1 updated), DESIGN.md, EVAL.md, NEXT.md, eval/seed.py, eval/results/retrieval.json, state/DECISIONS.md.

## Evidence

Full backend suite, run in a detached worktree at exactly 97070f3:
`TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""`

```
1275 passed, 1 skipped in 350.86s (0:05:50)
```

This matches the builder's 1275 / 1. I did not reproduce recall (that needs a freshly seeded DB, and the test DB is shared). `retrieval.json` changes only by float rounding plus one reordering inside 4.4(a)'s top 8 (passage 22 moves from 3rd to 5th), so recall staying at 0.745 / 0.626 / 0.964 is consistent with the file.

## Correctness (evidence.py:127-152)

- **Cap.** `boost = min(MAX_BOOST, code + min(rel / TOKEN_BOOST, 1.0) * TOKEN_BOOST * best)`. Every relative token weighs exactly TOKEN_BOOST, so `rel / TOKEN_BOOST` is the number of matching tokens. Any relative match therefore adds exactly 0.25 x best, and a weak passage overtakes the best only if its rank is above 0.75 x best, however many acronyms the question names. Review finding 1 is closed.
- **Floor.** `h.rank < min_score and h.id not in coded` tests rank, with the agreed exception for code matches. Nothing changes at the default of 0.0, because every hit has rank > 0 (the `raw > 0` filter). The floor and the per-document cap still run after the score sort, so a hit that fails the floor never uses up a document's cap slot. That is correct. Finding 2 is closed as decided.
- **Kind.** `must_have_tokens` returns (pattern, weight, kind). A code wins over an acronym with the same text (CHAS) through `setdefault`. All callers were updated: only evidence.py and the test use it. Finding 5 is closed.
- **Unchanged.** `best` is still taken over all candidates before the boost, the floor and the cap. Tenant scoping and the SQL are untouched.

## Tests

The four new tests check behaviour and each would fail on the slice-1 code:
- With four acronyms uncapped, the weak passage would get +1.0 x best and overtake.
- With three tokens it would get 0.75 x best, not 0.25.
- With the floor on score, the boosted weak hit would clear the midpoint floor.
- Without the exemption, the code hit would be rejected at a floor of 0.3.

`test_must_have_tokens` now checks the kinds. Good.

## Findings (all non-blocking)

1. **The formula in the docs is wrong as written.** DESIGN 4.2, the `search_evidence` docstring and NEXT.md say "min(sum of matching weights, 1) x 0.25 x best". The weights are 0.25 each, so read literally, three tokens give min(0.75, 1) x 0.25 = 0.1875 x best. The code (correctly) uses min(count, 1). Write it as "0.25 x best if any year/acronym matches, else 0" (or min(count, 1)). The code expression `min(rel / TOKEN_BOOST, 1.0) * TOKEN_BOOST` could also be simplified to `TOKEN_BOOST if rel else 0`, which is clearer.
2. **Some "score floor" wording is now stale.** These places still say the floor tests the score:
   - `draft.py:32` comment ("minimum retrieval score");
   - DESIGN 4.2 "Shown to the user" ("nothing scores above a floor");
   - DESIGN line 265 ("the score floor");
   - the EVAL.md Retrieval row ("score floor TBD");
   - the `min_score` parameter name.

   Rename the parameter to `min_rank` and fix the wording before L1 tunes the floor, so whoever tunes it is not misled.
3. **A side effect of the code exemption to note when tuning.** Any passage that merely mentions an asked-for code clears any floor, even an incidental mention ("we are working towards ISO 14001"). This is the intended trade-off (DECISIONS 2026-11-28T11:25Z). If L1 sees false "evidence" from incidental mentions, limit the exemption to the top coded hit per document.
4. **Seed doc: OK.** `UPLOADS_PER_HOUR` and `UPLOAD_PAGES_PER_DAY` map to `config.py:46-47` (pydantic settings). The EVAL.md and seed.py instructions are accurate.
5. **Honesty: OK.** NEXT.md and EVAL.md report recall as unchanged and still below the 0.8 trigger. They do not overclaim.

## Verdict

**PASS.** The change is correct, the tests are meaningful and green (1275 passed, 1 skipped), and findings 1, 2 and 5 of the slice-1 review are resolved. Fix findings 1 and 2 above (wording only) in the next T-216 slice.
