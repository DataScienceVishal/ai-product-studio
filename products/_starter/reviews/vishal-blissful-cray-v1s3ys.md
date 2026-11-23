# Review: products/_starter (T-6, plus T-8 part 1), branch vishal/blissful-cray-v1s3ys

- Reviewer: reviewer agent, 2026-11-23
- Reviewed: `git diff main...vishal/blissful-cray-v1s3ys` at commit `5df3b8b` (includes team invitations 9e6d7ca and
  the Team and accept-invite pages 5df3b8b). The whole `products/_starter/` folder is new code, plus
  `.github/workflows/_starter-ci.yml`.
- Not reviewed: uncommitted email-verification work that appeared in the shared working tree during the review
  (`config.py`, `deps.py`, `models.py`, `auth.py`, `routes/billing.py`, `team.py`, migration `0003`, `e2e.sh`).
  I reviewed and ran an export of the committed tree (`git archive 5df3b8b`), not the working tree.
- Deploy workflow: deliberately deferred to T-7 (NEXT.md). Noted, not counted against this review.
- Later commit: `f0f5b25` (email verification, T-8 part 2) landed after this review and is **not reviewed**.
  I checked that C1 to C8 are all still present there. Line numbers are unchanged except `config.py`, where
  the webhook secret moves to line 44 and the prod guard to line 53. `f0f5b25` adds a verified-owner gate on
  invites and checkout, which partly covers I4. It needs its own review.

## Verdict: CHANGES

The foundations are good and mostly well reasoned. Tenant isolation held against every attack I tried, and
sessions, CSRF, password hashing, webhook signatures and idempotency are done properly. The tests check
behaviour over HTTP against a real Postgres. But eight problems in the shared plumbing would be copied into
every product: an availability bug that one user can trigger, personal data in logs, a webhook-forgery path,
an AI cost cap that can be bypassed, spoofable rate limits, a Stripe plan bug, memory exhaustion, and a
delete-my-data gap. All eight are cheap to fix. Seven were reproduced against the committed code; C8 was found
by reading it.

## What I ran

| Check | Result |
|---|---|
| Backend tests (committed tree, private database) | 66 passed, 1 warning (httpx2 deprecation) |
| `alembic upgrade head`, `alembic check`, `downgrade base`, upgrade again | clean, "No new upgrade operations detected" |
| Frontend `tsc -b` and `vite build` (committed tree) | clean; JS 240.57 kB (74.64 kB gzip) |
| `scripts/e2e.sh` (committed tree, own database `starter_review_e2e`) | `E2E PASS: core flow` |
| Hashed `requirements.txt` with `--require-hashes` into a fresh venv | installs cleanly |
| Route table: auth and CSRF dependency on every route | correct (see the checklist below) |
| Cross-tenant and mass-assignment probes | all refused (see the checklist below) |
| `pip-audit` / `npm audit` | not run: blocked by the permission classifier. The security gate must run them |
| Docker image build | not run: no Docker daemon in this environment. CI doesn't build the image either (I10) |
| CI on GitHub | never run (NEXT.md says so). Reviewed statically and YAML-parsed |

The probe scripts are in this run's scratchpad and aren't committed. Every number below comes from them.

## Critical issues (blocking)

### C1. Every request holds its DB connection, inside an open transaction, across the AI and Stripe calls. Ten concurrent summaries take the whole app down

- Where: `backend/app/deps.py:36-48` (`current` runs SELECTs and never ends the transaction),
  `backend/app/routes/notes.py:89-99` (the AI call sits between reads and the commit),
  `backend/app/routes/billing.py:49` (the Stripe call inside the same request transaction),
  `backend/app/db.py:22` (pool 5 + 5 overflow), and `backend/app/ai.py:66,72-89` (a 30 s timeout per
  operation, 3 retries and up to 8 s sleeps, so roughly 2 minutes worst case).
- Evidence: I ran the committed app under uvicorn with an AI provider that takes 12 s and sent 14 concurrent
  summarise calls. All 10 pool connections sat `idle in transaction`, `/healthz` waited 9.6 s, and 4 calls
  queued for 24 s. With 40 s AI calls and 11 concurrent requests, `/healthz` returned **503 after 30.0 s**
  (logged as "health check: database unreachable") and one request returned **500** (QueuePool timeout).
