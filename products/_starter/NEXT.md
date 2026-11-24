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
Tests: backend 246 tests, 0 failures, 1 skipped (frontend not built); frontend vitest 111 passed.
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
