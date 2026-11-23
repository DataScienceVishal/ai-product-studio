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

## Re-review (2026-11-23)

- Reviewer: reviewer agent. Tree: `ce1fa5b`, checked out as a clean detached worktree. The starter's code there is
  identical to `7ab92be`; later commits up to `fe67f7a` change only `NEXT.md` under `products/_starter`.
- Commits reviewed: `f0f5b25` (email verification), `5a4b765` (C1 to C8 and the security Highs), `ed84b1a` (security
  Mediums, I1, I4 to I7, I9), `cd9b216` (frontend, I11), `7ab92be` (CI I10, docs I12). The ids `76c29fc` and
  `7ea1d7c` in the first brief don't exist; the coordinator confirmed the correction.
- Own workspace this time: databases `starter_rev_test` and `starter_rev_e2e`, ports 8400 and 4473 only. I read the
  security re-test (`c326528`, "Re-test" in SECURITY.md) without touching it. Its findings R1 to R11 are treated as
  known and only cross-referenced here.

### Verdict: CHANGES

All eight blockers are fixed, and every original reproduction now gives the right answer. I1 to I12 are fixed or
mostly fixed. CI is green on GitHub, e2e included. Three small things stop a PASS:
- the I11 fix introduced a regression in the delete-my-data path (B1);
- the liveness probe still waits for a worker thread (B2: the last piece of C1, also R4 in SECURITY.md);
- two of the new regression tests can't fail (B3).

Each is under ten lines. Once they're fixed, I'll re-check just those three. N1 to N3 can be fixed here or opened as
board tasks before G4.

### What I ran

| Check | Result |
|---|---|
| Backend tests at `ce1fa5b` on `starter_rev_test` | 113 passed, 1 warning (httpx2 deprecation), 20.8 s. The venv matches all 39 pins in `requirements-dev.txt` |
| `alembic upgrade head`, `check`, `downgrade base`, `upgrade`, `check` | clean |
| Frontend `tsc -b` and `vite build` | clean; JS 247.80 kB (76.37 kB gzip) |
| `scripts/e2e.sh` on 8400/4473 with `starter_rev_e2e` | `E2E PASS: core flow`. The "ai usage" line now shows `input_tokens: 65, output_tokens: 17`, and the API log holds no email |
| Original reproductions C1 to C8, and regression probes | The real app ran under uvicorn on :8400, through a scratch launcher that injects a slow or scripted AI and a fake Stripe API. The scripts are in this session's scratchpad (`probes/`) and aren't committed |
| Browser probe (Playwright 1.63) | wrong-password deletion, `?next=`, verify-email while signed out |
| 14 mutations on a scratch copy of the backend | 12 caught by a targeted test, 2 survive (B3) |
| CI run 45174839869 (push, `7ab92be`) | backend and frontend green: hash-checked install, migrations, 113 tests, pip-audit "No known vulnerabilities found", docker build done, npm audit "found 0 vulnerabilities". e2e skipped (branch push) |
| CI run 45175660079 (manual, `d0171f1`, same starter tree) | all three jobs green, e2e included ("E2E PASS: core flow" with the pinned Playwright) |
| CI run 45176951289 (push, `a9b9e19`) | green |

### Item by item