- Why it matters: one user clicking Summarise on ten notes, or a slow Azure OpenAI response, exhausts the pool
  for every tenant. The health check then fails and Container Apps restarts the replica, killing every
  in-flight request. Every product copies this endpoint shape.
- Fix:
  1. End the read transaction in `current` once the user and tenant are loaded. With `expire_on_commit=False`
     the objects stay usable and the connection goes back to the pool. Use `db.commit()`, not `rollback()`,
     which expires the objects.
  2. In `summarize`: read, check the plan and cap, commit, call the AI with no transaction open, then reload
     the note (it may have been edited or deleted meanwhile) and write the summary and usage in a new short
     transaction.
  3. Give interactive AI calls one overall deadline, about 25 s with at most one retry, below the frontend's
     30 s abort (`frontend/src/api.ts:18`).
  4. As a backstop, add `idle_in_transaction_session_timeout` to the connect options.
  5. Split liveness from readiness: `/livez` with no DB for the liveness probe, `/healthz` with the DB for
     readiness and the Docker HEALTHCHECK.
  6. Add a regression test with a fake AI whose `complete()` asserts `app.state.db.engine.pool.checkedout() == 0`.

### C2. Unhandled DB errors write emails and argon2 password hashes into the logs

- Where: `backend/app/db.py:22`. SQLAlchemy puts bound parameters into exception text by default, and
  `backend/app/main.py:61` (`log.exception`) writes that text. The key redaction in
  `backend/app/logs.py:35,50-52` only covers `extra=` keys, not exception text.
- Evidence: I locked `users` from another connection so that requests hit the 700 ms statement timeout. The
  resulting log lines:
  - login: `[parameters: {'email_1': 'victim.person@example.com'}]`
  - sign-up: the email and the full `$argon2id$v=19$m=65536,t=3,p=4$...` hash

  Any INSERT that fails would log note bodies the same way. Statement timeouts, failovers and migrations
  holding locks all trigger this in real life.
- Why it matters: the definition of done section 3 says "No secrets or personal data in logs", and ADR 0001
  item 10 promises the same.
- Fix: `create_engine(..., hide_parameters=True)`. Add a test that forces a DB error on a parameterised query,
  for example `select :e::int` with an email, and asserts the email is not in the formatted log line. While
  there, stop logging the email subject (`backend/app/email.py:34`): invitation subjects contain the tenant name.

### C3. An empty `BILLING_WEBHOOK_SECRET` passes the production guard, so anyone can forge billing webhooks

- Where: `backend/app/config.py:40,49` (it only rejects the dev default), `backend/app/billing.py:93-104`
  (`verify` happily uses an empty key), and `.env.example:15`, which ships the variable empty.
- Evidence: `Settings(env="prod", billing_webhook_secret="")` was accepted. A webhook signed with `""` returned
  `200 {"applied": true}` and moved the tenant to `plan=pro, status=active`.
- Why it matters: an empty secret is the most common deploy mistake (an env var defined with no value, or a
  missing Key Vault reference). With it, an attacker can set any known tenant's plan or status, which also
  means free upgrades and a bigger AI cap. In ENV=dev the secret is a public constant
  (`config.py:9`), so any deployed non-prod demo is open to the same forgery (see I2).
- Fix: in prod, require at least 32 characters (or `whsec_` when `BILLING_PROVIDER=stripe`). Make `verify()`
  refuse an empty secret. Outside tests, have dev generate a random secret per process instead of using a
  public constant. Add a test for the empty case.

### C4. The per-customer AI cap can be bypassed: failed calls aren't counted, and the race window is far wider than the comment says

- Where: `backend/app/ai.py:100-109` (an empty answer raises before usage is returned),
  `backend/app/ai.py:72-89` (timed-out or retried attempts that may have been billed are never recorded),
  `backend/app/ai.py:130-134` (check-then-call), and `backend/app/routes/notes.py:94-98`.
