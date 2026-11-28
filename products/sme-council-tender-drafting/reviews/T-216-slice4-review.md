# Review: T-216 slice 4 (RM3 pseudo-relevance feedback in `search_evidence`)

- Branch: `p/sme-council-tender-drafting/T-216-s4`, head `71d0032`, against `main` (`git diff main...branch`)
- Reviewer: reviewer agent, 2026-11-28
- **Verdict: PASS.** Nothing blocks the merge. Suggestions 1 and 2 are doc fixes and should go in with the merge or straight after it.

## Summary

The diff adds `_prf_weights` and a second scoring pass in `search_evidence` (`app/tender/evidence.py`), controlled by `PRF_ENABLED` (default True). It adds 7 tests and pins `PRF_ENABLED=False` in the 4 boost-arithmetic tests. It also updates DESIGN 4.2, the EVAL.md diagnostic row, NEXT.md and `eval/results/retrieval.json`.

What I checked, with evidence:

- **Full backend suite on `71d0032`.** Run in a separate worktree against a fresh Postgres DB (`s4_review`) with `python3.13 -m pytest -q -o addopts=""`: **1330 passed, 1 skipped** in 380 s.
- **I reproduced the measurement.** Fresh DB, `alembic upgrade head`, `eval.seed` with the raised upload limits, `python -m eval.run retrieval`, then the same seed with `PRF_ENABLED=False`:

  | | pooled recall@8 | primary hit | all primaries | S04 | S08 | S12 |
  |---|---|---|---|---|---|---|
  | off | 0.7446 | 0.9643 | 0.8214 | 0.669 | 0.833 | 0.733 |
  | on | 0.7643 | 1.0000 | 0.8214 | 0.646 | 0.769 | 0.867 |

  These match DESIGN, EVAL, NEXT and the committed `retrieval.json` exactly. I restored the worktree afterwards.
- **No frozen or key files changed.** `git diff main...branch --stat` touches only DESIGN.md, EVAL.md, NEXT.md, `evidence.py`, `test_tender_ingest.py` and `eval/results/retrieval.json`. `eval/keys/`, `FROZEN.sha256` and the packs are unchanged.
- **The parameters were set before measuring.** Commit `4d1077f` (15:21) has the code, the three parameter values (10 / 10 / 0.5), the method (including the idf factor) and the ship rule in DESIGN 4.2, with no result. The result first appears in the next commit, `71d0032`. Commit order cannot prove nobody ran the eval in between, but nothing in the diff points that way. One thing would change the outcome: the idf factor. It was written down in the first commit, so it was not added afterwards. The values 10 / 10 / 0.5 are Anserini's `fbDocs`, `fbTerms` and `originalQueryWeight` defaults. A test pins them.
- **Tenant isolation holds.** The only new SQL is a second run of the existing `_DF` statement. It is scoped to `:tenant` on `evidence_items` and `source_documents`, and both sides have `deleted_at IS NULL` and `d.kind = 'evidence'`. Feedback terms come only from that tenant's own candidates. `test_prf_does_not_see_another_tenant` covers this (another tenant's 6 "gritting" passages leave the ranking unchanged).
- **No injection risk.** Lexemes are passed as a bound `text[]` and turned into tsquery with `quote_literal(...)::tsquery`. I checked a backslash lexeme: `quote_literal('a\b')::tsquery` does not error. It just yields a lexeme that matches nothing (df 0). The English parser does not emit backslashes anyway.
- **`PRF_ENABLED=False` gives exactly the old ranking.** `rank2` starts as `{id: first-pass rank}`. With the flag off it is never replaced, so `best` and `score` are the main-branch expressions, and `_DF` is not run a second time (back to 4 statements). The off-run of the eval reproduces the slice 3 numbers to the last digit.
- **`RETRIEVAL_FLOOR` and the code boost behave as before.** The floor still tests `h.rank`, which is still the first-pass value. A code-holding passage still bypasses the floor through `coded`. The code boost is still +1.0 absolute. `rank2` is BM25 divided by its own ceiling (`c2 = sum(w x idf) x (k1+1)`), so it stays below 1 and a code match still beats any second-pass rank. The year/acronym boost is now relative to `max(rank2)`, as documented. `test_prf_floor_and_code_semantics_unchanged` runs with the flag both off and on.
- **The output is deterministic.** Ties break on `display_no` (unique per tenant) and then on the lexeme.

## Critical issues

None.

## Suggestions (numbered)

