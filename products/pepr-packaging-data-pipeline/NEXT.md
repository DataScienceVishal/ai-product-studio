# NEXT (T-56 proof test)

Done (slice 1): kill test written and committed on main (state/ideas/pepr-packaging-data-pipeline.md, "Proof test (T-56)"); benchmark README and truth schema in `benchmark/`.

Done (slice 2): `benchmark/generate.py` (seed 20261124; tuning seed 20261125), data in `benchmark/data/` (30 sheets, 5 tuning S901-S905, manifest.json; 2.4 MB, committed). Tests: `/usr/bin/python3 -m pytest benchmark/tests` (10 pass). Deps pinned in `benchmark/requirements.txt`. Regenerate: `python3 benchmark/generate.py`. Notes: 5 scanned sheets are image-only (no text layer); truth quotes are checked against PDF text only for the 25 text sheets. Feature keys appear in truth only when stated or explicitly missing.

Left:
- Optional: public spec PDFs (licence checked) under `benchmark/public/`.
- **Slice 3:** extractor built on `products/_starter` patterns: Azure OpenAI Responses API, provider interface, token budget guard (3M token cap), timeouts and retries, page-referenced output.
- **Slice 4:** run once on the 30 sheets, score with `score.py`, write results into the idea file, and have the validator re-score (pass) or record the failed G1 attempt (fail).

Verify: `python3 -c "import json;json.load(open('benchmark/truth.schema.json'))"`; each truth file validates against the schema.

## Status after run 37b8 (2026-11-24 ~15:50Z)
Slices 1-2 done; reviewer CHANGES (reviews/T-56-slice2.md). Before slice 3, fix every numbered item there:
the random single `missing` key per component (57 fields, pass mark 4 unscoreable), scoring rules for conflict fields /
unit quotes / image-only traceability / component matching without material, harder layouts (labels not equal to schema
names, more than 3 templates, varied missing markers), conflicts in the tuning set, nonsensical feature-component pairs.
Fix the kill test wording "hand-written truth" to "generator-written truth, spot-checked by hand" on main (allowed: no run
has happened yet; log it in DECISIONS.md). Then re-review, then slice 3.

## Status after run T-56 fix (2026-11-24)
Addressed reviewer items 1-12 in `benchmark/` (tests: 19 pass). Truth now labels every plausible feature key present or `missing`
(`taxonomy.py` PLAUSIBLE, shared with the future scorer); scoring rules (a)-(d) and "Run budget" (incl. USD 12 hard spend cap) are in
`benchmark/README.md`; `benchmark/KILL_TEST_AMENDMENT.md` is the text for the Studio Lead to paste into the kill test on main.
Harder sheets: label/name synonyms, distractor numbers, absent rows and varied missing markers, paraphrased features with a closed
vocabulary, headers/footers, 6 templates, footnote and notes-page conflicts, buried prose, carbon-black cases. 68 components, 466 scored
slots (307 present / 137 missing / 22 conflict) in the test set; tuning set covers clean, multi+missing, mixed units, scanned+conflict,
contradictory. Image-only sheets have recorded page text in manifest.json. PDFs are byte-reproducible (test). Runs used: 2 of 3.
Next: reviewer re-check, then slice 3 (extractor must return all plausible keys, closed feature vocabulary, stop at USD 12 or 3M tokens).

## Status after re-review fix (2026-11-24)
Re-review items 1, 2, 6, 7, 9 done: closed material/colour vocabularies, `taxonomy.quote_ok()`/`canonical()`, ram_category scored only when material present,
amendment text in `benchmark/KILL_TEST_AMENDMENT_2.md`. Data regenerated (accepted_values now list every variant; test set 457 slots: 307/128/22). 24 tests pass.
Still for slice 3: extractor isolation test, layout-aware input for two-column sheets, pre-call budget guard (USD 12 / 3M tokens), tuning prompt examples for "none stated" vs "sleeve: none".