- Evidence:
  - 30 calls where the provider returned `finish_reason=length`, empty text and `usage` of 5,000 + 1,200
    tokens: all returned 503. The provider billed 186,000 tokens and **0** were recorded.
  - Race: with a tenant 1 token under the 100,000 trial cap, 15 concurrent max-size calls let 10 through. Usage
    reached **161,999** (62% over). Only the DB pool size stopped it, not the cap. The comment at
    `ai.py:131` says "one call's tokens".
- Why it matters: gpt-5-mini is a reasoning model, and `max_completion_tokens=1200` includes the reasoning
  tokens. A user can write notes that make it reason until it runs out of room. Each such call costs about
  $0.004, is free to repeat and never counts. At the 20 calls per minute per tenant limit that is about $100
  a day per tenant (rough figure, at $0.25 and $2 per million input and output tokens). Trials are free and sign-up limits are spoofable (C5), and the studio's
  total Azure credit is $80.
- Fix:
  1. Record usage whenever the provider returns a `usage` object, then raise. For example, `AIUnavailable`
     can carry the usage, and `summarize` records and commits it before re-raising.
  2. Record a conservative estimate for attempts that timed out after sending.
  3. Reserve before calling: an estimated `AIUsage` row (input estimate plus `max_output_tokens`) inserted
     under `pg_advisory_xact_lock(tenant)` or a `SELECT ... FOR UPDATE` on a per-tenant counter, then
     reconciled with the real numbers.
  4. Consider a low `reasoning_effort` for summaries, after checking the API version supports it.
  5. Tests: empty answers are counted, and concurrent calls at cap minus one let at most one through.

### C5. The Dockerfile lets any client choose its own IP for rate limiting

- Where: `backend/Dockerfile:19` (`--proxy-headers --forwarded-allow-ips "*"`) together with
  `backend/app/config.py:21` (`TRUST_PROXY_HEADERS` defaults to false) and `backend/app/ratelimit.py:44-49`.
- Evidence: I started uvicorn exactly as the Dockerfile CMD does, with an auth limit of 3 a minute. Six
  sign-ups, each with a new `X-Forwarded-For`, all returned 201. With "*", uvicorn takes the **leftmost**
  `X-Forwarded-For` entry, which the client controls, as `request.client`. The app uses that whenever
  `TRUST_PROXY_HEADERS` is false. The Azure Container Apps ingress docs say: "If specified in initial request,
  it is appended to. Only the rightmost IP is provided by Azure Container Apps."
  (learn.microsoft.com/azure/container-apps/ingress-overview, read 2026-11-23). The per-email login key still
  held. Per-IP limits did not: sign-up, reset request, reset confirm, invitation accept, and login across many
  accounts (password spraying).
- A related problem: `ratelimit.py:27-28` clears **all** counters, per-email login limits included, once
  50,000 keys exist. Someone who can mint keys (spoofed IPs, made-up emails on cheap 422 paths) can reset
  everyone's limits.
- Fix: use one mechanism. Drop uvicorn's proxy flags (`--no-proxy-headers`) and keep the app's `client_ip()`,
  which already takes the rightmost hop. Require `TRUST_PROXY_HEADERS=true` in prod, or set it in the image.
  Evict expired or oldest keys instead of `clear()`. Add tests for `client_ip` with the flag on and off.

### C6. Stripe test mode: after a real checkout the plan is never recorded, so paying customers keep the trial cap

- Where: `backend/app/billing.py:206-208` (`checkout.session.completed` maps to `active` with `plan=None`),
  `billing.py:175-180` (plan and offer metadata go only on the *subscription*), and
  `backend/tests/test_billing.py:98-107` (the contract test never asserts the plan).
- Evidence: I parsed a realistic `checkout.session.completed` payload and applied it. The result was
  `plan=trial status=active current_period_end=None`, so the AI cap stayed at 100,000 for a Pro buyer. For a
  card checkout Stripe sends `customer.subscription.created`, which isn't handled, and often no `.updated`
  event at all, so nothing ever corrects the plan. The mock includes the plan, which is why the contract test
  passes.
