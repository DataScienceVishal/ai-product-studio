# Review: T-214 retrieval rescoring (`p/sme-council-tender-drafting/T-214` @ 66e78f7)

**Verdict: CHANGES**

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff main...66e78f7` (evidence.py +101, test_tender_ingest.py +19, eval/results/retrieval.json, NEXT.md).

## Summary

BM25 rescoring is the right direction, and the tenant scoping is sound. All three new SQL statements filter on `tenant_id`. The synonym expansion is passed as bound parameters and goes through `quote_literal`, so it is injection-safe. Synonyms cannot let a passage in on their own. The must-have code boost still beats rank. The tests are green. I reproduced the branch's numbers exactly.

Merging is blocked for three reasons:

1. The BM25 length normalisation compares two different measures.
2. The whole synonym gain, which is what takes recall from 0.76 to above the 0.8 trigger, comes from six entries. Each maps a word in a labelled question to the heading words of that question's labelled passage in the one demo library. With the length bug fixed, the result is 0.802, which only just clears the trigger, and all of that rests on the fitted entries.
3. DESIGN 4.2 and EVAL.md still describe the old ranking. The engineering rule is that docs change in the same change as the code.

## Evidence (commands run)

Setup: a detached worktree at 66e78f7, PostgreSQL 16 local, python3.13 venv from `requirements-dev.txt`.

- `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python -m pytest -q -o addopts="" tests/test_tender_ingest.py tests/test_tender_draft.py`: **63 passed** in 24.6 s.
- Full backend suite on the exact tree: **1265 passed, 1 skipped, 0 failed, exit 0** (243 s).
- Recall: fresh DB, `alembic upgrade head`, `UPLOADS_PER_HOUR=1000 python -m eval.seed`, then `python -m eval.run retrieval`.
  - Recall@8: S04 0.735, S08 0.852, S12 0.858, **pooled 0.817**, primary hit 1.00.
  - k=5: recall **0.642**, primary hit 0.893.
  - This is identical to the committed `eval/results/retrieval.json` (`git status` clean after the run).
  - Note: the default `uploads_per_hour` makes the seed hit 429 partway through, which gives a bogus 0.19. The seed docs should mention this.
- Ablations: a scratch script monkeypatches `evidence.SYNONYMS` and `_bm25` and calls `eval.run.retrieval_diagnostic`. No product code was edited.

| variant | Recall@8 pooled | k=5 |
|---|---|---|
| as built (BM25 + full SYNONYMS) | 0.817 | 0.642 |
| SYNONYMS = {} (BM25 alone) | 0.760 | 0.626 |
| SYNONYMS minus the 16 library/label-shaped keys (keeps mobilisation, tupe, transition, training, induction, continuity, environmental) | 0.760 | 0.626 |
| only `supervision`, `holiday`, `quality` | 0.793 | - |
| as built, BM25 length made consistent (finding 1) | **0.802** | 0.642 |
| BM25 alone, length consistent | **0.751** | 0.626 |

Single-entry gains over 0.760:

| entry | Recall@8 |
|---|---|
| supervision | 0.779 |
| case | 0.777 |
| references | 0.777 |
| staffing | 0.768 |
| holiday | 0.767 |
| quality | 0.767 |
| each of the other 17 | 0.760 (no gain) |

## Findings

### 1. BLOCKING: the BM25 document length and average length use different units
`evidence.py:104` vs `evidence.py:129`

- `_STATS` sets `avg_len = avg(length(e.tsv))`. `length(tsvector)` is the number of **distinct lexemes**.
- `_bm25` sets `length = sum(tf.values())`, the number of **lexeme positions**.
- On the demo library: average distinct lexemes per passage is 112.5, average positions is 158.1. The per-passage positions/distinct ratio runs from 1.16 to 1.89.
- So `length/avg_len` is inflated by about 1.4 on average, and the inflation is uneven: repetitive passages are penalised more than BM25 intends. This is the "correctness of the BM25 math" item, and it is wrong.
- Fixing it (use `len(tf)`, or compute avg_len from positions) lowers pooled Recall@8 from 0.817 to 0.802, and BM25 alone from 0.760 to 0.751. The tuning partly leaned on the bug.
- **Fix:** use one measure on both sides. Distinct lexemes (`len(tf)` against `avg(length(tsv))`) is simplest. Add a unit test of `_bm25` that pins the length term. Then re-run the eval and report the new numbers.

### 2. BLOCKING: the SYNONYMS map is fitted to the demo library and the labelled questions
`evidence.py:66-77`

- There are no client, pack or product names, so it passes the narrow check. But the entries that move recall are not synonyms. Each maps a word in a labelled question to the heading or filename words of the labelled passage:
  - `holiday -> "cover absence personnel"`, `supervision -> "personnel roles management"` and `staffing -> "personnel roles"` hit `32-key-personnel-roles.md` ("Key personnel (roles only)"). The questions are S04 Q4 ("supervised ... ill or on holiday", labels include 32) and S12 Q2 ("staffing, supervision and holiday cover", labels 13, 19, 29, 32). "Holiday" is not a synonym of "personnel".
  - `case` and `references -> "client results challenge"` hit the case-study section headings "## Challenge" and "## Results" (files 20 to 25). The question is S12 Q10 ("two relevant case studies or references", labels 20, 22). "case" is also a very general word ("in case of", "case management").
  - `complaint`, `report` and `kpi -> "account management ..."` reproduce the heading of `29-account-management-and-complaints.md` (S08 Q8, S12 Q8, both label 29). `report -> "account management"` is not general vocabulary.
  - `quality -> "policy audit inspection"` and `monitor -> "inspection audit"` (S04 Q8 and S12 Q8 label 4, the quality *policy*).
  - `carbon -> "emissions vehicles sustainability"` (S08 Q10) and `recruit -> "vetting induction"` (S08 Q3, label 28).
- The ablation shows every entry that is plausibly general (mobilisation/tupe/transition, training/induction, continuity, environmental) adds **0.000**. The whole +0.057 comes from the fitted entries.
- The held-out packs search the **same** demo library, so a held-out run would still flatter this map. A real customer library will not have these headings.
- NEXT.md flags the in-sample risk honestly. But the board line and STATUS headline "raised past the 0.8 trigger", and that claim does not survive: 0.760 without the fitted map, 0.751 with finding 1 fixed.
- **Fix (pick one, record it in DECISIONS):**
  - (a) Preferred: drop the library- and label-shaped entries. Keep only true equivalences (mobilisation/transition/TUPE/onboarding, training/induction, continuity/disaster recovery, carbon/emissions, safeguarding/DBS). Report the honest number (about 0.75 at k=8) and record that the 0.8 trigger is not yet met, so the next step is query expansion from the scoring criteria or embeddings (DESIGN 4.2).
  - (b) Keep the map, but label the EVAL.md and board numbers "in-sample, map written from these labels". State the BM25-only figure as the unbiased one, and do not mark the trigger as cleared.
- The test `test_domain_synonyms_add_score_but_never_admit_a_passage_alone` is fine either way.

### 3. BLOCKING (docs in the same change, engineering.md "Working rules"): DESIGN 4.2 and EVAL.md not updated
- DESIGN 4.2 still says ranking uses `ts_rank_cd(tsv, q, 32)` over an OR query, with no synonyms, BM25 or 0-1 rank.
- The EVAL.md "Retrieval diagnostic" row still has only the before numbers. T-214's own board line requires "report before/after in EVAL.md". NEXT.md lists it as not done.
- Update both, with the post-fix numbers from findings 1 and 2.

### 4. Non-blocking (decide before L1 floor tuning): the normalised `rank` makes `RETRIEVAL_FLOOR` structurally useless
`evidence.py:152,159`

- `rank = raw / top`, so the best candidate always has rank 1.0 and score at least 1.0, whatever the match quality. `min_score=RETRIEVAL_FLOOR` (draft.py:260, tender.py:419, eval/run.py:325) can therefore never turn a weak retrieval into "No evidence found". DESIGN 4.2 relies on exactly that ("nothing scores above a floor set during tuning", the deterministic gap path). One stray matching word gives a full-confidence top hit.
- Today the floor is 0, and both gap questions retrieved something before and after this change (`gap_retrieved_anything` 2/2), so nothing regresses yet.
- The API also now shows `rank: 1.0` for every top hit.
- **Fix:** keep an absolute score for the floor. For example, filter on raw BM25 (or on raw BM25 divided by the sum of the question's own-term idf, which is query-normalised but not candidate-normalised), and use the per-query 0-1 value only for display.

### 5. Non-blocking: about 36 round trips per search instead of 1, mostly for constants
`evidence.py:84-100,141`

- I counted with a SQLAlchemy `before_cursor_execute` hook: one 23-word question took **36 statements**. "Describe your approach" took 30. A stopword-only question took 1. The empty string took 0.
- The breakdown:
  - `_expansions` stems all 23 SYNONYMS keys with one `to_tsvector` round trip each, on every search, though they are constant.
  - `own` runs one `numnode(plainto_tsquery(...))` query per question lexeme (line 141). That is redundant: lexemes from `to_tsvector('english')` have already had stopwords removed.
  - Then one query per asked key, plus STATS, DF and CAND.
- Local latency on the 32-passage demo tenant: main 2.0 ms/search, branch 11.0 ms. Each extra round trip costs real time against Azure Postgres, and drafting calls this once per requirement.
- **Fix:** stem the SYNONYMS keys and values once, with a module-level cache filled on first use (or a single `unnest` query). Stem the question in one statement. Drop the per-lexeme `numnode` check. That brings it to about 5 statements.

### 6. Non-blocking: scale (CANDIDATES 300, three extra statements)
- I added synthetic tenants by copying the demo library: Bulk A with 5,120 passages and Bulk B with 20,000. Average over the 30 labelled questions:

| tenant | main | branch |
|---|---|---|
| demo (32 passages) | 2.0 ms | 11.0 ms |
| Bulk A (5,120) | 208 ms | 357 ms |
| Bulk B (20,000) | 816 ms | 1,189 ms |

- Per statement on Bulk B for one question: STATS 42 ms, DF 56 ms, CAND 325 ms.
- So the branch is about 1.5x main at scale. Main itself is already slow at thousands of passages, because the OR query matches most rows and `ts_rank_cd` sorts them. The synthetic rows are heavy duplicates, so treat these as rough figures.
- This is acceptable for SME libraries of hundreds of passages.
- **Suggestion:** STATS (count and average length per tenant) could be cached, or kept in a small per-tenant table updated on ingest and delete. Record the limit in DESIGN 4.2.

### 7. Non-blocking: TOKEN_BOOST semantics changed silently; the comment is stale
`evidence.py:14`

- Before, `ts_rank_cd(...,32)` values were small (usually well under 0.3), so a year or acronym match (+0.25) usually moved a passage to the top. Now rank fills 0 to 1, so +0.25 is a quarter of the best match. For questions with "COSHH", "DBS", "BS 7858" or "2025/26", that is a real reweighting, and no test covers it.
- CODE_BOOST still wins strictly: rank > 0 is guaranteed because `raw <= 0` is skipped and idf > 0, so a code hit scores 1 + ε against at most 1.0 for a non-code hit. `test_iso_14001_ranks_over_iso_9001` passes.
- The comment "ts_rank_cd(..., 32) is below 1, so a code match always wins" now describes the wrong mechanism.
- **Fix:** update the comment. Decide whether TOKEN_BOOST should move to about 0.5, and add a test where an acronym passage should rank first.

### 8. Non-blocking: tenant scoping is correct; one style nit
`evidence.py:108-114`

- `_STATS`, `_DF` and `_CAND` all carry `e.tenant_id = :tenant`. `_lexemes` touches no table. In `_DF`, the tenant filter sits in the LEFT JOIN's ON clause, so `count(e.id)` counts only that tenant's rows (correct for a LEFT JOIN). `source_documents` is constrained only through `d.tenant_id = e.tenant_id`.
- That is safe, but it breaks the file's own convention ("Every query carries tenant_id in SQL", and `_STATS`/`_CAND` also state `d.tenant_id = :tenant`). Add it for consistency.
- No test pins df/length isolation. **Suggestion:** a test where tenant B holds many passages containing the rare word, and tenant A's ranking is unchanged.

### 9. Non-blocking: edge cases checked, all OK
- Empty string or whitespace: returns [] with 0 queries.
- Stopword-only question ("the and of a"): returns [] after 1 query.
- Empty library: n=0, so CAND is empty and the result is [].
- Single passage: idf = ln(1 + 0.5/1.5) = 0.288 > 0.
- `avg_len` 0 is guarded (`avg_len or length`). `top` 0 is guarded (`or 1.0`). A zero-length tsv cannot match CAND.
- I fuzzed with backslashes, quotes, tsquery operators (`& | ! <-> :*`), `'); DROP TABLE tenants; --`, unicode, a URL with a quote, and a 5,000-character input. There were no exceptions, and none of the inputs got past the quoting (`quote_literal` plus bound arrays).
- The `_TV` regex handles weight labels (`[0-9A-D,]`). A stripped tsvector (no positions) would give tf 0 and be silently dropped. The generated column always has positions, so that cannot happen today.

