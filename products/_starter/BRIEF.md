# Starter comprehension brief (for Vishal)

Task T-90. Written 2026-11-25 against the code on `main`. Every claim below was checked in the file named next to it. Where I could not check something (it needs real Azure or real Stripe), it says so.

This is a platform, not a product. Nobody buys the starter. Every product is a copy of it with its own core object in place of `Note`. So you demo it to prove "the boring, dangerous parts are already done", and a buyer's hardest questions about any product land here first.

Terms are defined the first time they appear. Paths are under `products/_starter/` unless they start with `state/` or `.github/`.

---

## 1. One-picture overview

```
                      ONE ORIGIN (one web address, so the cookie and CSRF rules hold; ADR 0002 decision 2)
 +-----------+  HTTPS: page + JS    +-----------------------------------------------------+
 |  Browser  |--------------------->|  ca-starter  (one container, FastAPI + built React)  |
 |  React    |<---------------------|                                                     |
 |  SPA      |  JSON replies        |   RequestContext -> CORS -> CsrfGuard -> BodyLimit   |
 +-----------+  /api/... + cookie   |   routes: auth notes billing account team health     |
   (SPA = single-page app:          +---+------------+------------+------------+----------+
    one HTML page, JS swaps views)      |            |            |            |
                                        | SQL        | prompt +   | checkout   | "send this
                                        | (tenant_id | note text  | + signed   |  email"
                                        |  on every  v            v webhooks   v
                                        |  query) +-----------+ +--------+  +-----------+
                                        v         | Azure     | | Mock   |  | Outbox    |
                                 +-------------+  | OpenAI    | | billing|  | (memory   |
                                 | Postgres 16 |  | (or       | | (or    |  |  only, no |
                                 | one DB per  |  |  FakeAI)  | | Stripe |  |  real     |
                                 | product     |  +-----------+ | TEST)  |  |  email)   |
                                 +-------------+                +--------+  +-----------+
        counts of requests per key -> in-memory limiter (or Redis, optional, not provisioned)
        JSON log lines (ids only, never emails or note text) -> stdout -> Log Analytics
```

Where it runs on Azure (designed in `ADR/0002-azure-deploy.md`, built in `infra/main.bicep` and `infra/shared.bicep`, **not created yet**):

```
 GitHub Actions (manual, main branch only, signs in by OIDC = short-lived token, no stored password)
   build image -> Trivy scan -> push to ACR -> deploy new revision at 0% traffic
   -> migration job -> smoke test -> move traffic -> point purge job at new image
 rg-ai-studio  (resources placed in francecentral: Student policy, ADR 0002 "Region (T-61)")
   cae-studio   Container Apps environment (Consumption only, scales to zero)
     ca-<slug>               web app, 0.5 vCPU, 1 GiB, 0 to 1 replica   (main.bicep: cpu, memory, maxReplicas)
     caj-<slug>-migrate      job: alembic upgrade head, once per release
     caj-<slug>-purge        job: daily retention purge, 03:17 UTC (ADR 0002 decision 10)
   acrstudioznp96r   container registry (Basic)
   psql-studio-znp96r   Postgres Flexible Server B1ms, one database per product
   log-studio   Log Analytics, 30 days, 0.1 GB/day cap
   id-studio-acrpull, id-<slug>-app, id-<slug>-migrate   managed identities (see 4.10)
```

Status today (`state/BUDGET.md`): only `id-github-deploy` is live. Every other row is "planned". The deploy workflow refuses to create anything until the repository variable `STUDIO_AZURE_APPROVED` is `yes` (`.github/workflows/_starter-deploy.yml`, "check" job).

## 2. The 60-second story

Every product we sell needs the same ten things before its first real feature: sign-up and sign-in, one customer unable to see another's data, a trial and a payment page, AI calls that cannot run up a bill, logs that do not leak personal data, health checks, a database that migrates safely, and a deploy that cannot break the live site. These are easy to get subtly wrong and expensive to get wrong in front of a customer.

The starter builds them once. A new product copies the folder, swaps `Note` for its own object (a rota, an interview, a menu), sets its plans and prices, and writes its one core flow. Everything else is inherited and already tested: the README's tests table says 561 backend tests passed (stale: the board's latest merge note, T-86, records 566 backend and 182 frontend vitest tests passing), and the security gate re-test 3 passed 8 of 8 sections on 2026-11-23 (`SECURITY.md` top, `README.md` tests table). I re-read the code, I did not re-run the tests.

The risk we take on in exchange: a flaw in the starter is a flaw in every product. That is why it has its own reviews folder (`reviews/`) and security file.

Key terms:
- **Tenant**: one customer company. Every row a customer owns carries that company's `tenant_id`.
- **Slug**: the product's short folder name (`starter`, later e.g. `rota`). Azure resource names include it.
- **ADR**: architecture decision record, a short file saying what was decided and why (`ADR/`).
- **Adapter**: a swappable piece behind one interface, so dev and tests use a fake and production uses the real thing.

