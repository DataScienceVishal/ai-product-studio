### Amendment, 2026-11-24 (before any run)

Made before any extractor exists and before any run. Pass marks are unchanged.

1. **Ground truth.** Truth is written by the generator from the same data model that renders each sheet, not by hand. It lives at `benchmark/data/truth/` (tuning sheets: `benchmark/data/tuning_truth/`). It was spot-checked by hand against the PDFs. Every present value carries a page and a quote that is tested to appear on that page.
2. **Scoring rules (fixed before any run).**
   - (a) A conflict weight scores 1 only if the extractor flags a conflict and reports both truth values, each within tolerance (1% or 0.1 g, whichever is larger). A silent pick scores 0.
   - (b) The value-in-quote check parses number and unit from the quote (g, kg, mg, oz), converts to grams and applies the same tolerance. Strings must match after case and whitespace normalisation and listed synonyms. Feature quotes must be the canonical value or a listed paraphrase.
   - (c) Image-only (scanned) sheets are checked against the page text the generator rendered onto the raster, stored in `benchmark/data/manifest.json`. Whitespace and case normalised substring match. No OCR in scoring.
   - (d) Components are matched by normalised name first (listed name variants), with material as a tie-break only when the truth material is present. One-to-one, greedy.
3. **Missing features.** Every feature key that is plausible for a component type (map in `benchmark/taxonomy.py`) is labelled in truth as present or `missing`. The extractor must return all plausible keys for every component, using `missing` when the sheet does not state one. Only plausible keys are scored. Features are returned as one value from a closed vocabulary; sheets use paraphrases.
4. **Budget counting.** The 3M token cap counts input + output + reasoning + image tokens, tuning included. Model: Azure OpenAI deployment `gpt-5.4-pro`. Price basis: USD 15 per 1M input and USD 120 per 1M output (incl. reasoning), from `state/BUDGET.md`; GBP at 0.79 per USD. The GBP 0.25 per sheet check is computed on that basis. Added hard cap: USD 12 of model spend for the whole proof test (tuning + test run), enforced by the extractor guard; it stops at whichever cap comes first.
5. **Conflict count.** The test set has 22 conflict cases (7 in the moderate tier, 15 in the messy tier). The 80% conflict bar therefore needs at least 18 of 22. The test set has 68 components and 457 scored slots (307 present, 128 missing, 22 conflict; ram_category counted only where material is present).
6. **Tuning set.** The 5 tuning sheets (different seed) cover one clean sheet, one multi-component sheet with missing fields, one mixed-units sheet, one scanned sheet with a conflict and one contradictory sheet.
