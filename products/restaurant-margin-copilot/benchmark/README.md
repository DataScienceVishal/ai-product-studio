# Synthetic-invoice extraction benchmark (T-80)

Proof test for restaurant-margin-copilot. The rules, bars and kill lines are in `../KILL-TEST.md` and do not change.
Everything here is fictional: suppliers, addresses, VAT numbers and products are invented.

```
pip install -r requirements.txt        # Python 3.11+, pinned
python3 -m pytest -q                   # 61 tests, about 45 s (renders the DEV set twice)
```

## Files

| File | Job |
|---|---|
| `generate.py` | Deterministic generator: ground-truth JSON, PDF and page images, SHA-256 `MANIFEST.json`. Three dev layouts now (broadliner A, cash and carry, butcher). |
| `distort.py` | Phone-photo distortion (Pillow and numpy): crumple warp, rotation 2-12 degrees, perspective, shadow gradient, blur sigma 0.5-1.5, JPEG q 35-70. Parameters are logged in each truth file under `distortion`. |
| `packs.py` | Pack text to cost per g, ml or each ("12x1L", "5kg case", "6 x 2.5kg", "dozen", "24x330ml"). |
| `extract_config.py` | The frozen part: prompt, strict JSON schema, run config. Hashed. |
| `extract.py` | One call per page image, 16k output cap, one retry at 32k, spend guard, per-call log. `--provider fake` for tests. |
| `budget.py` | USD 5 ledger guard (T-56 pattern): worst case checked before every call; spend is cumulative through `results/ledger.jsonl`. |
| `score.py` | Scorer and markdown report; also prints the verdict against the fixed bars. |
| `freeze.py` | Writes `FROZEN.json` (hash of `extract_config.py`). |
| `smoke_check.py` | Scores single pages in isolation after a smoke call. |

## Sets and seeds

| Set | Seed | Invoices | Layouts | Status |
|---|---|---|---|---|
| dev | 1001 | 10 (14 pages, 5 photos, 2 credit notes, 4 multi-page) | the 3 dev layouts | generated and committed, `data/dev/MANIFEST.json` |
| test | 2025 (rerun 2026) | 50: 25 dev layouts, 25 held-out; 30 photos, 10 credit notes, 15 multi-page | all 6 | plan fixed in `generate.test_plan()`; **cannot be generated yet** |

Check the DEV set is still byte-identical: `python3 generate.py --verify`.

## Held-out layouts (hook)

`broadliner_b`, `greengrocer` and `dairy_drinks` are deliberately not written. After the prompt is frozen, add
`layouts_heldout.py` next to `generate.py`. It must call `generate.register_layout(key, supplier, catalog, rows_per_page,
renderer, page_size, date_format)` for each of the three keys (see the dev layouts in `generate.py` for the shapes).
`generate_set("test")` refuses to run until that module exists. The test set is gitignored under `data/test/` only until you
commit its manifest; remove that line from `.gitignore` when the set is made (the images are about 20 MB).

## Run order

1. Dev work (any number of runs while budget lasts):
   `python3 extract.py --set dev --provider azure --out results/dev1 [--reasoning-effort low|medium] [--limit-pages N]`
   then `python3 score.py --set dev --extractions results/dev1`.
2. Choose reasoning effort on dev, edit `extract_config.py`, then `python3 freeze.py` and commit `FROZEN.json`.
3. Write `layouts_heldout.py`, run `python3 generate.py --sets test`, commit `data/test` and its manifest.
4. The full TEST benchmark, once:

```
python3 extract.py --set test --provider azure --out results/test1 && python3 score.py --set test --extractions results/test1
```

`--set test` is refused unless `../KILL-TEST.md` exists, `FROZEN.json` matches `extract_config.py`, and `data/test` exists.
The fallback rerun (seed 2026) needs the seed changed in `generate.py` by a dated amendment, then `--out results/test2`.
Add `--resume` to continue a cut-off run; pages without a result file count as wrong.

## Spend guard

Prices (gpt-5-mini USD 0.25 in / 2.00 out per 1M tokens) live in `budget.PRICES` with their source. Before each call the
guard adds that call's worst case (estimated input plus the full output cap, reasoning included) to the ledger total and
refuses if it would pass USD 5. A timeout or unreadable reply is charged its worst case. The run stops with exit code 3; pages
not run count as wrong. Only the mini deployment (`AZURE_OPENAI_DEPLOYMENT_MINI`) is ever called. The key is never printed.

## Scoring

As KILL-TEST.md section 2: optimal one-to-one line assignment on description similarity; a line is correct when description
similarity >= 0.95, qty exact (sign included), pack cost per base unit within 0.5%, unit price and line total within 0.005, VAT
exact. Reported: overall, clean, distorted, held-out, dev-layout, credit-note and multi-page accuracy; reconciliation rate;
silent-error invoices; failure rate; cost per page; p95 latency; and, for information, accuracy by distortion severity.
