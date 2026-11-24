# Review: p/_starter/T-34-effort (commit dafdba1)

Reviewer gate, 2026-11-24. Diff: `git diff origin/main...HEAD` (5 files, +58 / -17).

## Summary

`AZURE_OPENAI_REASONING_EFFORT` now accepts `xhigh` as well as `low`, `medium` and `high`. `REASONING_EFFORTS` in
`backend/app/config.py` is the only list, and `ai.py` imports it instead of keeping its own copy. README and
`.env.example` say that gpt-5.4-pro rejects `low` with HTTP 400, so `medium` is its cheapest setting, and that a
400 is a config error that is not retried. The change is small and correct, and the tests are meaningful.

## Evidence

- Backend, full suite on this tree: `469 passed, 1 skipped in 66.28s`. This matches the README's new count (466 -> 469).
- Frontend vitest: `Test Files 5 passed (5)`, `Tests 114 passed (114)`.
- Mutation check: I put origin/main's `app/ai.py` and `app/config.py` back while keeping the new tests.
  `test_xhigh_is_accepted_and_sent` and `test_reasoning_efforts_has_one_source_of_truth` both FAIL, so they
  test the change. `test_model_400_on_reasoning_effort_is_a_non_retried_config_error` passes on main as well,
  as expected: it pins down existing behaviour (`ai.py:330-332`, any non-401/403 4xx -> `ai_rejected` 502 with no
  retry) that the docs now promise. I then restored the files, and `git status` was clean apart from this review.
- Circular import: none. `config.py` imports only `pydantic`, `pydantic_settings` and `.dbauth`, and `dbauth.py`
  imports only `sqlalchemy`/`logging`. Nothing on that chain imports `ai`, and the full suite imports both modules.

## Critical issues

None.

## Suggestions (non-blocking)

1. `backend/app/config.py:82`: the old comment line "Pro models may accept only high (they reject low)" is still
   there, directly under the new line 81, which says gpt-5.4-pro accepts medium, high and xhigh. The two contradict
   each other. Delete line 82 or reword it (for example "unset by default because support varies by deployment").
   Line 81 is also longer than the 120-character width the file uses elsewhere.
2. `ai.py:266`: `AzureOpenAI` checks the value with no `.strip().lower()`, while `Settings` normalises it.
   That is fine through `from_settings` and was already the case on main. A direct caller passing `"XHigh"` gets a
   ValueError, which is acceptable but worth knowing.
3. `test_reasoning_efforts_has_one_source_of_truth` checks for `'"low"' not in inspect.getsource(...)`. This is
   brittle: a future docstring or comment in `__init__` that quotes "low" would break it for no real reason. The
   `is` identity assert already proves there is one shared list, so the source check could go.
4. The docs claim about gpt-5.4-pro comes from one observed 400 message (2026-11-24) on the studio's deployment. The
   README wording ("The studio's gpt-5.4-pro deployment") scopes it correctly. No change is needed.

## Security / performance

There is no new endpoint, input path or query. The setting is still checked at startup. The 400 path logs only the
status code and shows the customer a generic message, which the test asserts (the model's text does not leak).
There is no cost change unless an operator picks `xhigh`, which is opt-in and documented.

## Verdict

PASS. The behaviour is correct, there is no circular import, and the docs are accurate. The tests fail without the change
(apart from the deliberate characterization test). Backend 469 passed / 1 skipped, vitest 114/114. Suggestion 1 (a stale,
contradictory comment) is worth fixing in a follow-up or before merging, but it does not block.
