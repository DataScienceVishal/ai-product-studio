# Review: p/restaurant-margin-copilot/T-80 (head ebf8646)

Reviewer, 2026-11-25. Scope: the benchmark harness in `products/restaurant-margin-copilot/benchmark/`, checked against `KILL-TEST.md` on main. Focus: anything that could make the single TEST run's verdict wrong or unsafe.

**Verdict: CHANGES.** The scorer is sound and the freeze order is right. Three small guards are missing around the one irreversible TEST run. Each fix is a few lines.

## Evidence

- Tests: `python3 -m pytest -q` gave **62 passed, 1 skipped in 52.44s**.
- `extract.check_test_allowed()` passes. `extract_config.py` still hashes to `FROZEN.json` (`30d9ce00…`).
- Commit order in git:
  - KILL-TEST.md on main: e371acf, 09:23.
  - Generator and DEV set: 8a11021, 09:28.
  - Freeze: 747e03a, 09:45:55.
  - `layouts_heldout.py` and the TEST set: 5b78f6b, 09:50:28.
  - The freeze came before the held-out code. The only change to `generate.py` after the freeze is a 4-line `sys.modules` alias, which does not touch the layouts.
- Perfect-prediction check (my script):
  - Feeding the ground truth through `score_invoice` for all 50 TEST invoices gives 100% line accuracy and 100% reconciliation. No scorer artefacts.
  - TEST mix: 50 invoices, 66 pages, 684 lines, 25 held-out, 30 distorted, 10 credit notes, 15 multi-page. This meets section 1.
- Ledger: 73 rows, USD 0.4571 in total, 0 estimated rows, 0 TEST rows. All 73 DEV and smoke records report `model: gpt-5-mini`.
- Secrets: grep of `results/`, the ledger and `*.py` for api-key values, `sk-`, `Bearer` and 32-hex strings found only config hashes. The API key is sent only as a header and is never written or printed.

## Scorer vs KILL-TEST section 2 and 3 (correct)

- **Matching:** Hungarian one-to-one assignment on normalised Levenshtein. Pairs below 0.5 similarity are left unpaired, which is stricter than the spec: a missing line plus a hallucinated line.
- **Line conditions:** all six (a) to (f) are implemented with the stated tolerances. Pack (c) compares cost per base unit, and the units must be of the same kind.
  - Only 48 TEST lines (pack `""`, unit `each`) fall back to per-each. For those lines, (c) reduces to (d). That is expected.
- **Accuracy:** correct / (truth + hallucinated). Failed pages and pages never run contribute no predictions, so all of their lines count as wrong. Both cases are tested.
- **Reconciliation:**
  - Checks that the extracted gross equals the truth gross within 0.005.
  - Checks that the extracted gross equals code-computed net + VAT (per-rate rounding) within 0.01.
- **Silent errors:** wrong lines > 0 and the invoice reconciles.
- **Failure rate:** (failed + unscored) / pages. This is stricter than the spec because it includes pages stopped by the budget.
- **Verdict:** KILL if any kill line holds, then PASS if all pass lines hold, else INCONCLUSIVE. Missing accuracy is treated as 0, so it kills.
- **Leakage:** none on the azure path. `AzureProvider.call` ignores `meta`. The payload is the prompt, the schema and the page image only. `truth_dir` is read only by `FakeProvider`.

## Critical issues (blocking)

1. **The hard cap can be raised from the command line.** `extract.py` `main()`: `ap.add_argument("--max-usd", type=float, default=budget_mod.MAX_USD)` is passed straight to `Budget`.
   - Why it matters: KILL-TEST says the USD 5 cap is hard. One flag removes it.
   - Fix: `max_usd = min(a.max_usd, budget_mod.MAX_USD)`, or refuse values above `MAX_USD`. Add a test.
2. **Nothing stops a TEST rerun or a cherry-picked page.** On `--set test`, `--only`, `--limit-pages` and a plain rerun into an existing `--out` are all allowed.
   - A rerun overwrites `TEST-xxx_pN.json` files, so failed pages can be replaced by later successes.
   - That would inflate accuracy and the failure rate, and it breaks "run once" (KILL-TEST section 5, item 5).
   - Fix: on the test set, refuse `--only` and `--limit-pages`. Refuse an existing `--out` unless `--resume` is given. `--resume` already skips pages that have any record, failed ones included. Never overwrite an existing page file.
3. **Cost per page is not taken from the ledger.** `score.py` `score_set`: `cost = sum(r["cost_usd"] for r in all_recs)` uses the page records.
   - KILL-TEST section 2 says "total billed USD … retries included (ledger)".
   - Attempt-1 spend is lost from the metric whenever no page record is written:
     - `BudgetExceeded` before the 32k retry;
     - `FatalError` part-way through;
     - an overwritten rerun.
   - Fix: sum ledger rows whose label starts with `TEST-` (labels are page ids) and divide by the TEST page count. Also report any mismatch with the record sum.
   - The practical risk is low (about USD 0.009 per page against a USD 0.02 bar), but it is the metric of record.

## Suggestions (non-blocking)

- **Budget race with parallel workers:**
  - `Budget.check` reads `spent_usd` but reserves nothing, so N workers can each pass the check. The overshoot is at most workers x one worst case (about USD 0.065 at 32k), as the docstring says.
  - The ledger also has no inter-process lock.
  - Fine at USD 0.46 spent with `--workers 3`. Still, reserve the worst case under the lock in `check()` and release it in `record()`.
- **Model check:** `rec["model"]` is logged but not checked. If `AZURE_OPENAI_DEPLOYMENT_MINI` ever pointed at a larger model, spend would still be priced as mini. Refuse or flag any response whose `model` does not start with `gpt-5-mini`.
- **Workers not recorded:** `run.json` does not record `--workers`, which affects p95 latency (DEV p95 was 134 s with 7 workers). Record it, and record the start and end time of the run.
- **Reconciliation reading:** VAT is computed in code from the extracted lines. The extracted VAT-by-rate is not used. That is a defensible reading of section 2 (the model never adds up). It means a wrong `vat_rate` on a line breaks reconciliation, so the error is flagged rather than silent. Note this interpretation in REPORT.md.
- **A reconciliation edge case:**
  - If the last page fails but an earlier page printed totals, `merge_pages` takes the earlier totals. That is harmless, because the lines are missing and reconciliation fails.
  - `unscored = total_pages - len(all_recs)` can go negative if stray `*_p*.json` files exist. Clamp it, or match records against the expected page ids.
- **Transient retries:** a page that is throttled on every attempt (`unavailable`) uses up the 32k retry and then counts as failed. That is stricter than the spec, which is fine. Log it distinctly in REPORT.md so a throttling problem is not mistaken for a model failure.
- **DEV-TUNING.md:** it already says that DEV distorted accuracy is 75% (below the 80% KILL line) and that the pass-5 pack rules were fitted to DEV lines. Good pre-registration. Keep that wording in the final report.
