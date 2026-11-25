# ADR 0001: Starter foundations

- Status: accepted for the starter (2026-11-23, T-6). Products inherit it; change it only with a new ADR.

## Context

Every studio product needs the same plumbing: sign-in, tenant isolation, billing in test mode, AI calls with
cost control, logs and health checks. It must run within $80 of Azure credit in total and be easy to hand over.

## Decisions

1. **Sessions are opaque random tokens in an HttpOnly, Secure, SameSite=Lax cookie.** The database stores only
   their SHA-256. A stolen database dump gives no working sessions. Logout and password reset revoke sessions
   server-side, which JWTs can't do without extra machinery.
2. **CSRF: cookie-authenticated writes need an `X-Requested-With` header.** Browsers can't add a custom header
   cross-site without a CORS preflight, and CORS allows only configured origins. The webhook is exempt and is
   protected by its signature instead.
3. **Passwords: argon2id** (argon2-cffi defaults), 10 to 128 characters. Unknown emails are verified against a
   dummy hash, so a miss takes as long as a wrong password.
4. **Tenancy: shared tables with `tenant_id` on every customer-owned row.** Every query goes through a scoped
   helper (see `routes/notes.py`). A missing row and another tenant's row both return 404. Tests prove it.
   Postgres row-level security would be a second layer; it isn't used yet, to keep the starter simple.
5. **Sync SQLAlchemy 2 with psycopg 3 and sync endpoints.** FastAPI runs them in its threadpool. This is
   simpler to reason about than async ORM code, and fast enough for small-business traffic. Every connection
   gets a 5-second connect timeout and a 10-second statement timeout.
6. **AI behind a provider interface.** `FakeAI` is used in dev and tests (no cost). `AzureOpenAI` uses the v1
   chat completions API with retries and friendly errors. Every call is recorded per tenant, and a monthly
   token cap per plan is checked before each call.
   *Update 2026-11-25:* `AzureOpenAI` now uses the v1 Responses API (`/openai/v1/responses`) for the studio's
   reasoning deployment, which refuses chat completions. Chat completions is still supported (`AZURE_OPENAI_API`
   is `auto`, `responses` or `chat`). Caps are now layered: a monthly token cap per plan, a daily cap for trials,
   a shared daily pool for all trials, and a studio-wide daily cap on all tenants. At most a few calls per tenant
   can be in flight at once (`ai_calls_per_tenant_at_once`). Free trials and the `mock` and `stripe` billing
   providers are all treated as limited (`LIMITED_PROVIDERS` in `routes/notes.py`).
7. **Billing behind a provider interface.** `MockBilling` is the default and signs its webhooks the same way
   Stripe does. `StripeBilling` refuses any key that isn't a test-mode key. Webhooks are idempotent (event ids
   are stored). Live payments stay locked until `unlock selling`.
8. **Rate limiting is in-process** (sliding window). With more than one replica, the real limit multiplies.
   Move it to Redis before scaling out.
   *Update 2026-11-25:* the Redis limiter is built (`RATE_LIMIT_REDIS_URL`, `app/ratelimit.py`). With the variable
   empty the limits stay in memory, so one replica is still the rule until Azure Cache for Redis is provisioned
   (it costs money, so it needs approval). If Redis is down the app falls back to in-memory limits, not a 500.
9. **Email is an adapter.** Real sending is a paid service and needs approval. The in-memory outbox never logs
   addresses or bodies, because reset links are secrets.
10. **Logs are JSON lines with request ids and tenant ids.** They never contain emails, names or content.
    SQLAlchemy's parameter dumps are off (`hide_parameters`), database error messages are reduced to their
    SQLSTATE code, and sensitive extra fields are redacted by whole key name.
11. **No transaction is held across a slow external call.** `deps.current` commits after loading the user. The
    AI flow reserves budget under Postgres advisory locks, releases the connection, calls the model and settles
    afterwards. Without this, a few slow AI calls exhaust the pool for every tenant.
12. **CSRF is global.** One ASGI guard covers every write under `/api`, with one listed exemption (the provider
    webhook). A test sweeps the route table, so a new router can't forget it.

## Consequences

- One small Postgres server can host every product (one database each), which keeps Azure costs down.
- A product copying the starter replaces `Note` with its own core objects and keeps the scoped-query pattern.
- Known gaps, tracked in NEXT.md: a real email adapter (needs approval) and the Azure Cache for Redis resource before
  scaling out (*update 2026-11-25:* the Redis limiter code is built; only the paid resource is missing).
- The sign-up and invitation forms reveal whether an email already has an account. That is accepted for a B2B
  sign-up form and is rate-limited; the password-reset form does not reveal it.