| Item | Status | Where | Proof |
|---|---|---|---|
| C1 | Fixed for the DB pool; a liveness gap remains (B2) | `deps.py:39` commits. `notes.py:91-118`: reserve, then the call with no transaction, then settle and reload. `ai.py:80-132`: one 25 s deadline and 1 retry. `db.py:27-29`: idle-in-transaction timeout. `health.py:17-20`: `/livez` | Tests `test_hardening.py:34,43,58`, `test_ai.py:138`. Repro with a pool of 2 + 0 (`DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=0`) and 14 concurrent summaries with a 12 s AI: all 200 in 12.2 s, `/healthz` max 58 ms, another tenant's list max 21 ms, 0 connections idle in transaction. Before: `/healthz` took 9.6 s, and with 40 s calls it gave 503 after 30 s |
| C2 | Fixed | `db.py:32-33` (`hide_parameters`); `logs.py:61-73` (DB errors reduced to the SQLSTATE); `email.py:34` | Test `test_hardening.py:73`. Repro: `users` and `notes` locked, 700 ms statement timeout. Login, sign-up and note creation gave 500. The log holds 0 emails, 0 `$argon2` and 0 note text, and the error ends `OperationalError: database error (sqlstate 57014); details hidden` |
| C3 | Fixed | `config.py:61,71-75`; `billing.py:100-101` | Tests `test_platform.py:101,120`, `test_hardening.py:96`. Repro: an empty secret is refused in prod and dev, and the server exits 1 with `BILLING_WEBHOOK_SECRET=`. Webhooks signed with `""` or the old public constant get 400, and the tenant stays `trial`/`trialing` |
| C4 | Fixed for both reproductions; known residue R1 and R2 | `ai.py:35-42,102-107,126-129` (billed usage travels with the error); `ai.py:179-199` (reserve under advisory locks); `notes.py:103-114` (settle on every path) | Tests `test_hardening.py:109,119,145`, `test_ai.py:150,166`. (a) 30 empty answers through the real `AzureOpenAI` adapter: 17 × 503, then 13 × 429; 105,400 tokens recorded (before: 0 of 186,000). (b) A tenant at 99,999 with 15 concurrent max-size calls: 1 × 200 and 14 × 429, usage 106,199 (before: 10 got through, 161,999). R2: the estimate under-counts non-Latin text. R1: the global budget forgets deleted tenants |
| C5 | Fixed | `Dockerfile:3-4,22`; `config.py:86-87`; `ratelimit.py:37-46,55-60` | Tests `test_hardening.py:176,182`. Repro with the CMD's flags, the image's env and an auth limit of 3 a minute. Each request had a new spoofed `X-Forwarded-For` plus the ingress IP: `[201, 201, 201, 429, 429, 429]` (before: 6 × 201). Same with trust off. 60,000 new keys left a blocked key blocked; the dict stayed bounded at 45,001 |
| C6 | Fixed | `billing.py:219-237,245-279`; `config.py:63` | Tests `test_hardening.py:203,212,225,235,240,256`. Repro through the real webhook route with the Stripe adapter. The session form carries `metadata[tenant_id]`, `[plan]` and `[offer]`. A realistic `checkout.session.completed` gives `pro`, `active`, `EARLY50` (before: `trial`). A basil-shape `customer.subscription.created` sets the period end from its items. Live-mode events are ignored, a stale `past_due` leaves `active`, and a second checkout gets 409 |
| C7 | Fixed | `main.py:64-112`; `billing.py:132,141-142`; `routes/billing.py:40`; `account.py:52,91` | Tests `test_hardening.py:267,280,289`. Repro: 150 MB to `/api/auth/login` gets 413 in 138 ms (declared) and 133 ms (chunked), and RSS stays near 91 MB (before: 129 to 539 MB). 300 checkouts: 10 × 200, 290 × 429. 25 wrong-password deletions: 5 × 401, 20 × 429 |
| C8 | Fixed | `billing.py:87-89,239-243`; `account.py:57-68` | Tests `test_hardening.py:300,309,326`. Repro with the Stripe adapter. With Stripe failing: 503, nothing deleted, still signed in. With Stripe up: `DELETE /v1/customers/cus_…` is sent while the tenant row still exists, then 204, and `/me` gives 401. A later webhook for the deleted tenant changes nothing |
| I1 | Fixed | `main.py:35-57` | Tests `test_hardening.py:415,426` sweep the OpenAPI route table. A mutation that widens the exemption to `/api/billing/*` is caught |
| I2 | Fixed | `config.py:64`; `routes/billing.py:128`; `main.py:177-179` | In prod with the flag on, mock pay gives 200; with it off, 404. The outbox warning is logged at startup. The flag defaulting to on is R3 |
| I3 | Fixed | `config.py:78-89` | Test `test_platform.py:101`. Nine realistic configs are accepted: mock demo, Azure AI, Stripe test mode, a Stripe CLI secret, a trailing slash, an upper-case scheme, two origins, an explicit mock secret and the dev defaults. No false rejections |
| I4 | Mostly fixed | `deps.py:49-53`; `team.py:39-43,69-76` | Tests `test_hardening.py:466,472`, `test_verification.py:51`. Bare domains such as `bit.ly/3xYz` still pass `email_safe` (R9) |
| I5 | Fixed | `logs.py:37-38,53-55` | Test `test_hardening.py:440`, and the e2e log shows the counts. The rule misses `password_hash`, `token_hash`, `stripe_secret_key` and `email_address` (minor) |
| I6 | Fixed | `maintenance.py`; `DATA.md` | Test `test_hardening.py:516`. The CLI purged 2,000,000 expired sessions in 2.1 s, inside the 10 s statement timeout |
| I7 | Fixed | `auth.py:176-209,219-226`; `config.py:33` | Tests `test_hardening.py:339,358`. Known and unknown emails take 3.85 and 3.77 ms median (before: 10.4 and 6.3 ms) |
| I8 | Partly fixed | `routes/billing.py:43-44,72-75`; `billing.py:213-216,234-236` | Event order, a second subscription, one idempotency key and unreadable replies are handled. The offer still comes from metadata with `allow_promotion_codes` (deferred in NEXT.md). The order check races when events arrive in parallel (N2) |
| I9 | Fixed | `conftest.py:23-31` | 113 passed on my own database |
| I10 | Mostly fixed | workflow lines 46, 53, 55, 73, 104-115 | Hash-checked installs, the docker build, pip-audit, npm audit, a pinned Playwright with a lockfile and browser cache, a push-only trigger, and one manual run with e2e. Actions are still pinned by tag (lines 39, 40, 64, 65, 91, 92, 97, 111, 125) |
| I11 | Fixed, with a regression (B1) | `api.ts:17-22,36-39,46-48`; `App.tsx:49-57`; `pages/app.tsx:339` | A failed sign-out keeps you signed in and shows a notice. `/billing/done` polls. Timeouts have their own message |
| I12 | Mostly fixed | README, ADR items 10 to 12, `billing.py:6` | The test count (113), "Not done yet" and the ADR consequences are current. `README.md:51-53` still describes the old prod guard. The table lacks `MOCK_CHECKOUT_ENABLED`, `AI_GLOBAL_DAILY_TOKENS`, `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `MAX_BODY_BYTES` and `STRIPE_API_VERSION` |

### Regressions the fixes could have introduced

| Area | Finding |
|---|---|
| BodyLimit and CsrfGuard order | Correct: RequestContext, then CORS, then CsrfGuard, then BodyLimit. CSRF 403s and 413s carry CORS headers for the allowed origin only, plus the security headers and `x-request-id`, and they are access-logged. Preflights get 200 from the allowed origin and 400 from others. Only the exact webhook path is exempt: `/api/billing/webhook/` gets 403. Minor: those two JSON bodies have no `request_id` (`main.py:44,70`) |
| Reserve/settle and advisory locks | No deadlocks in 3 rounds of 36 concurrent summaries across 3 tenants, with one tenant deleting its account mid-flight and another editing notes. Locks are always taken tenant first, then global, and nothing else takes them. When settle fails (`ai_usage` locked, 700 ms timeout), the request gets 500, the reservation keeps its 1,302-token estimate (it fails safe), and the log keeps only the SQLSTATE. With a year of rows (160,000), `reserve()` takes 8.4 ms median under the global lock against 1.5 ms without it, because the daily SUM is a sequential scan. That caps the app at about 120 reservations a second (R8). One summary in flight while its own tenant was deleted got 500 (FK violation 23503): minor. Summaries of edited notes: N3 |
| `deps.current` committing | No probe left a transaction or connection open (0 idle in transaction), and the objects stay usable after the commit. No test guards it (B3) |
| Verify-email needs sign-in | Works in the browser. A link opened while signed out shows "Sign in to confirm" and goes to `/login?next=/verify-email?token=…`. After sign-in the page says "your email is confirmed" and the flag is true. The pre-hijacking test passes |
| Reset through BackgroundTasks | Runs after the response with its own session; 60 known-address requests created 60 links. Known and unknown emails take the same time when requests are spaced out. Back to back on one connection, the next request overlaps the previous one's background work (2.35 against 3.48 ms), so the difference is small and noisy. Minor: the access log's `duration_ms` includes the background work |
| `_hash_slots` | Memory is bounded as intended. Availability isn't: see N1 |
| Log scrubbing | DB errors are scrubbed correctly. Minor: redaction misses `*_hash`, `secret_key` and `email_address`. A refused config prints pydantic's `input_value`, which ends with the last environment value set: my probe showed the last 22 characters of `STRIPE_SECRET_KEY`. Fix: `hide_input_in_errors=True` at `config.py:15` |
| Prod validator | No false rejections (see I3) |
| Stripe adapter | C6 holds. Minor: `_call` can take about 63 s (three 20 s timeouts plus sleeps of 1 s and 2 s, `billing.py:189,196-217`), past the browser's 30 s abort, for checkout and deletion. `checkout.session.completed` activates the plan even when `payment_status` is `unpaid` (Bacs Direct Debit): check it, and handle `checkout.session.async_payment_succeeded` and `..._failed` |
| Account deletion order | Correct (see C8). A retry after a partial failure is safe, because the DELETE's 404 counts as already gone |
| Retention purge | Works (see I6). Minor: DATA.md says links and invitations go N days "after use or expiry", but `maintenance.py:28-37` counts from `created_at` |
| Frontend SESSION_ENDED and `?next=` | See B1. `?next=//evil.example` and absolute URLs go home. `?next=/%5Cevil.example` passes `safeNext` (`auth.tsx:6-9`), but `pushState` refuses it, so the signed-in user stays on `/login`. That isn't a redirect: minor. At `App.tsx:20`, `refresh()` sets `me` to null on any error, so a network blip while `/billing/done` polls drops the user at `/login` (minor) |

