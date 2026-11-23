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
