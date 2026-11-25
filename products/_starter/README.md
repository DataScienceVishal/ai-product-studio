# Product starter

Every studio product starts as a copy of this folder (board task T-6). It gives you sign-in, tenant
isolation, billing in test mode, AI calls with a per-customer cap, logs, a health check and tests, so a
product only has to build its own core flow.

```
 browser ──► React app (Vite in dev; served by FastAPI in the image) ──/api──► FastAPI ──► Postgres
                                          │  ├─ AI adapter ──► Azure OpenAI (or FakeAI in dev/tests)
                                          │  └─ billing adapter ──► Mock (default) or Stripe test mode
                                          └─ JSON logs with request ids → stdout
```

Decisions and their reasons are in `ADR/0001-starter-foundations.md`.

## Run it locally

Needs Python 3.12, Node 22 and Postgres 16.

```bash
cd products/_starter/backend
uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -r requirements-dev.txt
createdb starter_dev   # or use any Postgres URL in DATABASE_URL
DATABASE_URL=postgresql+psycopg://studio:studio@localhost:5432/starter_dev .venv/bin/alembic upgrade head
COOKIE_SECURE=false .venv/bin/uvicorn app.main:app --reload
```

```bash
cd products/_starter/frontend && npm ci && npm run dev   # http://localhost:5173, proxies /api to :8000
```

## Tests

| What | Command | Where it runs |
|---|---|---|
| Backend unit and API tests (541 passed, 1 skipped) | `cd backend && .venv/bin/python -m pytest` | every push (CI `backend`) |
| Migrations match the models | `alembic upgrade head && alembic check` | every push |
| Frontend type check and build | `cd frontend && npm run build` | every push (CI `frontend`) |
| Browser end-to-end core flow | `./scripts/e2e.sh` | pushes to main and manual runs (CI `e2e`) |

Backend tests use a real Postgres at `TEST_DATABASE_URL` (default `postgresql+psycopg://studio:studio@localhost:5432/starter_test`).
Each pytest run creates its own database `<db>_t<epoch>_<pid>_<rand>` (through the server's `postgres` database, so the
user needs the CREATE DATABASE right) and drops it at the end, even when tests fail, so several runs can share one
Postgres at the same time. SIGTERM still drops it; SIGKILL cannot, so databases left by killed runs (marked with the comment
`starter-pytest-ephemeral`, owned by the same user) are dropped by the next run once over 6 hours old. The base name
must be letters, digits and underscores (max 36). By hand, only drop names you can see are yours: `psql .../postgres -c 'DROP DATABASE "<name>" WITH (FORCE)'`. `TEST_DATABASE_SHARED=1` uses the URL as-is
(one shared database, reset at start; do not run two at once). CI's Postgres user is the superuser, so it needs no opt-out.
The tests prove tenant isolation (and that every private route needs sign-in and every write needs the CSRF
header), session revocation, rate limits, the AI cap under concurrency, the billing provider contract, idempotent
and in-order webhooks, account deletion at the provider, log redaction and the retention purge.

Run the retention purge daily: `python -m app.maintenance purge`. What is stored and for how long is in `DATA.md`.
Security findings and their status are in `SECURITY.md`; the code review is in `reviews/`.

## One image, one origin

`Dockerfile` (build context `products/_starter`) builds the frontend with Node, then copies `dist/` into the
Python runtime image: `docker build -t starter -f Dockerfile .` from this folder. FastAPI serves it, so the
browser sees the app and `/api` on one origin (ADR 0002, decision 2):

- `/assets/*` is Vite's hashed output, cached for a year (`immutable`).
- A GET or HEAD for a known client route (`/`, `/login`, `/verify-email`, `/reset-password`, `/accept-invite`,
  `/billing/done`, ...) gets `index.html` with 200, `Cache-Control: no-cache` and a CSP of `script-src 'self'` (no
  inline script or style). Any other unknown path gets the same HTML with status 404, so crawlers and monitors
  see a real 404. HEAD returns the same headers as GET (including `Content-Length`) with no body.
  **Every new frontend page must be added to `CLIENT_ROUTES` in `backend/app/spa.py`**, or it will answer 404 when
  opened directly or refreshed. `test_client_routes_match_the_frontend_router` fails if the two lists differ.
- `/assets` and `/assets/` with no file are a 404 (no redirect).
- `/api/*`, `/livez` and `/healthz` are unchanged; an unknown `/api` path is still a JSON 404.
- It is on only when `FRONTEND_DIST` names a folder with `index.html` (the image sets `/app/static`). Without it
  the app is API-only, which is how dev, the tests and `scripts/e2e.sh` run (Vite serves the frontend and proxies `/api`).

