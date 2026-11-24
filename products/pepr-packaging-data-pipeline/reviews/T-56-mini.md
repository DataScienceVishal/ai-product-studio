# Review: T-56 mini switch (commit f7af48e)

Reviewer, 2026-11-24. Branch `p/pepr-packaging-data-pipeline/T-56`. No Azure calls made.

**Verdict: CHANGES** (one blocking item, small fix)

## Summary

The commit moves the proof test from gpt-5.4-pro to the `gpt-5-mini` deployment inside the shared USD 12 cap. Most of it is right.

- **Price table.** `PRICES` (gpt-5.4-pro 30/180, gpt-5-mini 0.25/2.00) matches the vendor pages cited.
- **Per-row pricing.** `entry_usd` prices each ledger row at its own `model`. The real ledger loads at USD 3.0915 and 25,805 tokens, all rows `gpt-5.4-pro`. A missing, empty or unknown model raises `UnknownModel` and is never priced at zero.
- **Guard and pre-flight.** `Budget.check` and the pre-flight use `budget.model`, the called model's price.
- **Spend gate intact.** `T56_SPEND_APPROVED=1` is still checked in `AzureResponsesProvider.__init__` and again in `complete()`.
- **No default deployment.** With no deployment set, or an unknown one, the run is refused with exit 2.
- **Untouched.** `score.py`, truth and the test set are not in the diff.

Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` gives **165 passed** in 7.2 s.

### Pre-flight: does it still guarantee the one-shot test run cannot be cut short?

Yes for mini, under two stated conditions. The new reservation is `30 * min(0.316, one_call) + one_call`.

- **Mini:** `one_call` (USD 0.017 at 6000 output tokens) is below 0.316. So the run reserves 31 full worst-case calls. Before sheet k, spend is at most (k-1) x one_call, so `spent + worst <= 30 x one_call < need`, and the guard never refuses. This is stronger than the old formula, which relied on the pass-mark average.
- **Pro:** the reservation is unchanged (USD 11.16) and still refuses.
- **Checked offline against the real ledger:** the pre-flight passes at 6000 output tokens (needs USD 0.527) and at 16000 (USD 1.147), against USD 8.91 left.

The guarantee holds only if:

- **(a) Input stays under 20,000 tokens a sheet.** Each sheet's input estimate must be at most `WORST_INPUT_TOKENS` = 20,000. I checked the largest estimate across the test, tuning and supplement sets: 19,237 (S021 to S023). That leaves about 4% headroom.
- **(b) At most one 5xx retry in the whole run.** Each 5xx is charged a full worst case.

With about USD 8.3 of headroom after the re-tune and USD 0.017 a call, (b) is a theoretical gap, not a practical one. See suggestion 1.

### Incomplete responses

Checked; this part is correct.

- `_parse` raises a non-fatal `ProviderError` that carries the used tokens.
- `extract_pdf` records those tokens in the ledger at the mini price.
- `run.py` writes the sheet with `components: []` and a warning, then prints a count.

I ran `score_sheet` offline on such a sheet (S901 truth): 7 slots, 0 correct, `missing_ok` 0, 0 fabricated, no crash. A truth-`missing` slot counts as missing_ok only when the prediction explicitly says missing. An empty sheet has no prediction for that slot, so it scores 0 there and pass mark 4a cannot be inflated.

### Amendment 6

- **No pass mark loosened.** Marks 1 to 5 match the kill test in `state/ideas/pepr-packaging-data-pipeline.md` (90 / 80 / 0 untraced / 95 / 80 / USD 0.316). `PER_SHEET_USD` stays 0.316, and the USD 12 / 3M caps stay.
- **The new allowance is fixed in advance.** One re-tune on S901 to S905, choosing only effort and max output tokens, recorded before the test run. Prompt changes are excluded and the test set is never used to choose anything. That is acceptable.

## Blocking

1. **The price follows the deployment *name*, not the model that actually answers.** Locations: `extractor/budget.py:26`, `extractor/extract.py:149`.
   - **The problem.** `DEPLOYMENT_MODELS = {name: name ...}` assumes an Azure deployment called `gpt-5-mini` serves gpt-5-mini. But Azure deployment names are free text. The API's reported model is stored as `served_model` and never compared with the price model.
   - **Why it matters.** If the deployment named in `AZURE_OPENAI_DEPLOYMENT_MINI` is backed by another model (for example a pro deployment named or renamed carelessly), every row is priced up to 120x too low. The USD 12 cap is then not a cap. A 30-sheet run could really spend about USD 50 while the ledger shows about USD 0.5. That is money at risk, and the fix is cheap.
   - **Fix.** After each successful response in `extract_pdf`:
     - Record the row first (already done).
     - Then require `re.fullmatch(re.escape(budget.model) + r"(-\d{4}-\d{2}-\d{2})?", res.model)`. Use a full match: a plain prefix check would let a future `gpt-5` price entry match `gpt-5-mini`.
     - On a mismatch, raise a fatal `ProviderError` (exit 5) naming both models.
     - Add a test: deployment `gpt-5-mini` returns `"model": "gpt-5.4-pro-2026-03-05"`, and the run stops after one sheet with a non-zero exit.
   - **Exposure after the fix:** at most one call before the stop.

## Suggestions (non-blocking)

1. **Make the pre-flight self-checking.** Location: `extractor/budget.py:42-43`.
   - Compute `max(estimate_input_tokens(...))` over the actual sheets, or assert that each sheet's `est_in <= WORST_INPUT_TOKENS`. Condition (a) then becomes enforced instead of coincidental (19,237 vs 20,000).
   - The token side reserves only `PER_SHEET_TOKENS` = 20,000 a sheet, but a worst-case call is 26,000 at 6000 output tokens and 36,000 at 16000. So the token reservation is not a true worst case. This is harmless now (about 2.97M tokens left against 1.08M worst), but the code comment should not claim more than it checks.
2. **`extractor/run.py:119`: the empty-sheet file shows `usage.usd` 0.0 even though the call was billed.** The ledger is the truth for pass mark 5, so the result is correct. But the file misleads anyone who reads it. Write the actual `usd(e.input_tokens, e.output_tokens, budget.model)`.
3. **`run.py` now writes an empty sheet for *every* non-fatal `ProviderError`, not only incomplete ones.** That includes a timeout and "gave up after 4 attempts". It still scores as missing, which is the conservative outcome. The run summary should list the reasons as well as the count, so an outage is not misread as an output-budget problem.
4. **The NEXT.md step 1 command (`T56_REASONING_EFFORT=low`) will be refused with exit 2.** `REASONING_EFFORTS` (`extractor/providers.py:18`) does not include `low`. No money is spent, and NEXT.md says so. Either add the value after checking the mini model page or change the command to `medium`, so the next run does not stumble on it.
5. **Tests.** Add a scored end-to-end test: a fake incomplete sheet run without `--no-score`, asserting that 4a is not inflated. It is verified manually above but not pinned by a test.

## Re-review: commit c8b6112 (2026-11-24)

**Verdict: CHANGES.** The code fix is correct. One line in the handover note must be corrected before merge.

Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` gives **181 passed** (165 before, plus 16 new). No Azure calls made.

