# Review: p/holiday-pay-payroll-lookback-audit/T-114 (a8ed38e)

Reviewer: reviewer agent, 2026-11-26. Scope: `mapper/` (extract_names, prompt, mapper, run, score, README) and `tests/test_mapper.py`, against `benchmark/KILL-TEST.md` Part B (B1 >= 95% on 200 names, B2 < $0.02 per 200, KILL if a run is retried with a changed prompt after seeing labels).
Blindness kept: I did not read the T-111-labels branch or any gold.csv. No network or Azure calls were made. All probes used mocked openers in the scratchpad.

## Verdict: CHANGES

The design is sound and most of the maths is right. But the live run is one-shot and can't be undone, and there are four ways it can end in a KILL, or a locked folder with no record, for reasons that have nothing to do with how well the mapper maps. All four must be fixed before the run, because none can be fixed after it.

## Tests

```
$ cd products/holiday-pay-payroll-lookback-audit && python3 -I -m unittest discover -s tests -t .
Ran 96 tests in 0.039s
OK
```

## What is right (checked)

- **Labels can't reach the model.** `extract_names.extract` builds rows only from `KEEP = (id, pay_element_name, source_style)`. `run.read_names` refuses any header that isn't exactly those three columns. `prompt.build_user_message` sends only those three fields. `FakeClient` reads only the user message. `run.py` never opens the gold file.
- **Scoring maths.** The sha256 of the gold file is checked before it is parsed (score.py 124-128). The nine-category figure is the headline and the one B1 is judged on. `fold` maps deduction_excluded to expense_excluded on both sides. A missing prediction becomes UNMAPPED, and UNMAPPED never matches. The AMBIGUOUS and other rows are split correctly. B1 uses `>=` 0.95. B2 gives PASS below $0.02, KILL above $0.05 and REVIEW between (boundaries tested). `test_maths` checks the 9-category, 8-category, ambiguous, per-category and confusion figures by hand.
- **Cost.** `(in*0.25 + out*2.00)/1e6` matches state/BUDGET.md (line 36, gpt-5-mini $0.25/$2.00). Estimate for this prompt: system prompt about 750 tokens and 200 names about 4,700, so about $0.0014 of input. That leaves about 9,300 output tokens (reasoning included) under the $0.02 B2 line. See S2.
- **Azure client.** Requests use the v1 URL with an `api-key` header and no temperature. The chat path sends `max_completion_tokens` and the Responses path sends `max_output_tokens` with `store: false`. The timeout is 180 s. Retries resend the identical body bytes, only after 429, 5xx or a network error, with 2 s and 4 s backoff. Error messages carry only the HTTP code or the exception class name, raised `from None`, so no URL or key reaches the message or a chained traceback. Nothing is logged.
- **One-shot guard.** `run.started` is written before the call, so a crash still blocks a second run. A fake run writes to `<out>/fake/` and can neither unlock nor overwrite a live run (tested).

## Critical issues

### 1. A request that fails before any answer exists locks the one shot and produces a guaranteed KILL (run.py 85-93, mapper.py 96-101)

Probe: mock opener returns HTTP 400 (for example the wrong API flavour or deployment name). `run.main` returns **0** and writes `predictions.csv` with every row `UNMAPPED`, a live `run.json` with 0 tokens, and `run.started`. A second run returns 3 (refused). Run through the README's next command, this scores 0% and a **B1 KILL**, caused by a configuration error.

**Why it matters:** the kill rule (KILL-TEST.md B1) forbids re-running *with a changed prompt after seeing test labels*. A request that got no answer produced no predictions. Nothing can have been learnt from the labels, so re-sending the identical prompt is not what the rule forbids. Locking here wastes the test on a typo. It also makes it tempting to delete `run.started` by hand, which is exactly the kind of unlogged override the guard exists to prevent.

