# Review: p/pepr-packaging-data-pipeline/T-56, slices 1-2 (commit b64b083)

Reviewer: reviewer agent, 2026-11-24. Scope: `products/pepr-packaging-data-pipeline/` (NEXT.md, benchmark/README.md, truth.schema.json, generate.py, requirements.txt, tests/, data/) against "Proof test (T-56)" in `state/ideas/pepr-packaging-data-pipeline.md`.

## Verdict: CHANGES

The plumbing is good. The benchmark is not yet fit to decide whether the idea lives or dies, for three reasons. Some truth labels can't be scored. The scoring rules for conflicts, scanned sheets and unit quotes aren't defined. And the sheets are easy enough that a pass would say little about real supplier PDFs. Fix these before slice 3. They change the dataset and the scoring rules, so they need to be settled before any results exist.

## Evidence

- `/usr/bin/python3 -m pytest -q` in benchmark/: **10 passed in 3.28s**.
- Regenerated into a scratch dir and ran `diff -r` against committed `data/`. All truth JSON, manifest and text PDFs are identical. The 6 rasterised PDFs (S021-S025, S905) differ only in Pillow's `/CreationDate` and `/ModDate` (6 bytes).
- Counts are correct: 30 test sheets, tiers 10/10/10, `messiest_10` = S021-S030 (the messy tier), and 5 tuning sheets S901-S905 with seed 20261125, stored apart in `data/tuning*`. Size is 2.4 MB. The pins in requirements.txt match the installed versions. No .pyc or cache files are tracked.
- Truth field tally (test set): 67 components and 448 scored slots. Core fields in the messy tier: material 21 present / 9 missing; colour 26 / 4; weight 11 present / 7 missing / **12 conflict**. Features: 123 present / 57 missing.
- The tests confirm that every quote in the 25 text sheets appears on its stated page.

## Critical issues

1. **Feature `missing` labels are arbitrary and can't be scored fairly** (`generate.py` lines 160-163, 227-231). Each non-clean component gets exactly one absent feature key labelled `missing`, picked at random. The other absent keys are left out of truth entirely, and the sheet says nothing that tells them apart. So an extractor can't know which absent key truth calls `missing`. If it returns `missing` for all six it is either right or "extra". If it returns nothing it misses 57 truth fields. This affects pass mark 4 (>= 95% missing handling).
   *Fix:* choose one of two options. (a) Label every absent feature key `missing` and require the extractor to return all six keys. (b) State the missing feature on the sheet (e.g. "Barrier layer: not specified") and define unlisted keys as unscored. Write the rule in README.

2. **Scoring rules the metric depends on are undefined.** These must be written down as a dated entry in the kill test before any run:
   - (a) How a `conflict` field scores for field accuracy, e.g. "1 if flagged as conflict and both values match within tolerance". It is 12 of the 30 messy weight slots, so it largely decides pass mark 2.
   - (b) How the "quote contains value" check works when units differ. The truth value is 159.5 but the quote is "159500 mg", so the check must parse the number and unit.
   - (c) How traceability (pass mark 3) is checked on the 5 image-only sheets, which have no text layer. One option is to check against generator-recorded page text, or against OCR with a stated tolerance.
   - (d) How components are matched "by name and material" when truth material is `missing`. There are 13 such cases.

3. **The benchmark is too easy, so a pass would mean little.** Field labels are literally `Material` / `Colour` / `Weight` / `Barrier layer`, the same as the schema keys. Component names are the canonical schema names. Feature values come from 12 fixed strings and are identical to their quotes. There are only 3 templates (table, matrix, prose) with fixed sentence frames. Missing values are shown as `-` or "not stated", which makes them easy to spot. The README promises "features buried in prose" for messy sheets, but that isn't implemented: messy sheets use the same notes and rows as moderate ones. Apart from the scans, "messy" means abbreviations plus one page-2 note.
   *Fix:* add label synonyms ("Resin", "Substrate", "Nett wt", "Mass", "Shade"). Add distractor numbers (gross or pallet weight, wall thickness, cap torque). Use absent rows rather than `-`. Paraphrase feature text so it needs normalising. Add headers and footers, a two-column layout, footnote-style conflicts, and real prose burial for the messy tier. Also make reporting the public-PDF set a hard requirement, as a realism check.

4. **The tuning set doesn't represent the hard cases** (`generate.py` line 375). The tuning sheets map to plans 2, 8, 12, 15 and 22. That gives 2 clean sheets, **zero conflict cases**, and no contradictory, multi_component or missing_fields layouts. This invites prompt iteration on the test sheets to get conflict handling right, which the kill test forbids.
   *Fix:* cover one clean, one multi-component/missing, one mixed-units, one scanned-with-conflict and one contradictory sheet.

5. **The kill test text doesn't match the artefact.** It says the truth is "hand-written" at `benchmark/truth/*.json`. In fact it is generator-written, at `benchmark/data/truth/`. Generator truth is better, but record the change as a dated amendment before the run (the kill test's own rule).

6. **Feature-to-component pairings are nonsensical.** Examples: a closure on an outer carton, label, tray or pouch; a shrink sleeve on a sleeve; S027 "outer carton - closure: HDPE cap with PE liner". A capable model may "correct" or drop these, and would be marked wrong for showing domain sense.
   *Fix:* restrict features to the ones each component can plausibly have.

## Suggestions

7. Determinism: strip or fix the PDF dates for raster output (post-process with pypdf, or set metadata), and add a byte-equality test for the PDFs.
8. The README example ("S014 ... contradictory, bottle") doesn't match the real S014 (mixed_units, carton/can/pouch). Label it illustrative or use a real sheet.
9. The kill test mentions a carbon-black flag and closure liners. Add at least a few carbon-black colour cases, since they matter for RAM.
10. Time box: record in NEXT.md how many of the 3 permitted runs slices 2-4 have used (slice 2 used 1). Token budget wording: say whether the 3M cap counts input plus output plus image tokens, and pin the model and GBP price per 1M tokens behind the GBP 0.25 per sheet check, so pass mark 5 can be computed as written.
11. With 12 conflict cases, the 80% bar means 10 of 12. Note this granularity, or add conflicts in the moderate tier so the measure is less noisy.
12. `t_is_text` in tests re-reads the manifest for every PDF. Fine at this size, but pass the manifest in instead.