## 3. One small example, end to end

Story: Priya runs "Priya's Bakery Ltd". She signs up, creates a note, asks for an AI summary, her trial runs out, she upgrades. Steps 1, 3, 4, 6 and 7 are the path the browser test walks (`tests/e2e/core_flow.cjs`); it runs with verification off and does not simulate the trial ending (steps 2 and 5).

Assume local or demo settings: `AI_PROVIDER=fake`, `BILLING_PROVIDER=mock`, `MOCK_CHECKOUT_ENABLED=true`. Whether email verification is on is called out at step 2.

| # | What Priya does | Request (all under `/api`, writes carry `X-Requested-With`) | What the server stores | What comes back |
|---|---|---|---|---|
| 1 | Fills in the sign-up form | `POST /api/auth/signup` `{company_name, email, password}` (`routes/auth.py`) | rows in `tenants`, `users` (role `owner`, argon2 hash of password), `subscriptions` (plan `trial`, status `trialing`, `trial_ends_at` = now + 14 days), `auth_sessions` (SHA-256 of the cookie token), `email_verifications` (hash of the link token) | 201 + profile, and a `Set-Cookie` that is `__Host-session` when `COOKIE_SECURE=true` (else `session`), HttpOnly, SameSite=Lax, 7 days |
| 2 | Clicks the emailed link | `POST /api/auth/verify-email` `{token}` while signed in | `users.email_verified_at` set; `email_verifications.used_at` set | 204. **The link goes to the in-memory outbox (`app/email.py`), so in any deploy today nobody receives it.** That is why the deploy workflow defaults `require_email_verification` to off (ADR 0002 "What a deployed demo can do") |
| 3 | Creates a note | `POST /api/notes` `{title, body}` (`routes/notes.py`) | `notes` row with `tenant_id` = Priya's tenant, `created_by` = Priya | 201 + note JSON |
| 4 | Clicks "Summarise" | `POST /api/notes/{id}/summarize` | (a) before the call: an `ai_usage` row, model `pending`, `input_tokens` = worst-case estimate. (b) after: the same row rewritten with the real tokens and model. (c) `notes.summary` set | 200 + note with summary. With FakeAI the text starts "Summary: " (`ai.py` `FakeAI`) |
| 5 | Day 15. Clicks "Summarise" again | same route | nothing new | **402** `plan_required`: "Your trial or plan has ended..." (`has_access` in `billing.py` is false once `trial_ends_at` has passed) |
| 6 | Opens Billing, enters `EARLY50`, picks Pro | `POST /api/billing/checkout` `{plan:"pro", offer_code:"EARLY50"}` (owner only; needs a verified email unless verification is off) | nothing yet; the mock keeps the session in process memory (max 1000, `MockBilling`) | `{checkout_id: "mock_cs_...", url}`; the SPA stays in-app at `/billing/mock-checkout?session=...` |
| 7 | Clicks "Pay (test)" | `POST /api/billing/mock/complete/{session_id}` (404 unless mock billing and `MOCK_CHECKOUT_ENABLED=true`) | the server builds a signed "checkout.completed" event and runs it through the **same** webhook parser as Stripe. `billing_events` gets the event id; `subscriptions` becomes `active`, plan `pro`, offer `EARLY50`, period end +30 days | `{plan:"pro", status:"active", offer:"EARLY50"}` |

Two things in this example surprise people:

1. **Upgrading does not raise the AI allowance yet.** In `notes.py`, `limited = sub.status == "trialing" or sub.provider in LIMITED_PROVIDERS` and `LIMITED_PROVIDERS = {"mock","stripe"}`. Mock and Stripe-test plans therefore use the *trial* allowance (30,000 tokens a day, 100,000 a month; `PLANS["trial"]` in `billing.py`). The comment says why: until `unlock selling` those plans cost nothing, so they must not unlock paid-sized AI spend. Remove `"stripe"` from that set in the same change that allows live keys.
2. **The "plan limit" in step 5 is the trial ending.** The AI-allowance limits are separate and return 429s: `ai_daily_cap_reached`, `ai_cap_reached` (monthly), `ai_in_progress` (more than 2 calls at once), and 503s `ai_trial_pool_reached` and `ai_budget_reached` (`ai.py` `reserve`). Section 4.4 explains them.

## 4. How each part works

### 4.1 Sign-in and sessions