### Blocking

**B1. A wrong password is treated as "session ended" (regression from the I11 fix).**
- Where: `frontend/src/api.ts:46-48` dispatches `SESSION_ENDED` for every 401 outside `AUTH_PATHS`, and
  `backend/app/routes/account.py:56,97` answer a wrong password with 401 `invalid_credentials`.
- Evidence: in the browser, a wrong password on Delete account sends the app to `/login`. "That password isn't
  right." never shows, and `GET /api/auth/me` still returns 200. "Leave this team" (`pages/app.tsx:311`) takes the
  same path.
- Why it matters: it's in the delete-my-data path, and it brings back what the I11 sign-out fix removed: the screen
  says signed out while the cookie still works. On a shared computer, the next person reloads straight into the
  account.
- Fix: dispatch only when `data.error === "not_signed_in"`, the code `current()` uses for every session failure, and
  drop `AUTH_PATHS`. Or answer re-authentication failures with 403. Add a wrong-password step to `core_flow.cjs`.

**B2. `/livez` waits for a worker thread (the rest of C1; also R4).**
- Where: `backend/app/routes/health.py:17-20` is a plain `def`, so it runs on AnyIO's 40-thread pool along with
  every other endpoint.
- Evidence: 45 concurrent summaries with a 12 s AI, from 3 tenants (15 each, inside the limit of 20 a minute).
  `/livez` took 11.7 s, `/healthz` 11.6 s, and another tenant's list 11.8 s. 39 calls had no effect. On a scratch
  copy with `async def livez`, under the same load, `/livez` stayed under 79 ms.
