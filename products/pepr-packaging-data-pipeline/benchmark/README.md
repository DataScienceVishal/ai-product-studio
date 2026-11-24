# pEPR spec-sheet extraction benchmark (T-56)

Kill test and pass mark: `state/ideas/pepr-packaging-data-pipeline.md`, section "Proof test (T-56)". The pass mark is fixed there and is not repeated here as a source of truth. Amendments dated 2026-11-24 are in `KILL_TEST_AMENDMENT.md`.

## Layout

```
benchmark/
  truth.schema.json     JSON Schema for one sheet's truth
  taxonomy.py           plausible feature keys per component type, feature vocabulary and paraphrases,
                        component-name synonyms, weight parsing and tolerance (shared by generator and scorer)
  generate.py           deterministic generator; tests in tests/ (byte-equal regeneration is tested)
  data/sheets/S001.pdf ...        30 synthetic test sheets
  data/tuning/S901.pdf ...        5 tuning sheets, different seed (prompt tuning only)
  data/truth/, data/tuning_truth/ truth JSON, one per sheet (written by the generator, spot-checked by hand)
  data/manifest.json              tiers, layouts, templates, messiest 10, stats, recorded page text of image-only sheets
  public/               genuinely public spec PDFs (licence noted), reported separately (optional)
  score.py              scorer (slice 4)
```

## Dataset

30 synthetic sheets (seed 20261124), three tiers of 10; `messiest_10` is the messy tier, S021-S030. 5 tuning sheets (S901-S905, seed 20261125).

| Tier | What is in it |
|---|---|
| clean (S001-S010) | one component, g only, all core fields present, canonical feature wording, one distractor (case count). Field labels are already synonyms (Resin, Shade, Nett wt...). |
| moderate (S011-S020) | 2-4 components, prose / matrix / bill-of-materials / two-column / table, mixed units (g, kg, oz, mg), missing fields, 7 conflicts, paraphrased features, 1-2 distractors |
| messy (S021-S030) | 3 components, abbreviations ("blk", "nat.", "CB black", "Al"), 2 missing core fields, 1-2 conflicts per sheet, 2-3 distractors, features and values buried in paragraphs of prose (S021, S027), S021-S025 rasterised (image only, skew and noise) |

Difficulty features: label synonyms (Resin, Substrate, Polymer, Construction; Shade, Tint; Nett wt, Mass, Net mass); component-name variants (shipper carton, sachet, bottle body); distractor numbers (gross weight, pallet weight, wall thickness, cap torque, case count, tolerance); absent rows instead of "-"; varied missing markers (`n/a`, `TBC`, `to be confirmed`, `none stated`, blank cell, or nothing at all); paraphrased feature text (truth holds the canonical value, the quote holds the paraphrase); headers and footers on every page; 6 templates (table, matrix, bill of materials, prose, buried prose, two-column); conflicts as a footnote on the same page or as a packing note on a later page; carbon-black colour cases (colour value `black (carbon black)`, stated as "carbon black pigmented", "CB black" etc.).

Counts, test set (from `manifest.json`): 68 components, 466 scored slots (307 present, 137 missing, 22 conflict), 8 carbon-black components. Tuning set: 14 components, 96 slots, 3 conflicts.

Tuning set (item: must cover the hard cases): S901 clean one-component table; S902 multi-component (4) with missing fields; S903 mixed units, two-column; S904 scanned with a conflict; S905 contradictory (two conflicts).

## Truth format

One JSON file per sheet, validated by `truth.schema.json`. Per component: `name`, `material`, `colour`, `weight_g` (grams), `features`, `ram_category`. Each field has `status` (`present`, `missing`, `conflict`), `value` or `conflict_values`, optional `accepted_values` (synonyms scored as correct) and `refs` (`page`, `quote`).