- **What it does.** Passwords are hashed with argon2id (a deliberately slow, memory-hungry hash, so a stolen database cannot be cracked quickly), 10 to 128 characters (`security.py` `MIN_PASSWORD`, `MAX_PASSWORD`). A session is a random 32-byte token in a cookie; the database stores only its SHA-256 (`models.AuthSession.token_hash`). Sessions last 7 days (`config.py` `session_days`).
- **Why a cookie token, not a JWT.** A JWT (self-contained signed token) cannot be revoked without extra machinery. Here, logout (`POST /api/auth/logout`) and password reset delete the rows, so access ends at once. ADR 0001 decision 1.
- **CSRF** (a malicious site making your browser send a request with your cookie): every write under `/api` needs an `X-Requested-With` header, which a browser cannot add cross-site without a CORS permission the server refuses. One global guard, `CsrfGuard` in `main.py`; the only exemption is `/api/billing/webhook`, protected by its signature instead. ADR 0001 decisions 2 and 12.
- **Cookie name.** With `COOKIE_SECURE=true` the cookie is `__Host-session`: the browser only accepts that prefix if it is Secure, has no Domain and Path is `/`, so a sibling subdomain cannot plant one (`deps.py` `session_cookie`).
- **Timing and enumeration.** An unknown email is checked against a dummy hash so a miss takes as long as a wrong password (`security.py`). Password-reset request always answers 202 (`routes/auth.py`). Sign-up and invitation forms do reveal that an email has an account; ADR 0001 "Consequences" accepts that for a B2B form, rate-limited.
- **Hash capacity.** Each hash uses about 64 MiB, so only 2 run at once (`HASH_SLOTS = 2`). A login burst waits up to 3 s (`HASH_WAIT_SECONDS`) on the async side, then gets 503 `busy` with `Retry-After: 5`. Cheap checks (rate limits, validation) run first so junk requests never take a slot.
- **Roles.** `owner` and `member` (`models.User.role`). `deps.owner` and `deps.verified_owner` guard owner actions. Team routes: `GET /api/team`, `POST /api/team/invitations`, `DELETE /api/team/invitations/{id}`, `DELETE /api/team/members/{id}`, `POST /api/invitations/accept` (`routes/team.py`).
- **Failure and what the user sees.** Wrong password: 401 `invalid_credentials`. Expired or missing cookie: 401 `not_signed_in`, and the SPA clears its state and goes to `/login` (`App.tsx`). Too many tries: 429 `rate_limited` with `Retry-After`. Too many hashes at once: 503 `busy`.

### 4.2 Tenancy (customer isolation)

- **What it does.** Shared tables, `tenant_id` on every customer-owned row (ADR 0001 decision 4). In `routes/notes.py`, `_scoped(me)` is `select(Note).where(Note.tenant_id == me.tenant.id)`, and every read, update and delete goes through it. Another tenant's note id returns the same 404 as a missing one, so ids cannot be probed.
- **Deleting a tenant** cascades to its users, sessions, notes, invitations (`ondelete="CASCADE"` in `models.py`). `ai_usage` is the exception: `tenant_id` is set to NULL so the studio-wide daily AI budget still counts the tokens, and the rows hold no personal data.
- **Proof.** The tests check every private route needs sign-in, every write needs the CSRF header, and cross-tenant reads fail (README "Tests"; SECURITY.md section 2: 29 of 29 live cross-tenant and role checks in the first gate, 48 of 48 at re-test 3).
- **Trade-off.** Postgres row-level security (the database itself refusing cross-tenant reads) would be a second layer. It is **not used** (ADR 0001 decision 4). So isolation depends on every query using `_scoped`. When a product adds objects, copy the tenancy tests for each one (README "Making a product from it", step 2).
- **Failure and what the user sees.** A forgotten filter is a data leak, not an error message. That is the main reason review exists for each product.

### 4.3 Billing (mock vs Stripe test, early-customer coupon)

- **What it does.** `app/billing.py` defines plans (`trial` free, `starter` 2900 pence, `pro` 7900 pence; placeholders, each product sets its own), one offer (`EARLY50`: 50% off for 3 months), and two providers behind one interface: `MockBilling` (default, no network) and `StripeBilling`.
- **Test mode only.** `StripeBilling` raises unless the key starts `sk_test_` or `rk_test_`. Live payments stay locked until you send `unlock selling` (ADR 0001 decision 7; CLAUDE.md section 6).
- **Mock signs like Stripe.** `sign()` and `verify()` use the Stripe header format `t=<unix>,v1=<hmac-sha256>`, with a 300 s tolerance, so the mock exercises the real webhook path.
- **Webhook rules** (`routes/billing.py` `apply_update`): each event id is stored in `billing_events`, so a repeat is a no-op; an event older than the last applied one is recorded but ignored; a cancellation wins a same-second tie; an event for a different subscription id cannot replace the current one; the subscription row is locked while updating. Body limit 256,000 bytes.
- **Early-customer coupon with Stripe.** The code you type is checked against `OFFERS` in `billing.py`. With Stripe the app creates a coupon with a deterministic id (`studio-early50-50pc-3m-v1`, built by `Offer.coupon_id`) and sends it with the Checkout Session, so the customer does not re-type anything. `allow_promotion_codes` is deliberately not sent: Stripe rejects it alongside discounts and it would let people type codes the app never validated (README "Billing and the early-customer offer", T-15 decision).
- **Other routes.** `GET /api/billing/plans`, `POST /api/billing/portal` (owner, with a verified email when verification is on; a Stripe-hosted page to change card or cancel), `POST /api/billing/checkout`. Past-due tenants cannot start a second checkout (409 `subscription_past_due`) so they are not charged twice.
- **Access rule.** `has_access`: `active` needs the period end plus a 3-day grace (`GRACE`) to be in the future; `trialing` needs `trial_ends_at` in the future.
- **Failure and what the user sees.** Stripe unreachable or refusing: 502 `billing_rejected` or a friendly 503. Account deletion calls the provider first and deletes nothing if that fails (503 `billing_unavailable`, `routes/account.py`).
- **Not proven.** The README and board (T-15) say the Stripe path has **never been run against real Stripe test keys**. Everything about Stripe is tested against recorded or faked responses. Stripe needs two dashboard settings that live outside the code: a saved Customer Portal configuration, and "cancel the subscription" after the last failed retry (README "Billing").