- Why it matters: T-7 will point the liveness probe at `/livez`. A stall of up to the 25 s AI deadline can get the
  replica restarted, which is the C1 outcome at a higher threshold. Splitting out `/livez` was meant to prevent
  exactly that.
- Fix: `async def livez()`. Tell T-7 to use `/livez` for liveness and `/healthz` for readiness. A cap on concurrent
  AI calls (R4) deals with the rest.

**B3. Two of the new regression tests can't fail.**
- `test_hardening.py:119` passes in 5 of 5 runs with the tenant advisory lock (`ai.py:184`) removed: the threads
  start too far apart to race. Fix: a `threading.Barrier` before `reserve()` and a monkeypatched
  `tokens_this_month` that sleeps about 50 ms, so a version without the lock lets several calls through.
- Nothing fails when the commit at `deps.py:39` is removed: all 113 tests pass, because the C1 test relies on
  `reserve()`'s own commit. Fix: a test endpoint that depends on `current` and asserts `not db.in_transaction()`
  and `pool.checkedout() == 0`.
- The first review's PASS condition was a regression test for each of C1 to C8.

### Important (fix here if cheap, or open board tasks before any product reaches G4)

**N1. Argon2 runs inside an open transaction, and threads waiting for a hash slot stay blocked.**
- Where: `routes/auth.py:146-147` (login reads the user, then verifies), `auth.py:121-124` (sign-up flushes the
  tenant, then hashes), `team.py:123-129` (accept), `auth.py:220-228` (reset confirm), and `security.py:13,31-41`
  (a blocking semaphore).
