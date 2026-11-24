# T-12 pilot check

Verdict: **PASS** (with one wording correction and one recommendation). Checked at c3b0746 in a clean worktree. No Azure OpenAI calls made; `run_pilot.py` not run.

## Evidence

1. pytest: `python -m pytest -q` gives 8 passed.
2. Rescore: `python rescore.py` reproduces every figure in RESULTS.md (clean_pdf cat 0.9375, routed 0.25, auto cat 0.9583, ratio 0.545; csv 0.9375 / 0.2188 / 0.92 / 0.5062; messy 0.9375 date/amount, cat 0.8438, 0.2812, 0.9565, 0.5587; scan and photo 0 / 1.0 / 1.075). `git status` clean afterwards (pilot.json rewritten identically). Token and latency table matches results/run.log (totals 5,709 / 27,619 / 501 s).
3. Scorer: read score.py. Date and amount are exact (amount rounded to 2 dp, signed); description is a SequenceMatcher ratio >= 0.6; routing is conf < 0.8 plus missed lines; auto accuracy uses only conf >= 0.8. Time model re-done by hand: clean PDF (60 + 24*4 + 8*35)/800 = 0.545; messy (60 + 23*4 + 7*35 + 2*25)/800 = 0.5587; scan (60 + 32*25)/800 = 1.075. All match. Independent line-by-line diff of raw output vs truth listed exactly these errors: PDF tyres (0.84, wrong) and ABERNETHY turnover->wages (0.56, flagged); CSV tyres x2 (0.83); messy tyres (0.97), trade-body sub x2 (0.72, flagged), 2 savings sign flips (0.58, flagged, counted as missed).
4. Ground truth vs documents: PDF (pdftotext) lines 1, 16, 32 match truth including balances; CSV rows 1, 16, 32 match; messy_sheet.csv all 32 rows match truth sheet_description and amount (and 5 date formats parse to the truth ISO dates); xlsx row 4 matches csv; scan image viewed, rows and balances match truth (first and last lines checked). Photo truth not eyeballed (same generator).
5. Fictional: "NORTHBANK plc (fictional)", sort code 00-00-00, account 00000000, "Synthetic test document" footer, invented merchants. Grep for common real UK bank/retailer names: no hits. No real people.
6. Secrets: grep for sk- keys, api_key assignments, bearer, azure endpoint, password: none. One long base64-like blob in results/raw_scan_image.txt and raw_phone_photo.txt is the model's encrypted reasoning output, not a credential. .pytest_cache is not tracked.
7. Caveats: honest. Scan and photo are labelled failed runs (8,000-token cap, truncated JSON, partial text previously discarded). Halving called borderline (all three working runs 50.6 to 55.9%, none under 50%). Assumptions are stated and flagged as guesses. Wrong high-confidence lines are counted: 4 (PDF 1, CSV 2, messy 1), confirmed.

## Discrepancy and corrections (RESULTS.md)

- RESULTS.md listed a wrong-sign "transfer from savings" among the category misses. It is not a category miss: the scorer counts those 2 messy-sheet lines as missed lines (amount mismatch), both flagged at 0.58. Reworded and added a bullet explaining it. No numbers changed.

## Undetected errors and the review-time model

The model charges 4 s per auto-accepted line and nothing for a wrong one, so it flatters the result. Recommendation (do not overhaul): report a second ratio with an error penalty, for example 120 s per undetected error (find later plus fix, or amend a return). That moves clean PDF 0.545 to 0.695, CSV 0.506 to 0.806, messy 0.559 to 0.709. So the halving claim fails once even a modest cost for silent errors is included. For the full benchmark, test a rule that sends known-ambiguous categories (tyres, subscriptions) to review regardless of confidence, or samples some auto lines, and report errors per 100 auto lines. Also note the 4 wrong lines are 3 of the same merchant pattern (tyres), so one rule would catch most of them, which also shows how synthetic the set is.
