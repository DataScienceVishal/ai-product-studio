# T-38 status

Done: test DB base-name cap lowered to 36 chars (`{0,35}`), so `<base>_t<10-digit epoch>_<pid>_<6hex>` is at most 63 bytes
(README and tests updated); if `COMMENT ON DATABASE` fails the new DB is dropped before `pytest.exit`. Route scanner in
test_spa.py now reads `"/x" === path` and flags `path === ROUTES.x`, `x === path`, `PAGES[path]`/`a.b[path]` as unreadable
(new `scan_routes` + unit test on synthetic snippets). Tests: worst-case name length, failed-COMMENT drop path.
The two unused variables in test_cookies_and_limits.py were already gone on main (nothing left to remove).
Left: nothing.
Verify: `cd backend && pytest` (339 passed, 1 skipped); `cd frontend && npx vitest run` (111 passed).

# T-37 status

Done: backend/tests/conftest.py gives each pytest run its own database (`<db>_t<epoch>_<pid>_<rand>`, created via the
`postgres` maintenance DB, dropped at session end in a finally). `TEST_DATABASE_SHARED=1` keeps the old shared behaviour.
Review fixes (reviews/T-37.md): stale cleanup drops only exact-shape names (10-digit epoch, pid, 6 hex) that carry the
`starter-pytest-ephemeral` database comment, are owned by the current user and are older than 6 h; each drop is
try/except. Base db name must match `^[A-Za-z_][A-Za-z0-9_]{0,40}$` (else pytest.exit); all SQL uses psycopg
sql.Identifier/Literal. No CREATEDB: one clear exit message. SIGTERM raises KeyboardInterrupt (DB dropped); SIGKILL still
leaks until a later run reclaims it after 6 h. Tests: backend/tests/test_testdb_cleanup.py.
Left: nothing.
Verify: `cd backend && pytest` (336 passed, 1 skipped), also two at once; `cd frontend && npx vitest run`.

# T-35 status

Done: `/assets/` with no assets folder is a plain 404 (spa.py registers both spellings; test added, GET and HEAD);
SPA fallback test loops over all of `CLIENT_ROUTES`; README backend count updated; `_TIMEOUT_MARGIN` constant in
ai.py; ADR 0002 note (Node 22 EOL April 2027, plan the move by Feb 2027, first Dependabot docker PR must be
digest-only); Dependabot github-actions PRs grouped into one. Not grouped: npm and pip, because dependabot.yml
has no entries for them (docker and actions only).
Left: nothing.
Verify: `cd backend && python -m pytest` (316 passed, 1 skipped); `cd frontend && npx vitest run`.

# T-34b status

Done (reviews/T-33-review.md, T-34-review.md): S1 an incomplete/failed Responses answer is never saved as a summary;
it is a billed `AIUnavailable` with its own message (out of room, thinking used it all, safety filter, declined,
failed, no answer). Chat keeps its old "any text is an answer" rule. S3 `AI_REASONING_HEADROOM` (default 1500) is added to
`max_output_tokens` in Responses mode and to the reservation (`reservation_estimate`), and a call whose reasoning used
the whole budget is named. R5 `_parse` errors (bad usage numbers, chat `choices` shapes) raise a billed clean error
instead of settling 0/0. S7 import moved, docstring, query string or fragment in the endpoint is a clear ValueError.
Extras: cost-guard harness `backend/tests/test_cost_guard.py` (needs jq), cost-guard names a bad AI_MONTHLY_BUDGET_USD.
Review fixes (reviews/T-34b.md): C1 `_parse` returns `why` only as str or None (junk list/dict/number becomes
"unknown" and the generic message), so no TypeError/500; usage counts are clamped to >= 0 and Infinity/overflow is a
billed parse error; a non-JSON or non-dict 200 bills the whole budget; `reservation_estimate` requires
`provider.output_headroom` (no silent default); README row for AI_REASONING_HEADROOM.
Left: S2 (Q-7), headroom price effect on pro caps (check sizing).
Verify: backend `pytest` 290 passed 1 skipped; frontend `vitest run`.

# T-33 status

