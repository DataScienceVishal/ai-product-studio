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
| Backend unit and API tests (323 passed, 1 skipped) | `cd backend && .venv/bin/python -m pytest` | every push (CI `backend`) |
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
| `RATE_LIMIT_REDIS_THREADS` | 8 by default (>= 1): size of the limiter's own thread pool for Redis checks, kept apart from the shared worker threads |
| `AI_PROVIDER` | `fake` (default) or `azure` |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY` | the key is a placeholder in cloud runs; the network secret injects the real one |
| `BILLING_PROVIDER` | `mock` (default) or `stripe` (test keys only; live keys are refused) |
| `BILLING_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY` | leave the secret unset with mock billing (a random one is made); with Stripe, its `whsec_` value and a test key |
| `MOCK_CHECKOUT_ENABLED` | `false` (default); `true` only for demos, where "Pay (test)" grants a plan with trial-sized AI allowances |
| `AI_GLOBAL_DAILY_TOKENS`, `AI_TRIAL_SHARE` | studio-wide AI budget per UTC day (default 100,000; the Bicep default too), and the share all free trials may use together (0.5). Size it from the price, see "Sizing the daily AI cap" |
| `AI_PRICE_PER_MILLION_TOKENS` | blended USD price per million tokens of the deployment (default 2.00, the gpt-5-mini assumption); documents what the cap costs, and the Bicep cost guard checks it |
| `AI_REASONING_HEADROOM` | extra output tokens (default 1500) added to each Responses-API call and to its token reservation, so reasoning cannot use up the answer's room; ignored for chat completions |
| `AI_CONCURRENT_CALLS`, `AI_CALLS_PER_TENANT_AT_ONCE` | at most 8 AI calls at once per process, 2 per customer |
| `SIGNUPS_PER_IP_PER_DAY`, `NEW_TRIALS_PER_DAY` | sign-up limits: 20 a day per IP, 200 new trials a day in total |

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
a friendly error. A reasoning model can take about 8 s for one word; the 25 s `AI_DEADLINE_SECONDS` still holds
but is tight for long summaries (raise it together with the frontend's 30 s abort if needed).

### Sizing the daily AI cap

The cap counts tokens, not money, so it is only as safe as the price you assume:

    monthly cost = AI_GLOBAL_DAILY_TOKENS x AI_PRICE_PER_MILLION_TOKENS / 1,000,000 x 30
    AI_GLOBAL_DAILY_TOKENS = monthly budget / (30 x price) x 1,000,000

The deployed budget is $6.10 a month (`state/BUDGET.md`). With a gpt-5-mini style blend of $2.00 per million,
100,000 tokens a day costs $6.00 a month. **A pro deployment needs a much smaller cap.** Assuming (check the current
Azure price list) about $120 per million output tokens, and counting every capped token as output, the same
$6.10 allows only 6.10 / (30 x 120) x 1,000,000, about 1,690 tokens a day: one or two summaries. At 100,000 tokens a
day that deployment could cost up to $360 a month, far over the $80 credit. Change the deployment, set
`aiPricePerMillionTokens` and `aiGlobalDailyTokens` together; `infra/cost-guard.sh` fails the build when
tokens x price x 30 passes $6.10. Raising the budget needs Vishal's approval.

## Azure OpenAI sign-in

`AZURE_OPENAI_AUTH=key` (default) sends the `api-key` header. `managed_identity` sends a bearer token from the
Container Apps identity endpoint instead (optional `AZURE_CLIENT_ID` for a user-assigned identity). The role
assignment is a manual step, see `ADR/0002-azure-deploy.md` decision 7.
