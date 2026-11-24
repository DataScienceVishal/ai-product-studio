# Re-review: p/pepr-packaging-data-pipeline/T-56, slice 2 fixes (HEAD 722e660)

Reviewer: reviewer agent, 2026-11-24. Scope: `benchmark/` and `NEXT.md` on the branch. Checked against the earlier review (`reviews/T-56-slice2.md`, items 1-12) and against the kill test on main, including "Amendment, 2026-11-24" (commit 6a842dc).

## Verdict: CHANGES (narrow, text only)

All 12 earlier items are fixed, and the dataset is now hard enough that a pass would mean something. Two scoring rules are still ambiguous, though, and each could swing pass mark 1 or 3 by itself:

- the rule for matching an extracted material or colour value;
- the rule for matching a quote.

Neither needs the data regenerated. Both need a second dated amendment on main **before any model call, including tuning calls**, because tuning output counts as seeing results. The slice 3 plumbing (provider interface, budget guard, retries) can start now.

## Evidence

- `/usr/bin/python3 -m pytest -q` in `benchmark/`: **19 passed in 3.79s**. This includes byte-equal regeneration and committed data matching a fresh run.
- Manifest stats for the test set: 68 components, 466 slots (307 present, 137 missing, 22 conflict), 8 carbon-black components. Templates by tier: messy = prose_buried 2, matrix 2, table 2, bom 2, two_column 2.
- I opened PDF text with pypdf for S001 (clean table), S016 (moderate two-column), S027 (messy, buried prose, notes-page conflicts) and S029 (messy BOM, footnote conflicts), and compared each to its truth JSON. Every truth value, quote and page matches. Examples: S027 pouch weight conflict [4.3, 6.9] with quotes "4300 mg" (p1) and "6900 mg" (p2); tray material and colour `missing` ("Resin: TBC", "Finish colour: n/a").
- Scanned sheets: I read the `page_text` for S021 and S024 in the manifest and rendered S024 page 1. The raster is fully legible: slight skew and noise, and the 8 pt footnote "(1) pouch: unit weight on retest 6.9 g." can be read. It matches `page_text` line for line. pypdf finds no text layer.
- `__pycache__` is not tracked (`.gitignore` added).

## Earlier items 1-12

| # | Status | Evidence |
|---|---|---|
| 1 missing feature labels | Fixed | Every key in `taxonomy.PLAUSIBLE` is labelled present or missing. Tested by `test_plausible_keys_all_present_and_no_implausible`. |
| 2 scoring rules (a)-(d) | Fixed as written | In the README and in the kill-test amendment on main. Two remaining gaps are listed below. |
| 3 too easy | Fixed | Label synonyms, distractors (gross weight, pallet weight, tolerance "+/- 0.3 g", torque), varied missing markers, paraphrased features, 6 templates, buried prose, footnote and notes-page conflicts. Tested. |
| 4 tuning coverage | Fixed | S901-S905: clean, multi plus missing, mixed units, scanned plus conflict, contradictory. 3 conflicts. Tested. |
| 5 kill-test wording | Fixed | Amendment items 1 and 8 on main. |
| 6 nonsensical pairings | Fixed | The PLAUSIBLE map is sensible and tested. |
| 7 determinism | Fixed | PDF dates are fixed, and a byte-equality test exists. |
| 8 README example | Fixed | It matches S018's truth ("tinplate steel", accepted "tinplate"). |
| 9 carbon black | Fixed | 8 test components, shown as "CB black" / "carbon black pigmented". |
| 10 budget wording | Fixed | Covers model, price basis, what counts toward the token cap, the USD 12 cap, and runs used (2 of 3). |
| 11 conflict granularity | Fixed | 22 conflicts, so at least 18 of 22 needed. |
| 12 manifest re-read | Fixed | `page_texts(d, sub, row)`. |

## Must fix before any model call (amendment 2 on main)

