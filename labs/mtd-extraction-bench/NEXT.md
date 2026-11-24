# NEXT: T-12 status

Status: full run done within the budget: 15 of 15 new calls, $4.49 recorded ($7.95 upper bound, two 502s of unknown billing), 12 of 14 docs scored. Headline in RESULTS.md: review time does not halve model-only (59% pilot formula, 72% with silent errors charged); it only halves with the merchant-memory layer, which is inflated on synthetic data.

## Verify
- `cd labs/mtd-extraction-bench`
- `python3 -m pytest tests` (the default python here has a broken system PIL, so 11 render tests skip; `/usr/bin/python3 -m pytest tests` runs all 26).
- `/usr/bin/python3 report.py` regenerates every table from `results/full.json` and `results/full_raw/` with no API calls. `/usr/bin/python3 run_full.py --score-only` re-scores.
- `run_full.py` resumes: it skips docs that already have raw output and refuses calls past 15 or $11.50 (state in `results/full_budget.json`, persisted, so a rerun cannot reset it). All 15 calls are spent, so it will refuse everything until a human raises the cap in `budget.Budget`. Pilot is never touched.

## Not done
1. Phone photo (`photo_consult`) and second scan (`scan_stall`) failed with HTTP 502; no calls left. Image accuracy rests on one scan. Needs a new budget (about $1.3 to $1.7 per image at medium effort, 14k output cap) and the 5xx retry fix already in `run_full.py` (5xx now bills worst case).
2. Rules are learned from a synthetic prior quarter with the same merchants, so the calibrated numbers are a ceiling. Needs real or at least new-merchant-heavy data to estimate the true benefit (a "new merchant share" parameter in `gen2.make_txns` would be a cheap start).
3. One run per doc: no variance. Repeats cost about $0.30 per text doc.
4. Review seconds are assumptions; run the timed 2-person test (50 lines manual vs assisted).
5. Reasoning effort: `minimal` rejected, `medium` accepted (images). Text docs ran at default effort. Testing `medium` explicitly on text docs could cut cost; untested.
6. Dext or PDF-converter comparison needs an account: ask Vishal first.

## Risk for reviewer
- 502 calls recorded at $0 (see full_budget.json note). - `calib.RISKY_CATS` was chosen from pilot errors; check it is not overfit. - Ambiguous-line truth labels are our own choices.