- Fix:
  1. Add `metadata[tenant_id|plan|offer]` to the Checkout Session itself, read them on
     `checkout.session.completed`, and handle `customer.subscription.created`.
  2. Make the contract test assert `plan` and `offer` for both providers.
  3. Pin a `Stripe-Version` header. On API versions from 2025-03-31 (basil) onwards, `current_period_end`
     lives on the subscription items, not the subscription; please confirm against Stripe's changelog.
  4. Also ignore `livemode: true` events, as a second guard for the selling lock (my probe showed they are
     accepted today).

### C7. Any caller can exhaust memory or CPU

- Unauthenticated: there is no request-body limit outside the webhook. A single 150 MB JSON body sent to
  `/api/auth/login` took the server's peak memory from **129 MB to 539 MB** before it returned 422. The
  Container Apps ingress docs list a 240 s request timeout and don't mention a body-size limit. Fix: a pure-ASGI body
  limit of about 1 MB by default, checking Content-Length and counting streamed bytes (reuse
  `_read_limited`, `routes/billing.py:84-95`), with per-route overrides.
- Any free account:
  - `MockBilling.sessions` (`billing.py:119-125`) grows forever, and `/api/billing/checkout` has no rate limit.
    300 checkouts left 300 in-memory sessions, and mock billing is the default provider in prod too. Fix:
    bound the dict (TTL or LRU) or store sessions in the DB, and rate-limit checkout per tenant.
  - `DELETE /api/account` (`account.py:54`) runs argon2 (64 MiB, t=3, p=4) with no rate limit: 25 wrong
    passwords, no 429. Fix: limit it per user, as login does.

### C8. Account deletion leaves the payment subscription and customer at the provider

- Where: `backend/app/routes/account.py:48-63`, and `BillingProvider` (`billing.py:77-83`) has no cancel or
  delete operation. Found by reading the code; not exercised, since Stripe isn't live.
- Why it matters: with Stripe, a deleted tenant keeps being charged, and Stripe keeps their personal data.
  That makes the "delete-my-data path" (definition of done section 4) incomplete in every product that copies
  this. Later webhooks for the deleted tenant are swallowed (`routes/billing.py:63-65`), so nobody notices.
- Fix: add `cancel(tenant_id, provider_ref)` to the provider interface (Stripe: cancel the subscription and
  delete the customer; mock: no-op) and call it before the DB delete. If the provider fails, fail closed with a
  friendly error. Add a contract test.

## Important (fix in this branch or open board tasks before any product reaches G4)

- **I1. CSRF and auth are opt-in per router.** Each router must remember `dependencies=[Depends(require_csrf_header)]`.
  `routes/billing.py` mixes exempt and protected routes, so a new billing route is unprotected by default. Today
  the route table is correct (checked below). Make the check global, with an explicit exemption for the webhook
  path, and add a guard test that every unsafe route has CSRF and every non-public route depends on `current`.
  Note for that test: in FastAPI 0.165 `app.routes` holds `_IncludedRouter` objects, not `APIRoute`s, so a
  naive loop finds nothing. Use `effective_route_contexts()` or the OpenAPI schema.
- **I2. Demo deploys force a choice between a broken checkout and unsafe settings.** `mock_complete` returns 404
  when `ENV=prod` (`routes/billing.py:114`), so a deployed demo with mock billing has a dead "Pay (test)"
  button. Running it as `ENV=dev` instead brings a public webhook secret, insecure cookies and exposed API
  docs. Add an explicit flag such as `MOCK_CHECKOUT_ENABLED` that is allowed with prod settings, or refuse
  `BILLING_PROVIDER=mock` in prod. Similarly, `OutboxEmail` in prod silently drops reset and invitation
  emails, so a deployed product has no working password reset (definition of done section 1). At least warn
  at startup and document it.
- **I3. The prod validator misses cheap checks** (`config.py:46-55`):
  - `APP_BASE_URL` must be https and not localhost; reset and invite links and Stripe return URLs use it.
  - `CORS_ORIGINS` must not contain `"*"`: Starlette reflects any Origin when credentials are allowed
    (`starlette/middleware/cors.py:163`), which would make the custom-header CSRF check meaningless.
  - `TRUST_PROXY_HEADERS` should be required (C5).
