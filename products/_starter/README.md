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
| Backend unit and API tests (see the latest run in CI) | `cd backend && .venv/bin/python -m pytest` | every push (CI `backend`) |
| Migrations match the models | `alembic upgrade head && alembic check` | every push |
| Frontend unit tests (vitest, 203 passed in 7 files) | `cd frontend && npx vitest run` | every push (CI `frontend`) |
| Frontend type check and build | `cd frontend && npm run build` | every push (CI `frontend`) |
| Deploy workflow checks (102 passed) | `bash infra/test-deploy-workflow.sh` | every push, no Azure needed |
| Deploy role checks (67 passed) | `bash infra/test-deploy-role.sh` | every push, no Azure needed |
| DB setup checks (33 passed, needs Postgres) | `bash infra/test-db-setup.sh` | every push |
| Bicep identity check | `bash infra/test-bicep-identities.sh <shared.json> <main.json>` (compiled templates) | CI, needs `az bicep` |
| Browser end-to-end core flow | `./scripts/e2e.sh` | pushes to main and manual runs (CI `e2e`) |

Counts measured on 2026-11-25.

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

Run the retention purge daily: `python -m app.maintenance purge`.

Run `python -m app.maintenance cancels` every few minutes or hourly (T-175): it retries subscription cancels that failed after a new checkout replaced a lapsed subscription (table `pending_cancels`, written in the takeover transaction; also retried on the tenant's next billing event). It prints counts. A failing row is retried with backoff (2^attempts minutes, at most 24 h; the webhook retries only rows with fewer than 3 failures), logged at ERROR, and at its 10th failure once at CRITICAL (`pending cancel needs operator`: cancel it by hand at the provider), then at WARNING. In Azure it runs as the Container Apps job `caj-<slug>-cancels` every 30 minutes (`infra/main.bicep`, `cancelsSchedule`), next to the purge job. What is stored and for how long is in `DATA.md`.
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
| `AI_GLOBAL_DAILY_TOKENS`, `AI_TRIAL_SHARE` | studio-wide AI budget per UTC day (default 98,000; the Bicep default too), and the share all free trials may use together (0.5). Size it from the price, see "Sizing the daily AI cap". On the Responses API `AI_REASONING_HEADROOM` raises the answer part of each summary's reservation from 1,200 to 2,700 tokens (whole call: 1 KB note about 2,504 on chat, 4,004 on Responses); a hold only, the cap still counts settled tokens |
| `AI_PRICE_PER_MILLION_TOKENS`, `AI_MONTHLY_BUDGET_USD` | optional explicit blended USD price per million tokens (unset: looked up by `AZURE_OPENAI_DEPLOYMENT` in the table in `app/aicost.py`; an unknown deployment must set it), and the monthly AI budget (default 6.10). With `AI_PROVIDER=azure` the app refuses to start when `AI_GLOBAL_DAILY_TOKENS` x 31 x price is above the budget. `fake` needs no price. The deploy guard applies the same rule |
| `AI_REASONING_HEADROOM` | extra output tokens (default 1500) added to each Responses-API call and to its token reservation, so reasoning cannot use up the answer's room; ignored for chat completions |
| `AI_CONCURRENT_CALLS`, `AI_CALLS_PER_TENANT_AT_ONCE` | at most 8 AI calls at once per process, 2 per customer |
| `SIGNUPS_PER_IP_PER_DAY`, `NEW_TRIALS_PER_DAY` | sign-up limits: 20 a day per IP, 200 new trials a day in total |

## Billing and the early-customer offer

`BILLING_PROVIDER=mock` is the default (no network). `stripe` uses Stripe test mode only; live keys are refused.

**Stripe webhook setup.** Subscribe the webhook endpoint (`POST /api/billing/webhook`) to exactly these five events:
`checkout.session.completed`, `checkout.session.async_payment_succeeded`, `customer.subscription.created`,
`customer.subscription.updated`, `customer.subscription.deleted`. Without the two `checkout.session.*` events a paying
customer stays on the trial: an `active` subscription event alone never starts or replaces a subscription (T-173 S5,
because delayed payment methods can report `active` before the money arrives).

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

- **Duplicate and replaced subscriptions (which one is kept).** The first working subscription wins, not the one the
  customer paid for last. If a tenant already has an active, in-date subscription and a second paid one starts (two
  checkout tabs), the second is cancelled at the provider and the first is kept, even if the second was a different plan.
  When the old subscription is past_due or lapsed (active but past its period end plus 3 days), a new paid checkout
  takes over instead: the new one is kept and the old one is cancelled at the provider (T-174). If that cancel fails, or
  the old one belongs to another provider (for example a mock one), the app logs "cancel it by hand" with the
  subscription id: an operator must cancel it in the provider dashboard. Failed cancels of a true duplicate answer 503, so
  Stripe redelivers and the cancel is retried. Cancel calls use an 8 s timeout and one retry.
- **One Stripe customer per tenant (T-181).** Checkout sends `customer=<stored id>` when the tenant already has a customer
  at the current provider, so every subscription shares one customer (no `customer_email` is sent then). Every customer a
  billing event reveals is recorded in `billing_customers`. Account deletion deletes all of them at the provider first
  (the stored one with its subscription, then the others); a failure answers 503 `billing_unavailable`, nothing is
  deleted, and the list stays, so a retry finishes the job. A customer already recorded for another tenant is never
  stored for this one.
- **Trial and period end.** A failed first payment (a never-activated subscription going past_due, expired or deleted) does
  not end the free trial early. After a paid checkout the app reads the subscription from Stripe to store its period end;
  if that read fails, the next renewal event sets it.
- **Billing portal:** `POST /api/billing/portal` (owner only) returns a Stripe Customer Portal URL for the tenant's customer
  (409 `no_billing_customer` if there is none for the current provider). The return URL comes from `APP_BASE_URL`, never
  from request headers. A past_due tenant is refused a new checkout and pointed at the portal.
- **Stripe portal setup:** Stripe refuses `POST /v1/billing_portal/sessions` (the app then shows 502 `billing_rejected`)
  until a default Customer Portal configuration is saved in the Stripe dashboard (Settings, Billing, Customer portal).
  Test mode and live mode are configured separately, so save it in both.
- **Stripe dunning setting:** in the Stripe dashboard (Billing, Subscriptions and emails, "Manage failed payments") set the
  action after the last retry to **cancel the subscription**, not "mark the subscription as unpaid". Stripe `unpaid` maps to
  `past_due` here and never sends `customer.subscription.deleted`, so a tenant would stay blocked from checkout until
  someone acts. With "cancel", the deleted event moves them to `canceled` and they can buy again by themselves.

## Making a product from it

1. Copy the folder to `products/<slug>/` and the workflow to `.github/workflows/<slug>-ci.yml`, replacing
   `_starter` in the paths.
2. Replace `Note` (model, routes, page) with the product's core objects. Keep `_scoped()`: every query filters by
   `tenant_id`, and the tenancy tests are copied for each new object.
3. Set the plans and prices from the product's SPEC.md in `app/billing.py`.
4. Add an Alembic migration for every model change: `alembic revision --autogenerate -m "..."`.

## Not done yet

See `NEXT.md`. The Azure deploy is designed in `ADR/0002-azure-deploy.md` (Bicep in `infra/`, manual workflow
`.github/workflows/_starter-deploy.yml`); it creates nothing until Vishal approves the costs (Q-5). Also open:
provisioning Azure Cache for Redis (costs money, ask first; the code is built and tested, see `RATE_LIMIT_REDIS_URL`)
before running more than one replica, and a real email adapter (paid, needs approval). Frontend unit tests are done (vitest).

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

    monthly cost = AI_GLOBAL_DAILY_TOKENS x AI_PRICE_PER_MILLION_TOKENS / 1,000,000 x 31
    AI_GLOBAL_DAILY_TOKENS = monthly budget / (31 x price) x 1,000,000

The AI budget is $6.10 a month (`state/BUDGET.md`'s "at most 6.10", which Vishal approved; checked over a 31-day month). With a
gpt-5-mini style blend of $2.00 per million, the default 98,000 tokens a day costs at most $6.08 a month. **A pro deployment needs a much smaller cap.** gpt-5.4-pro lists at
$180 per million output tokens ($30 input; OpenAI's model page and Microsoft's Foundry launch post, checked 2026-11-24).
Counting every capped token as output, $6.10 allows only 6.10 / (31 x 180) x 1,000,000, about 1,093 tokens a day. The smallest
reservation for one call is 1,504 tokens (3,004 on the Responses API), so **gpt-5.4-pro at the default budget means AI is
effectively off**: not one call fits. The real choices are a cheaper deployment, or a bigger budget from Vishal. At 98,000
tokens a day that deployment could cost up to $547 a month, far over the $80 credit. **Since T-91 this can't happen by accident:**
the price comes from the deployment that is actually deployed (`MODEL_PRICES_PER_MILLION` in `backend/app/aicost.py`, estimates
dated 2026-11-25; gpt-5.4-pro is 180, the output price). The app (`AI_PROVIDER=azure`) refuses to start, and `infra/cost-guard.sh`
fails the deploy workflow's check job, when `AI_GLOBAL_DAILY_TOKENS` x 31 x price is above `AI_MONTHLY_BUDGET_USD` (6.10). A
deployment name not in the table needs `AI_PRICE_PER_MILLION_TOKENS` (app) or the repository variable of the same name (workflow);
an explicit price can only raise a table price, never lower it (a lower price needs a reviewed change to the table). Error messages
never print the deployment name or any setting value. Those checks price the deployment *name*, which is free text, so at
runtime the app also compares the model each reply reports (`model`, matched to the table by exact name, one date suffix
ignored) with the price the startup check used (T-100 M1). A dearer model, or an unknown or missing one, logs one error and switches AI off: the call that revealed
it is kept and recorded, later calls get 503 `ai_budget_reached`. An explicit `AI_PRICE_PER_MILLION_TOKENS` only vouches for
unknown models when the deployment name is NOT in the table (T-163); for a table deployment the table decides. The trip is
saved in the database (`ai_guard_trips`, keyed by a hash of endpoint, deployment and checked price, no secrets), so a cold
start or another replica stays off too. Changing the endpoint, deployment or price clears it by itself; otherwise
`DELETE FROM ai_guard_trips` and restart. If the table cannot be read the call is refused (fail closed). A cheaper model is fine.

**Calls per day.** A call reserves its upper bound before it runs, and `settle()` replaces the reservation with the
tokens actually used. The reservation is `system prompt (287 bytes) + note bytes + 17 + 1,200 answer budget`, plus
`AI_REASONING_HEADROOM` (1,500) only on the Responses API (Bicep `auto` picks chat unless the endpoint ends in
`/openai/v1/responses`). So the cap is not a daily call count: a call is refused once less than its reservation is
left, and `cap / reservation` is a floor (calls that all run at once, or each use their full budget). Short answers
leave room for more.

Worked example (Responses API, 1 KB note): reservation about 287 + 1,000 + 17 + 2,700 = 4,004, so 98,000 admits at
least 24 such calls (98,000 / 4,004). A 20,000-character note reserves 23k to 83k (multibyte text), which can exceed the 30k trial cap on
its own. Until `unlock selling`, `LIMITED_PROVIDERS` (mock, Stripe test) makes every tenant draw on the trial half
(`AI_TRIAL_SHARE` 0.5, 49,000 of 98,000). Size the cap from the reservation of your typical note, then check the cost
with the formula above.

**The cap formula is unaffected by the headroom.** Caps count settled tokens (what the call actually used), and the
reservation is only a hold placed before the call and replaced by `settle()`. The headroom (answer part 1,200 to 2,700 on
the Responses API) changes how many calls can be held at once, not what the cap costs: the monthly ceiling is still
`AI_GLOBAL_DAILY_TOKENS` x 31 x price. For scale, an empty note reserves 287 + 17 + 2,700 = 3,004 on the Responses API
(1,504 on chat), so 98,000 holds at most 32 such calls at once (98,000 / 3,004 = 32.6) instead of 65 (98,000 / 1,504 = 65.2).

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