- Evidence: 200 concurrent wrong-password logins, with the rate limit raised to stand in for about 20 IPs. They
  drained in 23 s, with all 10 pool connections idle in transaction. `/healthz` took 10.0 s (its pool timeout is
  10 s), `/livez` 7.4 s and another tenant's list 7.0 s; the slowest login took 20.5 s. Argon2 takes 57 ms per
  check here, on 4 CPUs.
- Why it matters: credential stuffing from a proxy pool would stall every tenant. This isn't in SECURITY.md, whose
  login test measured memory.
- Fix: read the hash and commit (or hash first) before any argon2 work. Wait for a hash slot without holding a
  thread, for example with an `anyio.CapacityLimiter` in an async dependency. Or fail fast: `acquire(timeout=1)`,
  otherwise 503 with `Retry-After`.

**N2. Webhooks delivered in parallel can still apply a stale event.**
- Where: `routes/billing.py:68` reads the subscription without a row lock. Two deliveries can both pass the order
  check at `:72`, and the last commit wins.
- Evidence: a newer `checkout.completed` and a `subscription.past_due` 50 s older, posted at the same instant:
  past_due won 8 of 40 rounds. Stripe delivers events in parallel and doesn't guarantee their order.
- Why it matters: a paying customer stays `past_due`, so AI is blocked for them, until the next event arrives.
- Fix: `.with_for_update()` on that select, and a test that posts two events concurrently.

**N3. A summary of the old text is saved onto an edited note.**
- Where: `routes/notes.py:115-116` reloads the note after the AI call but only handles deletion.
- Evidence: all 36 notes edited while the AI worked ended up with their old summary, for example "Summary: n0" on a
  note now titled "edited".
- Why it matters: every product will copy this write-back pattern.
- Fix: keep `updated_at` (or a hash of the input) from before the call. If it has changed, don't save, and return
  409 "The note changed while we were summarising".

Known from the security re-test, and confirmed by my probes where they overlap:
- R1 and R2: trials can use up the global budget, and it forgets deleted accounts.
- R3: mock checkout is on by default in prod. I got Pro for free under prod settings.
- R4: AI calls tie up threads (the B2 evidence).
- R8: the global SUM is a sequential scan (the 8.4 ms figure above).
- R9: bare domains in invitations, and the verification resend rate.

### Minor

- `billing.py:105`: `isdigit()` still accepts "²", so `t=\xb2` gives an unauthenticated 500 and an "unhandled
  error" log line (carried over). Use `isdecimal()`.
- `config.py:15`: set `hide_input_in_errors=True` (see "Log scrubbing" above).
- `logs.py:37`: match on key parts, so `password_hash`, `token_hash`, `stripe_secret_key` and `email_address` are
  redacted too.