**Blocker 1 (served model) is resolved.**
- **The match rule.** `budget.served_model_matches` (`extractor/budget.py`) requires a full match: the price-table name, optionally followed by `-YYYY-MM-DD`. The tests cover these cases: `gpt-5-mini-pro`, a partial date, a trailing suffix, the pro name, `gpt-5`, an empty string and `None`.
- **No default model.** `_parse` no longer falls back to the deployment name when the response names no model (`extractor/providers.py:202`), so a missing model counts as a mismatch.
- **On a mismatch** (`extractor/extract.py:149-158`), the row is recorded at `most_expensive_model()` (gpt-5.4-pro), and the code raises a fatal `ProviderError`. `run.py` then returns exit 5 after one ledger row. A test covers this end to end.
- **The fake provider** now reports `gpt-5-mini`. The fake-provider tests that previously used a pro budget now use mini, so the fake path also goes through the check.
- **Remaining exposure** is one call. The guard reserved that call at the expected model's price before it was made. If the deployment actually serves pro, a worst-case call costs about USD 1.68 at 6000 output tokens (about USD 3.48 at 16000), which fits within the USD 8.91 left. A served model that is not in the table at all is priced at the table's maximum, which could still be too low. That is acceptable: the run stops at once.
- **False alarms.** If Azure reports the model in an unexpected format, the check stops the run falsely. That one row is overcharged at pro prices against the cap (USD 1 or less at expected token counts). It cannot affect pass mark 5, because the re-tune runs before the test set and would show the problem there first. Acceptable.
- `REASONING_EFFORTS` now includes `minimal` and `low`. The default stays `medium`, and an HTTP 400 is fatal with no spend.