Done: Azure provider supports the v1 Responses API (`AZURE_OPENAI_API=auto|responses|chat`, endpoint
normalisation, usage and failure billing as chat), tests in `backend/tests/test_ai.py`, README, .env.example.
Review fixes (reviews/T-33-review.md): B1 `store=false` sent and documented in DATA.md; B2 new setting
`AI_PRICE_PER_MILLION_TOKENS` (default 2.00), README "Sizing the daily AI cap" with the pro-model warning,
Bicep `aiPricePerMillionTokens` param and corrected cap description, and `infra/cost-guard.sh` now fails when
tokens a day x price x 30 passes $6.10; S6 prod-settings test clears AZURE_OPENAI_*/AI_PROVIDER env; S4 malformed
`output` is treated as no text and billed usage is still recorded.
Left: set `AZURE_OPENAI_API=responses` (or the /openai/v1/responses endpoint) in the cloud app. If the pro
deployment is used, set `aiPricePerMillionTokens` and a much smaller `aiGlobalDailyTokens` together (needs a
Bicep default change and Vishal's approval for any budget above $6.10). Price figures are assumptions to check.
Open question: 25 s deadline vs ~8 s+ reasoning latency.

# T-17 status

Done: `ManagedIdentityToken` and auth mode in `backend/app/ai.py`, settings `AZURE_OPENAI_AUTH` and
`AZURE_CLIENT_ID`, tests in `backend/tests/test_ai.py`, ADR 0002 decision 7, README.

Left (needs Vishal, ask-first): attach an identity to the app, grant "Cognitive Services OpenAI User" on the
OpenAI resource, set the two settings. No Bicep changed: the infra has only the shared pull identity
(`lifecycle: None`), so there is nothing to scope a role to yet.

- T-15 async-login slice (branch p/_starter/T-15-async-login), done: hashing capacity is now taken on the event
  loop (`security.hash_capacity`, an async dependency on login, signup, reset-confirm, accept-invite and both
  account deletes) before a worker thread is assigned; waiters cost no thread and get the same 503 busy with
  Retry-After: 5 after HASH_WAIT_SECONDS. The thread semaphore stays as a backstop. New
  tests/test_async_hash_capacity.py (mutation-checked); two unused test variables removed. 209 backend tests
  (208 pass, 1 skip: frontend not built). Left: nothing from this slice.
- T-15 cookies slice (branch p/_starter/T-15-cookies), done: tests that the cookie clears on logout, owner
  account deletion and member leave carry the same Secure, HttpOnly, SameSite and Path=/ as the set (secure and
  plain-http modes, mutation-checked); a test tying LIMITED_PROVIDERS to the live-key refusal; the CLIENT_ROUTES
  sync test now accepts any quote style and fails on other path comparisons; `normalise("//")` returns "/".
  The `__Host-` prefix was already in main (A8/R7), so only docs were updated. 205 backend and 111 frontend tests
  pass. Left: nothing from this slice; the e2e was not re-run (no core-flow change).

- 2026-11-23, later: the security re-test (FAIL 2 of 8: R1-R4) and the re-review (CHANGES: B1-B3, plus N1-N3)
  are addressed in 93f7aba. 132 backend tests pass; e2e passes (now including a wrong-password delete). The
  two B3 tests were mutation-checked: each fails with its protection removed. Waiting for both checkers again.

- The first review gave CHANGES (8 blocking: C1 to C8) and the security gate gave FAIL. Both are addressed in
  commits after `5df3b8b`. Waiting for re-review and a security re-test.
- 113 backend tests pass against Postgres 16. The full CI passed on GitHub (run 13, manual): hash-checked
  installs, migrations, tests, pip-audit and npm audit with no known vulnerabilities, the production image build,
  and the browser end-to-end core flow with pinned Playwright.

## What changed since the first review (see reviews/ and SECURITY.md for the findings)

- **C1:** no transaction is held across AI or payment calls; there's one 25 s AI deadline; `/livez` (no DB) is
  separate from `/healthz`.
- **C2:** parameters are hidden and database errors are scrubbed in logs.
- **C3:** webhook secrets of 32+ characters, `whsec_` for Stripe; `verify()` refuses an empty one.
- **C4:** billed tokens of failed calls are counted; reservations happen under advisory locks; there's a global
  daily budget.
- **C5:** `--no-proxy-headers`; proxy trust is required in prod; rate-limit eviction can't unblock anyone.
- **C6:** Stripe metadata is on the checkout session; `subscription.created` is handled; the period end is read
  from items; live-mode events are ignored.
- **C7:** a 1 MB body limit; bounded mock sessions; rate limits on checkout and deletion.
- **C8:** deletion closes the provider customer first and fails closed.
- **Security Mediums:** argon2 concurrency cap; verification needs the right signed-in account (pre-hijacking);
  reset timing, single use and an hourly cap; HSTS/CSP; invitation caps and email-safe names; member self-service;
  retention purge; DRAFT privacy notice and terms.
- **Review I1 to I12:**
  - Done: global CSRF and an auth sweep; `MOCK_CHECKOUT_ENABLED`; the prod validator; redaction; DATA.md and the
    purge; reset races; part of I8 (event order, a second subscription, the idempotency key); a clean test schema;
    CI hashes, image build, audits and pinned Playwright; frontend 401, sign-out and billing-done; docs.

## Left to do

1. **Gates:** reviewer re-review and security re-test.
2. **Deploy (T-7):** the architect designs Container Apps + Bicep (registry, Postgres, the purge job), writes the
   monthly estimates in `state/BUDGET.md`, and asks Vishal if one resource passes $10 a month.
3. **Later:**
   - Redis-backed rate limits before running more than one replica.
   - A real email adapter (paid, needs approval). Until then the outbox drops emails: prod logs a warning.
   - The early-customer offer applied server-side as a Stripe coupon (review I8).
   - The `__Host-` cookie prefix.
   - Frontend unit tests.

## How to verify

```bash
cd products/_starter/backend && TEST_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/<your_db> .venv/bin/python -m pytest -q
cd products/_starter && E2E_API_PORT=8300 E2E_WEB_PORT=4373 E2E_DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/<your_e2e_db> ./scripts/e2e.sh
```
Verify: `cd backend && TEST_DATABASE_URL=... .venv/bin/python -m pytest`.

## T-32 status (run 010e hand-off, rebased on main with T-33/T-34, awaiting re-review)
All reviewer items from reviews/T-32.md are addressed (see its Response section). Merged origin/main (Responses API in ai.py kept).
Re-review fix: `short` is now `left < self._timeout - 0.05` (was always true on the real clock); real-clock test added; mutation (revert to `left < self._timeout`) fails test_a_real_endpoint_timeout_is_cached_on_the_real_clock.
Tests: backend 247 tests, 0 failures, 1 skipped (frontend not built); frontend vitest 111 passed.
Mutation check: with the lock removed (`if False` instead of `acquire`, `pass` instead of `release`), three tests fail:
test_concurrent_callers_share_one_fetch, test_lock_waiter_gives_up_at_its_own_deadline,
test_fetch_gets_only_what_is_left_after_waiting_for_the_lock. Restored, all pass.
Left: reviewer re-review and security re-test.

## T-34 (slice S5, R3, R4, R6 from reviews/T-33-review.md)

Done:
- S5: `infra/main.bicep` has `azureOpenAiApi` (default `auto`, allowed auto/chat/responses) passed to the app as `AZURE_OPENAI_API`.
- R3: `infra/cost-guard.sh` fails when tokens or price is 0 or negative, fails (no longer skips) when either AI parameter exists without a default, and prints money with 2 decimals. No harness exists for this script, so it was run on hand-made JSON templates:
  ok (100000 tokens, 2.00) rc 0; over (500000, 2.00) rc 1, "$30.00 a month"; price "0" rc 1; tokens -5 rc 1; both params without defaults rc 1; only one param (with default) rc 1; price "abc" rc 1; no AI params at all rc 0.
- R4: `ai_global_daily_tokens` default is now 100,000 (no test depended on 500k; tests set their own caps). `test_settings_accept_only_known_auth_modes` uses `monkeypatch.delenv("AZURE_OPENAI_AUTH")`.
- R6: `.env.example` lists `AI_GLOBAL_DAILY_TOKENS` and `AI_PRICE_PER_MILLION_TOKENS` with comments.

Tests: backend suite 238 passed, 1 skipped (frontend not built), both normally and with `AZURE_OPENAI_AUTH=managed_identity` exported. Bicep was not compiled here (`az` not installed), so CI should confirm.

# T-15 async-login status

Review C1 and C2 fixed. Every hashing route now uses `hash_capacity_after(gate)` (security.py): the gate holds the
cheap checks (rate limits, session/role, weak password, confirmation) and runs first, so rejected requests never
take or wait for a hash slot. C2: tests/test_hash_capacity_slots.py runs on one event loop and asserts the limiter
holds 0 slots after 200, 401, 409, 422, 429, 503 and 500 (mutation: removing `limiter.release()` fails 2 of them).
Verify: `TEST_DATABASE_URL=...starter_test_t15 .venv/bin/python -m pytest` (310 passed, 1 skipped) and
`npx vitest run` (111 passed). Not merged to main. Review suggestions S2-S4 left open.
