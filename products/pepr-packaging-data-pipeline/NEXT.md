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

## Status after run 4500 (slice 3 done, no model call made)
Built in `extractor/` (plain package, run from the product dir: `python3 -m extractor.run --set tuning|test --provider fake|azure --out results/NAME`) and `benchmark/score.py`.
- Scorer: README rules (a)-(d), quote_ok, missing, ram only with material, false conflict = 0; reports per sheet and overall field accuracy, messy-10, untraced, missing %, fabricated, conflict-flag % (strict: both values; "flagged at all" also shown), pass/fail per mark. Cost mark uses the ledger: mean USD per sheet <= 0.316 and a cost entry for every sheet (no ledger = not passed). Untraced = a non-missing predicted value with no refs, or any ref whose quote fails quote_ok on the stated page (all refs must pass; matched or not).
- Extractor: one call per sheet carrying all pages (conflicts span pages). Text pages go as `extract_text(extraction_mode="layout")`; pages with under 20 non-space characters go as the embedded image (pypdfium2 render fallback); `pages[].input` records which. ram_category is derived in code from the canonical material (`vocab.RAM_CATEGORY`, tested equal to the generator's mapping), not asked of the model. Nothing is filled in: bad fields are dropped with a warning.
- Isolation (item 3): the PDF is copied to an empty temp dir and only the copy is read; only `taxonomy` (vocabularies, PLAUSIBLE) is imported; tests check no module other than the CLI names manifest/truth, and trace `open()` calls. The CLI loads the scorer only after extraction.
- Budget (item 5): pre-call worst case (UTF-8 bytes of input + 6000 per image + max_output_tokens, default 12000) at USD 15/120 per 1M, refused if it could pass USD 12 or 3M tokens; JSONL ledger (default `results/ledger.jsonl`, shared by tuning and test so the caps cover everything) with billed tokens and USD per sheet; a timed-out call is charged its worst case and never resent.
- Azure provider: v1 Responses API, `gpt-5.4-pro` (env T56_DEPLOYMENT), explicit reasoning effort (env T56_REASONING_EFFORT, default `low`, chosen to keep cost per sheet inside USD 0.316; revisit on tuning), timeouts (300 s), 3 retries with backoff on connect errors/429/5xx. Refuses to construct or call unless `T56_SPEND_APPROVED=1` (Q-11). Uses stdlib urllib (httpx is not installed here). Not exercised against the real service.
- Prompt (items 8 and the two re-review notes): "missing" (silent, n/a, TBC, none stated) versus stated-absent ("Sleeve: none" -> "no sleeve"), single-cell/single-sentence quotes, never both columns of a two-column row, quote the material cell alone (kraft vs kraft brown).
Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` = 65 pass (13 scorer, 28 extractor, 24 generator). An oracle built from truth, run through the whole extractor pipeline, scores 100% and passes all five marks on the 30 sheets.
Left: Q-11 answer (spend approval); slice 4 tuning on S901-S905 (per-sheet cost check on tuning first; the unit price assumption is untested against a real bill), then the single test run, scoring, validator re-score. Reviewer pass on slice 3. Not done: public spec PDFs.
Run (after approval): `T56_SPEND_APPROVED=1 python3 -m extractor.run --set tuning --provider azure --out results/tuning1`, then `--set test`.

## Review fixes for slice 3 (reviews/T-56-slice3.md)
C1: default max_output_tokens 6000; `--set test` refuses to start (exit 4) unless remaining budget covers 30 x USD 0.316 + one worst-case reservation (and a token analogue). C2: pass mark 4b = share of conflicts flagged (Studio Lead decision); both-values rate is information only; README updated. S1 (unknown feature keys count as untraced), S3 (HTTP 400/401/403 stops the run, exit 5), S4, S5 done. Not done: S2 (5xx retries share one reservation), S6 (record image tokens after first scanned tuning sheet). After tuning set max_output_tokens to ~3x the largest output seen, minimum 4000.

S2 fixed: `AzureResponsesProvider.complete(..., budget, label)` (passed by `extract_pdf`) records every 5xx at its worst case (estimated entry) and re-runs `budget.check` before each retry; a refused retry raises BudgetExceeded and makes no further call. Timeouts were already never retried and are charged by `extract_pdf`; connect errors and 429 stay free. S6 still not done.

## Run bea4 (2026-11-24 ~18:50Z)
- S2 nits done (05509da, 03cdff8), reviewer PASS (reviews/T-56-s2.md "Nits review").
- `benchmark/REALISM.md`: 13 real public spec sheets vs our synthetic set. Verdict MIXED: easier on layout/wording (always a per-unit weight, one product per sheet, closed wording), harder on conflicts/scans. A 90% pass likely overstates real-sheet accuracy on weight, colour, material.
- Amendment 3 (scorer, before any run): `parse_weight` accepts gm/gms/gram/grams (test added; 81 pass). Test sheets and truth unchanged.
- **Next (slice S7, before or alongside slice 4, model-free):** a separate ~10-sheet "realism supplement" set (new seed) per REALISM.md changes 1-5, reported separately; pass marks unchanged. Decide in writing first: truth for blends ("rPET 30% + PET 70%"), bare number under "Weight (g)" label (quote_ok must accept unit in label), weight given only as gsm/µm/case weight -> `missing`. Plus one UK-source search round (British Glass members, Berry, Bericap, DS Smith).
- Still waiting: Q-11 ($12). No Azure call made.

## Run 6224 (S7, 2026-11-24, model-free)
Done: realism supplement. `benchmark/supplement.py` (seed 20261126) writes 12 sheets S801-S812 to `benchmark/supplement/` (data/sheets, data/truth, manifest.json; 22 components, 162 slots: 86 present, 76 missing, 0 conflicts), covering REALISM items 1-5 (see `benchmark/KILL_TEST_AMENDMENT_4.md` for D1-D4 and the truth decisions). Scorer: `taxonomy.quote_ok` blend rule (D1) and label-unit rule (D2); `score.py --set supplement`; `extractor.run --set supplement` (no budget preflight; the `--set test` guard is unchanged). Schema: optional `target_item`, layout `supplement`, templates `catalogue`/`two_block`/`unit_header`. Prompt: D2 line plus blend, areal-weight, catalogue and secondary-packaging lines (the Studio Lead asked for the D2 line only; the others were needed to make the sheets answerable, no model has seen the prompt). `cryptography==50.0.1` pinned (it was installed; AES PDFs need it); pdfio opens S812 unchanged (pypdf tries the empty password itself).
Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` = 119 pass (was 81). The 30 test sheets, 5 tuning sheets, seeds and truth are byte-identical (existing reproducibility test passes). No model or Azure call made.
Not done / open: header-unit weight columns ("Weight" over a column of bare numbers under "(g)") cannot be quoted contiguously, so S810 keeps units in the cells (needs a decision); decimal comma weights not parsed; the extra UK-source realism search round; Q-11 (spend) still pending.
Run the supplement only AFTER the test-set run (same ledger; `--set supplement` exits 6 until the ledger has test-set entries): `T56_SPEND_APPROVED=1 python3 -m extractor.run --set supplement --provider azure --out results/supplement`.

### Review fixes for S7 (reviews/T-56-s7.md)
C1 prompt packing-notes line narrowed (listed components such as "outer case, Material n/a" stay components; test). C2 blend rule: PET/rPET only, one reading direction, shares sum to 100 +-1. C3 S805 truth colour white, "WhiteSolid" via truth `accepted_values` (scorer honours it, only for the truth value; vocabulary untouched). S1 label-unit number must end the quote (optional tolerance); label must say weight/wt/mass. S3 supplement run order enforced by the CLI. S806 weights now scale with volume. 139 tests pass; test and tuning data untouched.
