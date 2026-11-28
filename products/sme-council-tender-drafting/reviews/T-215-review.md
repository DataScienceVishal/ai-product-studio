# Review: p/sme-council-tender-drafting/T-215 (commit 6ad37fd)

Reviewer: reviewer agent, 2026-11-28. Diff: `git diff origin/main...6ad37fd` (7 files, +97 / -12). Scope: the T-206 review nits.

## Verdict: PASS

## Summary

All six nits are done correctly. No product runtime code changed, only eval scripts, tests, a results file and a product `.gitattributes`.

| Nit | Status | Evidence |
|---|---|---|
| Real-library bound `<= e+400` to `<= 32` | done | `test_tender_retrieval_eval.py:175`. `SD.evidence_docs` excludes README.md, so there are exactly 32 evidence files (`ls demo-data/evidence` gives 32 files plus README). The test passes. |
| Stale docstrings | done | `eval/run.py retrieval_diagnostic` now names the callers correctly: the draft task (`draft.py:262`) and the draft route (`routes/tender.py:419`) use `limit=APP_PASSAGES, min_score=RETRIEVAL_FLOOR`, and `/evidence/search` (`routes/tender.py:118`) uses the defaults with no floor. `score.py retrieval_recall` explains any vs all primaries. |
| `labels_sha256` in retrieval.json | done | `main` hashes the exact bytes it parses (`run.py:383-384`; `hashlib` is already imported). The value `5d9541d3...3d3c` matches `sha256sum eval/keys/retrieval_labels.json` and the FROZEN.sha256 entry. |
| `all_primaries_hit_rate` | done, correct | Uses the same denominator as `primary_hit_rate` (questions with a non-empty `primary`). Missing questions get `top=[]` and count as a miss. Gap questions are excluded. It can never be above the any-primary rate. Reported per pack, pooled and under `at_app_passages`. |
| `.gitattributes -text` | done, correct | See below. |
| Freeze test asserts exactly 9 held-out packs | done | `test_tender_eval_keys.py:119` checks the count and that there are no duplicates. `manifest.json` heldout has 9 entries. |

## Verification run on the exact branch tree (separate worktree at 6ad37fd)

- **Full backend suite** on a fresh Postgres `starter_test`, python3.13: **1281 passed, 1 skipped in 309s**, exit 0. This matches the expected count.
- **Retrieval rerun** on a fresh DB `t215_eval`: `alembic upgrade head`, then `UPLOADS_PER_HOUR=1000 UPLOAD_PAGES_PER_DAY=100000 python -m eval.seed`, then `python -m eval.run retrieval`. The rewritten `eval/results/retrieval.json` is **byte-identical** to the committed file (`git status` clean). Recall@8 is 0.7446 (0.745) and primary hit is 0.9643 (0.964), both unchanged. all_primaries is 0.821 pooled (S04 0.778, S08 1.0, S12 0.7).
- **Freeze:** `sha256sum -c eval/keys/FROZEN.sha256` gives every entry OK. FROZEN.sha256 is not in the diff.

## .gitattributes check

- `git ls-files --eol` shows every matched file stored as `i/lf` (or `i/-text` for the docx), with no CRLF in the index. Running `git add --renormalize .` afterwards changes nothing. There is no root `.gitattributes`, and `core.autocrlf` is unset here. So adding the attributes changes no checked-in blob and no hash.
- `-text` on `pack-sources/*.md` is the right choice. Those `.md` files are hashed as raw bytes in FROZEN.sha256, and on a Windows checkout with `core.autocrlf=true` they would get CRLF and fail the freeze test. `-text` only turns off EOL conversion. It does not set `-diff`, so `git diff` still shows them as text. The rule also covers the non-held-out demo sources, which does no harm.
- Two files under those directories are not covered and do not need to be: `build_docx.py` and `manifest.json`. Neither is in FROZEN.sha256.

## Tests: do they test behaviour?

- `test_all_primaries_hit_rate_needs_every_primary_in_the_top_k`: I checked the expected values by hand. Any-primary: q1, q2 and q3 hit, so 0.75. All-primaries: q1 and q3 hit, so 0.5. At k=1 only q3 hits, so 0.25. All correct.
- The real-labels test runs perfect retrieval (1.0), then keeps only the first primary per question (all < any = 1.0). This shows the labels contain multi-primary questions, which is why the metric is meaningful.
- `test_main_passes_the_sha256_of_the_labels_file_bytes` goes through `main` with a monkeypatched diagnostic and `RESULTS_DIR`. It checks both the value passed in and the value written to the file. Good.

## Critical issues

None.

## Suggestions (non-blocking)

1. `test_tender_retrieval_eval.py:175`: the `32` is a magic number. Using `len(SD.evidence_docs(SD.EVIDENCE_DIR))` would keep the test right if the library grows.
2. `EVAL.md` retrieval row: it defines `primary_hit_rate` but not the new `all_primaries_hit_rate`, and it does not mention `labels_sha256`. Add one sentence and the 0.821 figure.
3. `test_frozen_files_are_marked_text_off...` parses `.gitattributes` by hand. `git check-attr text -- <path>` would test the real effect, but the test would then need git at test time. Optional.