- **I4. Invitations can be used as a spam and phishing relay.** Any free account can send 20 emails a minute per
  tenant, with unlimited tenants, to any address, carrying an attacker-chosen tenant name (up to 120
  characters, including URLs and newlines) in the subject and body (`team.py:71-73`). Before a real email
  adapter exists:
  - require a verified owner email (`f0f5b25` adds this gate; not reviewed);
  - add daily caps and a limit on pending invitations;
  - strip control characters and URLs from tenant names used in email.

  `team.py:60` also tells any owner whether an email has an account anywhere. Sign-up already reveals that by
  design, so note it in the ADR.
- **I5. Log redaction over-matches and under-matches.** `logs.py:35` matches substrings, so `input_tokens` and
  `output_tokens` become `[redacted]` in every "ai usage" line, as the e2e log shows. Per-customer token use
  never reaches the logs. Match whole key names instead, and extend the test to check that `input_tokens`
  survives. uvicorn's `color_message` (ANSI escape codes) also leaks into the JSON; drop it.
- **I6. Nothing is ever purged.** Expired sessions, used reset links, expired invitations, `billing_events` and
  `ai_usage` grow forever. Definition of done section 4 needs retention rules. Add a cleanup command (run as a
  scheduled job) and a data-inventory template listing the starter's tables.
- **I7. Password reset details.**
  - The link isn't strictly single-use under concurrency: two simultaneous confirms both succeeded in 5 of 5
    trials (`auth.py:182-192`). Use `UPDATE ... WHERE used_at IS NULL AND expires_at > now() RETURNING user_id`.
  - The reset request takes 10.4 ms for an existing email and 6.3 ms for an unknown one (median), so timing
    reveals accounts. Move the write and the send off the request path, or equalise them.
  - 10 reset emails a minute per address (`auth.py:159`) is enough to bomb an inbox. Use something like 3 an hour.
- **I8. Stripe adapter robustness** (`billing.py:166-221`, `routes/billing.py:54-78`):
  - events can arrive out of order, and a stale `past_due` overwrites a newer `active`;
  - a second checkout while already subscribed creates a second subscription;
  - the offer is recorded from metadata even if the customer never entered the promotion code. Apply the
    discount server-side instead of `allow_promotion_codes`;
  - the Idempotency-Key (`billing.py:184`) ignores the offer and changes every minute. Generate one key per
    logical checkout before the retry loop;
  - a non-JSON response or a missing `id`/`url` gives a 500.
- **I9. The test fixture breaks on a shared database.** `tests/conftest.py:25-26` uses
  `drop_all`/`create_all`, which cannot drop `users` when the database holds tables from another branch. During
  this review the committed suite gave **66 errors** against `starter_test` because of the builder's
  uncommitted migration. Create a fresh database per session, as `test_migrations_match_models` already does,
  or `DROP SCHEMA public CASCADE`.
- **I10. CI gaps** (`.github/workflows/_starter-ci.yml`):
  - CI installs the unhashed `requirements-dev.txt` (line 46) and never builds the image, so the hashed
    `requirements.txt` and the Dockerfile are never checked. Add `docker build` and install with
    `--require-hashes`, for example dev requirements compiled with hashes.
  - Playwright is unpinned and has no lockfile or browser cache (line 100). Pin it in a small `package.json` +
    lockfile and cache `~/.cache/ms-playwright`.
  - Actions are pinned by tag, not SHA.
  - `push` plus `pull_request` runs every job twice on PR branches; limit `push` to main.
  - There is no `pip-audit`/`npm audit` step.
  - The workflow has never run on GitHub. Run it once with `gh workflow run` before PASS.