**Blocking**
1. **`products/pepr-packaging-data-pipeline/NEXT.md` (run bb8d, step 1) says "the reviewer checked gpt-5-mini accepts both".** The reviewer did not check this: neither review made a model call or looked up accepted reasoning-effort values. The note must not credit me with a check I never did. Fix: change it to "minimal/low are allowed by the code but not verified against gpt-5-mini; if the re-tune returns HTTP 400 (fatal, no spend), rerun with medium". This is a documentation fix only; no code needs to change.

**Suggestion**
- **`Budget.record` has a duplicate check.** Its new `if model not in PRICES` repeats what `price_for` already does. It is harmless; drop it or keep it.
- **Earlier suggestions 1 to 3 and 5 still stand.** Suggestion 4 is resolved, apart from the NEXT.md wording above.

## Final verdict (HEAD 4fbfac0): PASS

`1feb857` and `4fbfac0` change only NEXT.md. It no longer credits the reviewer with checking the effort settings: it says the Studio Lead checked minimal and low with two tiny calls, untested on full sheets, and the re-tune command now uses medium. The full suite passes again: 181 tests, no Azure calls. Not blocking: those two "say ok" calls are not in `results/ledger.jsonl`. Their cost is negligible (well under USD 0.001), but any future call made outside the extractor should be recorded in the ledger so that the USD 12 cap covers all spend.

## T-56 resume review: commit 28fae5e (2026-11-24)

**Verdict: CHANGES** (one blocking item, small fix)

Tests: `/usr/bin/python3 -m pytest -q extractor/tests benchmark/tests` gives **197 passed**. No Azure calls were made. I did not run score.py on test1 and did not open any test truth.

**What is right**
- **Resets after send are charged and retried.** These are `ConnectionResetError`, `ConnectionAbortedError`, `BrokenPipeError`, TLS errors and `http.client` errors, whether raw or wrapped in `URLError`. Each one goes through `_charge_and_retry` (`extractor/providers.py`), which works like the 5xx path:
  - it writes a worst-case `estimated` row first;
  - it runs `budget.check` again before the next attempt, and a `BudgetExceeded` from that check propagates, so no further call is made;
  - then it backs off.
- **Why the old crash happened.** In CPython's `urllib`, `getresponse()` is outside the `URLError` wrapper. So a raw `OSError` really does mean the request was sent, which is how S017 crashed. Errors before send (connection refused, DNS) stay free. Timeouts are still charged and never resent.
- **Retries are bounded and stay under the cap.**
  - The loop is `range(retries + 1)`, which is 4 attempts.
  - Every attempt is preceded by a guard check: `extract_pdf` checks the first, `_charge_and_retry` checks each retry.
  - So recorded spend can reach the USD 12 cap but never pass it, given that a real call costs no more than its worst case.
  - When retries run out, the result is a non-fatal `ProviderError` with no tokens. `extract_pdf` adds no row for it, so there is no double charge, and the sheet is written empty with a warning.
