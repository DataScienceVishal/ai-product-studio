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