**Recommendation (answer to the brief's question 3):** make a no-answer failure re-runnable with the **same** prompt, under rules the code enforces:
- If every batch ended in `ClientError` (no completion parsed), do **not** write `predictions.csv` or a live `run.json`. Append an entry to `attempts.jsonl` (time, prompt_sha256, error text, transport attempts), remove `run.started`, print a clear error and exit non-zero (for example 4).
- On a later run, refuse if `attempts.jsonl` holds any entry whose `prompt_sha256` differs from the current `PROMPT_SHA256`. This turns "same prompt only" into code instead of trust.
- Once any reply has been parsed (even all-invalid), keep today's behaviour: predictions are written, the folder is locked and the result is scored.
- Copy `attempts.jsonl` into `run.json` (`"failed_attempts": [...]`) so the results show every attempt.
- Tests: a 400 leaves no predictions, exits non-zero and allows a same-prompt re-run. A changed prompt sha is refused. A parsed-but-invalid reply still locks.

### 2. Unhandled reply shapes crash after `run.started`, leaving a locked folder with no run.json and unrecorded spend (mapper.py 208-222)

`_parse` is guarded only for `ValueError, TypeError, KeyError`. Probes:
- Chat reply with `"choices": []` (possible on some Azure content-filter replies) raises **IndexError**, which goes uncaught through `map_names` and `run.main`. The folder holds only `run.started`. The usage block (6,000 in and 9,000 out in the probe) is lost, so the spend is never recorded.
- A Responses reply whose `output` holds a non-dict item raises **AttributeError**, with the same outcome.
- `http.client.IncompleteRead` during `response.read()` is an `HTTPException`, not an `OSError`, so it also escapes.

**Fix:** parse defensively. Catch `(ValueError, TypeError, KeyError, IndexError, AttributeError)` in `complete`, and add `http.client.HTTPException` to the transport catch (it is a network error, so retry it). When the body was valid JSON but its shape was wrong, still return the usage (for example a `Completion` with empty text, or a `ClientError` that carries the token counts) so `run.json` records the real spend. In `run.main`, wrap `map_names` so that any exception still writes `run.json` with what is known (`"crashed": true`, error class) before exiting. Add tests for empty `choices`, a non-dict output item and IncompleteRead.

### 3. The scorer doesn't check the gold and prediction contract that the blind author had to guess (score.py 43-69, 129-133)

The mapper author can't see the gold file, so the column names (`id`, `category`, `note`), the nine category ids and the `AMBIGUOUS:` prefix are assumptions. If any of them is wrong, the score is silently wrong. Probes:
- A gold category outside the nine (`ssp_smp_excluded`) is always counted wrong, and its row is **left out of the confusion table** (render loops only over `CATEGORIES`), so the cause is invisible. One renamed category could mean a KILL.
- Duplicate gold ids are accepted, and every duplicate is counted.
- A note starting `ambiguous:` (lower case) gives an AMBIGUOUS count of 0, with no warning.
- Prediction ids are never compared with gold ids. Names taken from a different file would score every row UNMAPPED with no explanation.

**Fix:** before computing, `score.main` should refuse (non-zero exit, no RESULTS.md) when any gold category is not in `CATEGORIES` (listing the unknown values and their counts), when gold ids aren't unique, or when the set of prediction ids differs from the set of gold ids. Match `AMBIGUOUS` case-insensitively and print the AMBIGUOUS count in the report. Tests for each case. **Process step (Studio Lead, not the mapper author):** someone allowed to see the labels branch confirms the gold header, the category vocabulary and the AMBIGUOUS convention match this scorer. They also confirm that `id` and `source_style` carry no category signal (for example no id prefixes like `BAS-` or `SSP-`), because both columns go to the model. Only the schema should be confirmed, not the labels' content.

### 4. All-or-nothing parse with no pre-registered tolerance (mapper.py 52-59, prompt.py 59-60)

A single batch of 200 means one reply wrapped in a ```` ```json ```` fence, or in `{"items": [...]}`, makes all 200 rows UNMAPPED: 0%, a KILL. `test_fenced_json_is_not_repaired` locks that in. The "never repair" rule is right *after* the run, because any parsing choice made after seeing the output is post-hoc. But this choice can and should be made **now**, blind, and recorded.

**Fix (pick one before the run and record it in state/DECISIONS.md):**
- (a, recommended) Use structured outputs: chat `response_format: {"type": "json_schema", "json_schema": {"strict": true, ...}}` with the category as an `enum` of the nine ids, wrapped as `{"items": [...]}` because strict schemas need an object at the top level. The Responses equivalent is `text.format`. This removes the formatting failure mode altogether and turns invalid categories into an impossibility rather than an UNMAPPED.
- (b) Pre-register one deterministic unwrapping: strip a single surrounding markdown fence. Nothing else.

Either option changes the prompt and payload, which is fine before any labels are seen. Bump `PROMPT_VERSION` if you do.

## Suggestions (non-blocking)

1. **Record more in run.json:** transport attempts per batch (a timed-out request may have been billed; BUDGET.md line 36 already shows a "worst-case charge for a connection reset"), `finish_reason` / Responses `status` and `incomplete_details` (so a truncated reply caused by the 16,000-token cap can be diagnosed), and the payload settings (api flavour, max tokens, reasoning effort).
2. **B2 headroom:** only about 9,300 output tokens fit under $0.02. At default (medium) reasoning on gpt-5-mini, 200 classifications plus a JSON answer of about 3,000-4,000 tokens could land in REVIEW. Pre-register `reasoning_effort` now (for example `low`; Responses: `reasoning: {effort}`), record it in run.json and in DECISIONS.md. It can't be changed after the run.
3. **Diagnosable 4xx:** read the HTTPError body and include Azure's `error.code` and a truncated `error.message` (no headers; also redact the api-key value, as defence in depth). A bare "HTTP 400" won't say whether the problem was the deployment, a parameter or a content filter.
4. **Scorer guards:** print B1 and B2 as "N/A (fake run)" for fake runs. The probe shows a fake report printing `**KILL**`, which could be pasted by mistake. Warn when `run.json.prompt_sha256` differs from the current `PROMPT_SHA256`, or when `run["names"]` differs from the number of gold rows.
5. **Headline pre-registration:** the code makes the nine-category accuracy the B1 headline (stricter than KILL-TEST's eight-category wording, and consistent with the status note there). Ask the Studio Lead to record "B1 is judged on nine categories" in DECISIONS.md before the run, so the choice is visibly made before any numbers exist.
6. **extract_names:** accept an optional `--expect-sha` so the names are provably taken from the frozen file, and refuse duplicate ids at extraction.
7. **Tests:** line 191 (`read(...) if False else open(...).close()`) is confusing. Write it as a plain `open(...).close()`. Add a `run.main` test of the no-answer failure path (issue 1) and of the cost recorded on a partial failure.
8. **Worst-case spend per attempt:** 3 transport attempts × (about 5.5k in + 16k out) comes to about $0.10. That is trivial, but worth noting in the Q-16 spend ask.

## Top issue

Issue 1: an HTTP 400 or similar failure before any answer exists locks the one-shot folder and writes all-UNMAPPED predictions that score as a B1 KILL. Make no-answer failures re-runnable with the same prompt sha only, enforced in code and logged in `attempts.jsonl`.