- **I11. Frontend error paths.**
  - There is no global 401 handling. A removed member or an expired session stays in the app shell with
    "Your session has ended" banners; reset `me` and redirect.
  - A failed sign-out is ignored (`App.tsx:38`), so the user thinks they're signed out while the cookie stays
    valid.
  - The Stripe success URL `/billing/done` (`routes/billing.py:50`) has no route and lands on Notes; add a page
    that polls `/api/auth/me` until the plan is active.
  - The 30 s client abort (`api.ts:18`) shows "Can't reach the server" while the backend may still be working (C1).
- **I12. The docs have drifted.**
  - The README says 56 tests (there are 66). Its "Not done yet" (line 74) and ADR 0001's consequences (line 43)
    still list invitations and member roles as missing.
  - `billing.py:6` cites `tests/test_billing_contract.py`, which doesn't exist.
  - ADR item 10 ("logs never contain emails") is false until C2 is fixed.

  The playbook asks for docs to change in the same commit as the code.

## Suggestions (minor)

- `verify()` (`billing.py:97-99`) uses `isdigit()`, which accepts `²`. `int()` then raises, and an
  unauthenticated request gets a 500 (reproduced over a raw socket). Use `fullmatch(r"\d+", ...)`.
- AI retry: a negative or NaN `retry-after` makes `time.sleep` raise. A non-JSON 200 raises an uncaught
  `JSONDecodeError`. Azure also sends `retry-after-ms`.
- Prompt-injection framing (`notes.py:21-25,95`): a note can contain `</note>` and break out of the delimiters.
  Use a random boundary per request, or strip the delimiter, and offer a shared `wrap_untrusted()` helper for
  products that summarise documents or web pages. The risk is low today: the output goes back to the same
  tenant as text, there are no tools, and the model sees only that note.
- Reset and invite tokens travel in query strings (`auth.py:169`, `team.py:70`), so they end up in the frontend
  host's access logs and browser history. Put them in the URL fragment and call `history.replaceState` after
  reading them.
- Add `Strict-Transport-Security` and an API CSP (`default-src 'none'; frame-ancestors 'none'`). The host that
  serves the HTML (T-7) needs frame protection too: the Delete-account page can otherwise be clickjacked.
- Paid-plan access is only enforced on summarise. Provide a `require_active_plan` dependency so products apply
  it consistently.
- Notes have no per-tenant storage cap or write limit. With one shared Postgres server for all products, one
  trial tenant could fill the disk for every product. The connection budget matters too: 10 per replica, times
  products, times replicas, against the B1ms limit. This is input for T-7.
- `scripts/e2e.sh`:
  - The trap is set only after both servers start (line 31), so an early failure leaves uvicorn running.
  - `DROP DATABASE ... WITH (FORCE)` runs on whatever `E2E_DATABASE_URL` names (line 17). Refuse names that
    don't end in `_e2e`.
  - Add password reset and invite/accept/remove to the e2e. That needs a dev-only outbox endpoint, which
    replaces the scratch harness.
- Accessibility basics are mostly met (labels, `role=alert`, focus outline; contrast checked: slate-600 on
  white is about 7.6:1). Remaining gaps:
  - no h1 on app pages, and `document.title` never changes;
  - focus doesn't move on route change;
  - every "Summarise" button has the same name (add an aria-label, as Delete has);
  - the textarea hint isn't linked with `aria-describedby`.
- Maintainability:
  - `team.py` imports the private `_start_session` from `auth`; move session helpers to their own module.
  - `_limit` versus direct `limiter.check` calls is inconsistent, and the invite limit of 20 is hard-coded.
  - `frontend/tsconfig.tsbuildinfo` is a build artifact; gitignore it.
  - Add a `.dockerignore`.
