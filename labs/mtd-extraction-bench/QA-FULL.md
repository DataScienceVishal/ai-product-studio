# T-12 full-run QA check

Verdict: **PASS with caveats** (numbers reproduce, spend is within the cap, no scoring bug changes the conclusion). Checked at 7990159 in a clean worktree, offline only: no model calls made, `run_full.py` run only conceptually (see 3). The G1 question "does review time halve?" stays **not proven**: model-only does not halve; the calibrated 35.4% is a ceiling.

## 1. Tests
`/usr/bin/python3 -m pytest tests -q` -> `26 passed in 0.50s`.

## 2. Numbers reproduce
`/usr/bin/python3 report.py` regenerates results/full_report.md figures. All match RESULTS.md and NEXT.md: model-only pilot formula 59.3%, silent-charged 71.8%, calibrated silent-charged 35.4% (pilot formula 32.9%), category accuracy 95.6% (94.4 PDF / 95.8 CSV / 97.9 sheet / 93.8 scan), ambiguous accuracy 98/112 = 87.5%, silent errors 3.7 per 100 auto (0.6 calibrated), threshold sweep 34.0/35.4/37.0/37.0, per-format table, tokens 11,263 in / 36,041 out, total $4.49 (4.4939), 15 of 15 calls, 12 of 14 docs scored. Deterministic extraction 100% on text docs is asserted by tests (not by report.py). No mismatch.

## 3. Spend
- Recorded $4.4939 over 15 calls: 1 HTTP 400 ($0, rejected before generation, reasonable), 12 completed, 2 HTTP 502 at $0.
- Upper bound: per image reserve = 3000 in x $15/M + 14,000 out x $120/M = $1.725; 4.49 + 2 x 1.73 = $7.95. Correct arithmetic and honestly stated as unknown billing. It does not include the pilot (about 5,709 in / 27,619 out = $3.40 at the same prices) or any earlier probes. Combined worst case about $11.35, under the $15 cap.
- Guard: persisted in results/full_budget.json, reservation under a lock, refuses past 15 calls or $11.50. With calls=15 the next `reserve` raises before any HTTP request. Weakness: the state is a tracked file and the cap is a constructor default, so anyone (or a fresh clone with the file deleted) can reset it; two concurrent processes would race on the file. Acceptable for a human-gated lab, not a hard control. The real stop is that credentials are only present when a human supplies them.
- Resume gotcha: the two 502 docs are recorded in results/full_runs.json, and `run_full.py` skips docs present there, so even with a bigger cap a rerun will not retry them until their entries are removed. Documented here; NEXT.md should say so.

## 4. Overfitting and merchant memory
- Every document contains each merchant template of its persona once (picks = permutation of the merchant list, then repeats), and the prior quarter uses the same list. Rule coverage: 356 of 384 scored lines (92.7%); xlsx lowest (22 to 28 of 32) because sheet wording differs.
- 20 of the 37 merchant keys in the full run also exist in the pilot list (gen.MERCHANTS), so the full run is not independent of the pilot.
- `RISKY_CATS` effect is nil: calibrated with rules and cap 35.4%; rules only 35.65%; cap only (no rules) 72.9%; nothing 71.8%. The pilot-derived category list is not what produces the gain. The gain is merchant memory, and the rules are built from truth labels, which makes category accuracy 100% on most docs by construction.
- Share of the gain from memory: simulation re-scoring with a random subset of the rules (mean of 20 seeds):

| Rules kept | Calibrated ratio (silent charged, 120 s) |
|---|---|
| 100% (reported) | 35.4% |
| 75% | 45.3% |
| 50% | 54.4% |
| 25% | 64.1% |
| 0% (cap only) | 72.9% |

So the halving holds only if roughly 60% or more of lines hit a known merchant. RESULTS.md already called 35.4% a ceiling; I added these figures.

## 5. Ambiguous lines
112 of 384 scored lines (29%) are truth-flagged ambiguous (labels are ours). Model category accuracy: 98 of 112 = 87.5% on ambiguous, 269 of 272 = 98.9% on non-ambiguous, 95.6% overall. Excluding ambiguous lines raises accuracy by 3.3 points. Ambiguity is also what pushes routed share up (more flags), so the model-only time ratio depends on how ambiguous real clients are.

## 6. Limitations stated, and sensitivity
RESULTS.md already states: one run per doc and no error bars (about 3 points per line), the 120 s silent-error cost as a guess, review seconds as assumptions, scan evidence of 1 doc. Sensitivity (12 docs pooled, assisted time as share of manual):

| Silent-error cost | Model only | Calibrated |
|---|---|---|
| 0 s (pilot formula) | 59.3% | 32.9% |
| 60 s | 65.6% | 34.1% |
| 120 s (reported) | 71.8% | 35.4% |
| 240 s | 84.3% | 37.9% |
| 480 s | 109.3% | 42.9% |

Per format model-only (60 / 120 / 240 s): PDF 68.3 / 72.8 / 81.8, CSV 63.5 / 66.0 / 71.0, sheet 62.1 / 67.1 / 77.1. The RESULTS.md claim "62 to 68% at 60 s" is confirmed. Model-only never reaches 50%, even at 0 s. The scan (one doc, 4 silent errors) drives the high-cost tail.

## 7. Scoring code
Read score.py and calib.py. Greedy line matching, silent error = wrong category/date/amount/description at conf >= 0.8, time model hand-checked in the pilot check and consistent here. No bug found that changes the conclusion. Notes: (a) rule override in calib uses the reviewed prior label, so calibrated category accuracy is circular; (b) calibrated silent errors exclude lines overridden by a rule (routed at 0.6), which is intended; (c) scan figures rest on one document.

## Caveats the validator must weigh
1. Synthetic, self-generated data with a short repeating merchant list; 29% ambiguous lines with our own labels.
2. Model-only floor (59 to 72%) is the defensible number; 35.4% needs about 60%+ known-merchant spend and reviewed history.
3. Full run shares 20 of 37 merchants with the pilot; not an independent sample.
4. One run per doc, no variance, 3 to 5 docs per format; images: 1 scan scored, 0 phone photos.
5. All review seconds are assumptions; no timed human test. Silent-error cost is a guess (table above).
6. Spend: $4.49 recorded, up to $7.95 if the 502s were billed; plus pilot about $3.40; under the $15 cap either way.
7. Cost per text doc about $0.29 on a pro-tier model: the unit economics at about 32 lines per doc need checking against the price of the product.
