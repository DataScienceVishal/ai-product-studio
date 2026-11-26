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

---

## Re-review: 0de8caf..0022fde (2026-11-26)

Same rules as before: I did not read the labels branch or any gold.csv, and made no network calls. Lead decisions are on main (state/DECISIONS.md, 837cb1d). I took the gold format as the Lead confirmed it: header `id,pay_element_name,source_style,gold_category,note`, 200 unique ids, exactly the nine categories, 32 notes starting `AMBIGUOUS:`, and sequential ids with shuffled categories.

```
$ python3 -I -m unittest discover -s tests -t .
Ran 121 tests in 0.063s
OK
```

### Verdict: PASS

| Item | Status | Evidence |
|---|---|---|
| C1 no-answer failure locks the one shot | Fixed | run.py 125-135: if no reply was parsed and the run did not crash, it appends to `attempts.jsonl`, removes `run.started`, writes no predictions or run.json, and exits 4. A re-run is refused if any logged attempt has a different `PROMPT_SHA256` (run.py 100-103). Once any reply is parsed, the folder stays locked (`test_invalid_reply_still_locks`). My probe: a mocked 400 gives rc 4 and only `attempts.jsonl` in the folder; a same-prompt re-run gives rc 0 with `failed_attempts` (1 entry) in run.json; a third run gives rc 3. |
| C2 crashes on reply shape | Fixed | `_parse` (mapper.py 278-302) catches KeyError, IndexError, TypeError, AttributeError and ValueError, and keeps the usage figures. `http.client.HTTPException` is retried as a network error. A body that isn't JSON counts as no answer. run.py 119-124 writes run.json even when it crashes (exit 5). My probe: `choices: []` with 6,000 in and 9,000 out gives a locked folder, run.json with cost $0.0195 and all rows UNMAPPED. |
| C3 scorer contract | Fixed | `check_inputs` (score.py) refuses on a wrong header (`gold_category`, which matches the Lead's confirmation), duplicate gold or prediction ids, gold categories outside the nine (with counts) and prediction ids not in gold. The AMBIGUOUS count is printed (exact prefix, case-sensitive, as the Lead confirmed). Each case is tested. |
| C4 all-or-nothing parse | Fixed | Strict JSON schema with a nine-value `enum` on both APIs. Chat sends `response_format.json_schema {name, strict, schema}` and Responses sends `text.format {type: json_schema, ...}`. Every object has `additionalProperties: false` and lists all its properties as required, as strict mode needs. Still no repair. `PROMPT_VERSION` moved to v2. |
| S1 run.json detail | Done | Transport attempts, finish reasons or Responses status and incomplete reason, settings, batch failures and failed attempts are all recorded. |
| S2 reasoning effort | Done | Effort is `low`, sent as `reasoning_effort` (chat) or `reasoning.effort` (Responses), and recorded in run.json and DECISIONS.md. |
| S3 diagnosable 4xx | Done | Azure's `[code] message`, truncated to 300 characters, with the key redacted (probe: `HTTP 400 [DeploymentNotFound] key [redacted] bad`). Headers are never included. |
| S4 fake verdicts and sha warning | Done | A fake run reports B1 and B2 as `N/A (fake)`. A prompt sha that differs from the current one, or a names count that differs from the gold row count, adds a warning to the report. |
| S5 headline pre-registered | Done | Lead decision recorded (nine categories). |
| S6 extract_names | Done | Optional `--expect-sha`; refuses duplicate or empty ids. |
| S7 tests | Done | Tests added for every path above. |

### Builder's open point: should the guard hash the schema and settings, not only the system prompt?

**Yes, but it doesn't block the merge. Do it before the live run.** The kill rule concerns anything that shapes the model's answers, and the system prompt is only part of that. The guard matters only for no-answer re-runs, and since no predictions existed at that point, a change couldn't have been informed by them. So the risk is small. Even so, binding everything makes the "identical prompt" claim auditable from run.json alone, without reading the git history. Recommendation:

- Add `RUN_CONFIG_SHA256`: the sha256 of canonical JSON (`sort_keys`, no spaces) over `SYSTEM_PROMPT`, `RESPONSE_SCHEMA`, `SCHEMA_NAME`, `REASONING_EFFORT`, `MAX_OUTPUT_TOKENS`, the user-message template (the `build_user_message` prefix and its fields) and the sha256 of the names file. Store it in `attempts.jsonl` and `run.json`, and make the re-run guard compare it in place of `PROMPT_SHA256` (keep recording `PROMPT_SHA256` as well).
- **Leave out** the endpoint, API flavour, deployment name, timeout and retries. Fixing those is exactly what a no-answer re-run is for. They are already recorded in `settings` and `deployment`, and the model that actually answered is in `reported_model`.
- Add one test: changing `REASONING_EFFORT` or the schema between a no-answer attempt and a re-run is refused.

### Remaining minor points (non-blocking)

1. run.py 121-124: on the crash path, `result` is replaced with a fresh `MapResult`, so any usage counted before the crash is lost from `cost_usd`. Today only a bug inside `validate_reply` could reach this path, so the impact is small. If you want the figures, keep the partial result.
2. `attempts.jsonl` tokens are not added to `cost_usd`. That is correct for B2, since a failed attempt produced nothing, but the Q-16 spend ledger should add them (they are 0 for 4xx).
3. A 200 reply whose body isn't JSON is treated as no answer and can be re-run. That is acceptable (nothing was seen), but its token usage is unknown. The Azure spend report remains the source of truth, as the README already says.

---

## Follow-up review: 647a8d1..bb5f1a2 (run-config sha guard, crash usage kept)

Same rules: I did not read any labels or gold.csv and made no network calls. Test run: `python3 -I -m unittest discover -s tests -t .` gives `Ran 126 tests ... OK`.

### Verdict: PASS

- **Config guard:** this matches the recommendation. `config_sha256` (prompt.py) hashes canonical JSON (`sort_keys`) over the system prompt, schema name, schema, reasoning effort, output cap, user template and the names-file sha. It leaves out the endpoint, API type, deployment, timeout and retries. run.py compares it against every `attempts.jsonl` entry before writing anything, and records it, together with `names_sha256`, in both `attempts.jsonl` and `run.json`. An older attempt entry without the field is refused, which is the safe side. Tests cover a changed setting, a changed names file, each input to the hash, and the sha being recorded. score.py warns if the sha is missing or differs between the failed attempts and the final run.
- **Usage kept on crash:** `map_names(..., into=result)` fills the result in place, so tokens counted before a crash stay in `run.json` and `cost_usd`. Missing ids are filled with UNMAPPED. A crash still locks the folder (exit 5). The test checks that 11 in and 22 out tokens are kept and costed.

Minor (non-blocking): `USER_TEMPLATE` is a hand-written string, separate from `build_user_message`. Someone could change the message prefix or its fields and forget to update the template, and the hash would not change. A safer version derives it from the code, e.g. `USER_TEMPLATE = build_user_message([{"id": "<id>", "pay_element_name": "<name>", "source_style": "<style>"}])`, defined after the function. The names-file sha already covers the data, so the remaining gap is a code change, and git history would show that.