### 10. Non-blocking: tests
- The two new tests check behaviour and are well named. Missing:
  - a `_bm25` unit test (it would have caught finding 1);
  - a cross-tenant df test (finding 8);
  - a test that a below-floor retrieval yields [] once the floor is absolute (finding 4).

## What must change before PASS
1. Make the BM25 length consistent, add a unit test, and re-run `python -m eval.run retrieval`.
2. Strip the SYNONYMS entries shaped to the library and labels, or explicitly label the gain as in-sample. Either way, the board, STATUS and EVAL.md must stop calling the 0.8 trigger cleared unless the honest number clears it.
3. Update DESIGN 4.2 (ranking method, synonyms, normalised rank) and the EVAL.md before/after row.

---

## Re-review: 877a936 (2026-11-28)

**Verdict: PASS.** Before merge, two sentences in the docs need correcting (R2 below). This is a docs-only fix, and the Studio Lead can check it in the diff without another re-review.

Diff checked: `git diff 66e78f7 877a936`. Changed files: evidence.py, test_tender_ingest.py, DESIGN.md, EVAL.md, NEXT.md and retrieval.json. Everything below was run on a detached worktree at exactly 877a936, which includes the docs commit.

### Evidence (commands run)
- `pytest -q -o addopts="" tests/test_tender_ingest.py`: **46 passed**.
- **Full backend suite on 877a936: 1268 passed, 1 skipped, 0 failed, exit 0** (245 s). This matches the builder's count, so the docs edits changed nothing.
- `UPLOADS_PER_HOUR=1000 python -m eval.seed` on a fresh DB, then `python -m eval.run retrieval`:

| | Recall@8 | primary hit @8 | k=5 recall | primary hit @5 |
|---|---|---|---|---|
| pooled | **0.727** | 0.929 | **0.602** | 0.893 |
| S04 | 0.669 | | | |
| S08 | 0.778 | | | |
| S12 | 0.733 | | | |

  - These match EVAL.md, NEXT.md and the committed `retrieval.json`.
  - The only diff against the committed file is the last float digit of two recall values (`0.6023809523809522` vs `...524`). The retrieved lists are identical. That is float summation noise, not a correctness problem.
- I counted statements with a SQLAlchemy `before_cursor_execute` hook:
  - **Exactly 4 for each of the 30 labelled questions.**
  - The empty string takes 0. A stopword-only question takes 1 and returns [].
  - Average time on the 32-passage demo tenant: 6.5 ms (previous tip 11.0, main 2.0).
- Scale, using the same synthetic tenants as before:

| tenant | main | previous tip | 877a936 |
|---|---|---|---|
| Bulk A (5,120 passages) | 208 ms | 357 ms | **298 ms** |
| Bulk B (20,000 passages) | 816 ms | 1,189 ms | **913 ms** |

  DESIGN 4.2 now records the scale limit.
- I re-ran the fuzz inputs: quotes, `'); DROP TABLE tenants; --`, backslashes and tsquery operators. There were no errors, and none of the inputs got past the quoting.

