# T-80 benchmark: state and next steps

## State (branch `p/restaurant-margin-copilot/T-80`)

Done and pushed:
- Generator, DEV set (seed 1001) and manifest, committed before any model call.
- Extractor (one call per page, 16k cap, one retry at 32k), scorer with every KILL-TEST.md metric, USD 5 ledger guard.
- DEV tuning, 5 passes (`results/DEV-TUNING.md`). Chosen config: medium reasoning effort, prompt as of pass 5.
- `FROZEN.json` committed (sha256 `30d9ce00e7fa...`), **before** the held-out layouts were written (commit order: 747e03a freeze, then the held-out commit).
- `layouts_heldout.py` (broadliner B, greengrocer, dairy and drinks wholesaler) and the TEST set (seed 2025): 50 invoices, 66 pages, 25 dev-layout and 25 held-out, 30 photos, 10 credit notes, 15 multi-page. `data/test/MANIFEST.json` committed.
- `main` was merged into this branch only to bring in `KILL-TEST.md`, which the test guard requires. Nothing was merged to main.
- Tests: 62 passed, 1 skipped (the skip is "test set refused until held-out layouts exist", which no longer applies).

**Not run: the TEST extraction.** No TEST image has been sent to a model.

Ledger (`results/ledger.jsonl`): about USD 0.457 spent of the USD 5 cap (3 smoke calls plus 5 full DEV passes). DEV tuning stayed inside the USD 0.60 allowance.

## Known risks the TEST run may hit

- DEV distorted accuracy at the chosen config is 75%, below the 90% PASS bar and below the 80% KILL line. DEV has only 5 distorted invoices, so treat it as a rough signal. The cause is column drift on tilted photos: numbers on the right are read from a neighbouring row.
- Latency: p95 was 91 s and 134 s on DEV with 7 pages in flight (bar 90 s, timeout 180 s). Use `--workers 3` or fewer for the TEST run so latency is closer to a single job. `--workers` is not part of the frozen hash.
- The two pack rules added in pass 5 ("2.5KG X4", "X2 400G") were written after seeing those DEV lines, so DEV accuracy is a little flattered.
- Expected TEST cost: about USD 0.009 per page times 66 pages, about USD 0.6, plus retries.

## Remaining steps

1. **Reviewer gate on this branch** (reviewer agent, then security if wanted): check the freeze order in git history, that `extract_config.py` still hashes to `FROZEN.json`, that no code path reaches the pro deployment, and that the scorer matches KILL-TEST.md section 2.
2. **Verify the data and the freeze before running:**
   ```
   cd products/restaurant-margin-copilot/benchmark
   python3 -m pytest -q
   python3 generate.py --verify --sets dev test
   python3 -c "import extract; extract.check_test_allowed(); print('ok')"
   ```
3. **One TEST run** (do not rerun; any rerun is a full rerun with seed 2026, both results reported):
   ```
   python3 extract.py --set test --provider azure --out results/test1 --workers 3 && python3 score.py --set test --extractions results/test1
   ```
   If the run is cut off, continue it with the same command plus `--resume`. Pages with no result count as wrong.
4. **Score against KILL-TEST.md:** `results/test1/REPORT.md` prints PASS, KILL or INCONCLUSIVE against the fixed bars. The validator writes the dated re-score note and the gate log entry. Commit `results/test1/` and `results/ledger.jsonl`.
5. If INCONCLUSIVE: one prompt or config revision on DEV only, a fresh 50-invoice set with seed 2026 on the same layouts, run once inside the same USD 5 total, judged against the same bars (INCONCLUSIVE again counts as KILL).
