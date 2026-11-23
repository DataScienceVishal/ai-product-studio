# Review: p/_starter/T-17 (Azure OpenAI via managed identity)

Reviewer: reviewer agent, 2026-11-23. Diff: `git diff origin/main...origin/p/_starter/T-17` (commit 3c0e3fe), 6 files, +276/-60.

**Verdict: PASS** (with three should-fix items below, none blocking; the mode is off by default).

## Summary

`ManagedIdentityToken` (backend/app/ai.py:90-155) fetches a bearer token from the Container Apps identity
endpoint, caches it until 5 minutes before `expires_on`, shares one fetch across threads with a lock, drops it on
401/403, and turns every failure into `AIUnavailable` with zero billed tokens. `AzureOpenAI` sends
`Authorization: Bearer` instead of `api-key` when a provider is set; `build_provider` wires it from the new
settings `AZURE_OPENAI_AUTH` (`Literal["key","managed_identity"]`, default `key`) and `AZURE_CLIENT_ID`. The
provider is built once at app start-up (main.py:178), so the cache is process-wide as intended.

## Tests

Full backend suite, own DB `starter_test_rev17`, `--junitxml`: **212 tests, 0 failures, 0 errors, 1 skipped**
(`test_spa::test_the_real_vite_build_has_no_inline_script`, frontend not built; expected). test_ai.py: 27 cases,
14 of them new (11 functions, one parametrized x4).

Mutation check (copy of backend, test_ai.py only):

| Mutation | Caught by |
|---|---|
| drop the 5-minute refresh margin | test_token_is_cached_then_refreshed_five_minutes_before_expiry |
| skip `invalidate()` on 401 | test_rejected_token_is_dropped_so_the_next_call_fetches_a_new_one |
| drop `api-version` | test_token_request_follows_the_container_apps_contract |
| drop `X-IDENTITY-HEADER` | test_token_request_follows_the_container_apps_contract |
| log the identity header | test_token_and_identity_header_never_reach_logs_or_errors |
| **remove the lock in `get()`** | **not caught** (see S2) |
| remove per-request `timeout=` | not caught (client default is also 5 s, so harmless) |

## Security check of the auth change

Token endpoint contract, against Microsoft Learn "Managed identities in Azure Container Apps", REST endpoint
reference (fetched 2026-11-23):

- `GET $IDENTITY_ENDPOINT?resource=...&api-version=2019-08-01`: matches ("Use 2019-08-01 or later").
- Uses `resource` (not `scope`), correct for this endpoint; value without `/.default`: correct.
- Header `X-IDENTITY-HEADER` = `$IDENTITY_HEADER`: matches.
- `client_id` query param for a user-assigned identity, omitted for system-assigned: matches.
- `expires_on` is epoch seconds as a string (doc example `"1586984735"`); parsed with `float()`: correct.
- Audience `https://cognitiveservices.azure.com`: listed as the OAuth2 scope in the Azure OpenAI v1 REST reference
  (`azure/ai-foundry/openai/latest`, "Scopes: https://cognitiveservices.azure.com/.default"). Note the Entra ID
  how-to and the v1 lifecycle page use `https://ai.azure.com/.default` in their SDK samples, so both are documented;
  see S3.

Secrets: the token and header value never reach logs, error messages or responses. Every error path logs only a
status code or exception class name and raises with `from None`, so no chained exception carries the request.
httpx's INFO request log shows the URL (resource, api-version, client_id), never headers. Error bodies from the
identity endpoint are not logged. Responses to users carry only the fixed `AIUnavailable` messages.

SSRF/steering: the endpoint and header come only from process env (`os.environ`) or constructor args; nothing from
a request reaches them. `client_id` comes from settings. httpx doesn't follow redirects by default.

Timeouts: 5 s per fetch (client default and per-request). Bounded per call, but not against the AI deadline (S1).

## Critical issues

None.

## Should fix (next touch of ai.py)

**S1. Token fetch ignores the call deadline, and failures are not cached** (ai.py:116-121, 137, 189-191).
The fetch runs under the lock with a fixed 5 s timeout. If the identity endpoint hangs, up to 8 concurrent callers
(`ai_concurrent_calls`) queue on the lock and each waits its own 5 s, so the last one waits about 40 s, past the
25 s deadline and the frontend's 30 s abort that config.py documents. After a slow fetch,
`min(self.timeout, remaining())` can also be zero or negative. Fix: pass the remaining deadline into `get()`
(fetch timeout = `min(self._timeout, remaining())`, and use `lock.acquire(timeout=...)`), and/or remember a
failed fetch for a few seconds so waiters fail fast instead of each retrying.

**S2. The concurrency test doesn't exercise the lock** (tests/test_ai.py:249). The fake endpoint answers at once, so
the 8 threads run one after another and the test passes with the lock removed (checked). Make the fake block on a
`threading.Event`/`Barrier` until all threads are waiting, then assert one request.

**S3. ADR wording on the audience** (ADR/0002-azure-deploy.md:225). "This corrects the `ai.azure.com` guess" is
overstated: Microsoft's current Entra ID guide for the v1 API uses `https://ai.azure.com/.default`, and the v1 REST
reference lists `https://cognitiveservices.azure.com/.default`. Say both are documented, name the source for the
one chosen, and say that a 401 after switch-on would mean trying the other. Making `RESOURCE` a setting would
make that a config change rather than a code change.

## Minor

- `test_unreachable_or_missing_identity_endpoint_is_ai_unavailable` builds a real `httpx.Client` for the empty-endpoint
  case. It works because the client is never used, but injecting the mock keeps it hermetic.
- The 401 path drops the token but doesn't retry, so the first request after a revoked or rotated token fails once.
  That matches the "never retry a sent call" rule. A 401 is not billed, so one retry with a fresh token would be safe
  if this ever shows up in practice.
- `import logging` and `from app.ai import ...` in the middle of test_ai.py (with `noqa: E402`): move them to the top.

## Docs

README, ADR decision 7 and NEXT.md match the code. The manual steps (identity, "Cognitive Services OpenAI User"
role on the OpenAI resource only, settings) are marked ask-first. Keeping the shared pull identity at
`lifecycle: None` with no OpenAI role is the right call.
