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
7. **Billing behind a provider interface.** `MockBilling` is the default and signs its webhooks the same way
   Stripe does. `StripeBilling` refuses any key that isn't a test-mode key. Webhooks are idempotent (event ids
   are stored). Live payments stay locked until `unlock selling`.
8. **Rate limiting is in-process** (sliding window). With more than one replica, the real limit multiplies.
   Move it to Redis before scaling out.
9. **Email is an adapter.** Real sending is a paid service and needs approval. The in-memory outbox never logs
   addresses or bodies, because reset links are secrets.
10. **Logs are JSON lines with request ids and tenant ids.** They never contain emails, names or content.
    Sensitive-looking extra fields are redacted as a safety net.

## Consequences

- One small Postgres server can host every product (one database each), which keeps Azure costs down.
- A product copying the starter replaces `Note` with its own core objects and keeps the scoped-query pattern.
- Known gaps, tracked in NEXT.md: invitations and member roles, email verification, Redis rate limiting.