1. **The rule for matching extracted material and colour values is undefined.** The README says "case, whitespace and listed synonyms (`accepted_values`) are normalised". But `generate.accepted_for` (generate.py, `accepted_for`) leaves out every display string that *contains* the canonical value, so truth assumes a containment match that no rule states. In the test set, 18 present slots have a quote that is neither the value nor an accepted synonym: BOPP, PP film, PP copolymer, soda-lime glass, uncoated paper, wet-strength paper, tinplate steel, jet black, bright white, royal blue, rigid PVC film (S012-S029). That is about 4% of all slots, half the 10% error budget. Neither choice works as it stands:
   - With exact match, an extractor that copies "jet black" or "BOPP" is marked wrong.
   - With containment, "PETG" scores as PET, and "black (carbon black)" scores as "black".

   *Fix:* treat material and colour like features. Give the extractor the closed canonical list (the `COMPONENTS` values and the `COLOURS` keys) and score by exact match after normalisation against `value` plus `accepted_values`. Make `accepted_values` list every display variant, not only the non-containing ones. Then state in amendment 2 that returning `black` for truth `black (carbon black)` is wrong (a missed carbon-black flag).

2. **Quote matching is brittle, and pass mark 3 allows zero untraced values.** Two problems:
   - Rule (b) says a feature quote must *equal* the canonical value or a paraphrase. An extractor that quotes the row ("Glue: hotmelt adhesive") or the sentence ("Please note aqueous varnish on this item.") is untraced, and one such quote fails the whole proof test. *Fix:* the normalised quote must *contain* exactly one listed paraphrase or canonical value for that key.
   - Quote-on-page matching treats text sheets and scanned sheets differently. On text sheets, pypdf splits table cells onto new lines, which become spaces after normalisation, so "Nett wt 179.7 g" matches. On scanned sheets, `page_text` joins cells with " | " (render_pdf, `lines.append(" | ".join(cells))`) and two-column cells with three spaces, so the same quote fails. *Fix:* in amendment 2, normalise `|` to whitespace on both sides before the substring check, and name pypdf `extract_text()` plus `norm_text` as the page text used for text sheets. The README does not say this today; only the tests do.

## Must fix in slice 3 (extractor)

3. **Keep the extractor away from scorer-side data.** The extractor must take only the PDF bytes, plus the canonical vocabularies and the PLAUSIBLE map. Add a test proving it never opens `manifest.json`, `truth/` or `tuning_truth/`, for example by running it on a copy of the PDF in an empty temp dir. `page_text` and truth sit next to the sheets, so a leak would quietly invalidate the scanned-sheet result.
4. **Two-column sheets need layout-aware input.** pypdf's plain text interleaves the two components row by row. In S016, "Shade: blu" (pouch) and "Resin: soda-lime glass" (container) alternate. This is a fair and realistic difficulty, but a text-only extractor cannot attribute the fields. Send page images, or `extract_text(extraction_mode="layout")`, for every sheet, and record which one was used.
5. **The budget guard must stop before a call can cross a cap, not after.** It needs a pre-call estimate plus `max_output_tokens`, set reasoning effort explicitly, and must log billed tokens per sheet. With reasoning billed at USD 120 per 1M, one sheet with 2k reasoning tokens costs about USD 0.24, close to the USD 0.316 per-sheet bar, and only about USD 2.5 is left for tuning (roughly 8 tuning-sheet calls). Before the test run, check the per-sheet cost on the 5 tuning sheets. If a sheet costs more than USD 0.25, cut reasoning effort before tuning the prompt.

## Suggestions

6. `ram_category` comes straight from material. A missing material therefore costs two slots, and a wrong material usually costs two. Note this in amendment 2, or score `ram_category` only when material is present.
7. The kill test lists label "type, material, coverage" and closure "material, liner". The benchmark collapses each feature to one canonical value, and coverage is not modelled. Amendment item 3 implies this but should say so in one line, so the validator doesn't read a pass as covering label coverage.
8. Missing marker "none stated" sits close to the present paraphrases "sleeve: none", "liner: none" and "barrier layer: none". This is fair, but show one example of each in the tuning prompt.
9. A false conflict flag on a truth-`present` weight isn't defined. It presumably scores 0; say so.
10. Process, for the Studio Lead: `state/BUDGET.md` says the gpt-5.4-pro price is unconfirmed. T-12's model spend was agreed with Vishal (Q-7). The T-56 USD 12 cap is logged only as a reversible decision. Confirm that it is covered, because spending is on the ask-first list.

## Is a pass meaningful?

Yes, for capability on realistic-looking messy layouts, once items 1 and 2 are settled. The sheets force the extractor to:
- normalise synonyms;
- reject distractor weights;
- attribute fields in buried prose and two-column layouts;
- read scans;
- find conflicts on later pages and in footnotes.

The limit is that it is still one generator with fixed sentence frames. That is why the public-PDF realism report (amendment item 7) must be in the slice 4 write-up, and the validator should weigh it.