### 4.4 The AI layer: guardrails, caps, deadlines, cost guard

- **Provider adapter** (`ai.py`). `FakeAI` in dev and tests (no cost). `AzureOpenAI` in the cloud. `AI_PROVIDER` is `fake` by default; the deploy workflow also defaults to `fake`.
- **Two Azure APIs.** `AZURE_OPENAI_API=auto` uses the Responses API only when the endpoint ends in `/openai/v1/responses`, otherwise chat completions. The studio's reasoning deployment refuses chat, so the cloud needs the `responses` form (README "Azure OpenAI API"). The call sends `store=false` so Azure does not keep the response object.
- **Prompt guardrail** (`routes/notes.py`). The system prompt tells the model the note is data, not instructions. `_as_data` swaps `<` and `>` in user text for look-alike characters, so no text can close the `<note>` block early. This reduces prompt injection; it cannot eliminate it. The harm ceiling is one summary saved on that user's own note.
- **Reserve, call, settle.** Before the call, `reserve()` takes Postgres advisory locks, checks every cap against the worst-case token estimate, and writes a `pending` row. The DB connection is released, the model is called, then `settle()` replaces the estimate with the real tokens. No transaction is held during the slow call (ADR 0001 decision 11). A failed call still records what it may have billed. A `pending` row older than 15 minutes (process died) is zeroed by the purge or the tenant's next call (`STALE_RESERVATION`).
- **The caps** (defaults from `config.py`, `billing.py`):

| Cap | Value | Refusal |
|---|---|---|
| Calls at once per tenant | 2 (`AI_CALLS_PER_TENANT_AT_ONCE`) | 429 `ai_in_progress` |
| Calls at once per process | 8 (`AI_CONCURRENT_CALLS`), waits 2 s | 503 `ai_busy` |
| Requests per minute per tenant | 20 (`AI_RATE_LIMIT_PER_MINUTE`) | 429 `rate_limited` |
| Plan, per month | trial 100,000; starter 500,000; pro 2,000,000 tokens | 429 `ai_cap_reached` |
| Trial, per day | 30,000 tokens | 429 `ai_daily_cap_reached` |
| All free trials together, per UTC day | 50% of the global cap (`AI_TRIAL_SHARE`) | 503 `ai_trial_pool_reached` |
| Whole studio, per UTC day | 100,000 (`AI_GLOBAL_DAILY_TOKENS`) | 503 `ai_budget_reached`, "The AI is resting until tomorrow" |

- **Calls per day is not a fixed number.** The reservation is the prompt bytes plus 1,200 answer tokens (`MAX_SUMMARY_TOKENS`), plus 1,500 more (`AI_REASONING_HEADROOM`) on the Responses API. README worked example: a 1 KB note reserves about 4,004, so 100,000 admits at least 24 such calls.
- **Deadlines.** Each attempt 20 s (`AI_TIMEOUT_SECONDS`), whole call 25 s (`AI_DEADLINE_SECONDS`), one retry (`AI_RETRIES`). The browser aborts at 30 s (`FRONTEND_TIMEOUT_SECONDS`), served at `GET /api/config` and read once by the SPA (`frontend/src/api.ts`). The app **refuses to start** if the AI deadline plus 2 s exceeds the browser timeout (`config.py` validator), because a call the browser abandoned is still billed. A request sent and then timed out is never retried (it could be billed twice).
- **Cost guard.** `infra/cost-guard.sh` fails the build if `tokens/day x price per million x 30` passes $6.10 a month. Defaults: 100,000 tokens x $2.00 per million x 30 = $6.00. The price assumes a gpt-5-mini-style model. **If a product points at gpt-5.4-pro ($180 per million output tokens, per README) the daily cap must drop to roughly 1,130 tokens, about one summary**, or the same cap could cost up to $540 a month. `state/BUDGET.md` notes the existing deployment is gpt-5.4-pro.
- **Wrong or missing answers.** An answer that is incomplete, refused, or all "thinking" is never saved as a summary; the user sees a specific friendly message and the tokens are still counted (`_parse` and `_NO_ANSWER` in `ai.py`). Summaries are cut at 4,000 characters. If the note is edited while the AI works, the save is refused with 409 `note_changed`.
- **What the user sees when Azure is down.** 503 `ai_unavailable`: "The AI service is busy right now. Please try again in a minute." Bad credentials: "isn't configured correctly" (the same 503). A 400 from the model: 502 `ai_rejected`, which is not retried.