- `auth.tsx:8`: reject `\` in `next`, or check `new URL(next, location.origin).origin`.
- `DATA.md` against `maintenance.py:28-37`, and `README.md:51-53` and its config table (I12).
- `main.py:44,70`: add `request_id` to the CSRF and 413 bodies.
- Stripe: give `_call` an overall deadline under 30 s, and check `payment_status`.
- `scripts/e2e.sh`:
  - `:31` reuses any existing `dist`, so a local run can test a stale build (this time it wasn't stale);
  - the trap at `:34` is set only after both servers start;
  - `DROP DATABASE` isn't limited to names ending `_e2e`.
- CI:
  - pin actions by SHA (the rest of I10);
  - `pipx run pip-audit` resolves its own dependencies unpinned;
  - pin the base image by digest.
- Carried over from the first review and still open:
  - tokens travel in query strings;
  - there's no `require_active_plan` dependency and no per-tenant storage cap;
  - `team.py` imports `auth._start_session`;
  - `tsconfig.tsbuildinfo` is still tracked, and there's no `.dockerignore`;
  - the export leaves out pending invitations;
  - a signed-in user who opens `/signup` or `/accept-invite` gets a second session.

### What PASS needs now

1. Fix B1 to B3. I'll then check B1 in the browser, B2 with the 45-call probe, and B3 by re-running the two
   mutations. There's no need to repeat the rest.
2. Fix N1 to N3 here, or open board tasks for them.
3. Fix the security re-test's R1 to R4 and have the security agent re-test them.

Products shouldn't copy the starter until both gates pass.

## Re-review 2 (2026-11-23)

- Tree: `7da307b`, in a clean detached worktree. The fixes are in `93f7aba`; `7da307b` adds only DATA.md, NEXT.md
  and state/. Later commits (`3b66b5b`, `f074262`, `d051954`, `b0f72ae`) are not part of this pass.
- Own workspace again: `starter_rev_test`, `starter_rev_e2e`, ports 8400 and 4473.

### Verdict: CHANGES (one new blocker, B4)

B1, B2, B3, N2 and N3 are fixed, each with a test that I mutation-checked. N1 is mostly fixed. All the earlier
reproductions still hold. One regression came in with the R11 fix: the new purge of unverified accounts deletes
active and paying accounts, and under the default configuration it deletes every account 30 days after sign-up
(B4). `d051954`, which I haven't reviewed, appears from reading to address all three parts of B4. Re-check it
there.

### What I ran

| Check | Result |
|---|---|
| Backend tests at `7da307b` | 132 passed, 1 warning, 22.8 s |
| Migrations | `upgrade`, `check`, `downgrade base` and `upgrade` all clean. 0005 with data in the table: deleting a tenant leaves its usage row with `tenant_id` NULL (rule SET NULL). Downgrade removes the unlinked rows and restores CASCADE and NOT NULL |
| Frontend `tsc -b`, `vite build` | clean; JS 248.50 kB (76.63 kB gzip) |
| `e2e.sh` on 8400/4473 | `E2E PASS: core flow`, including the new wrong-password step. The drop guard refuses `starter_rev_test` |
| Mutations | The coordinator's two are both caught. The lock test fails in 5 of 5 runs without the lock and passes in 5 of 5 with it. Of 11 mutations to the new fixes, 7 are caught and 4 survive (H, J, L and M, below). My 12 earlier ones, re-run: all caught |
| CI | The runs for `93f7aba` and `7da307b` were cancelled, superseded by newer pushes. Run 45225652013 at `f074262` has the same starter code and CI workflow (it adds only infra/ and state/) and is green: 132 tests, alembic check, pip-audit clean, docker build, npm audit 0. e2e was skipped (branch push) |

### Status

| Item | Status | Proof |
|---|---|---|
| B1 | Fixed | `api.ts:47` ends the session only on `not_signed_in`. In the browser, a wrong password on Delete account stays on /settings, shows "That password isn't right." and `/api/auth/me` stays 200. The e2e step at `core_flow.cjs:56` covers it |
| B2 | Fixed | `health.py:18` is `async def`; `AISlots` (`ai.py:69`) allows 8 calls with a 2 s wait. 3 tenants × 15 calls of 12 s: 6 run (2 per tenant) and 39 are refused at once. `/livez` max 280 ms, `/healthz` 381 ms, another tenant's list 210 ms (before: 11.7 s). 25 tenants × 2: 8 run and 42 get 503 `ai_busy` after 2 s; `/livez` max 110 ms, others 1.7 s or less. Mutation G caught |
| B3 | Fixed | Removing the tenant lock fails `test_hardening.py:670` (and the cap test). Removing `deps.current`'s commit fails `:709` |
| N1 | Mostly fixed | Login commits before verifying (`auth.py:148`); sign-up, reset and accept hash first. In a burst of 200 logins, at most 1 connection was idle in transaction (was 10), and nothing failed. Remainder: a login waits up to 10 s for a hash slot (`security.py:35`) while holding a worker thread. Measured with curl from a separate process, `/healthz` took 5.7 s and `/livez` 1.5 s (CPU). With a hasher that only sleeps, both stayed under 1 s. Mutation F caught |
| N2 | Fixed | `routes/billing.py:69` locks the row. A newer and an older event posted at once: the stale one won 0 of 40 rounds (before: 8 of 40); no deadlocks. Mutation C caught |
| N3 | Fixed | A note edited during the AI call gets 409 `note_changed` and no summary is saved; an untouched note is summarised. Mutations D and E caught |

The earlier C3, C4, C6, C7 and C8 reproductions give the same results as in the first re-review. The empty-answer
run now stops at the trial's daily cap: 5 × 503, then 429s, with 31,000 tokens recorded.

### R1 to R11: regression check

- R1, R5, R6, R9, R10, the R11 wording, `--no-server-header`, and removing tokens from the address bar (checked in
  the browser on the verify and reset pages): no regressions found.
- R2:
  - It works, and the global budget can't be overshot.
  - It is conservative by design: a 20,000-character English note now reserves about 21,500 tokens. A trial can
    summarise about two long notes a day, and a plan near its monthly limit is refused calls that would actually fit.
- R3 works. `.env.example:19` still sets `MOCK_CHECKOUT_ENABLED=true`, so copying it into prod turns free Pro back on.
- R4: see B2.
- R11's purge: B4.

### Blocking

**B4. The new purge deletes active and paying accounts.**
- Where:
  - `backend/app/maintenance.py:43-47` deletes every tenant whose owner is unverified and was created more than
    30 days ago.
  - `:61` turns the rule on whenever `REQUIRE_EMAIL_VERIFICATION` is true, which is the default.
- Evidence: the purge CLI with the default config, on four seeded accounts.
  - Deleted: a 31-day-old trial whose owner can't verify (outbox only), with its notes.
  - Deleted: a 31-day-old paying tenant (`active`, Stripe customer `cus_test_paying`) whose owner signed up while
    verification was off. No provider call was made.
  - Kept: a verified tenant and a 10-day-old one.
- Why it matters:
  - With only the outbox, no owner can verify, so every account goes 30 days after sign-up. T-7's Bicep at
    `f074262` (outside this pass) defaults `requireEmailVerification = true` (`infra/main.bicep:48`) and gives the
    purge job the same environment, so the first deploy would do exactly that.
  - A tenant with a provider subscription is deleted without `close()`. That bypasses C8: the customer stays
    billed at Stripe while their data is gone.
  - R11 asked for "after 30 days with no sign-in". The code ignores sign-ins, so an active user who never verified
    loses their data.
- Fix:
  1. Run the rule only when real email exists (`email_provider != "outbox"`).
  2. Skip tenants with a provider customer or subscription.
  3. Require no sign-in for 30 days. This needs a sign-in time, because sessions are purged after 7 days.
  4. Tests: a paying unverified tenant is kept, an outbox-only config purges no accounts, and a recently signed-in
     unverified owner is kept.

  `d051954` appears to do 1 to 3.

### Minor (new)

- `notes.py:122`: `db.expire_all()` also expires `me.tenant`. Summaries in flight while their own account is
  deleted now return 500 (`ObjectDeletedError`, 6 of 6), where they used to return 404. Capture the tenant id
  before the call, or refresh only the note (`populate_existing`).
- Surviving mutations: the tests cover the helpers, not their use in summarise.
  - H: `with ai_slots` removed.
  - J: the old `used >= cap` monthly rule. Test it with 99,000 used and a 2,000 estimate.
  - L: the in-flight limit not passed.
  - M: the period end ignored.

  Add one HTTP-level test for each.
- Shorten the hash-slot wait to 1 or 2 s, with `Retry-After`; that is the rest of N1. Size the slots to the CPU
  count: 4 slots × parallelism 4 is 16 lanes, more than Container Apps' 0.25 to 1 vCPU. The 503 `busy` and
  `ai_busy` answers have no `Retry-After`.
- `scripts/e2e.sh`: the trap killed `npx` but not its `vite preview` child, which stayed on port 4473 (PPID 1).
  `b0f72ae` appears to fix this; not reviewed.
- `README.md:51-60` still has the old prod-guard text. It doesn't say that `REQUIRE_EMAIL_VERIFICATION` now also
  gates trial AI and the purge, and it doesn't list `MOCK_CHECKOUT_ENABLED`.
- Carried over: `t=\xb2` still gives a 500 (`billing.py:105`), and `?next=/%5C…` leaves the user on /login.

### What PASS needs now

Fix B4 with its tests. If `d051954` is the fix, I'll re-run the purge probe and the suite on it, plus a quick
review of its other changes. Everything else in this pass can become board tasks.

## Re-review 3 (2026-11-23)

- Tree: `95360d8`, in a clean detached worktree. It contains `d051954` (B4/R13 and the security re-test 2 items),
  `b0f72ae` (e2e.sh) and `95360d8` (the re-review 2 minor items). `3b66b5b` and `f074262` (T-7) were left to their
  own reviewer. The commits after `95360d8` don't touch the starter's code.
- Own workspace again: `starter_rev_test`, `starter_rev_e2e`, ports 8400 and 4473.

### Verdict: PASS

B4 is fixed, and so is everything left open from re-review 2 except the N1 remainder and a few small items. Every
blocker from the four passes (C1 to C8, B1 to B4) is now fixed, reproduced and guarded by a test I
mutation-checked. CI is green, and the security re-test 3 passed. The remaining items below are follow-ups for a
board task, not blockers.

### What I ran

| Check | Result |
|---|---|
| Backend tests at `95360d8` | 144 passed, 1 warning, 27.1 s |
| Migrations | `upgrade`, `check`, `downgrade base`, `upgrade` and `check` all clean. 0006 applied to existing data backfills `last_sign_in_at` for old users; old usage rows get `trial = false` |
| Frontend `tsc -b`, `vite build` | clean; JS 248.56 kB (76.63 kB gzip) |
| `e2e.sh` on 8400/4473 | `E2E PASS: core flow`, including the wrong-password step. No server processes were left 3 s after exit (the process-group kill works). A busy port is refused |
| Mutations | 19 on a scratch copy. 18 caught, including the coordinator's five: AI slots, the "would cross" monthly cap, the in-flight limit, a lapsed period, and the 404 reload. P4 survives (below) |
| CI run 45227833791 (push, `95360d8`) | backend and frontend green: 144 tests, alembic check, pip-audit "No known vulnerabilities found", docker build done, npm audit 0. e2e skipped (branch push) |

### Status

| Item | Status | Proof |
|---|---|---|
| B4 | Fixed | My purge probe on six accounts. With the default config (outbox), the CLI doesn't run the account rule at all and all six are kept. With `purge(..., unverified_after_days=30)`, as it would run once real email exists, only two go: unverified with no sign-in for 31 days, and unverified never signed in. Kept: the paying tenant with a Stripe customer, the verified one, the 10-day-old one, and the unverified one who signed in 2 days ago. Mutations P1 (outbox gate), P2 (paying exclusion) and P3 (sign-in condition) are each caught |
| Account deleted mid-summary | Fixed | 3 rounds: 404 and 404 each time, no unhandled errors (before: 6 × 500) |
| Wiring tests | Fixed | Mutations H, J, L and M are each caught by their new endpoint test |
| Hash slots | Better; N1 remainder open | 200 concurrent logins: 129 checked, 71 got 503 `busy` with `Retry-After: 5`, and nothing failed. Measured with curl from a separate process: `/livez` max 1.2 s (CPU) and `/healthz` 5.0 s (was 5.7 s). Logins waiting up to 3 s for a slot still hold worker threads, so other requests queue behind them during a burst |
| Retry-After on `ai_busy`, ASCII-only signature timestamps | Fixed | `t=\xb2` now gets 400 (was 500). Mutations V and S caught |
| Docs | Fixed | `.env.example` sets `MOCK_CHECKOUT_ENABLED=false` with a comment, and the README lists the new settings |
| Trial pool, sign-up caps, no retry after a post-send timeout, mock plans on trial caps | Work as described | Mutations T, W, X and U caught. My empty-answer run stops at the trial's daily cap. At cap − 1, 0 of 15 concurrent calls got through |

The earlier probes still hold: B2's 45-call case (`/livez` 67 ms, `/healthz` 161 ms), N2 (0 of 40 stale wins), N3
(409), B1 in the browser, the verify-email flow while signed out, and link tokens removed from the address bar.

### Follow-ups (board task, before any product reaches G4)

- **N1 remainder:** take hash capacity before a worker thread is assigned, for example an async dependency with an
  `anyio` limiter, or a try-acquire that answers 503 at once. Then a login burst can't queue `/healthz` and other
  requests behind it.
- **P4:** nothing fails if login stops recording `last_sign_in_at` (`routes/auth.py`), and the purge's
  live-account guard depends on it. Add a test that login moves it, or an end-to-end purge test: an old,
  unverified owner signs in and survives.
- **Sign-up caps (a trade-off):** `new_trials_per_day = 200` together with `signups_per_ip_per_day = 20` means
  about 10 IPs can close sign-ups for everyone for the rest of the UTC day. That's right for the $80 credit now;
  revisit before G4. The count also scans `tenants`, which has no `created_at` index.
- **`scripts/e2e.sh`:**
  - the port check runs after the e2e database is dropped and recreated, so a refused run leaves it empty (it
    happened to me). Move the check first;
  - the trap is still set only after both servers start;
  - `[ -d dist ] ||` reuses a stale build.
- **Carried over:**
  - `README.md:51-53` still has the old prod-guard text;
  - `?next=/%5C…` leaves a signed-in user on /login (not a redirect);
  - actions are pinned by tag, not SHA.
