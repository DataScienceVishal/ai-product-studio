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

## Re-review at 0fe5d46

Reviewer: reviewer agent, 2026-11-24. Scope: `git show 0fe5d46` (fixes for B1, B2, S4, S6), read against the
whole `main...p/_starter/T-33` diff. No live Azure calls.

**Verdict: CHANGES.** One small doc fix is left (R1). The code fixes are correct and tested. B1 and B2 are
resolved, and S4 and S6 are done. Once R1 is fixed, a quick diff check is enough for a PASS. No new code review
is needed.

### Tests

Postgres 16 `starter_test`, `TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_test`,
Python 3.11 venv.

| Environment | Result |
|---|---|
| Sandbox as is (`AZURE_OPENAI_ENDPOINT`, `_DEPLOYMENT`, `_API_KEY` exported) | **238 passed, 1 skipped** |
| Those three unset (as in CI) | **238 passed, 1 skipped** |
| Exported, plus `AI_PROVIDER=azure`, `AZURE_OPENAI_API=responses` | **238 passed, 1 skipped** |
| `tests/test_ai.py` alone | 46 passed (43 before, plus 3 parametrised S4 cases) |

The skip is `test_spa.py` (frontend not built), as before. The earlier failure in
`test_prod_settings_refuse_unsafe_values` with the sandbox variables set is gone (S6).

Frontend unit tests were not run. The branch doesn't touch `frontend/`, and the worktree has no `node_modules`.

One more failure appears, but only with `AZURE_OPENAI_AUTH=managed_identity` exported:
`test_ai.py::test_settings_accept_only_known_auth_modes`. It has the same non-hermetic pattern as S6 and is already
on main. No session exports that variable today, so it is not blocking; see R4.

### Prior items

| Item | Status | Evidence |
|---|---|---|
| B1 `store: false` | **Resolved** | `ai.py:203` sends it. The exact-body assertion in `test_responses_request_shape_and_usage` now includes `"store": False`, so removing it fails the test. DATA.md documents it, but see R1 |
| B2 cap priced for mini | **Resolved** | New `ai_price_per_million_tokens` (config.py:65) and Bicep `aiPricePerMillionTokens` (main.bicep:43-44), wired to the app env (main.bicep:220-223). The cap description is corrected. README "Sizing the daily AI cap" gives the formula and the pro warning. `cost-guard.sh` checks the defaults; results below |
| S4 malformed `output` | **Done** | `_dicts()` drops non-list and non-dict items, and text must be `str`. The parametrised test covers a string, mixed junk and a dict `output`, and checks that usage (40/200) is still billed via `AIUnavailable` |
| S6 hermetic prod-settings test | **Done** | `monkeypatch.delenv` for the five `AZURE_OPENAI_*` variables and `AI_PROVIDER` (test_platform.py:101-104) |

### cost-guard.sh, run on hand-made templates

There is no bicep CLI here, so I wrote JSON shaped like `bicep build` output (`int` default as a number, `string`
default as a string) and ran the script on it. Script: `infra/cost-guard.sh:40-52`.

| Template defaults | Exit | Message |
|---|---|---|
| 100,000 tokens, "2.00" (the shipped defaults) | 0 | pass ($6.00) |
| 101,666 tokens, "2.00" | 0 | pass ($6.0999) |
| 101,667 tokens, "2.00" | 1 | "= $6.1 a month, over the $6.10" (correct, but the rounding reads oddly) |
| 100,000 tokens, "120" | 1 | $360 a month |
| 1,700 tokens, "120" | 1 | $6.12, see R2 |
| tokens only, or price only | 1 | "needs both ..." |
| price "abc", or tokens an ARM expression | 1 | "not a number" |
| price "-5" | 0 | passes, see R3 |
| 0 tokens | 0 | pass |
| both parameters present, no `defaultValue` | 0 | **skipped silently**, see R3 |
| neither parameter (shared.json) | 0 | pass, as intended |
| two files, first bad | 1 | the error is counted and the loop goes on to the next file |
| `AI_MONTHLY_BUDGET_USD=1` | 1 | $6 over $1 |
| `AI_MONTHLY_BUDGET_USD=abc` | 1 | fails closed, but blames "tokens or price" |