- The export (`account.py:27-40`) leaves out pending invitations (third parties' emails) and AI usage rows.
- Signed-in users who open `/signup`, `/login` or `/accept-invite` silently get a second session or tenant;
  the old session stays valid.

## Checklist results

| Area | Result |
|---|---|
| Authorization on every endpoint | PASS. Owner-only: delete, export, checkout, mock-complete, invite, revoke, remove member. Member: notes, usage, team, me. Public: auth flows, accept, plans, webhook, health |
| Tenant scoping of every query | PASS by reading every query and by probes. Another tenant's note, invitation, member and checkout all gave 404. Smuggled `tenant_id` and `role` in sign-up, note and accept bodies were ignored. A member couldn't delete the account or remove the owner (403) |
| Session cookie, expiry, revocation | PASS. HttpOnly, Secure, SameSite=Lax, host-only, 7-day server-side expiry, SHA-256 at rest. Revoked on logout, reset, member removal and account deletion (tested) |
| Timing-safe login, enumeration | Login PASS (76.8 vs 76.5 ms median). Reset request leaks by timing (I7). Sign-up and invite 409s accepted by design |
| CSRF (header plus CORS, webhook exemption) | PASS today. Fragile by design (I1); misconfigurable through `CORS_ORIGINS` (I3) |
| Webhook signature, replay, idempotency | PASS: HMAC-SHA256, `compare_digest`, ±300 s, insert-first idempotency in the same transaction, streamed size cap. FAIL on the empty secret (C3) |
| Live-key refusal | PASS (`sk_test_`/`rk_test_` only, tested) |
| mock-complete exposure | PASS in prod (404). Tied to the demo-deploy conflict (I2) |
| AI framing, cap, cost, timeouts | Framing adequate (minor). Cap FAIL (C4). Timeouts too long and they pin DB connections (C1) |
| FastAPI 0.165 / Starlette 1.10 / SQLAlchemy 2.1 correctness | Dependency caching gives one Session per request (verified). Rollback after IntegrityError is correct. The one async endpoint (webhook) does DB work through `run_in_threadpool`. The "connection held per request" pattern is the problem (C1) |
| Logging context | PASS: 160 concurrent access lines across 4 tenants, 0 with the wrong tenant. PII FAIL on error paths (C2) |
| Pure-ASGI middleware | PASS: validated request ids, de-duplicated security headers, JSON last-resort 500 with request id, no stack in body |
| Frontend XSS | PASS: no `dangerouslySetInnerHTML` or `innerHTML`; React escaping. `location.assign(checkout.url)` trusts the backend's Stripe URL |
| Frontend redirects | `/accept-invite` is public and routed (5df3b8b). Gaps listed in I11 |
| CI | Structure fine (services, caches, conditional e2e, `NODE_PATH` works). Gaps in I10 |
| Dockerfile | Non-root uid 10001 PASS. Hashed install PASS. Proxy headers FAIL (C5). HEALTHCHECK checks the DB (see the C1 fix) |
| Tests | Behavioural and HTTP-level, real Postgres, migration drift test, and a tenancy test that NEXT.md says was mutation-checked (not re-verified). Gaps: the C1-C8 regressions, a route-table guard (I1), `client_ip`, rate limits on accept, reset and sign-up, Stripe `customer.subscription.updated`, fixture isolation (I9) |

## Definition of done sections 1 to 5: does the starter make them achievable?

| Section | Status |
|---|---|
| 1. Works for real | Sign-up, argon2id, expiring sessions and the reset flow are built. The reset email never arrives once deployed (I2). Tenant isolation is proven by a test. Sample data and the empty state exist; there is no demo-account seed script. Deploy is in T-7 |
| 2. Payments in test mode | Plans, trial and offer sit behind an adapter, with mock contract tests and the live lock. Stripe mapping is wrong (C6), deletion leaves the subscription (C8) |
| 3. Reliability | Timeouts, retries, request-id logs, health check, rate limits and the AI cap are all present, but C1, C2, C4 and C5 each break one of these in practice |
| 4. Security and privacy | The delete and export paths exist. They're incomplete at the provider (C8); there are no retention rules (I6) and no data-inventory template. Privacy and terms drafts are product-level |
| 5. Onboarding | Empty state, optional sample data, a guided first task and a help page are in place |

## What PASS needs

Fix C1 to C8, each with a regression test, and update the README and ADR in the same change (I12). Then rerun
the backend tests, `alembic check`, the frontend build and `e2e.sh`, and run CI once on GitHub. Fix I1 to I11
in this branch where cheap. Otherwise open board tasks (I9 and I10 are quick). The security gate still has to
run `pip-audit` and `npm audit`.