### 4.5 Rate limiting

- **What it does.** A sliding-window counter per key (`ratelimit.py`). Examples: 10 a minute for login, sign-up and reset gates (`auth_rate_limit_per_minute`); 20 sign-ups a day per IP (`SIGNUPS_PER_IP_PER_DAY`); 200 new trials a day studio-wide (`NEW_TRIALS_PER_DAY`); 3 reset emails an hour per address; 10 checkouts a minute.
- **In memory by default**, per replica. With more than one replica the real limit multiplies. That is why `maxReplicas` is pinned to 1 (`infra/main.bicep`, ADR 0002 decision 1).
- **Redis optional.** Set `RATE_LIMIT_REDIS_URL` and counts are shared through one Lua script. Redis calls time out at 200 ms; on any Redis error the app falls back to in-memory limits, logs a warning at most every 30 s, and never returns a 500. **Azure Cache for Redis is not provisioned** (costs money, ask-first); no Bicep resource exists for it.
- **Real client IP.** Behind Azure's ingress the app trusts only the rightmost `X-Forwarded-For` hop (`client_ip`), and `TRUST_PROXY_HEADERS` must be true in prod (`config.py` validator), else every user shares one bucket.
- **What the user sees.** 429 `rate_limited`, "Too many attempts", with `Retry-After`.

### 4.6 Logging

- **What it does.** One JSON line per log entry, with `request_id` and `tenant_id`, to stdout (`logs.py`). A request id comes from a valid `X-Request-ID` header or is generated; it is returned as a response header and inside error bodies, so a customer can quote it.
- **Never in logs.** Emails, names, note text, tokens. Extra fields with sensitive names (password, token, secret, email, cookie, api key) are replaced by `[redacted]`. SQLAlchemy parameter dumps are off (`hide_parameters=True` in `db.py`), and database errors are cut down to the error code (`safe_exception`). Uvicorn's own access log is disabled; our middleware writes one line per request instead.
- **Where they go when deployed.** Console and system logs to `log-studio`, kept 30 days. The ingress HTTP access log is deliberately not collected because it would hold IPs and the tokens in email links (ADR 0002 decision 11; `DATA.md`).
- **Failure.** A last-resort 500 returns `{"error":"internal_error", "request_id":...}` (`RequestContext` in `main.py`).

### 4.7 Database and migrations

- **What it does.** Postgres via SQLAlchemy 2 and psycopg 3, synchronous (ADR 0001 decision 5). Connect timeout 5 s, statement timeout 10 s, idle-in-transaction timeout 15 s, pool of 5 plus 5 overflow by default (`db.py`, `config.py`; the Bicep sets a smaller pool of 3 plus 2 per ADR 0002 decision 4).
- **Migrations** are Alembic files in `backend/migrations/versions/` (0001 to 0007 today). CI runs `alembic upgrade head` then `alembic check` so the files must match the models (README tests table). Run them as a separate job (`caj-<slug>-migrate`), never in the web process.
- **Rollback rule.** A rollback moves traffic and never runs a downgrade (a downgrade can delete data). So every migration must work with the previous release's code: add first, drop or rename in a later release (ADR 0002 decision 9).
- **Passwordless database sign-in (ADR 0003).** With `DB_AUTH=entra` the app fetches a short-lived Microsoft Entra token from its managed identity and uses it as the Postgres password (`dbauth.py`). The URL must have no password and `sslmode=verify-full`, else the app refuses to start. Deploys check on every release that the server has password sign-in disabled (`infra/check-auth-config.sh`). Two database roles per product: `<db>_app` (read and write rows) and `<db>_migrator` (owns tables). Not verified: a real Entra connection; tests assert the connection parameters only (README, `tests/test_db_entra.py`).
- **Failure.** `/healthz` returns 503 with `db: "down"` if the database is unreachable (`routes/health.py`). `/livez` never touches the database, so a busy pool does not get the replica restarted.

### 4.8 One image, one origin (serving the SPA)

