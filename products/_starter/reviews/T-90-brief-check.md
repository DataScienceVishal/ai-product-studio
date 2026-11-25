# T-90 brief check: `products/_starter/BRIEF.md`

Checker: reviewer. Date: 2026-11-25. Checked against `main` at `da45579` (brief draft commit).
Scope: accuracy only, not style. Every route, env var, default, table name, number, path and ADR reference in
the brief was checked against the code, ADRs, README, SECURITY.md, DATA.md, `.github/workflows/_starter-deploy.yml`,
`state/BOARD.md` and `state/BUDGET.md`.

## Verdict: PASS (after 10 checker corrections)

The brief is accurate. I found 10 inaccurate or stale claims. Each was a small wording or number problem, and I
fixed each one in BRIEF.md (listed below). Nothing else needed changing.

- **Test counts are quoted, not re-run.** This sandbox has no Postgres and no pytest, so I could not run the backend
  suite. The brief now gives both the README figure (561) and the newer board figure (566 backend, 182 vitest,
  T-86 merge note).
- **Every cited file path exists.** That includes `tests/e2e/core_flow.cjs`, `scripts/e2e.sh`,
  `infra/{main,shared}.bicep(param)`, `infra/cost-guard.sh`, `infra/smoke.sh`, `infra/check-auth-config.sh`,
  `backend/tests/test_db_entra.py`, `frontend/src/api.ts`, `frontend/src/pages/legal.tsx`, ADR 0001, 0002 and 0003,
  migrations 0001 to 0007, NEXT.md, DATA.md and SECURITY.md.
- **Every ADR section the brief cites exists.** That includes ADR 0002 decisions 1, 2, 4, 6 to 11, "Region (T-61)",
  "What a deployed demo can do", "Monthly cost" and the failure table, plus ADR 0001 decisions 1, 2, 4, 5, 7, 11 and 12
  and its "Consequences".

## Inaccurate claims (all fixed in BRIEF.md)

