# Review: T-56 commit cf4faac: amendment 3 (gram spellings) and benchmark/REALISM.md

Reviewer: reviewer agent, 2026-11-24. Scope: `git show cf4faac` (benchmark/taxonomy.py, benchmark/tests/test_generator.py, benchmark/REALISM.md, NEXT.md).

## Verdict: CHANGES (documentation only; the code is correct and changes nothing on the scored data)

The regex change is safe. Every number and truth check on the 30 test sheets and 5 tuning sheets is the same as before, and the oracle still scores 100%. The blocking problem is the record: the kill test says "Any change needs a new dated entry here before the next run". Amendment 3 exists only as a code comment, a NEXT.md bullet and a sentence in REALISM.md. The written rule in the idea file and the README still says the units are "(g, kg, mg, oz)".

## Part 1: code

### Evidence

- Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` gave **81 passed** in 7.0 s. That includes `test_perfect_prediction_scores_100_and_passes` and `test_tuning_perfect`, so the oracle is still at 100% on both sets.
- Data is byte-identical. I ran `generate.py --out <scratch>/new` with the new taxonomy, then `diff -r <scratch>/new benchmark/data`: no differences. `git diff cf4faac^ cf4faac -- benchmark/data` is also empty. The generator never calls `parse_weight` (only `score.py` reaches it, through `quote_ok`).
- Old and new regex compared directly. I ran the old pattern `(kg|mg|g|oz)\b` and the new one over `norm_quote(page)` for all 48 page texts (test and tuning) and got the same 198 matches at the same positions. Over 30-character windows starting at every digit there were 0 differences. Over all 349 truth quotes there were 0 differences. No page contains "gm", "gms", "gram" or "grams". `quote_ok` requires the quote to be a substring of the page text, so for any possible prediction its result on the 35 sheets is the same as before. The scores cannot move.
- Mutation check. I reverted the alternation to `(kg|mg|g|oz)` and `test_amendment3_gram_spellings_parse` failed (AssertionError at test_generator.py:365). I restored the file with `git checkout -- benchmark/taxonomy.py`, after which the test passed and the worktree was clean. I also reordered the alternation to `gm|gms|gram|grams`, and the test still passed: `\b` backtracking makes the order irrelevant, which is fine.
- False-match probe (old -> new):

| Input | Old | New | Note |
|---|---|---|---|
| `37 gsm`, `37gsm` | None | None | correct (areal weight) |
| `24 gauge`, `37 grammage`, `37 gr`, `37 grs`, `37 gramm`, `37 gmt`, `37 gmax`, `37 gm2`, `37gm²` | None | None | correct |
| `37 gms.`, `37 GMS`, `37 Grams`, `0.5 gm.` | None | 37 / 37 / 37 / 0.5 | intended |
| `37 gm/m2` | None | 37.0 | same behaviour as the existing `37 g/m2` -> 37.0 (see S1) |
| `1,000 gm` | None | 0.0 | same as the existing `1,000 g` -> 0.0 (see S2) |
| `37 grammes` | None | None | British spelling still rejected (see S3) |

- `quote_ok` is consistent. It is the only caller, and weights still go through `parse_weight` followed by `weight_within`. The prompt (`extractor/prompt.py:43`) only asks for "number and unit", so the prompt and the scorer do not disagree.
- No model run has happened: there is no `results/` directory, and NEXT.md says "No Azure call made". So the change is genuinely "before any run".

### Critical issues

C1. **Amendment 3 is not recorded where the kill test says amendments live.**
- Where: `state/ideas/pepr-packaging-data-pipeline.md`, on main. Amendment 1 item 2(b) and Amendment 2 item 2 both fix the weight units as "(g, kg, mg, oz)". `benchmark/README.md:64` and `benchmark/KILL_TEST_AMENDMENT_2.md` item 2 say the same.
- Why it matters: the idea file says "No pass mark is changed after seeing results. Any change needs a new dated entry here before the next run." As things stand, the validator would read written rules that disagree with `taxonomy.py`. The change is harmless, but the record of it is part of what makes the kill test trustworthy.
- Fix:
  - Add "### Amendment 3, 2026-11-24 (before any model call)" to the idea file on main. It should say: weight units in the quote rule also accept gm, gms, gram and grams (case-insensitive, word-bounded); pass marks unchanged; test and tuning data byte-identical; evidence is this review.
  - Mirror it as `benchmark/KILL_TEST_AMENDMENT_3.md`.
  - Update the unit list in `benchmark/README.md:64`.

### Suggestions (not blocking)

- S1. Per-area units still parse as unit weight: `72 g/m²`, `37 gm/m2`, and (new with this change) Veritiv-style `12 gms/100 sq in`. This is not a regression on the scored data, but REALISM change 2 ("weight given only as gsm, µm or case weight is `missing`") will want a negative lookahead such as `(?!\s*/\s*(m|100))`. Put it in the same dated amendment as the supplement set.
- S2. Thousands separators: `1,000 g` parses as 0.0. Real sheets with case or roll weights can contain them. Fix it alongside S1, before the supplement set exists.
- S3. The market is the UK, so consider accepting `gramme` and `grammes` too. Do it in the same amendment rather than a fourth.

## Part 2: REALISM.md

### Claims about our code, checked against generate.py, taxonomy.py and manifest.json

| Claim | Result |
|---|---|
| 6 templates: table, matrix, bom, prose, prose_buried, two_column | True (`generate.py:461-462`) |
| Units g/kg/oz/mg; weights are single values | True (`generate.py:131-140`) |
| 128 of 457 scored slots missing; 22 conflict slots; 8 of 68 components carbon black | True (`manifest.json` stats) |
| No recycled-content field; ram_category derived from material, never printed | True: no recycled-content key in the schema or generator; ram_category is set only in the truth (`generate.py:524-528`) |
| PET and rPET are separate canonical values | True (`taxonomy.py:81-82`) |
| Feature-present rate 0.45 to 0.6 | True (`generate.py:233`: clean 0.6, moderate 0.5, messy 0.45) |
| Buried prose on S021 and S027 | True (`generate.py:105-107`) |
| A stand-alone "Tolerance +/- x g" distractor | True (`generate.py:215`) |
| 5 raster sheets | True (S021-S025, `generate.py:105-106`) |
| Missing markers include n/a and TBC | True (`generate.py:74, 257`) |
| pypdf text keeps each label next to its value | True for label and value (for example "Mass: 0.268 oz" on S016). Note that two_column sheets interleave the two components' rows in pypdf text (S016, S028), so "row by row" understates the reading-order difficulty we already have. |
| Colour labels "Shade, Tint, Colour" | **Incomplete:** the generator also uses "Finish colour" (`generate.py:64`). This weakens the point that real "Finish: Clear" is unlike our labels. |
| `parse_weight` does not parse "37.00gm" (section 2 item 2) | **Stale within the same commit.** It was true before cf4faac and is false after it. Add "fixed by amendment 3" to the sentence. The bare "167" under "Glass weight (g)" case is still correctly described as unsupported. |
| "amendment 7" (section 4) | Refers to Amendment 1 item 7 in the idea file, which exists and says what is claimed. Write it as "Amendment 1, item 7" to avoid confusion with Amendment 3. |

### Internal consistency

- "Recyclability claim with no RAM class: 7 of 13 (rows 3, 5, 6, 7, 8, 9, 12 plus SAICA)" lists 8 documents. Either the count or the list is wrong.
- SAICA is "grades 40B, 99H, 99Z (one page each)" with 15 pages, of which pp 1-3 were read. Section 2 item 3 says "one grade per page (15 pages)", which implies 15 grades. Reword it.
- The country split (UK 2, EU 3, US 5, AU 3 = 13) checks out against the table. "Unit weight in grams or convertible: 5 (rows 1, 2, 3, 4, 9)" and "absent or not per unit: 8" add up to 13.

### URL spot-checks (no web tool, so only internal checks)

- Row 1 (Vision 128-116PCR100): the file name matches the item code, and the quoted "37.00gm ± 2.00gm" matches the new test string. Consistent.
- Row 3 (Colorlites 14097): the file name has the code 14097 and "212ml_Bonta_Jar", matching the row. Consistent.
- Row 4 (Uline): the URL is `RS-17491pdf` but the item is S-17491. That is plausible as Uline's spec-sheet prefix, but I could not verify it.
- Also noticed: row 13's file name ends `-nl` while the row describes Spanish and English content. I could not verify it; a one-line note would help.

### Recommendations vs the fixed bars

- Pass marks are untouched: section 4 says "The pass marks are fixed and I do not suggest changing them".
- The 30 scored sheets are untouched: all five changes go to a separate supplement set with a new seed, reported separately, with any scorer change dated before its first run. NEXT.md follows this (slice S7, "pass marks unchanged").
- Tension to resolve before the optional public set is built: Amendment 1 item 7 covers PDFs "whose licence permits use". REALISM found no permitting licence for any of the 13, yet proposes hand labelling with run-time download. That needs a logged Studio Lead decision, or the "state that none were found" route that item 7 already allows. It is not a merge blocker for this commit.

## To clear CHANGES

1. C1: record Amendment 3 in the idea file on main, in `KILL_TEST_AMENDMENT_3.md` and in `README.md:64`.
2. In REALISM.md, mark the section 2 item 2 `parse_weight` sentence as fixed by amendment 3.
3. Optional in the same pass: the 7-vs-8 count, the SAICA wording, "Finish colour", and "Amendment 1, item 7".
