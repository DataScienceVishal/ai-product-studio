# Review: T-56 tuning1 fixes (commits e1f881f, 21f56ce; diff against 71388e9)

Reviewer gate, 2026-11-24. Branch `p/pepr-packaging-data-pipeline/T-56`. No model or Azure calls made; `T56_SPEND_APPROVED` not set.

## Summary
Fixes for the first real tuning run (results/tuning1): prompt now asks for the whole printed feature value and adds an OWN ROW ONLY
rule; `extract.drop_unverified` turns an unverifiable text-page field into `missing`; reasoning effort default moves from `low`
(rejected by gpt-5.4-pro) to `medium`, allowed set `("medium","high","xhigh")`. Amendment 5 is a proposal only, not applied.
The change is sound, only drops values, and does not touch scorer, truth, sheets or pass marks.

## Checks asked for

1. **Drop only, never invent or alter.** `drop_unverified` (extract.py:103-126) only ever assigns `{"status": "missing"}` to a field
   and resets `ram_category` to `missing` when material is not present (the same rule `clean_output` already applies, so no new
   value). It uses only `vocab.tx` (taxonomy: `canonical`, `norm_quote`, `quote_ok`, `VOCAB`). It never passes `extra_words`, so
   truth `accepted_values` are not used; `grep accepted_values|manifest extractor/extract.py` finds nothing. The isolation source
   test (`test_no_module_but_cli_names_truth_or_manifest`) still covers the new code. Dropping turns an untraced value into a
   missing slot, which the scorer counts as wrong for accuracy when truth is present, so the real-world cost of the drop shows up
   in field accuracy. Acceptable product behaviour. See S1 on how to report it.
2. **Reads only the copied PDF.** `drop_unverified` works on the `pages` list from `pdfio.read_pages(copy)`, which `extract_pdf`
   already had. No new file access. `test_extraction_reads_only_a_temp_copy` still passes and now runs through the drop path too.
3. **On-page checks with layout text.** Both sides go through `norm_quote` (case, whitespace collapse, `|` as space). Refs are
   range-checked before indexing; refs to an image page skip the field. Each conflict value must be backed by a ref, and each ref
   must back a value. **Empirical false-drop check** (scratch script, product code untouched): ran `drop_unverified` on the
   *truth* components of all 35 sheets (30 test, 5 tuning; 48 pages, 9 image pages, about 290 quotes) using the extractor's own
   layout-mode text: **0 fields dropped**. So the layout text (extractor) vs plain text (scorer) difference costs nothing on this
   data.
4. **Effort.** `REASONING_EFFORTS`, the default in `AzureResponsesProvider`, and the tests all agree. The only stale mention is
   NEXT.md line 43 ("default `low`"), which line 73 supersedes (nit).
5. **No change to protected data.** `git diff 71388e9 21f56ce --stat`: the only benchmark change is the new
   `KILL_TEST_AMENDMENT_5.md`. score.py, taxonomy.py, data/ (sheets, tuning, truth, tuning_truth, manifest) and the kill-test
   pass marks are unchanged.
6. **Amendment 5.** The diagnosis is right: both S902 quotes are verbatim sub-spans, and the scorer is right under the letter of
   `quote_ok`. The recommendation to keep the scorer as it is is the right one. Loosening the rule after seeing results would
   need a dated entry before the next run, and fixing it on the extractor side does not weaken the test. Agree it should not be
   applied.

## Critical issues
None.

## Suggestions (non-blocking)
- **S1 Honest reporting.** On text pages the extractor now pre-applies the scorer's own `quote_ok`, so pass mark 3 (0 untraced)
  is met by construction on text pages, and only image pages can still fail it. That is legitimate (the product only outputs
  verified values), but the test-set write-up should say so and also report the raw pre-drop count: the number of
  `"... dropped"` warnings per sheet, already saved in each prediction JSON. Then the validator can see the model's true
  traceability rate.
- **S2 Output headroom vs effort.** S904 used 5543 of 6000 `MAX_OUTPUT_TOKENS` at `medium`. `high` or `xhigh` will probably
  truncate, which gives invalid JSON and an empty sheet. Before anyone sets `T56_REASONING_EFFORT=high|xhigh`, raise the cap
  with it (the budget worst case scales with it) or detect an `incomplete` response and warn.
- **S3 Mixed refs.** extract.py:113: if *any* cited page is an image, the whole field is skipped, including its text-page refs.
  Verifying the text-page refs and skipping only the image refs would be stricter. This is rare.
- **S4** `drop_unverified` runs inside the `try` whose `except` reports "model answer was not valid JSON" and discards every
  component. An unexpected TypeError in the drop path would be mislabelled and lose the whole sheet. Low risk, because
  `clean_output` normalises the shapes, but a separate call outside the `try` would be clearer.
- **S5 Tests.** Add one for a weight `conflict` (each value must have a passing ref) and one for a feature key outside `VOCAB`
  (dropped).
- **Nit** NEXT.md line 43 still says the default is `low`.

## Evidence
```
$ cd products/pepr-packaging-data-pipeline && /usr/bin/python3 -m pytest -q extractor/tests benchmark/tests
........................................................................ [ 49%]
........................................................................ [ 99%]
.                                                                        [100%]
145 passed in 8.88s

$ git diff 71388e9 21f56ce --stat -- products/pepr-packaging-data-pipeline/benchmark
 .../benchmark/KILL_TEST_AMENDMENT_5.md | 27 ++++++++++++++++++++++
 1 file changed, 27 insertions(+)

False-drop check (drop_unverified applied to truth refs, extractor layout text, 35 sheets):
sheets 35 false drops on truth 0
```
`test_tuning1_s902_misses_would_now_be_dropped_not_scored_untraced` shows that S902 goes from 2 untraced to 0 with the real
tuning1 output.

## Verdict
**PASS**