### Original findings, status
1. **BM25 length: fixed.** `evidence.py:103` uses `length = len(tf)` (distinct lexemes), which matches `avg(length(tsv))`. The new test `test_bm25_length_term_uses_distinct_lexemes_on_both_sides` pins the formula: 3 positions of one lexeme give length 2, not 4, checked at two average lengths.
2. **Synonym overfitting: fixed.** `SYNONYMS`, `_expansions` and `EXPANSION_WEIGHT` are gone. Candidates and scoring both use only the question's own lexemes. EVAL.md states that k=8 is still below the 0.8 trigger. It also says the synonym map was removed because it was in-sample, and that BM25 alone is the unbiased gain (0.68 to 0.73). The board line still carries the old 0.82 claim from the previous tip, so the Studio Lead should update it when recording the merge.
3. **Docs: done.** DESIGN 4.2 now describes the two-step search, the tenant-scoped statistics, the absolute rank, the floor and the scale note. EVAL.md has the before/after row. Two inaccuracies remain; see R2.
4. **Floor: fixed.**
   - `rank = raw / (sum(idf) * (k1+1))` (`evidence.py:123,132`). For each term, tf*(k1+1)/(tf+norm) < k1+1 because norm >= k1*(1-b) > 0, so rank is strictly between 0 and 1 and the code boost (+1.0) still always wins.
   - `test_retrieval_floor_can_reject_a_weakly_related_pack` shows a one-word match gets rank < 0.3, and `min_score=0.3` returns [].
   - On the demo labels the floor cannot yet separate gap questions cleanly: the two gap questions' top hits have rank 0.054 and 0.118, and the lowest answerable top hit is 0.069. That is a job for L1 tuning, not a defect here.