| # | Brief line | Brief said | Correct fact | Evidence |
|---|---|---|---|---|
| 1 | 18 (diagram) | Middleware order `CsrfGuard -> CORS -> BodyLimit -> RequestContext` | Request order is `RequestContext -> CORS -> CsrfGuard -> BodyLimit` (Starlette's last `add_middleware` is outermost) | `backend/app/main.py:192-197` ("# outermost" on RequestContext) |
| 2 | 59 | "the README says 561 backend tests passed" (offered as the current count) | The README figure is stale. The board's latest merge note records 566 backend tests and 182 vitest tests passing | `README.md:36`; `state/BOARD.md` T-86 entry ("vitest 182, build ok, backend 566 pass") |
| 3 | 71 | The worked example "is the same path the browser test walks" | The e2e test covers sign-up, note, summary, EARLY50 and Pay (test). It runs with verification off and never simulates the trial ending, so steps 2 and 5 aren't part of it | `tests/e2e/core_flow.cjs:16-45`; `scripts/e2e.sh:37` |
| 4 | 107 | "SECURITY.md section 2: 29 of 29 live cross-tenant checks passed" | 29/29 was the first gate. Re-test 3 (the latest) ran 48/48 | `SECURITY.md:25`, `:591`, `:911` |
| 5 | 118 | `POST /api/billing/portal` (owner) | `verified_owner`: an owner who also needs a verified email when verification is required | `backend/app/routes/billing.py:65`; `backend/app/deps.py:52-56` |
| 6 | 174 | "Every response gets ... `Cache-Control: no-store`" | Non-SPA responses get `no-store`. The SPA `index.html` gets `no-cache`, and `/assets` files get `public, max-age=31536000, immutable` (the SPA's own headers override) | `backend/app/main.py:26-31,121`; `backend/app/spa.py:8,36`; `README.md:59-64` |
| 7 | 198 | `DATA.md` says "UK region" "as a goal" | DATA.md states it as a fact, not a goal, and so does the customer-facing DRAFT privacy page. Both are out of date | `DATA.md:38`; `frontend/src/pages/legal.tsx:19`; `infra/main.bicepparam:7` |
| 8 | 200 | "The call sends `store=false`" (unconditional) | `store: False` is sent only on the Responses API path. The chat-completions payload has no `store` field | `backend/app/ai.py:282-291` |
| 9 | 245 | "checkout 'Choose' buttons are not disabled for unverified owners ... (`NEXT.md`, T-76)" | Fixed in T-77 (S5). `NEXT.md:7` is stale | `frontend/src/pages/app.tsx:231,279-280` (`disabled={!isOwner \|\| blocked}`); `state/BOARD.md` T-77 |
| 10 | 272 (quiz answer 10) | AcrPull and the live-revision read listed as reasons the workflow "stop[s] before touching Azure" | Only the three gate conditions (check job) and the Trivy scan stop it before Azure sign-in. The AcrPull check and the live-revision read happen after sign-in, though they still create nothing | `.github/workflows/_starter-deploy.yml:117-136` (gate), `:163-176` (Trivy), `:181-223` (sign-in, then AcrPull) |

### Spot-checked and correct (sample)

- **Signup.** Signup writes rows to `tenants`, `users` (owner), `subscriptions` (trial/trialing, +`trial_days`=14) and
  `auth_sessions` (SHA-256), then sends a verification (`routes/auth.py:150-177`, `config.py:107`).
- **Session cookie.** The cookie is `__Host-session` or `session`, HttpOnly, SameSite=Lax, 7 days (`routes/auth.py:86-87`,
  `deps.py:17-20`, `config.py:41`).
- **Password hashing.** `MIN_PASSWORD` is 10 and `MAX_PASSWORD` is 128. `HASH_SLOTS` is 2 and `HASH_WAIT_SECONDS` is 3.
  A busy hasher returns 503 `busy` with `Retry-After: 5` (`security.py:18-42`).
- **AI limits.** 2 calls in flight per tenant, 8 per process with a 2 s wait (`ai.py:110`). 20 requests a minute per
  tenant. Caps are 100k/500k/2M tokens a month, with 30k a day on the trial. The trial share is 0.5 of a 100k global cap
  (`config.py:84-96`, `billing.py:52-56`, `ai.py:501-511`).
- **Token reservation.** The answer budget is 1,200 tokens (`MAX_SUMMARY_TOKENS`), with 1,500 headroom on the
  Responses API. A 1 KB note reserves 4,004 tokens, so the global cap admits at least 24 calls (`notes.py:27`,
  `config.py:87`, `README.md:197`).
- **Timeouts.** 20 s per attempt and 25 s per call, 1 retry. The browser waits 30 s, with a 2 s margin enforced at
  startup (`config.py:16,74-84,117-121`).
- **AI cost check.** cost-guard's limit is $6.10. At the defaults (100k tokens a day at $2.00 per million) the cost is
  $6.00 a month. On gpt-5.4-pro at $180 per million output tokens, the cap would need to be about 1,130 tokens a day,
  and 100k a day would cost up to $540 a month (`infra/cost-guard.sh:18,43-61`, `README.md:184-188`).
- **Billing.** Plans are 2900 and 7900 pence, and EARLY50 gives 50% off for 3 months. The Stripe coupon id is
  `studio-early50-50pc-3m-v1`. Stripe accepts only `sk_test_`/`rk_test_` keys. Webhooks allow 300 s of clock skew,
  `GRACE` is 3 days, the webhook body limit is 256,000 bytes, and a past-due tenant gets 409 `subscription_past_due`
  (`billing.py`, `routes/billing.py:47,134`).
- **Mock checkout.** At most 1000 sessions are kept. The mock endpoint returns 404 unless the provider is mock and
  `MOCK_CHECKOUT_ENABLED` is on. A mock period lasts 30 days (`billing.py:148,171`, `routes/billing.py:173-186`).
- **Purge job.** Sessions are removed at expiry, reset and verification rows after 7 days, invitations after 30, and
  billing events and `ai_usage` after 400. Stale reservations are released after 15 minutes. The job runs at 03:17 UTC
  (`maintenance.py:33-56`, `ai.py:456`, `main.bicep:85`).
- **SPA routes.** There are 16 `CLIENT_ROUTES` (`spa.py:32-35`).
- **Database.** Pool 5+5 in the app and 3+2 in the Bicep. Timeouts are 5 s to connect, 10 s per statement and 15 s
  idle in a transaction (`config.py:29-32`, `main.bicep:324-329`, `db.py:36`).
- **Infra.** The web app has 0.5 vCPU and 1 GiB, scales 0 to 1, and maxReplicas is pinned to 1. Log Analytics keeps
  30 days with a 0.1 GB daily cap. Postgres is B1ms with 7-day backups. The region is francecentral
  (`main.bicep:87-93,487`, `shared.bicep:73,79`, `modules/postgres.bicep:47,67`, `*.bicepparam:7/46`).
- **Deploy workflow.** It defaults to `require_email_verification=false` and `ai_provider=fake`, and gates on
  `STUDIO_AZURE_APPROVED`, main and the OIDC secrets (`_starter-deploy.yml:32-50,117-136`).
- **Budget.** Only `id-github-deploy` is live and everything else is planned. Hosting is estimated at $5.07 a month with
  the student Postgres allowance and $23.20 without (`state/BUDGET.md`, ADR 0002 "Monthly cost").
- **Board status** is as the brief describes for T-60 (doing), T-62 (todo), T-65 (blocked, Q-14 A), T-69 (todo),
  T-18 (slices 1 to 6 merged) and T-15/T-34 (todo).

## The four surprises the teacher flagged

1. **`LIMITED_PROVIDERS = {"mock","stripe"}` is intentional, not a defect.**
   - The code comment at `routes/notes.py:107-109` says so.
   - ADR 0002 "What a deployed demo can do" says "mock plans keep the trial's AI allowance (R15)" and "R17 is fixed
     (Stripe plans use the trial pool)". SECURITY.md R15 and R17 and the board's T-21 entry agree.
   - `tests/test_cookies_and_limits.py:100-117` pins that every provider that refuses live keys is in the set.
   - Upgrading is not meant to lift the cap until a selling ADR allows live keys. The brief explains this correctly.
   - A small demo-UX nit remains: the billing page shows "2,000,000 AI tokens a month" for Pro, but a mock or Stripe-test
     Pro tenant actually gets 30k a day and 100k a month. Optional low-priority task: *"_starter billing page: when the
     provider is mock or Stripe test mode, label plan AI allowances as 'after launch; test plans use the trial
     allowance' so demos don't promise 2M tokens."*
2. **francecentral vs "UK region" is a real defect (documentation and customer-facing text).**
   - `infra/main.bicepparam:7` and `shared.bicepparam:46` pin francecentral.
   - `DATA.md:38` says "Microsoft Azure: hosting and database, UK region". So does the DRAFT privacy notice shown to
     users (`frontend/src/pages/legal.tsx:19`). Products copy both.
   - ADR 0002 lines 13 and 413 still price "uksouth", and `infra/README.md:16` says "rg-ai-studio, uksouth" (true for the
     resource group only).
   - A wrong hosting location in a UK GDPR inventory and privacy notice is a compliance misstatement (EU, not UK).
   - Board task: *"_starter: DATA.md processors list and legal.tsx privacy notice say 'UK region'; change to France
     Central (EU) while on the Student subscription, say UK hosting is a handover decision, and note the Azure OpenAI
     deployment type's processing geography; update ADR 0002's 'uksouth' price labels."*
3. **gpt-5.4-pro vs the daily token cap: a real defect, because the guard is only partial.**
   - `infra/cost-guard.sh` checks only the Bicep parameter defaults `aiGlobalDailyTokens` x `aiPricePerMillionTokens`.
     The price parameter is a fixed `'2.00'` (`main.bicep:59`) with no link to the deployment.
   - The deployment name comes from the `AZURE_OPENAI_DEPLOYMENT` secret (`_starter-deploy.yml:264`), so pointing it at
     the existing gpt-5.4-pro deployment passes the guard. The 100k a day cap would then allow up to about $18 a day,
     about $540 a month.
   - The app's `AI_PRICE_PER_MILLION_TOKENS` setting (`config.py:93`) is set by Bicep but never read at runtime: no
     startup check uses it.
   - Mitigations exist: `ai_provider` defaults to `fake`, deploys are manual and approval-gated, and the README and
     the brief warn about it.
   - Board task: *"_starter cost guard: tie price to deployment. Fail the deploy (and app startup) unless
     AZURE_OPENAI_DEPLOYMENT is in a known price table or AI_PRICE_PER_MILLION_TOKENS is set explicitly, and refuse to
     start when AI_GLOBAL_DAILY_TOKENS x price x 30 exceeds the monthly AI budget."*
4. **The stale README and ADR 0001 are real (doc-only, low).**
   - `README.md:141-145` "Not done yet" still lists "frontend unit tests". They exist (`frontend/src/*.test.ts(x)`), and
     CI runs them (`_starter-ci.yml:98-99`, `npm test` = `vitest run`).
   - The README tests table (`README.md:32-39`) has no vitest row, and its count of 561 is stale.
   - ADR 0001 decision 6 says chat completions only and "a monthly token cap per plan". It doesn't mention the Responses
     API, daily or trial-pool or global caps, in-flight limits or `LIMITED_PROVIDERS`.
   - ADR 0001 decision 8 and "Consequences" still list Redis as a gap, but it is built (only provisioning is open).
   - `NEXT.md:7` is stale on the Choose buttons (see error 9).
   - Board task: *"_starter docs: README 'Not done yet' and tests table (add the vitest row, refresh counts), ADR 0001
     decisions 6 and 8 and Consequences (Responses API, daily, trial-pool and global caps, in-flight limit,
     LIMITED_PROVIDERS, Redis built), NEXT.md line 7 (Choose buttons fixed in T-77)."*
