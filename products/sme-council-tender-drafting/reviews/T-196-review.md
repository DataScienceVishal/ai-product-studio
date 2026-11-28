# Review: p/sme-council-tender-drafting/T-196

Scope: the code in `git diff origin/main...HEAD`, which is `eval/seed.py` (new `evidence_docs()`) and `app/backend/tests/test_tender_eval_keys.py`. I only skimmed the JSON keys to check that `eval/run.py` can load them. The validator already checked their content in `reviews/T-196-validator.md`.

## Summary
- `evidence_docs()` keeps the upload order the seed already used: sorted `*.md` files, then sorted `*.txt` files. The only change is that `README.md` is now dropped (the match ignores case). `seed()` uses the helper, so the eval and the demo seed upload the same files. `demo-data/evidence` holds 33 files, so 32 are uploaded.
- Nothing else in the repo depends on README being uploaded:
  - Seed test `test_tender_eval.py:594` builds its own temporary evidence directory and expects `evidence_documents == 2`.
  - No other script or test points at `demo-data/evidence`.
  - The `run.py` loaders find the fields they need: trap items have `id`, `question` and `word_limit`, and fixture drafts have `id`, `text` and `retrieved_ids`.
- The new test does not depend on the working directory. Paths come from `__file__`. `run_worker` runs in a child process with `-I` and `cwd=tmp`. I ran it from `/tmp` and got 4 passed. It does not use the database.
- Test runs:
  - `tests/test_tender_eval_keys.py` plus `tests/test_tender_eval.py`: **123 passed**.
  - The keys file alone, run from `/tmp`: **4 passed**.

## Critical issues
None.

## Suggestions
1. `app/backend/tests/test_tender_eval_keys.py:38`: `assert t["question"].strip() and ".md" in t["why"] or "library" in t["why"]`. Python reads this as `(A and B) or C`. If `why` mentions "library", the check passes even when `question` is blank. Add brackets: `t["question"].strip() and (".md" in t["why"] or "library" in t["why"])`.
2. Fresh tenant needed. Evidence numbers come from a per-tenant counter that only goes up (`app/tender/evidence.py:20`). A demo tenant seeded before this change still has the README passages and the old numbers. Re-seeding returns 409 for files already uploaded and does not renumber anything. The E-n keys only hold for a tenant seeded from scratch after this change. Say so in `eval/keys/README.md`, or have `run.py` check that no README document exists for the tenant.
3. `test_seed_skips_readme` hard-codes 32. That is fine as a tripwire, but the message could say "update evidence_map.json" when the count changes.

## Verdict
**PASS**