5. **Round trips: fixed** (4 statements, see above).
6. **Scale:** acceptable and documented.
7. **TOKEN_BOOST:** see R1.
8. **`_DF` tenant filter: fixed.** `evidence.py:84` adds `d.tenant_id = :tenant`. The new test `test_df_is_per_tenant` gives tenant B 10 passages containing the query words and asserts that tenant A's ranks are unchanged to 9 decimals. Since n, df and avg_len all feed rank, that test would catch a leak.

### Re-review findings
**R1. Non-blocking: leaving TOKEN_BOOST at 0.25 is acceptable, but it now behaves differently from what the docs say.**

- Measured top-1 rank over the 28 answerable questions on this branch: median 0.118, range 0.069 to 0.385. Every rank returned for any question fell between 0.017 and 0.385.
- On main, `ts_rank_cd` gave top-1 median 0.564 (max 0.73).
- So a +0.25 year or acronym boost has gone from about half the typical top rank to about twice it. In practice it now lifts any passage holding a year or acronym above every passage that lacks one.
- Sweep (pooled recall at k=8 / k=5 / primary hit @8):

| TOKEN_BOOST | 877a936 | main |
|---|---|---|
| 0.0 | 0.745 / 0.626 / 0.964 | 0.676 / 0.529 (k=8 / k=5) |
| 0.1 | 0.727 / 0.602 / 0.929 | - |
| 0.25 | 0.727 / 0.602 / 0.929 | 0.682 / 0.524 (k=8 / k=5) |
| 0.5 | 0.727 / 0.602 / 0.929 | - |

  The boost helped slightly on main and costs about 0.02 here.
- Keeping 0.25 is defensible. The difference is about one question in 28, picking a value from this sweep would be tuning on the labels (exactly what finding 2 removed), and code boosts, the case that matters for "ISO 14001", are unaffected.
- Suggested follow-up, chosen without the labels: express the year/acronym boost relative to the candidate set, for example 0.25 times the best candidate's rank, so its effect stays the same whatever the rank scale. Or decide at L1 on a held-out pack.

**R2. Fix before merge (docs only): two sentences misstate the boost.**
- `DESIGN.md:98` says the +0.25 is "a quarter of the rank scale, so it can reorder close candidates". In practice no rank observed exceeded 0.385, so it overrides nearly all BM25 differences. Suggested wording: "a year or acronym +0.25, which is larger than typical BM25 ranks (top hit median about 0.12 on the demo library), so in practice it lifts any passage with that token above those without; left untuned (T-214 re-review R1)".
- `NEXT.md:7` says ranks are "typically 0.2 to 0.5". Measured: top-1 median 0.12, all returned ranks 0.017 to 0.385. Correct the range.

**R3. Nit:** `EVAL.md:18` is missing a full stop: "... embeddings Tuning may use these labels".

**R4. Nit:** the board line for T-214 still says "Recall@8 0.68->0.82". Update it to 0.73 (k=5 0.60) when recording the merge.

### Verdict
**PASS.** The code is correct, tenant-safe, injection-safe and tested, and the full suite is green on the exact tree. Apply the R2 sentence fixes (and the R3/R4 nits) in the merge commit.
