# Review: p/sme-council-tender-drafting/T-206 (held-out pack answer keys)

Reviewer, 2026-11-28. Diff `git diff main...p/sme-council-tender-drafting/T-206`: 9 keys `eval/keys/S*.json`, README rules 15-19, `app/backend/tests/test_tender_pack_keys.py` (90 lines), NEXT.md, reviews/T-206-checker.md. I did not re-check key content against the packs: the independent checker did that (reviews/T-206-checker.md, PASS on re-check). T-213 (invented limits unscored, deadlines unscored) is queued separately and does not block this.

**Verdict: PASS.** No critical issues. The suggestions below are cheap hardening and can go with the T-206 retrieval-label follow-up.

## Evidence

- `pytest tests/test_tender_pack_keys.py tests/test_tender_eval_keys.py tests/test_tender_eval.py`: all passed. The caller reports the full suite at 1228 passed, 1 skipped.
- File names match what `run.py` looks for: for all 9 keys, `path.stem == Path(d["pack"]).stem`, so `_key_items` (`keys_dir / f"{Path(pack).stem}.json"`) finds every held-out key.
- Question counts for the drafting held-out packs: S01 18, S05 16, S09 20. Each is at least 15, so `build_plan("draft_heldout")` gets 15 questions from each pack.
- I ran mutation tests on a scratch copy of the product: I broke one thing at a time and ran the new test.

| Mutation | Result |
|---|---|
| `word_limit` as the string `"400"` | fails (good) |
| `weight_pct` +1 on one question | fails, 71 != 70 (good) |
| `kind: "Question"` typo | fails (good) |
| all keys deleted | fails (test_keys_present, and StopIteration in test_spot_limits) |
| `word_limit: true` (bool) | **passes**, because `isinstance(True, int)` is true |
| two questions' weights swapped / wrong limit on a non-spot item | passes. Expected: that is content, which the checker covers |
| `shared_words` without `shared_group`, `case_studies: "two"` | **passes**, extra fields are only half-checked |
| S11 key deleted, or S01 (drafting) key deleted | **passes** |
| S02 key renamed `S02-cleaning.json` (run.py can no longer find it) | **passes** |
| a demo retrieval-label file `S04-....json` or `S04-retrieval-labels.json` added to `eval/keys/` | **fails** (S04 is not in heldout, and QUALITY_TOTAL has no S04 entry) |

## Shape against the consumers

- `run.py _key_items` reads `key["items"]`. `build_plan draft_heldout` reads `kind`, `ref`, `text` and `word_limit` (`.get`). Every key has all four. Question refs are unique within each pack (the test asserts this), so the draft ids `"<stem>:<ref>"` are unique.
- `score.py score_extraction` / `match_items` read only `kind`, `ref`, `text` and `LIMIT_FIELDS` (word_limit, page_limit, marks, weight_pct). It filters items by `kind == "question"` or `"mandatory"`, so `deadline` items are ignored (T-213). It never reads `case_studies`, `shared_group` or `shared_words`, so those fields have no effect on scoring. Null fields are skipped from A2 (`if ks[i].get(f) is not None`), which is consistent with README rules 7 and 8.
- Side effect to note: shared-group members (S09 2.1-2.3) have `word_limit: null`, so in E2 they are drafted with no limit at all. `shared_words` is not passed to the drafter. This is acceptable for an eval of grounding, but A4-A8 results on those 3 items will not reflect the 800-word cap. Record it in EVAL.md or pass `shared_words` later. Not blocking.

## Critical issues

None.

## Suggestions (non-blocking)

1. **The test does not check that the keys cover the held-out packs** (`test_tender_pack_keys.py` l.35-36). It passes with S11 or S01 deleted, and with a key named so that `run.py` cannot find it. `run.py` would raise PhaseNotReady at run time, so nothing gets scored wrongly, but the pre-registration commit could be made with a gap. Fix: `assert {p.stem for p in KEYS} == {Path(n).stem for n in MANIFEST["heldout"]}`, and in `test_pack_key` assert `path.stem == Path(d["pack"]).stem` instead of the 3-character prefix check (l.45).
2. **The glob will catch the demo retrieval labels** (l.8, `glob("S*.json")`). The rest of T-206 adds labels for S04, S08 and S12. If they go in `eval/keys/` with an `S0x-` name, this test fails, loudly rather than silently, but it will be confusing. Fix: either store the labels under another name or directory (for example `eval/keys/retrieval/` or `retrieval_labels.json`), or build `KEYS` from `MANIFEST["heldout"]` (which also fixes suggestion 1). Note that on Windows, `Path.glob` is case-insensitive, so `S*.json` would also match `seeded_claims.json`. Building the list from the manifest avoids that too.
3. **Booleans pass the integer check** (l.53). Fix: `type(it[f]) is int`.
4. **Extra fields are only half-checked** (l.71-74). Assert that `shared_group` and `shared_words` appear together, that `shared_words` is a positive int, and that `case_studies` is an int >= 2 with a non-null word or page limit. README rule 14 says the test checks these fields, so the test should do what the README claims.
5. **`read_text()` has no encoding** (l.9, l.30). All 9 keys contain non-ASCII characters (4 or more lines each). This works on Linux and in CI, but fails under a non-UTF-8 locale. `test_tender_eval_keys.py` and `run.py` both pass `encoding="utf-8"`; do the same here.
6. Checker nit R1 is still open: S01 2.4 sits after M10, not at its pack position as README l.30 requires. Order does not affect scoring. Either move the item or list the exception in the README.
7. Skip vs fail: when the keys are missing, the test fails. That is the right behaviour for committed ground truth; do not change it to a skip. A missing `demo-data/packs/manifest.json` errors at collection (module-level read), which is also acceptable.