The old `backend/Dockerfile` is gone; nothing else used it.

## Configuration

Environment variables only; names are in `.env.example`. The app refuses to start with an empty or short
webhook secret, a non-`whsec_` secret with Stripe, or `*` in CORS_ORIGINS. In production (`ENV=prod`) it also
needs an https APP_BASE_URL that isn't localhost, COOKIE_SECURE and TRUST_PROXY_HEADERS true, and an
AZURE_OPENAI_ENDPOINT with AI_PROVIDER=azure. API docs are hidden in production.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | Postgres URL (`postgresql+psycopg://...`) |
| `APP_BASE_URL`, `CORS_ORIGINS` | where the frontend lives; only these origins may call the API |
| `FRONTEND_DIST` | folder with the built frontend; empty (default) means API-only. The image sets `/app/static` |
| `COOKIE_SECURE` | `true` everywhere except local http. When true the session cookie is `__Host-session` (Secure, `Path=/`, no Domain); when false it is plain `session` |
| `REQUIRE_EMAIL_VERIFICATION` | `true` (default) makes owners verify their email before inviting or checking out; `false` only where no real email is sent |
| `TRUST_PROXY_HEADERS` | `true` behind Azure Container Apps ingress, so rate limits see the real client IP |
| `RATE_LIMIT_REDIS_URL` | empty (default) keeps rate limits in memory, per replica (fine for one replica). `redis://` or `rediss://` (TLS) shares them across replicas; it holds a password, so treat it as a secret. If Redis is unreachable (200 ms timeout) the app logs a rate-limited warning and uses in-memory limits, never a 500. Azure Cache for Redis is not provisioned yet (ADR 0002) |
| `RATE_LIMIT_REDIS_THREADS` | 8 by default (>= 1): size of the limiter's own thread pool for Redis checks, kept apart from the shared worker threads. Only matters with `RATE_LIMIT_REDIS_URL` (the in-memory limiter has no pool) |
| `RATE_LIMIT_REDIS_QUEUE_TIMEOUT` | 1.0 by default (seconds, > 0, <= 30): longest a login-style gate waits for a free Redis pool thread. On timeout the in-memory check answers at once and it counts as a Redis failure (breaker trips). Only matters with `RATE_LIMIT_REDIS_URL` |
| `AI_PROVIDER` | `fake` (default) or `azure` |
| `AZURE_OPENAI_REASONING_EFFORT` | empty (not sent) | optional `low`, `medium`, `high` or `xhigh`; gpt-5.4-pro rejects `low`, so `medium` is its cheapest (see Azure OpenAI API) |
| `FRONTEND_TIMEOUT_SECONDS` | `30` | how long the browser waits before aborting; served at `/api/config`, max 600 |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY` | the key is a placeholder in cloud runs; the network secret injects the real one |
| `BILLING_PROVIDER` | `mock` (default) or `stripe` (test keys only; live keys are refused) |
| `BILLING_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY` | leave the secret unset with mock billing (a random one is made); with Stripe, its `whsec_` value and a test key |
| `MOCK_CHECKOUT_ENABLED` | `false` (default); `true` only for demos, where "Pay (test)" grants a plan with trial-sized AI allowances |
| `AI_GLOBAL_DAILY_TOKENS`, `AI_TRIAL_SHARE` | studio-wide AI budget per UTC day (default 100,000; the Bicep default too), and the share all free trials may use together (0.5). Size it from the price, see "Sizing the daily AI cap" |
| `AI_PRICE_PER_MILLION_TOKENS` | blended USD price per million tokens of the deployment (default 2.00, the gpt-5-mini assumption); documents what the cap costs, and the Bicep cost guard checks it |
| `AI_REASONING_HEADROOM` | extra output tokens (default 1500) added to each Responses-API call and to its token reservation, so reasoning cannot use up the answer's room; ignored for chat completions |
| `AI_CONCURRENT_CALLS`, `AI_CALLS_PER_TENANT_AT_ONCE` | at most 8 AI calls at once per process, 2 per customer |
| `SIGNUPS_PER_IP_PER_DAY`, `NEW_TRIALS_PER_DAY` | sign-up limits: 20 a day per IP, 200 new trials a day in total |

## Billing and the early-customer offer

`BILLING_PROVIDER=mock` is the default (no network). `stripe` uses Stripe test mode only; live keys are refused.

- The offer code a customer enters in the app is checked against `OFFERS` in `app/billing.py` (EARLY50: 50% off for 3 months).
- With Stripe, the app applies it **server-side**: it creates the coupon (`POST /v1/coupons`) and sends
  `discounts[0][coupon]` when it creates the Checkout Session. The customer does not re-type anything on Stripe's page.
- The coupon id comes from the offer's terms (`studio-early50-50pc-3m-v1`), so changing the percent or months makes a new
  coupon (Stripe coupons cannot be edited). Creation uses an `Idempotency-Key`, and "resource_already_exists" counts as
  success. In that case the coupon is read back once and must match the offer's terms, or checkout fails with
  `billing_rejected` rather than give the wrong discount. Ensured ids are cached per process.
- **Decision (T-15): `allow_promotion_codes` is no longer sent.** Stripe rejects it together with `discounts`, and it would
  let customers type promotion codes the app never validated or recorded. Only app-validated offers exist. If you ever want
  promotion codes, add them as a deliberate feature.

## Making a product from it

1. Copy the folder to `products/<slug>/` and the workflow to `.github/workflows/<slug>-ci.yml`, replacing
   `_starter` in the paths.
2. Replace `Note` (model, routes, page) with the product's core objects. Keep `_scoped()`: every query filters by
   `tenant_id`, and the tenancy tests are copied for each new object.
3. Set the plans and prices from the product's SPEC.md in `app/billing.py`.
4. Add an Alembic migration for every model change: `alembic revision --autogenerate -m "..."`.

## Not done yet

See `NEXT.md`. The Azure deploy is designed in `ADR/0002-azure-deploy.md` (Bicep in `infra/`, manual workflow
`.github/workflows/_starter-deploy.yml`); it creates nothing until Vishal approves the costs (Q-5). Also open: provisioning Azure Cache for Redis (costs money, ask first; the code is ready, see `RATE_LIMIT_REDIS_URL`) before running more than one replica, a real email adapter
(paid, needs approval), and frontend unit tests.

## Azure OpenAI API

`AZURE_OPENAI_API` is `auto` (default), `responses` or `chat`. `auto` uses the v1 Responses API
(`/openai/v1/responses`) when `AZURE_OPENAI_ENDPOINT` ends in `/openai/v1/responses`, otherwise chat completions.
The studio's reasoning deployment refuses chat (HTTP 400), so set `responses` or give that endpoint form. The
endpoint may be the resource root or end in `/openai/v1`, `/openai/v1/responses` or `/openai/v1/chat/completions`.
Reasoning tokens count inside the output budget, and an `incomplete` answer with no text is billed and shown as
a friendly error. A reasoning model can take about 8 s for one word.

**Reasoning effort.** `AZURE_OPENAI_REASONING_EFFORT` (`low`, `medium`, `high` or `xhigh`; empty by default; `minimal` and `none`
are left out on purpose, since only some models accept them: add them to `REASONING_EFFORTS` in `config.py`, the single
list `ai.py` also uses, when a deployment needs one) is sent as `reasoning: {"effort": ...}` on the Responses path only.
A bad value stops the app at startup. The studio's gpt-5.4-pro deployment rejects `low` (HTTP 400, "Supported values
are: 'medium', 'high', and 'xhigh'"), so `medium` is its cheapest setting; other deployments accept `low`. An HTTP 400 from the
model on this field is a config error: the app does not retry it and shows `ai_rejected` (502) with a generic message; the
status is in the logs. Fix the value rather than retrying.

**Latency versus the browser's abort.** The browser aborts after `FRONTEND_TIMEOUT_SECONDS` (default 30). The
backend serves that number at `GET /api/config` and the SPA reads it once at startup (falling back to 30 s if the
call fails), so there is one source and no build variable. We chose this over a Docker build argument because an
image then needs no rebuild to change it, and the startup check guards the value the browser really uses. The server
refuses to start if `AI_DEADLINE_SECONDS` (default 25) is not at least 2 s below it. We refuse rather than warn
because a call the browser has abandoned is still billed, and at pro prices a warning in a log nobody reads is too
easy to miss. `AI_TIMEOUT_SECONDS`, `AI_DEADLINE_SECONDS` and `FRONTEND_TIMEOUT_SECONDS` must be finite, above 0
and at most 600 (nan and inf are refused). To allow a longer AI call, raise the deadline and the frontend timeout
together (for example deadline 55, timeout 60). If a pro model's
latency still exceeds the deadline, the route is the Responses API's background mode with polling (start the
call, return at once, poll for the result). It is not built here.

### Sizing the daily AI cap

The cap counts tokens, not money, so it is only as safe as the price you assume:

    monthly cost = AI_GLOBAL_DAILY_TOKENS x AI_PRICE_PER_MILLION_TOKENS / 1,000,000 x 30
    AI_GLOBAL_DAILY_TOKENS = monthly budget / (30 x price) x 1,000,000

The deployed budget is $6.10 a month (`state/BUDGET.md`). With a gpt-5-mini style blend of $2.00 per million,
100,000 tokens a day costs $6.00 a month. **A pro deployment needs a much smaller cap.** gpt-5.4-pro lists at $180 per
million output tokens ($30 input; OpenAI's model page and Microsoft's Foundry launch post, checked 2026-11-24).
Counting every capped token as output, the same $6.10 allows only 6.10 / (30 x 180) x 1,000,000, about 1,130 tokens
a day: one summary. At 100,000 tokens a day that deployment could cost up to $540 a month, far over the $80 credit. Change the deployment, set
`aiPricePerMillionTokens` and `aiGlobalDailyTokens` together; `infra/cost-guard.sh` fails the build when
tokens x price x 30 passes $6.10. Raising the budget needs Vishal's approval.

**Calls per day.** A call reserves its upper bound before it runs, and `settle()` replaces the reservation with the
tokens actually used. The reservation is `system prompt (287 bytes) + note bytes + 17 + 1,200 answer budget`, plus
`AI_REASONING_HEADROOM` (1,500) only on the Responses API (Bicep `auto` picks chat unless the endpoint ends in
`/openai/v1/responses`). So the cap is not a daily call count: a call is refused once less than its reservation is
left, and `cap / reservation` is a floor (calls that all run at once, or each use their full budget). Short answers
leave room for more.
Worked example (Responses API, 1 KB note): reservation about 287 + 1,000 + 17 + 2,700 = 4,004, so 100,000 admits at
least 24 such calls (100,000 / 4,004). A 20,000-character note reserves 23k to 83k (multibyte text), which can exceed the 30k trial cap on
its own. Until `unlock selling`, `LIMITED_PROVIDERS` (mock, Stripe test) makes every tenant draw on the trial half
(`AI_TRIAL_SHARE` 0.5, 50,000 of 100,000). Size the cap from the reservation of your typical note, then check the cost
with the formula above.

## Azure OpenAI sign-in

`AZURE_OPENAI_AUTH=key` (default) sends the `api-key` header. `managed_identity` sends a bearer token from the
Container Apps identity endpoint instead (optional `AZURE_CLIENT_ID` for a user-assigned identity). The role
assignment is a manual step, see `ADR/0002-azure-deploy.md` decision 7.

## Entra ID database sign-in

`DB_AUTH=password` (the app's default, for local development and CI) uses the password in `DATABASE_URL`. Azure deploys use `entra`: the server has password sign-in disabled, and every release checks that. `DB_AUTH=entra` signs in to Postgres with the app's
managed identity instead, with no password anywhere:

- `DATABASE_URL=postgresql+psycopg://<entra-role-name>@<host>:5432/<db>?sslmode=verify-full`: host, database and the
  Entra role as user (for example the identity's name). `verify-full` also needs `sslrootcert`: libpq looks for
  `~/.postgresql/root.crt` unless told otherwise, and the image has no such file, so without it the connection fails.
  The deploy appends `sslrootcert=/etc/ssl/certs/ca-certificates.crt` (the CA bundle path); add the same to a URL you
  write by hand. A `password` or `passfile` in the query is refused too. The app refuses to start if the URL has a
  password or `sslmode` is not `verify-full` (ADR 0002). `AZURE_CLIENT_ID` picks a user-assigned identity.
- On every new pooled connection the app fetches a token for `https://ossrdbms-aad.database.windows.net` from the
  Container Apps identity endpoint and passes it as the password (`app/dbauth.py`). Tokens are cached until 2 minutes
  before expiry, so a burst of connections shares one fetch. Connections are recycled after 45 minutes; Postgres checks
  the token only when connecting, so an open connection outlives its token.
- The Alembic migration job and `python -m app.maintenance purge` use the same setting and the same sign-in.
- If the token cannot be fetched the connection fails and an error is logged (class only, never the token or header).

The deploy must create the Entra role in the server's default `postgres` database with
`SELECT * FROM pgaadauth_create_principal('<identity name>', false, false);` and grant it rights on the app database.
Infra for this is designed in ADR 0003. Tests cannot reach a real Entra server, so they assert on the connection
parameters (`backend/tests/test_db_entra.py`).
