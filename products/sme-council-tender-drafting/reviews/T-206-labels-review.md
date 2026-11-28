# Review: p/sme-council-tender-drafting/T-206-labels

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff main...HEAD` (6 commits, ddc90d5 tip). No app code changed (`app/backend/app` untouched).

## Verdict: PASS

There is one condition before merge: regenerate `eval/results/retrieval.json` (see M1). Nothing else blocks.

## Evidence
- Full backend suite on this tree, Postgres `starter_test`: **1262 passed, 1 skipped in 326.94s**. The skip is not in the new file or the key tests.
- Targeted run of `test_tender_retrieval_eval.py`, `test_tender_pack_keys.py` and `test_tender_eval_keys.py`: **36 passed, 0 skipped**, so the label-structure test really ran. The two existing key test files have no changes in the diff.

## What I checked

### Recall maths (`eval/score.py` `retrieval_recall`)
- Per-question recall is |relevant ∩ top-k| / |relevant|. Pooled and per-pack recall are the macro mean over questions with non-empty `relevant`. The docstring says this and `test_pooled_is_mean_over_questions_across_packs` pins it down.
- Only the first k count (`(got or [])[:k]`), checked at k=8 and k=9 by `test_k_cutoff`.
- A question missing from `retrieved` counts as recall 0 and as a primary miss, and it is listed with `not_retrieved: True`. An empty list counts as retrieved-nothing with `not_retrieved: False`. The distinction is correct.
- Gap questions (empty `relevant`) are kept out of `scored` and recall. They are counted, and `gap_retrieved_anything` is reported. Correct.
- `misses` lists every scored question with at least one relevant passage outside the top k. Correct.
- With empty labels the result is `None` and nothing crashes (`_ratio`).
- None of this goes into `BARS` or any `pass` field, which fits DESIGN 4.2 ("diagnostic, not a bar").

### `at_app_passages` (k=5)
- It re-scores the depth-8 retrieval at `dr.APP_PASSAGES` (5). This is valid only if the top 5 of `limit=8` equals what `limit=5` returns. I checked `search_evidence` (`app/tender/evidence.py:79-102`): the sort is deterministic (`-score, display_no`), and the per-doc cap and floor are applied greedily before the `limit` break. So the top 5 is exactly a prefix of the top 8. Correct.

### Same retrieval path as drafting
- `draft.py:260` calls `search_evidence(db, tenant, rtext, limit=APP_PASSAGES, min_score=RETRIEVAL_FLOOR)`, with per_doc taken from the default `PER_DOC=3`.
- The runner calls `search_evidence(db, tenant_id, text, limit=8, min_score=dr.RETRIEVAL_FLOOR)` with the same default per_doc. It imports the constants from `draft` rather than copying them, so it follows any change made during tuning. The only difference is depth, which is intended.
- Tenant scoping is the SQL `e.tenant_id = :tenant AND d.tenant_id = :tenant`. The tenant is the `FIRM` tenant looked up by `main` (unchanged).
- `local_database` still guards the retrieval phase.

### No ledger, no model
- On `phase == "retrieval"` the runner skips `ScriptedFakeAI`, `load_budget_config` and `Ledger`, so they are neither imported nor built. `retrieval_diagnostic` touches only `search_evidence`, which is a read-only SELECT, and ends with `db.rollback()`.
- The test asserts there is no `AIUsage` row afterwards. The labels-missing guard returns 4 before any DB access.

### seed.py change
- `base_url="https://testserver"` and `X-Requested-With: seed` are set on the in-process `TestClient` only. This is eval tooling and changes nothing in the app's CSRF or cookie policy. Safe.

## Must do before merge
- **M1. `eval/results/retrieval.json` is stale.** It was committed at 09:25:16, but it predates the label edits it should reflect. For example, S08 Q2 now has E-13 in `relevant`, and the WIP pooled recall is 0.68 / 0.52@5 on the old labels. Re-run `python -m eval.run retrieval` on a freshly seeded tenant (`UPLOADS_PER_HOUR=1000 UPLOAD_PAGES_PER_DAY=100000`) and commit the output. Otherwise EVAL.md readers will quote numbers for labels that no longer exist.

## Suggestions (non-blocking)
1. **Query text vs drafting text.** The runner queries with the label `text`, which is verbatim from the pack-source markdown. Drafting queries with the parsed requirement `r.text`, and the parser may differ in whitespace, numbering, or limits and marks it strips or keeps. This is fine for a diagnostic, but say it in EVAL.md and the README row. Later, consider running on the parsed requirements of the seeded packs, matched by ref.
2. **Primary semantics.** `primary_hit_rate` counts a hit if *any* primary is in the top k. The label derivation defines primary as "the passage(s) without which the answer would be weak", and some questions have 2 or 3 primaries. Either document "any", or also report an all-primaries rate. The README row also says "the ones that must be found", which reads as "all".
3. **Weak test assertion.** In `test_runner_on_the_real_library_numbers_passages_like_the_keys` (tests/test_tender_retrieval_eval.py, last runner test), `1 <= n <= emap["e"] + 400` bounds almost nothing, and `len(got) > 5` depends on how many files match one first80 query. Asserting `all(1 <= n <= 32 for n in got)` would actually pin the "E-n = file n" numbering the labels rely on.
4. **Stale docstrings.** The test module docstring says "skipped until qa commits ... retrieval_labels.json", but the file is now committed. The `retrieval_diagnostic` docstring says "as draft and the retrieve route call it". The `/search` route at `routes/tender.py:118` uses defaults, which happen to match, and the `/evidence` route uses k=5. Make the docstring precise.
5. **Overwrites without labels.** `main` writes `eval/results/retrieval.json` with no labels hash or timestamp. Add `labels_sha256` so a stale results file is detectable. That would have caught M1.

## Freeze commit (8e0c647): PASS

Reviewed with `git show HEAD`. It changes EVAL.md, `test_tender_eval_keys.py`, `eval/keys/FROZEN.sha256` and the `eval/keys/README.md` freeze note.

### Evidence
- `sha256sum -c eval/keys/FROZEN.sha256` (run from the product root) reports all 34 entries OK.
- The manifest covers all 16 files in `eval/keys/` except itself, plus the `.docx` and source `.md` for each of the 9 `heldout` packs in `demo-data/packs/manifest.json`.
- The key, retrieval and pack-key tests give 37 passed. The coordinator reports the full suite at 1263 passed, 1 skipped on this tree, and a mutation check of the test.
- The test is sound. It fails on any hash change and on any key file missing from the manifest, and it checks every held-out pack in both forms. `hashlib` is imported.

### Correction to M1 (withdrawn)
I re-scored the committed `eval/results/retrieval.json` `retrieved` lists against the current `retrieval_labels.json`. The result is identical to the stored output: pooled 0.6815, S04 0.657, S08 0.787, S12 0.608, primary hit rate 0.857; at k=5, recall 0.524 and primary 0.786; the same 18 misses. The file was written 32 seconds after the label fix commit (3cd3a5c), and it is consistent. The figures EVAL.md quotes are therefore correct, and M1 does not block. Regenerating it is still fine but not required.

### EVAL.md
The new retrieval row covers my nits 1 and 2. It says the query is the label text, not the parsed text, and that the primary hit rate is "any primary". Its numbers match the re-score above.

### Nits (non-blocking, for the board)
- `demo-data/packs/manifest.json` is not itself in FROZEN.sha256. If someone shrinks its `heldout` list, the test checks fewer packs, and the per-file hash check would still catch only the packs left listed. Add the manifest to FROZEN.sha256, or assert `len(heldout) == 9`.
- The hashes are of raw bytes. A checkout with `core.autocrlf=true` would fail the test on `.md` and `.json` files. Add a `.gitattributes` with `eval/keys/** -text` and `demo-data/pack-sources/** -text` (or `eol=lf`).
- The EVAL.md pre-registration row still says "Freeze commit: recorded ... once merged". Fill in the merge hash at merge time.