1. **Call it "RM3-style", not "RM3 with the Anserini defaults", and list the deviations** (DESIGN 4.2, the `evidence.py:16` comment). The three numbers are Anserini's, but the model differs from Anserini RM3 in three ways:
   - Term weight multiplies by idf (`_prf_weights`, `acc[t] += dw * (c / ln) * idf_all[t]`). Anserini uses doc score x tf/len and drops terms whose df is over 10% of documents.
   - At scoring, `wi = w * idf2[t]` then puts idf on each feedback term a second time, so feedback terms are weighted by about idf squared. The question's own terms get idf once.
   - The second pass reranks the same 300 candidates instead of retrieving again.

   All three were written in DESIGN before measuring, so this is not overfitting. But "literature defaults" overstates how much the outcome is fixed by the literature: fb_terms=10 was tuned for a model without the idf weighting. A doc fix only.
2. **The `search_evidence` docstring still says "Four statements per search"** (`evidence.py`, end of the docstring). It is now five when PRF is on (DESIGN already says five). The docstring should also say that sorting uses the second-pass score while `rank` stays first-pass.
3. **`Hit.rank` against the sort order.** Both `/evidence/search` (`routes/tender.py:121`) and `/requirements/{id}/evidence` (`routes/tender.py:422`) return `rank` and `score`. With PRF on, the list is sorted by `score`, so `rank` is no longer monotone down the list. The frontend does not display or use `rank` (I grepped `app/frontend/src`), so no user sees this today. It matters only to an API reader or someone setting the floor later. That person must know the floor cuts on first-pass relevance while the order is second-pass. This is consistent with DESIGN's "the floor tests raw relevance". I would not change the code. Add one line to DESIGN 4.2 or the API notes saying `rank` is first-pass and not the sort key.
4. **The size of the `_DF` lexeme list has no cap.** It is every distinct lexeme in the top 10 passages, so a few hundred up to about 2,000 for long passages. I timed the same statement shape on a synthetic 3,000-passage table with the GIN index: 1,000 lexemes took 63 ms and 200 lexemes took 13 ms. That is acceptable for a library of hundreds to low thousands, and it runs once per question (about 30 per pack). If it grows, take only the top N terms by tf/len before the idf lookup (N=100 would still be ten times `PRF_FB_TERMS`), or keep per-tenant df up to date on ingest. NEXT.md already notes the 45 ms.
5. **Process: `PRF_ENABLED = True` was already set in `4d1077f`, before the measurement** that, under the ship rule, decides whether it is enabled. The rule was met, so this had no effect. Next time, commit the flag off and flip it in the measurement commit.
6. **Test strength.** `test_prf_off_is_the_first_pass_ranking_exactly` checks `rank == score` and descending order. It does not compare against a reference ranking, so a regression in the off path that keeps those properties would pass. The code path is plainly identical, and the eval off-run confirms it, so this is minor. A small fixture comparing exact (name, score) tuples taken from main would make the test say what its name says.
7. Nit: `import re` in `test_tender_ingest.py` sits in its own group after `uuid`. It belongs with the other stdlib imports.

## Ship decision (PRF on by default)

**Enabling is acceptable.** The pre-stated rule was "pooled recall@8 and primary hit must not fall". Both rose: 0.745 to 0.764, and 0.964 to 1.000. I reproduced both independently. The rule said nothing about per-pack movement or latency. Overriding it now because S04 (-0.022) and S08 (-0.065) fell would itself be a decision made after seeing the results, the forking path the rule exists to prevent.

The branch's own write-up is honest about the limits:
- The gain is about one primary hit and about 0.02 recall over 28 questions, which is noise-level.
- all_primaries is flat pooled but falls in S04 (0.778 to 0.667).
- Latency goes up about 6x (7.5 to 45 ms), which is negligible next to a model call.

Conditions on keeping it on:
- The held-out run after the freeze should report PRF on and off. If held-out recall@8 or primary hit is lower with PRF on, turn it off. That is the real test, because the demo packs are tuning data.
- Do suggestion 1, so nobody later reads "Anserini defaults" as a guarantee against overfitting.

## How I ran it

- Worktree at `71d0032` under the session scratchpad. Fresh DBs `s4_review` for the tests and `s4_eval` for the eval reproduction, then `s4_perf` for the synthetic `_DF` timing, which I dropped afterwards.
- `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/s4_review python3.13 -m pytest -q -o addopts=""` gave 1330 passed, 1 skipped.
- Eval: `alembic upgrade head`, `UPLOADS_PER_HOUR=1000 UPLOAD_PAGES_PER_DAY=100000 python -m eval.seed`, `python -m eval.run retrieval`, run with PRF on and then off. The worktree was restored with `git checkout -- .`.