The logic is sound for the shipped template. It fails closed on bad input. The deploy workflow doesn't override
either parameter (main.bicepparam has no `aiGlobalDailyTokens` or `aiPricePerMillionTokens` line), so the checked
defaults are the deployed values.

### R1 (blocking, doc only). DATA.md points to an ADR section that doesn't exist

`DATA.md:20-21`: "(Azure's separate abuse-monitoring retention is covered in ADR 0002)". ADR 0002 has no mention
of abuse monitoring. `grep -in abuse ADR/0002-azure-deploy.md` returns nothing. Its OpenAI text (section 7, the
line 388 cost row) covers only auth and cost.

Why it matters: DATA.md is the customer-facing data inventory (the Sellable bar). The sentence before this says
"Azure keeps no copy of the prompt or the answer". Read with a dead pointer, that sounds stronger than it is.
Azure OpenAI abuse monitoring can still keep prompts and completions that its systems flag. A reader who follows
the link finds nothing.

Fix: choose one.
- (a) Trim it to: "`store=false` means Azure keeps no stored response object. Azure's abuse monitoring is separate
  and may still keep flagged content for a limited time (Microsoft Learn, 'Data, privacy, and security for Azure
  OpenAI'). Check the current wording and period before launch." Cite the Learn page, not the ADR.
- (b) Add a short "Abuse monitoring" bullet to ADR 0002 section 7 that says the same thing, with the link. Then
  keep the pointer.

Either is a one-paragraph change. Don't claim a specific retention period without checking the page.

### Suggestions (non-blocking)

- **R2. The README pro figure is a little high.** `README.md:129` says "about 1,700 tokens a day". 6.10 / (30 x 120)
  x 1,000,000 is 1,694, and the guard rejects 1,700 at $120 ($6.12). Say "about 1,690" (or "under 1,700") so an
  operator who copies the number doesn't hit a red build. Fix it with R1.
- **R3. Make the guard check stricter.**
  - A price of 0 or less passes. Require `$p > 0`.
  - If a product drops the defaults and passes the values from `main.bicepparam`, the check is skipped without a
    word. When either parameter exists without a `defaultValue`, report it.
  - Round the message to two decimals with the trailing zero kept (`$6.10`, not `$6.1`), or print the unrounded
    value.
- **R4. App default `AI_GLOBAL_DAILY_TOKENS=500,000`** (config.py:62). Not blocking. Every deploy sets it from Bicep
  (100,000, guarded), and the app default applies only to local or test runs that opt in with `AI_PROVIDER=azure`.
  That opt-in still uses the studio's real key: 500k a day is about $30 a month at $2/M and about $60 a day at pro
  prices. Two cheap fixes:
  - lower the default to 100,000 so it matches Bicep and the README;
  - or have `Settings` log a warning (or refuse, when `env=prod`) when `ai_global_daily_tokens x
    ai_price_per_million_tokens x 30 / 1e6` passes 6.10. That would also give the new price setting a runtime use;
    today only the deploy guard reads it.

  Also make `test_settings_accept_only_known_auth_modes` hermetic: delete `AZURE_OPENAI_AUTH` from the env, as S6
  did.
- **R5. Leftover parse gaps** (low risk; the provider is trusted).
  - A non-numeric `usage.input_tokens`, or a non-dict `incomplete_details`, still raises outside `fail()` and would
    settle at 0/0.
  - The chat path's `choices[0]` has the same S4 gap.

  Wrapping `_parse` in `try/except (TypeError, ValueError, AttributeError)` would close all three.
- **R6.** `.env.example` doesn't list `AI_GLOBAL_DAILY_TOKENS` or `AI_PRICE_PER_MILLION_TOKENS`. The README table
  does, so this is optional.
- S1, S2, S3, S5 and S7 from the first review are still open. They stay non-blocking. S5 (passing
  `AZURE_OPENAI_API` from Bicep) and S2 (the pro model versus the 25 s deadline) should be settled before any
  product switches the cloud app to `responses`.
