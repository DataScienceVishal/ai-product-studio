# Review: T-219 slice 1, `eval.run --live` for tuning phases T1-T3

Branch `p/sme-council-tender-drafting/T-219` at 9d3d402, against `main`. Reviewer: `reviewer` (opus). No live model calls were made during this review.

**Verdict: PASS.** Nothing blocks the merge. The suggestions below are not blocking. S1 and S2 must be fixed before R1 or E1 can go live.

## Summary

The diff touches 4 files (+223/-14): `eval/run.py`, `eval/ledger.py` (a one-line change to the model check), `tests/test_tender_eval.py` and `NEXT.md`. `--live` is now allowed for T1, T2 and T3 only. It builds the app's `AzureOpenAI` (responses API, headroom 0, 180 s timeout and deadline, 2 retries) and writes to `eval/ledger.jsonl` with `dry_run=False`, with results in `eval/results/`.

Tests: full backend suite on a fresh `starter_test` database (dropped and recreated, `alembic upgrade head` to 0019), python3.13, Azure env vars unset. **1356 passed, 1 skipped, 0 failed** (322 s). This matches NEXT.md.

## The six checks

1. **No scored or recording phase can run live.** PASS. There are two independent barriers.
   - `main` (run.py:414) returns exit 3 for any phase not in `LIVE_PHASES`. This happens before the env check and before any provider or ledger is built. `config` and `retrieval` are refused as well.
   - `run_phase` (run.py:266) raises `PhaseNotReady` for any non-tuning phase whose provider is not named `fake`. `AzureOpenAI.name == "azure"` and `ScriptedFakeAI.name == "fake"`.
   - `LIVE_PHASES` is tested to equal the tuning group in `PHASES`.
   - Mutation check on a scratch copy: removing the `run_phase` guard makes 6 tests fail (the parametrised E1-R2 cases).
2. **Holds, worst-case charges and caps in live mode.** PASS. The ledger has `dry_run=False`, so `LedgerBudget.hold` calls `Ledger.reserve`.
   - `reserve` checks the group sub-cap and the $6.00 total under one `flock`, then writes the hold row with fsync.
   - `run_task` holds before `provider.complete` (llm.py:208).
   - A failed call with 0 tokens is charged the worst case (`charged_worst`). `Context.__post_init__` refuses a provider whose headroom differs from budget.json (0), so the reservation estimate prices the cap that is actually sent.
   - Tests cover all of these on a temp ledger with `dry_run=False`: every hold is matched by its settle, the tuning sub-cap refuses before the call, the total cap binds on its own, and ledger rows without a results file are refused.
3. **Model check in `settle`.** PASS.
   - Dry and fake paths: `dry` is true only when `model == "fake"` on a dry ledger, so these paths never raise. `ScriptedFakeAI` reports `"fake"`.
   - Failed calls: run_task always settles them as `"unknown", failed=True`, which is exempt, so infrastructure failures still go to the AIUnavailable stop.
   - Successful replies: a missing name (`_clean_model` maps it to `"unknown"`), `""`, `gpt-5` and `gpt-5.4-pro` all stop the run (exit 7).
   - The mismatch settle row is written and priced before the raise, and the item is not recorded.
   - Mutation check: putting back the old `model != "unknown"` condition fails `test_live_missing_or_other_model_name_stops_the_run[unknown]`.
   - Under-charging: see S2. This is pre-existing behaviour and is limited to one call.
4. **The key cannot leak.** PASS.
   - The key exists only in `AzureOpenAI.headers`.
   - The missing-env message lists variable names only.
   - Ledger rows hold phase, task, label, model and tokens.
   - Results are item outputs. The stop text for AIUnavailable is `type(e).__name__` only.
   - Client log lines carry kind or status only.
   - A test checks that a sentinel key appears neither in `run_configuration()` nor in run.py.
