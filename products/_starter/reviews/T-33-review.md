# Review: p/_starter/T-33 (Azure OpenAI v1 Responses API)

Reviewer: reviewer agent, 2026-11-24. Diff: `git diff main...origin/p/_starter/T-33` (dfc8808 plus board-only
ee79d26). 7 files, +214/-12. No live Azure calls were made for this review.

**Verdict: CHANGES.** Two blocking items. Both fixes are small: one line plus a test for B1, and a doc/param change
for B2. The rest of the work is good. The request shape, endpoint handling, usage parsing, failure billing and
tests are correct, and the chat path behaves the same as before.

## Summary

`AzureOpenAI` takes `api=auto|chat|responses`. `auto` resolves to `responses` only when the raw endpoint ends in
`/openai/v1/responses`. `normalise_endpoint` strips any known `/openai/...` suffix, so the URL is built from the
resource root (ai.py:161-187). In responses mode the payload is
`{model: <deployment>, instructions: system, max_output_tokens, input: [{role: user, content: user}]}`
(ai.py:196-198), which is a valid Responses request. `_parse` (ai.py:256-270) joins `output_text` parts from
`message` items only, ignoring reasoning items and refusal parts. It takes `usage.input_tokens` and
`usage.output_tokens`; the latter already includes reasoning tokens, so they count against every cap. An empty text
result bills its usage and raises the existing "ran out of room" `AIUnavailable`. Retry, timeout, 401/403 and 400
handling is shared with chat, so failure billing is identical in both modes. The setting is a pydantic `Literal`
(config.py:54) and goes through `build_provider`.

## Tests

The suite ran the CI way: local Postgres 16, `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test`,
pinned `requirements-dev.txt` installed with `--require-hashes`, Python 3.11.

- `alembic upgrade head && alembic check && alembic downgrade base`: clean, "No new upgrade operations detected".
- `python -m pytest`: **235 passed, 1 skipped** (`test_spa.py:104`, frontend not built; expected).
  `tests/test_ai.py`: 43 passed.
- Environment note: this sandbox exports `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` and
  `AZURE_OPENAI_API_KEY`. With them set, `test_platform.py::test_prod_settings_refuse_unsafe_values` fails,
  because `Settings` picks the endpoint up from the environment. This is not caused by this branch: the same test
  and assertion are on main. The figures above are with those three variables unset, as in CI. See S6.

Mutation check (copy of backend, test_ai.py only):

| Mutation | Result |
|---|---|
| subtract `reasoning_tokens` from `output_tokens` | caught (test_responses_request_shape_and_usage) |
| keep refusal parts in the text | caught (test_responses_joins_text_parts_...) |
| `auto` always resolves to chat | caught (test_build_provider_passes_the_api_setting) |
| don't bill an empty/incomplete answer | caught (test_responses_incomplete_is_a_clean_error_and_still_billed) |
| send `input` as a bare string | caught (test_responses_request_shape_and_usage) |
| parse responses with the chat parser | caught (several) |
| ignore `status` entirely | **survives**: `status` only reaches a log line (see S1) |

The tests test behaviour, and they would fail if the feature broke. The managed-identity test proves the v1
responses path sends `Authorization: Bearer` and no `api-key`.

## Critical issues (blocking)

### B1. Every tenant's note text is stored on the Azure resource for 30 days (`store` not set)

`backend/app/ai.py:197-198`. The Responses API stores each request and response by default. Microsoft Learn,
"Responses API" how-to (learn.microsoft.com/azure/foundry/openai/how-to/responses, read 2026-11-24): "By default,
response data is retained for 30 days." The Azure data-privacy page also names the Responses API among the
"stateful entities" whose data is automatically stored at rest in the resource. Chat completions does not do this.

Why it matters: switching to `responses` silently adds a 30-day copy of every note body and summary to the Foundry
resource. That copy outlives note deletion and account deletion, which breaks the deletion promises in `DATA.md`
(the `notes` row says "the user or the account deletes it"). The starter never reads a stored response
(it is stateless, with no `previous_response_id`), so storing gains nothing.

Fix: add `"store": False` to the responses payload. Extend the exact-body assertion in
`test_responses_request_shape_and_usage` so removing it fails the test. Add one line to DATA.md's processors
section saying Responses calls are sent with `store: false`.

### B2. The daily token cap is priced for gpt-5-mini, but this change makes the pro deployment usable

The cap lives in `infra/main.bicep:43-44` (default 100,000 tokens/day), `backend/app/config.py:62`
(500,000/day) and `state/BUDGET.md:18` ("at most 6.10 with azure and the 100,000-token daily cap"). The budget
logic counts tokens, not money. The Bicep description justifies 100,000 tokens/day as "at most $0.20 a day ...
($2.00 per million)", which is gpt-5-mini's output price. The README section added here (README.md:108-116) tells
operators to point the starter at "the studio's reasoning deployment", the only one that exists: gpt-5.4-pro.

Why it matters: pro models cost about two orders of magnitude more per token. gpt-5-pro's list price is about
$15/M input and $120/M output; check the exact gpt-5.4-pro price on the Azure pricing page. At $120/M output, the
Bicep default of 100k tokens/day is about $12/day (about $360/month), and the app default of 500k is about
$60/day. That burns the studio's $80 credit in days, while BUDGET.md still says $6.10/month. Token accounting is
correct (reasoning tokens count); the cap's size in money is what breaks.