- **`--resume` was checked offline against the real `results/test1` and a copy of the ledger.**
  - It skips S001 to S016, including S016, which has an empty incomplete output and a final, non-estimated mini row. It never re-calls S016.
  - It plans S017 to S030 (14 sheets).
  - It stops with exit 7 if an output has no row for this price model, or if a final row has no output.
  - A sheet with only estimated rows and no output is re-run, which is what S017 needs after the charge.
- **`--charge-worst-case` cannot double-charge.** It refuses a sheet that already has an output or any ledger row, for any model. I ran it a second time on the copy and it was refused. It also requires `--resume`.
  - The S017 charge is USD 0.017: 20,000 input tokens plus 6,000 output at the mini price. It is an upper bound, because S017's real input estimate is lower.
  - It adds to S017's mark 5 cost. That is conservative and honest.
- **The pre-flight with `--resume` is sound.** It reserves 14 times one worst-case call, plus one more: USD 0.255. Spend after the charge is USD 3.222, so USD 8.78 is left.
  - The earlier argument still holds: each remaining sheet's input estimate is at most 19,237 tokens.
  - Each reset retry uses one extra reservation of USD 0.017. With about USD 8.5 of headroom, a cut-short run is not realistic.

**Blocking**
1. **`extractor/run.py:133` (with lines 137-147): `--resume` overwrites `results/test1/run.json` and never checks that the resumed settings match the original run.**
   - **Why it matters.** Amendment 6 item 4 and the Studio Lead's decision require the same settings for the single test run. Today `run.json` is rewritten before the resume plan is built. A resume that silently uses a different `T56_MAX_OUTPUT_TOKENS`, effort or deployment would mix two configurations in one "single" test. For example, a value left in the shell from tuning would do it. The overwrite would also replace the on-disk record of what S001 to S016 ran with. Git still has it, in c334ce4, but the tool should not depend on that.
   - **Fix.** With `--resume`, read the existing `<out>/run.json` before writing anything. Refuse with exit 7 if any of `set`, `deployment`, `price_model`, `max_output_tokens` or `reasoning_effort` differs. Write the resume's own record to `<out>/run-resume.json` instead of overwriting `run.json`. Add a test for each case: matching settings resume, and a different `max_output_tokens` exits 7 before any charge or call.

**Suggestions**
- **Do the S017 charge after the consistency checks.** `_resume_plan` writes the `--charge-worst-case` row before it checks the other sheets. If that check then exits 7, the charge is already in the ledger, and re-running the same command is refused because S017 now has a row. That is loud and safe, but confusing. Checking everything first and charging last would avoid it.
- **`ssl.SSLError` wrapped in `URLError` is charged at worst case.** This includes certificate failures during the handshake, which happen before send. It is conservative, at most 4 times USD 0.017 a sheet. Acceptable, but a comment would help.
- **Refresh the NEXT.md resume command.** It should show the recorded values (`T56_REASONING_EFFORT=medium T56_MAX_OUTPUT_TOKENS=6000`) instead of `<recorded>`.

**Resume re-review, commit 91b9318: PASS.**
- **Blocker 1 is resolved.** With `--resume`, the run compares `set`, `deployment`, `price_model`, `reasoning_effort` and `max_output_tokens` with the first run's `run.json`. If any differ, or `run.json` is missing or unreadable, it exits 7 before any charge, call or write. The first `run.json` is never overwritten; each resume writes its own record to `run-resume[-n].json`.
- **The real `results/test1/run.json` exists.** It records test, gpt-5-mini, gpt-5-mini, medium and 6000. I checked it offline: those settings match, and `max_output_tokens` 16000 is refused.
- **Tests:** 206 passed. No Azure calls, no scoring.
- **Suggestion, not blocking:** a `--set test` run *without* `--resume` into an `--out` that already holds outputs still overwrites `run.json` and re-calls every sheet. Consider refusing that case unless a new, empty `--out` is given.
