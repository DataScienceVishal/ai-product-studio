# Product starter

Every studio product starts as a copy of this folder (board task T-6). It gives you sign-in, tenant
isolation, billing in test mode, AI calls with a per-customer cap, logs, a health check and tests, so a
product only has to build its own core flow.

```
 browser ──► React app (Vite) ──/api──► FastAPI ──► Postgres
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
| Backend unit and API tests (113) | `cd backend && .venv/bin/python -m pytest` | every push (CI `backend`) |
| Migrations match the models | `alembic upgrade head && alembic check` | every push |
| Frontend type check and build | `cd frontend && npm run build` | every push (CI `frontend`) |
| Browser end-to-end core flow | `./scripts/e2e.sh` | pushes to main and manual runs (CI `e2e`) |

Backend tests use a real Postgres at `TEST_DATABASE_URL` (default `postgresql+psycopg://studio:studio@localhost:5432/starter_test`).
The tests prove tenant isolation (and that every private route needs sign-in and every write needs the CSRF
header), session revocation, rate limits, the AI cap under concurrency, the billing provider contract, idempotent
and in-order webhooks, account deletion at the provider, log redaction and the retention purge.

Run the retention purge daily: `python -m app.maintenance purge`. What is stored and for how long is in `DATA.md`.
Security findings and their status are in `SECURITY.md`; the code review is in `reviews/`.

## Configuration

Environment variables only; names are in `.env.example`. In production (`ENV=prod`) the app refuses to start
with the dev webhook secret, with insecure cookies, or with `AI_PROVIDER=azure` and no endpoint. API docs are
hidden in production.

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | Postgres URL (`postgresql+psycopg://...`) |
| `APP_BASE_URL`, `CORS_ORIGINS` | where the frontend lives; only these origins may call the API |
| `COOKIE_SECURE` | `true` everywhere except local http |
| `REQUIRE_EMAIL_VERIFICATION` | `true` (default) makes owners verify their email before inviting or checking out; `false` only where no real email is sent |
| `TRUST_PROXY_HEADERS` | `true` behind Azure Container Apps ingress, so rate limits see the real client IP |
| `AI_PROVIDER` | `fake` (default) or `azure` |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_KEY` | the key is a placeholder in cloud runs; the network secret injects the real one |
| `BILLING_PROVIDER` | `mock` (default) or `stripe` (test keys only; live keys are refused) |
| `BILLING_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY` | leave the secret unset with mock billing (a random one is made); with Stripe, its `whsec_` value and a test key |
| `MOCK_CHECKOUT_ENABLED` | `false` (default); `true` only for demos, where "Pay (test)" grants a plan with trial-sized AI allowances |
| `AI_GLOBAL_DAILY_TOKENS`, `AI_TRIAL_SHARE` | studio-wide AI budget per UTC day (default 500,000), and the share all free trials may use together (0.5) |
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
`.github/workflows/_starter-deploy.yml`); it creates nothing until Vishal approves the costs (Q-5) and the frontend
is served from the API image (T-16). Also open: Redis-backed rate limits before running more than one replica, a real email adapter
(paid, needs approval), and frontend unit tests.