Fix: either is enough to unblock.
- (a) README and .env.example: state that `AI_GLOBAL_DAILY_TOKENS` must be sized from the deployment's output
  price, with the formula (daily $ budget / output $ per token). Give the pro figure: about 10,000 tokens/day for
  about $1.20/day. Update the Bicep param description so it no longer claims $2/M for any deployment.
- (b) Better: add a `aiOutputUsdPerMillion` Bicep param, derive or validate the cap from it in the existing cost
  guard, and fail the deploy when the deployment is not gpt-5-mini and the price was not given.

Separately, record in DECISIONS.md which deployment products should use. A pro model is a poor fit for
interactive summaries anyway (see S2).

## Suggestions (non-blocking)

- **S1. An `incomplete` answer with some text is returned as a success** (ai.py:248-253, 266-268). With
  `status: incomplete` (reason `max_output_tokens` or `content_filter`) and a partial `output_text`, the truncated
  text is saved as the summary and the reason is lost. Chat has the same behaviour with `finish_reason: length`, so
  this is not a regression. Consider treating `status != completed` as a failure (still billed). Alternatively,
  at least log it and add a test, so the "ignore status" mutation fails. Likewise, `status: failed`, a
  `content_filter` reason, or a refusal-only message all show "The AI ran out of room... Try a shorter input",
  which misleads the user. Consider separate messages for refusal/filter versus `max_output_tokens`.
- **S2. Latency versus deadline.** The per-attempt timeout (20 s, `AI_TIMEOUT_SECONDS`) and the deadline (25 s,
  `AI_DEADLINE_SECONDS`) can be set from the environment, but the frontend's 30 s abort is hard-coded
  (frontend `api.test.ts:62` pins it), so the ceiling is about 29 s. A pro model took 8.4 s for "ok". A
  1,200-token summary with high-effort reasoning will often pass 20 s. A `ReadTimeout` then bills the whole
  1,200-token output budget (correct, but costly at pro prices) and returns nothing. Recommendations:
  - use a non-pro reasoning deployment (for example gpt-5-mini) for product features;
  - add an optional `AZURE_OPENAI_REASONING_EFFORT`, sent as `reasoning: {effort}` when set (pro models may only
    accept `high`, so leave it unset by default);
  - if pro must be used, consider background mode with polling, rather than raising the sync deadline past the
    frontend abort.
- **S3. Reasoning can use up `max_output_tokens`.** `MAX_SUMMARY_TOKENS = 1200` (routes/notes.py:26) now covers
  reasoning plus the answer. On a high-effort model, many calls will hit `incomplete` with no text and still be
  billed. Measure this on the T-12 pilot data before a product depends on it.
- **S4. A malformed `output` can bill zero.** If `output` holds a non-dict (for example a string), `item.get`
  raises `AttributeError`. That error is not caught in `complete()`. `notes.py:125-126` then settles the
  reservation at 0/0 tokens for a call that ran and cost money. Wrap `_parse` and raise `fail()`, billing
  `usage` if it parsed. This risk is low because the provider is trusted. The chat path has the same gap for
  `choices`.
- **S5. Infra doesn't set `AZURE_OPENAI_API`.** `infra/main.bicep` (aiEnv, around line 235) passes only the
  endpoint. `auto` works only if the deployed endpoint string ends in `/openai/v1/responses`. Pass
  `AZURE_OPENAI_API` explicitly (a param defaulting to `auto`) so a root endpoint doesn't fall back to chat and get
  an HTTP 400 (`ai_rejected`).
- **S6. Make the settings test hermetic** (pre-existing). Have `test_prod_settings_refuse_unsafe_values`
  `monkeypatch.delenv` the `AZURE_OPENAI_*` variables, or build `Settings(_env_file=None, ...)` with explicit
  empties, so it passes inside the cloud sessions that export them.
- **S7. Minor points.**
  - The new tests import `normalise_endpoint` mid-file with `# noqa: E402`; move the import to the top.
  - The ai.py docstring's first paragraph still says the v1 API is chat/completions. Reword it to "chat
    completions or responses".
  - `normalise_endpoint` doesn't strip a query string such as `?api-version=...`. A config like that would build a
    broken URL. Either reject it with a clear `ValueError` or document it.

## Checklist

| Area | Result |
|---|---|
| Request shape (model = deployment, input, instructions, max_output_tokens) | OK; missing `store: false` (B1) |
| Response parsing: output[].content[].text, reasoning items, refusals, missing text | OK; partial-incomplete and failure messages (S1) |
| Usage and reasoning tokens against caps | Counted correctly. The cap's money value is wrong for pro (B2) |
| Failure billing as chat (timeout after send, empty answer, retries, bad JSON) | OK, tested |
| Auth: api-key versus managed identity on the v1 responses path | OK, tested (Bearer, no api-key) |
| 25 s deadline | Can be set from the environment; tight for reasoning models, capped by the 30 s frontend abort (S2) |
| Chat path unchanged | OK: same URL, payload and parsing; `or 0` and the dict check only harden it; existing tests pass |
| Security: secrets, injection, SSRF | No new surface; the endpoint is operator config. Header handling unchanged |
| Tests meaningful | Yes; 6 of 7 mutations caught |