- **What it does.** The `Dockerfile` builds the React app and copies it into the Python image. FastAPI serves it, so the browser sees the app and `/api` on one origin (`spa.py`). Known client routes (`CLIENT_ROUTES`, 16 of them) return `index.html`; any other unknown path returns the same HTML with status 404.
- **Gotcha.** Every new frontend page must be added to `CLIENT_ROUTES` in `backend/app/spa.py`, or opening it directly or refreshing returns 404. A test compares the two lists (README "One image, one origin").
- **Headers.** Every response gets `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `X-Robots-Tag: noindex, nofollow` (private demos) (`main.py`). API responses also get `Cache-Control: no-store`; the SPA's `index.html` gets `no-cache` and `/assets` files are cached for a year (`spa.py`). With `COOKIE_SECURE=true`, HSTS (one year). In prod, JSON gets `default-src 'none'`; HTML gets a policy with `script-src 'self'` (no inline script). API docs are hidden in prod.

### 4.9 Deploy: GitHub Actions with OIDC, Bicep

- **Bicep** is Azure's infrastructure-as-code language. `infra/shared.bicep` creates shared pieces once; `infra/main.bicep` creates one web app and two jobs per product on every release.
- **OIDC** (OpenID Connect): GitHub proves "this run is on branch main of this repo" and Azure hands out a token that lasts minutes. No password is stored in GitHub. The identity `id-github-deploy` trusts only `refs/heads/main` (ADR 0002 decision 8). Cloud studio runs never hold Azure credentials.
- **Approval gate.** The workflow deploys only if the three OIDC secrets exist, `STUDIO_AZURE_APPROVED=yes`, and the run is on `main`. Otherwise it compiles the Bicep and stops with a notice.
- **Release order** (ADR 0002 decision 9): build, Trivy scan (fails on fixable HIGH or CRITICAL vulnerabilities), push, deploy at 0% traffic, run migration job, smoke test (`infra/smoke.sh`: `/livez`, `/healthz` with `db: ok`, HSTS, HTTP-to-HTTPS redirect), then move traffic. If anything fails the old revision keeps serving. Manual rollback is the `rollback_to` input.
- **Cost traps blocked in code.** `infra/cost-guard.sh` refuses a Dedicated or GPU workload profile, a custom network, a private endpoint or a maintenance window (each starts a flat charge, about $73 a month for the Dedicated case).
- **Failure.** First request after about 5 idle minutes is a cold start (image pull plus app start), acceptable for demos (ADR 0002 failure table).
- **Not applied.** The least-privilege deploy role (T-65) is written but Vishal has not applied it, so the deployer is still Contributor on `rg-ai-studio`.

### 4.10 Security posture and data handling

- **Secrets** come only from environment variables. In Azure they are Container Apps secrets filled from GitHub, never in templates (ADR 0002 decision 6). There is no Key Vault yet. The app refuses to start with a short webhook secret, `*` in `CORS_ORIGINS`, or, in prod, a non-https `APP_BASE_URL`, `COOKIE_SECURE` off, or `TRUST_PROXY_HEADERS` off (`config.py`).
- **Managed identities.** The registry-pull identity is attached with `lifecycle: None`, so code in the container cannot get tokens for it. Separate app and migrate identities mirror the two database roles (ADR 0003 decision 1).
- **Body limits.** 1,000,000 bytes per request (`max_body_bytes`), enforced while streaming.
- **Deletion and export.** `DELETE /api/account` (owner, needs password and typing DELETE), `DELETE /api/account/me` (member), `GET /api/account/export`, `GET /api/account/me/export` (`routes/account.py`, `DATA.md`).
- **Retention.** `python -m app.maintenance purge` removes expired sessions, reset and verification rows after 7 days, invitations after 30 days, billing event ids and `ai_usage` after 400 days (`maintenance.py`). Backups keep 7 days, so a deleted row can survive there up to 7 days (`DATA.md`).
- **Honest gap.** Until ADR 0003 slice 7 and T-18 are verified on real Azure, "passwordless Postgres" is proven in tests and review, not in a live deploy.

## 5. Questions a buyer (or his friend) might ask about any product built on this

1. **Is our data safe from other customers?** Every row carries a tenant id and every query is filtered by it; another customer's record looks like "not found". Tests and a security pass checked this. We do not use database-level row security, so a coding slip in a new product is the real risk, and each product gets its own review.
2. **Where does our data live?** Azure Postgres in `francecentral` (France), per `infra/main.bicepparam`. Not the UK. `DATA.md` (processors list) and the DRAFT privacy page (`frontend/src/pages/legal.tsx`) still say "UK region", which is out of date: the Student subscription only allows five regions (ADR 0002 "Region (T-61)"). Say this plainly. A paying customer's hosting is a handover decision (ADR 0002 failure table: "No customer may depend on this subscription").
3. **Is it UK GDPR compliant?** It has the basics: a data inventory (`DATA.md`), export and delete routes, retention purge, no personal data in logs, and DRAFT privacy and terms pages (`frontend/src/pages/legal.tsx`). `DATA.md` says it is not legal advice and needs legal review before launch. Processors to list: Azure, Azure OpenAI, the payment provider, an email provider once approved.
4. **Does our note text go to OpenAI?** It goes to Azure OpenAI, not OpenAI directly. On the Responses API the call sends `store=false`. Azure's abuse monitoring is separate and may keep flagged content for human review; `DATA.md` tells us to check Microsoft's terms before real customer data.
5. **What if the AI is wrong?** Summaries are suggestions saved on the note, never actions. Prompt text tells the model to ignore instructions inside notes. Incomplete or refused answers are not saved. A product with riskier output (money, rotas) needs its own review step; the starter does not judge truth.
6. **What if the AI is down?** The user gets a friendly 503 "try again in a minute"; everything else (notes, billing, sign-in) still works. Nothing queues or retries in the background.
7. **What does the AI cost per customer?** The caps bound it. With the default $2.00 per million blended price, one trial tenant is limited to 30,000 tokens a day (about $0.06 at most), and the whole studio to 100,000 tokens a day (about $6 a month). Paid-plan allowances (500,000 and 2,000,000 tokens a month) are placeholders in `billing.py`, and today mock and Stripe-test plans still draw on the trial allowance. A bigger model changes all of this (section 4.4).
8. **How much does hosting cost?** Estimate: $5.07 a month with the Student allowance for Postgres, $23.20 without, plus at most $6.10 for real AI (ADR 0002 "Monthly cost"). Estimates, not billed figures; nothing is deployed yet.
9. **What uptime can we promise?** None, honestly. One replica, no high availability, scale-to-zero cold starts, Student credit that can run out, Postgres on a B1ms server (ADR 0002). Fine for private demos. A real SLA needs a hosting decision at handover.
10. **What if our payment fails or we cancel?** The webhook moves the subscription to `past_due` or `canceled`; access follows `has_access` with a 3-day grace on an ended paid period. A past-due customer is sent to the card-update portal rather than charged twice. Stripe's dunning setting must be "cancel" (README). All of it is only proven against test-mode fakes.
11. **Can we take payments now?** No. Live keys are refused by code, and live payments are locked until you send `unlock selling`.
12. **Can we leave and take our data?** Yes: owners can download everything via `GET /api/account/export`, and delete the account (and the Stripe customer first) with `DELETE /api/account`. Backups keep deleted rows for up to 7 days.
13. **Do you send us emails (receipts, resets, invites)?** Not yet. There is no real email provider (paid, needs approval); messages go to an in-memory outbox. In a deployed demo that means no one can verify an email, reset a password or accept an invite. This is the largest functional gap before any customer pilot.
14. **How do you stop abuse and bills running away?** Per-IP and per-account rate limits, daily sign-up caps, a studio-wide daily AI budget, and a build-time cost check. In-memory limits reset when the app restarts and are per replica.
15. **Who can touch production?** Releases run from the `main` branch only, by OIDC, behind an approval variable, with a vulnerability scan. The deploy identity is still broad (Contributor); the narrower role (T-65) and a required-reviewer environment (T-62) are open. Anyone who can push to `main` can change the workflow (ADR 0002 decision 8 notes the limit).

## 6. Demo map: five minutes, starter itself

Run locally per `README.md` ("Run it locally"), or `./scripts/e2e.sh` to watch the scripted version. For the demo use `COOKIE_SECURE=false`, `REQUIRE_EMAIL_VERIFICATION=false`, `MOCK_CHECKOUT_ENABLED=true`, defaults otherwise (these match `scripts/e2e.sh`).

| Min | Step | Say | Part shown |
|---|---|---|---|
| 0:00 | Open `/signup`, create "Priya's Bakery Ltd" | "Account, tenant and a 14-day trial in one step" | 4.1, 4.2 |
| 0:45 | Empty page, click "Add two sample notes", add one note | "Every note carries the company's id" | 4.2 |
| 1:30 | Click "Summarise" | "Cap reserved first, model called, real tokens recorded" (FakeAI answers "Summary: ...") | 4.4 |
| 2:15 | Open `/api/docs` (dev only), show the error shape; show a log line with `request_id` and no email | "Ids, never personal data" | 4.6 |
| 2:45 | Billing: enter `EARLY50`, Choose Pro, "Pay (test)" | "Same signed webhook path as Stripe, test money only" | 4.3 |
| 3:30 | Sign out, sign in | "Server-side session; the cookie holds a random token" | 4.1 |
| 4:00 | Settings: wrong password on Delete, then delete | "Delete is real, provider closed first, password required" | 4.10 |
| 4:40 | Show the Actions workflow and `infra/cost-guard.sh` | "Releases from main only, scan, smoke test, no cost traps" | 4.9 |

Hard question to expect at 1:30: "Is that real AI?" Answer: no, `AI_PROVIDER=fake`. The Azure path is built and tested with a fake HTTP client, and the deploy default is also `fake`.

## 7. Limits and roadmap

Not done, with where each is tracked:

- **Nothing is deployed.** No resource except `id-github-deploy` exists (`state/BUDGET.md`). The whole live path (build, scan, deploy, migrate, smoke) has never run to completion on real Azure.
- **OIDC (T-60, doing).** The first OIDC run failed on the subject format; the fix needs a federated credential with GitHub's immutable IDs. Remaining per the board: one green OIDC run, then you revoke the old service principal.
- **Deploy permissions.** T-65 (custom least-privilege role): written, blocked until you apply it at your next deploy (Q-14 A). T-62 (required-reviewer `production` environment, ruleset on `main`): todo, needs you. T-69 (move `id-github-deploy` to its own resource group, split a shared-deploy role): todo, needs you as Owner.
- **Passwordless Postgres (T-18).** Slices 1 to 6 are merged and reviewed; nothing is verified on real Azure. Slice 7 (OIDC) overlaps T-60.
- **Stripe (T-15).** Never run against real Stripe test keys. The first test-mode checkout should confirm Stripe accepts the coupon form. Also Stripe-side settings in 4.3.
- **Redis.** Code is built and tested; Azure Cache for Redis is not provisioned. Required before `maxReplicas` goes above 1.
- **AI model choice (T-34).** The cap sizing assumes a mini model. The pro model can exceed the 25 s deadline; "background mode with polling" is the planned fix and is not built. The cloud app needs `AZURE_OPENAI_API=responses`.
- **Managed identity for Azure OpenAI.** Built (`AZURE_OPENAI_AUTH=managed_identity`), not switched on; the role assignment is a manual Owner step (ADR 0002 decision 7).
- **Real email.** No provider. Deployed demos run with verification off.
- **Data residency.** France Central while on the Student subscription.
- **Row-level security, Key Vault, a registry cleanup, a stop/start schedule for Postgres.** Follow-ups in ADR 0001 and 0002.
- **Frontend tests exist** (vitest files under `frontend/src`); the README "Not done yet" line that still lists them is stale. (`NEXT.md` is also stale here: it says checkout "Choose" buttons are not disabled for unverified owners, but T-77 fixed that; `frontend/src/pages/app.tsx` disables them when verification is required and the owner is unverified.)
- **Legal.** Privacy and terms pages are DRAFT. Legal review before launch.

## 8. Self-check quiz

1. Where is a session token stored in the database, and why does a stolen database dump not let someone sign in?
2. Which single header must a browser add to every write under `/api`, and which route is exempt and what protects it instead?
3. In the worked example, why does a customer who pays with mock checkout still hit the trial AI cap?
4. Name the three AI refusals that are HTTP 429 and the two that are HTTP 503 for budget reasons.
5. Why does the app refuse to start if `AI_DEADLINE_SECONDS` is only 1 second below `FRONTEND_TIMEOUT_SECONDS`?
6. What do you change, and in which file, when you add a new page to the SPA, and what happens if you forget?
7. With one replica and no Redis, what happens to rate-limit counts when the app restarts, and what would you have to do before running two replicas?
8. What blocks a live Stripe key, and what must you send before that can change?
9. A buyer asks "where is our data?" What is the honest answer today, and why?
10. The deploy workflow succeeded in compiling but created nothing. Name two reasons it might stop before touching Azure.

### Answers

1. In `auth_sessions.token_hash`, the SHA-256 of the random token. The cookie holds the token itself; a hash cannot be turned back into it (`models.py`, `security.py`, ADR 0001 decision 1).
2. `X-Requested-With`. `POST /api/billing/webhook` is exempt; its HMAC signature protects it (`main.py` `CsrfGuard`, `CSRF_EXEMPT`).
3. `LIMITED_PROVIDERS = {"mock","stripe"}` in `routes/notes.py` makes those plans draw on the trial allowance (30,000 a day) until live billing is unlocked. Paying only restores access after the 14-day trial ends.
4. 429: `ai_in_progress`, `ai_cap_reached`, `ai_daily_cap_reached`. 503: `ai_trial_pool_reached`, `ai_budget_reached` (`ai.py` `reserve`). Also `ai_busy` (503) is about concurrency, not budget.
5. `config.py` requires a 2 s margin. A call the browser has abandoned is still billed, so the server would rather not start than let that happen silently.
6. Add the path to `CLIENT_ROUTES` in `backend/app/spa.py` (and the router in `App.tsx`). If you forget, opening or refreshing that page returns 404; a test compares the two lists.
7. They reset (in-memory, per replica). Before two replicas: get approval, provision Azure Cache for Redis, put the `rediss://` URL in a secret and set `RATE_LIMIT_REDIS_URL`, then raise `maxReplicas` (ADR 0002 decision 1).
8. `StripeBilling` raises unless the key starts `sk_test_` or `rk_test_` (`billing.py`). You must send `unlock selling` (confirmed with a button) and a product ADR must then change the code, including removing `"stripe"` from `LIMITED_PROVIDERS`.
9. France Central, because the Student subscription only allows five regions and the UK is not one of them. Hosting for real customers is decided at handover (ADR 0002 "Region (T-61)").
10. Any two of: `STUDIO_AZURE_APPROVED` is not `yes`; the run is not on `main`; the OIDC secrets are missing (these three make the "check" job stop with a notice); or, in the deploy job before Azure sign-in, Trivy found a fixable HIGH or CRITICAL vulnerability (`_starter-deploy.yml`). Later stops, such as AcrPull not yet granted or a failed live-revision read, happen after signing in to Azure but still create nothing (ADR 0002 decision 9).