Illustrative example (real sheet S018, component "can"; page numbers and quotes are from that sheet's truth file):

```json
{"name": "can",
 "material": {"status": "present", "value": "steel", "accepted_values": ["tinplate steel", "tinplate"],
              "refs": [{"page": 1, "quote": "tinplate steel"}]},
 "features": {"label": {"status": "present", "value": "PP film label", "refs": [{"page": 1, "quote": "polypropylene film label"}]},
              "ink_coating": {"status": "missing"}, "barrier_layer": {"status": "missing"}}}
```
Always read `data/truth/*.json` for the exact content.

## Features: plausible keys and vocabulary

`taxonomy.py` holds `PLAUSIBLE`, the feature keys that make sense for each component type (bottle: closure, label, sleeve, ink_coating, barrier_layer; cap: liner, ink_coating; label: adhesive, ink_coating; outer carton: ink_coating, adhesive, barrier_layer; sleeve: ink_coating, adhesive; tray and pouch: barrier_layer, ink_coating, label; can: label, ink_coating, barrier_layer). Truth labels every plausible key either `present` or `missing`. Only plausible keys are scored; the extractor must return all of them for every component (value or `missing`). Returning an implausible key is ignored, not penalised.

`VOCAB` gives the closed set of canonical values per key (for example "HDPE cap with PE liner"). The extractor is given this list and must return one canonical value; the sheet and the quote hold a paraphrase ("HDPE cap, PE wad liner").

## Scoring rules (fixed before any run)

Slots per component: material, colour, weight_g, ram_category and each plausible feature key. Tolerance: grams within 1% or 0.1 g, whichever is larger. Case, whitespace and listed synonyms (`accepted_values`) are normalised; component names are normalised with `taxonomy.norm_name`.

- **(a) Conflict fields.** A truth `conflict` weight scores 1 only if the extractor flags a conflict AND reports both truth values, each within tolerance. Flagging without both values, or picking one value silently, scores 0 (a silent pick is also counted as an unflagged conflict).
- **(b) Value-in-quote check.** For weights, the scorer parses number and unit from the quote (`taxonomy.parse_weight`, units g, kg, mg, oz), converts to g and compares to the extracted value with the same tolerance. For strings (material, colour) the quote, after whitespace and case normalisation, must contain the extracted value or one of its accepted synonyms. For features the normalised quote must equal the canonical value or one of its listed paraphrases in `VOCAB`. Anything else is an untraced value.
- **(c) Image-only sheets.** The five scanned test sheets (and the scanned tuning sheet) have no text layer. Traceability is checked against the page text the generator rendered onto the raster, recorded per page in `manifest.json` (`page_text`): the quote, whitespace and case normalised, must be a substring of the stated page's text. No OCR is used in scoring. The extractor never sees `page_text`.
- **(d) Component matching.** Extracted components are matched to truth by normalised name first (`norm_name`: case, whitespace, listed variants such as "shipper carton" = "outer carton"); material is a tie-break only when the truth material is present and two candidates share a name. Matching is one-to-one and greedy in sheet order. An extracted component with no match scores one wrong field per slot; an unmatched truth component misses all its slots.
- **Missing.** For a truth `missing` slot the extractor must return `missing`. A value there is a fabrication: wrong, and reported separately.

Pass marks and their definitions stay in the kill test. Granularity: with 22 conflict slots the 80% bar means at least 18 of 22 (4 or fewer misses allowed). The public-PDF set is a realism check: it must be run and reported, but never changes the pass mark.

## Run budget

- Model: the existing Azure OpenAI deployment `gpt-5.4-pro` (the only deployment available).
- Assumed price (from `state/BUDGET.md`): USD 15 per 1M input tokens, USD 120 per 1M output tokens including reasoning tokens. GBP at 0.79 per USD.
- Token cap: 3M tokens for the whole proof test, counting input + output + reasoning + image tokens, tuning included.
- Spend cap: hard USD 12 (about GBP 9.48) for the whole proof test (tuning + test run), computed at the assumed price. The extractor's guard stops at whichever cap is reached first. At these prices the USD cap binds before the token cap in almost every case (3M tokens of pure input alone is USD 45).
- Per-sheet check (pass mark 5): at most GBP 0.25 = USD 0.316 per sheet, from tokens billed at the assumed price; GBP 7.50 (USD 9.49) for the 30 sheets, which leaves about USD 2.5 for tuning inside the USD 12 cap.
- Runs: 3 permitted for slices 2-4. Slice 2 used 1; this fix run is 2 of 3.

## Regenerate and test

```
python3 generate.py            # rewrites data/ byte-for-byte identically (PDF dates are fixed)
/usr/bin/python3 -m pytest -q  # in benchmark/
```