5. **FROZEN.sha256.** PASS. `sha256sum -c eval/keys/FROZEN.sha256` from the product dir: 34/34 OK. The diff does not touch `eval/keys/`, `demo-data/` or `eval/budget.json`. The budget.json values match the brief: total $6.00, tuning $2.00, model gpt-5-mini, and the caps are pinned in ledger.py as `APPROVED_*`.
6. **Tests are meaningful.** Mostly yes. The `LiveFake` provider is named `azure`, so it goes through real holds and settles. Both mutations above were caught. The gaps are listed in S3.

## Critical issues

None.

## Suggestions (not blocking)

- **S1: the live cache will feed R1 (fix before R1 is enabled).**
  - Problem: `AzureOpenAI` is `cacheable` (the default is True), so every live T1-T3 answer is written into the demo tenant's `ai_cache` (llm.py:235). R1 is not in `CACHE_CLEAR_PHASES`. If the frozen config keeps any T-phase prompt version, R1 would be answered from tuning-run cache, with no ledger row, no fresh recording and no cost measured.
  - T1 is affected the same way on a database that is not fresh: the calibration would under-measure.
  - Fix: clear (or assert empty) the demo tenant's `ai_cache` at the start of every live phase, or run live with caching off. Add a test that a live phase never serves an item from `ai_cache`.
- **S2: wrong-model calls are priced too low, and a truncated wrong-model reply escapes the check (fix before scored phases).**
  - Problem 1: `settle` prices an unapproved model at gpt-5-mini rates. One call to a dearer model could cost more than the ledger records. The run then stops, so this is one call, but the ledger is no longer a true record of spend.
  - Problem 2: on an `AIUnavailable` (truncation or empty answer) run_task settles `"unknown", failed=True` and drops the model Azure reported. A wrong model that keeps truncating never trips the check: the item becomes `ai_truncated`, the run moves on, and it is bounded only by the caps.
  - Fix: build the client with `checked_price` set from budget.json so the app's own guard (`_check_reported_model`) also trips, and turn the resulting 503 into a stop. In the ledger, charge an unapproved model the hold's worst case (or flag the row `unpriced`). Have `AIUnavailable` carry the reported model through to settle.
- **S3: missing tests for `main` in live mode.**
  - Gap: nothing calls `main(["T1", "--live"])` with env set and a monkeypatched `build_live_provider`, `LIVE_LEDGER` and `RESULTS_DIR`. So the wiring is untested: ledger `dry_run=False` on the live path, results dir and exit codes 7 and 8. `test_live_ledger_and_results_defaults_point_at_the_committed_paths` checks constants only.
  - Fix: add one test per exit code.
- **S4: some live failures crash instead of stopping cleanly.**
  - Problem: an HTTP 400 from Azure raises `AppError(502, "ai_rejected")`, which is not `TaskFailed` or `AIUnavailable`, so a live run ends with a traceback (exit 1) instead of a clean stop. The settle row is still written with the worst-case charge, so the ledger stays correct.
  - Fix: either catch it and stop with exit 8, or document it in NEXT.md.
- **S5: the tuning cap is below the tuning worst case.** The worst-case figures for T1+T2+T3 add up to $2.68 against the $2.00 tuning cap. Per-call holds will stop T3 (or T2) early instead of overspending, which is correct, but the operator should expect this. Add a line to NEXT.md.
- **S6: the "fake" name check could be stronger.** The defence-in-depth check relies on `provider.name == "fake"`. It would be more robust to check `ctx.dry` as well, refusing a non-tuning phase when `not ctx.dry`, so that a non-fake but non-network provider on the live ledger is also refused.

## Evidence

- `git diff main...p/sme-council-tender-drafting/T-219`, read in full. I also read the context in `app/ai.py` (AzureOpenAI 331-560), `app/tender/llm.py` (run_task 178-240) and `eval/ledger.py` (reserve and settle).
- Suite: `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test python3.13 -m pytest -q -o addopts=""`. Result: `1356 passed, 1 skipped in 322.16s`.
- Mutations were run on a throwaway copy in the scratchpad (deleted afterwards). No product code was edited.
