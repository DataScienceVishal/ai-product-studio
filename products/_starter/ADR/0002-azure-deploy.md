# ADR 0002: Azure deploy path for the starter

- Status: proposed (2026-11-23, board task T-7). Nothing is created until Vishal approves the costs below.
  Products inherit this design. Change it only with a new ADR.
- Files: `infra/` (Bicep, SQL, smoke test, runbook) and `.github/workflows/_starter-deploy.yml`.
- Prices are estimates for uksouth, read on 2026-11-23 from Microsoft's Retail Prices API and pricing docs
  (sources at the end). They change; the daily spend report (T-2) shows what is really billed.

## The picture

```
            GitHub Actions (_starter-deploy.yml, manual)                     the browser
            build ─► scan ─► push ─► deploy ─► migrate ─► smoke ─► traffic        │ https only
                               │        │         │                               ▼
  rg-ai-studio (uksouth)       ▼        ▼         ▼                       ┌──────────────────────────┐
  ┌──────────────────┐   ┌──────────────────────────────────────────┐   │ ca-starter (one origin)   │
  │ acrstudioznp96r  │◄──┤ cae-studio: Container Apps environment     │   │  /api, /livez, /healthz   │
  │ registry, Basic  │   │ Consumption profile only, scale to zero    ├──►│  (+ the built SPA after   │
  └──────────────────┘   │  ca-<slug>            web app, 0-1 replica │   │   the follow-up task)     │
   ▲ AcrPull             │  caj-<slug>-migrate   alembic upgrade head │   └────────────┬─────────────┘
  ┌┴─────────────────┐   │  caj-<slug>-purge     daily retention purge│                │ TLS 1.3,
  │ id-studio-acrpull│──►│  (pull identity: image pulls only)         │                │ full cert check
  └──────────────────┘   └───────────────┬──────────────────────────┘                ▼
  ┌──────────────────┐                   │ console + system logs       ┌──────────────────────────┐
  │ log-studio       │◄──────────────────┘                             │ psql-studio-znp96r        │
  │ 30 days, capped  │                                                 │ Postgres 16, B1ms, 32 GB  │
  └──────────────────┘                                                 │ one database per product  │
                                                                       └──────────────────────────┘
```

Shared, created once (`infra/shared.bicep`): the environment, the registry, the pull identity, the logs and
Postgres. Per product, on every release (`infra/main.bicep`): one web app and two jobs.

## Decisions

### 1. Host on Container Apps, Consumption profile only, on the default network

- A workload profiles environment (Microsoft's default type) with only the Consumption profile. It scales to
  zero, and a revision with no replicas costs nothing. The subscription gets 180,000 vCPU-seconds,
  360,000 GiB-seconds and 2 million requests free each month. That is about 100 active hours a month for
  one app at 0.5 vCPU and 1 GiB.
- **No custom virtual network.** With one, Azure bills a Standard Load Balancer ($0.025/hour) and two static
  public IPs ($0.005/hour each): about $25.55 a month before anything runs. It also adds a managed resource
  group outside `rg-ai-studio`.
- **Cost trap avoided:** a Dedicated workload profile, a private endpoint or a planned maintenance window
  each starts a flat management charge of $0.10 an hour, about $73 a month. Microsoft announced in November
  2026 that these meters get clearer names from December ("Environment Management Hour" and others). A Microsoft Q&A thread (10 Nov 2026) reports
  the charge on a Consumption-only environment that had a maintenance window set. `infra/` uses none of
  them, and the workflow refuses any template that does.
- Environments idle for 90 days are deleted automatically. The daily purge job keeps this one active.
- `maxReplicas` is pinned to 1, because rate limits are in-process (ADR 0001, decision 8; T-15 moves them to
  Redis). That also caps the worst case at one replica's cost.

### 2. One origin: the backend serves the built frontend

The session cookie is SameSite=Lax and the CSRF guard relies on CORS, so the browser must see the SPA and
`/api` on one origin.

| Option | Cost a month | Why not / why |
|---|---|---|
| **FastAPI serves `dist/` from the same container (chosen)** | $0 | One container, one origin, no extra hop. The ingress's X-Forwarded-For rule (the app trusts only the rightmost hop) stays true. Needs an app change: proposed board task 1 |
| nginx or Caddy sidecar in the same app, proxying `/api` | $0, but more vCPU and memory per active second | No app change, but a second image to build and scan, and the proxy must pass X-Forwarded-For through unchanged or every user shares one rate-limit bucket |
| Static Web Apps with a linked Container Apps backend | $9 per app (Standard plan is required) | A fee per product. SWA's proxy would probably become the rightmost X-Forwarded-For hop, which breaks the rate limits (not tested) |
| Azure Front Door Standard in front | $35 base fee | Over the $10 rule on its own |

- **HSTS:** the app already sends `Strict-Transport-Security: max-age=31536000; includeSubDomains` on every
  response when `COOKIE_SECURE=true`, which the deploy sets. The ingress doesn't add HSTS itself.
  The smoke test checks the header on every release.
- **CSP:** the app sends `default-src 'none'` with JSON today. HTML responses get the SPA policy from
  SECURITY.md I4: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;
  connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`. The built `index.html`
  has no inline script or style, so the policy holds. This is part of board task 1.
- **HTTP:** the ingress redirects plain HTTP to HTTPS (`allowInsecure: false`) and serves TLS 1.2 or 1.3.
  The smoke test checks the redirect.
- Until task 1 lands, a deployed starter serves the API, probes and health only. A browser demo needs task 1.

### 3. Registry: Azure Container Registry Basic

| | GHCR (private image) | **ACR Basic (chosen)** | ACR Standard |
|---|---|---|---|
| Cost a month | $0 ("currently free", with a month's notice before any change) | $5.07 ($0.1666 a day), 10 GiB included | $20.28; $0 for 12 months under the student allowance |
| How the app pulls | a classic personal access token with `read:packages`. Fine-grained tokens aren't supported, the token can't be limited to one package, and it is long-lived and in Vishal's name | the managed identity `id-studio-acrpull` (AcrPull). No secret exists | same as Basic |
| SECURITY.md I7 ("a managed identity for pulling images") | fails | meets it | meets it |
| Cold starts | every start pulls across the internet | pulls inside the region | same |

- The pull identity is attached to every app and job with `lifecycle: None`, so code in a container can't
  get tokens for it. It can only pull images.
- `roleAssignmentMode: LegacyRegistryPermissions` is pinned. In that mode the deployer's Contributor role
  can push, so no extra role assignment is needed. Microsoft plans to make ABAC mode the default for new
  registries, and in ABAC mode Contributor has no data-plane access. Revisit at handover, with per-product
  pull identities scoped to their own repository.
- Images are deployed by digest, so a revision always runs exactly the image that was scanned.
- **Cheaper if eligible:** if Vishal's portal "Free services" page lists Container Registry, Standard costs
  $0 until the 12 months end. Then it must be downgraded to Basic (no downtime) or it costs $20.28 a month.
  Basic is the default because nobody has to remember the downgrade.

### 4. Postgres: one shared Flexible Server B1ms, one database per product

| Option | Cost a month | Why not / why |
|---|---|---|
| **Flexible Server, Burstable B1ms, 32 GB (chosen)** | $0 under the student allowance; $18.13 otherwise ($0.019/hour × 730 = $13.87, plus 32 GB × $0.133 = $4.26) | Managed backups and patching, TLS, a database per product. The playbook's default |
| B1ms stopped outside demo hours | about $7.60 (176 hours of compute + storage) | A fallback if the allowance doesn't apply. A stopped server restarts itself after 7 days, so it needs a scheduled workflow |
| Postgres in a container app | about $13 or more | Must stay at one replica with a persistent volume, has no managed backups, and Postgres on an SMB file share is unsafe |
| Neon or Supabase free tier (not checked on their own pages) | $0 | A new third-party account (ask-first), another processor outside Azure for the privacy notice, small storage caps and harder handover. Fallback only |
| Azure SQL Database free offer (not priced here) | free tier | SQL Server, not Postgres. The app uses Postgres advisory locks and psycopg |

- The Azure for Students page lists "750 hours of Flexible Server: Burstable B1MS Instance, 32 GB storage,
  and 32 GB backup storage" for 12 months, for new Azure customers only. 750 hours covers one server for a
  whole month, which is why there is exactly one server. Storage autogrow is off, so the server can't grow
  past the allowance unnoticed.
- **Vishal confirms eligibility** on the portal's "Free services" page (Cost Management + Billing). Until he
  does, `state/BUDGET.md` counts the pay-as-you-go price, so the projection errs high.
- PostgreSQL 16 (CI and local development use 16), 7-day backups, no high availability, TLS 1.3 minimum.
- **Two roles per product**, created by `infra/db-setup.sql` and `db-grants.sql`:
  - `<db>_migrator` owns the tables and runs Alembic. Only the migration job has its password.
  - `<db>_app` reads and writes rows only. The web app and the purge job use it.
  - Each database revokes CONNECT from PUBLIC, so one product's roles can't open another product's database.
  - Connection limits are 12 (app) and 3 (migrator). The server allows 35 user connections for everyone,
    and Burstable servers have no built-in PgBouncer. Each app replica pools at most 5 connections
    (`DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`).
  - Tested on PostgreSQL 16.15 with a non-superuser admin, as on Azure: re-runnable, real migrations as the
    migrator, the purge as the app role, DDL refused for the app role, other roles refused CONNECT.
- Backups keep deleted rows restorable for 7 days. DATA.md should say so (small follow-up).

### 5. Postgres network: public endpoint, Azure IPs only, strong sign-in (a documented deviation)

SECURITY.md I7 asks for Postgres to be "not publicly reachable, or firewalled to Container Apps egress".
Neither is affordable or reliable here:

| Option | Problem |
|---|---|
| Private access (VNet integration) | Needs the custom network from decision 1: about $25.55 a month extra |
| Firewall rules for the environment's outbound IPs | Microsoft: outbound IPs "might change over time". In May 2026 a user saw traffic from an IP missing from the app's own list. Either way the database disappears without warning |
| **Allow Azure services (the 0.0.0.0 rule), chosen** | Any Azure customer's resources can reach the port. Microsoft's warning: "make sure your sign-in and user permissions limit access to only authorized users" |

Compensating controls, all in this design:
- TLS 1.3 only, and clients use `sslmode=verify-full` against the image's CA bundle. That is Microsoft's
  recommended configuration and stronger than the `sslmode=require` I7 asks for.
- Every password is 43 characters, from HMAC-SHA256 of the role's name keyed by the `STUDIO_DB_SEED` secret.
  No password is stored anywhere except as a Container Apps secret.
- The server admin password exists only inside GitHub Actions runs. No app or job has it.
- The app role can't change the schema. Each database is closed to other products' roles. Azure Postgres
  has no superuser login.
- Follow-up (board task 3): passwordless Entra ID sign-in with managed identities, then
  `passwordAuth: Disabled`. After that, there is no password to steal or guess.
- **At handover**, on the business's own subscription, use private access (decision 1's network). The
  template change is small; the cost is the reason it waits.

The security gate decides whether to accept this. If it doesn't, the alternative is private networking, at
about $25.55 a month extra, which needs Vishal's approval.

### 6. Secrets: Container Apps secrets, filled from GitHub, never in the template

| Secret | Comes from | Reaches the app as |
|---|---|---|
| `DATABASE_URL` (app role, migrator role) | derived in the workflow from `STUDIO_DB_SEED` | Container Apps secret `database-url`, referenced by `secretRef` |
| `AZURE_OPENAI_API_KEY` | Actions secret (SETUP.md step 3), only with `ai_provider=azure` | secret `azure-openai-api-key` |
| `BILLING_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY` | Actions secrets `STARTER_BILLING_WEBHOOK_SECRET` and `STARTER_STRIPE_SECRET_KEY`, only with `billing_provider=stripe` | secrets `billing-webhook-secret`, `stripe-secret-key` |

- Values travel as `@secure()` Bicep parameters, read from the workflow's environment by the `.bicepparam`
  files. Azure doesn't keep secure parameters in deployment history, and the workflow masks derived values.
- Jobs get only their database URL. They never see the AI or payment keys.
- **No Key Vault yet.** It would need one more resource and a role assignment that only an Owner can make,
  for no gain at this size. It becomes worth it when secrets must rotate without a redeploy (handover).
- With the mock billing provider, no webhook secret is set and the app makes a random one per process. That
  is correct for one replica.

### 7. Azure OpenAI: a key for now, a managed identity next

- **Now:** the key is a Container Apps secret, from the `AZURE_OPENAI_API_KEY` Actions secret. Deploys
  default to `ai_provider=fake`, so nothing is spent until someone chooses `azure`. Even then
  `AI_GLOBAL_DAILY_TOKENS=100000` caps spend at $0.20 a day (all output at $2.00 per million).
- **Next (board task 2):** a per-product user-assigned identity with the "Cognitive Services OpenAI User"
  role on the Azure OpenAI resource. The app gets a token from the Container Apps identity endpoint
  (`IDENTITY_ENDPOINT` with the `X-IDENTITY-HEADER`; audience `https://ai.azure.com/.default` per Microsoft's
  Entra ID guide) and sends `Authorization: Bearer` instead of `api-key`. That is an app change in `ai.py`.
  The role assignment needs an Owner: Vishal, and ask-first if the resource sits outside `rg-ai-studio`.

### 8. Identities and permissions

- **Deployer:** the existing `AZURE_CREDENTIALS` service principal, Contributor on `rg-ai-studio` only
  (SETUP.md step 3). Cloud runs never hold Azure credentials.
- Contributor can't create role assignments (that needs Owner or Role Based Access Control Administrator)
  and can't register resource providers. So Vishal does three things once, in Cloud Shell (infra/README.md):
  register the providers, grant AcrPull to the pull identity, and later the Azure OpenAI role (task 2).
- **Gates in the workflow:** it deploys only with `AZURE_CREDENTIALS` set, the repository variable
  `STUDIO_AZURE_APPROVED=yes` (Vishal's approval of `state/BUDGET.md`), and a run on `main` (reviewed code
  only). Otherwise it compiles the Bicep and stops with a notice.

### 9. Releases: a new revision gets traffic only after it passes

1. Build the image, then scan it with Trivy (decision 12). Both happen before the Azure sign-in.
2. Push to the registry and deploy by digest.
3. Deploy `main.bicep`. The app is in multiple-revision mode: the live revision keeps 100% of traffic and the
   new revision `ca-<slug>--r<run>a<attempt>-<sha>` starts at 0%.
4. **Migrations run as a separate job** (`caj-<slug>-migrate`, `alembic upgrade head`, as the migrator), never
   in the web process. The workflow waits for it to succeed.
5. Smoke-test the new revision at its own address (`infra/smoke.sh`): `/livez`, `/healthz` with
   `"db":"ok"`, HSTS, and the HTTP-to-HTTPS redirect.
6. Move all traffic to it, then smoke-test the public address.
7. **Rollback:** if the public test fails, traffic goes straight back to the previous revision. If anything
   fails earlier, traffic never moved and the new revision is deactivated. The previous revision stays
   active at 0% (no replicas, no cost) for an instant manual rollback with the `rollback_to` input. Older
   revisions are deactivated and can be re-activated the same way.
- Probes: startup and liveness use `/livez` (no database, so a busy pool never restarts the replica).
  Readiness uses `/healthz` (checks the database). `TRUST_PROXY_HEADERS=true` with uvicorn's
  `--no-proxy-headers`, as the image already does.
- **Rule for every migration:** it must work with the previous release's code (expand, then contract in a
  later release). Rolling back moves traffic only. It never downgrades the schema, because a downgrade can
  delete data.
- Caveat: the previous revision stays reachable at its own revision address until the next release. After a
  security fix, release again or deactivate it by hand (infra/README.md).

### 10. Retention purge as a scheduled job

`caj-<slug>-purge` runs `python -m app.maintenance purge` daily at 03:17 UTC, as the app role (DELETE is
enough), with one retry. The schedule is a parameter. It costs about 450 vCPU-seconds a month, inside the
free grant.

### 11. Logs

The environment sends console and system logs through a diagnostic setting to `log-studio`. This is the
"azure-monitor" destination, which Microsoft's November 2026 update recommends over the shared-key
Log Analytics one. Settings:
- 30-day retention with `immediatePurgeDataOn30Days` (SECURITY.md D3; 31 days are included in the
  ingestion price anyway).
- A daily cap of 0.1 GB, so at most about 3 GB a month, inside the free 5 GB.
- Logs hold ids, not personal data (DATA.md). A day that hits the cap loses the rest of that day's logs;
  that is acceptable for demos.

### 12. Cost and supply-chain guards

- The workflow refuses templates with billable environment features (decision 1).
- Scale to zero, one replica at most, storage autogrow off, the AI daily token cap, and `ai_provider=fake`
  by default.
- Trivy 0.76.2, pinned by digest, fails the release on fixable HIGH or CRITICAL vulnerabilities. It reads a
  saved image tarball rather than the Docker socket, before any Azure sign-in, so it can't see credentials.
  A justified exception goes in `<product>/.trivyignore`.
- Not yet: pinning `FROM python:3.12-slim` by digest, and actions by commit SHA (SECURITY.md section 6;
  deferred in DECISIONS.md). These are follow-ups.

## Monthly cost

Estimates, uksouth, one demo product plus the shared pieces.

| Resource | Settings | $ a month | Worked out from |
|---|---|---|---|
| `cae-studio` environment | Consumption profile only, no network of its own | 0 | no environment fee without Dedicated profiles, private endpoints or maintenance windows |
| `ca-starter` web app | 0.5 vCPU, 1 GiB, 0 to 1 replicas | 0 for the first ~100 active hours, then 0.076 per active hour | grant ÷ size; 0.5 × $0.000034 + 1 × $0.000004 per second |
| `caj-starter-migrate`, `caj-starter-purge` | 0.25 vCPU, 0.5 GiB, about a minute a run | 0 | inside the grant |
| Requests | | 0 | first 2 million a month free |
| `acrstudioznp96r` registry | Basic, 10 GiB included | 5.07 | $0.1666 a day; extra storage $0.10 per GB-month |
| `psql-studio-znp96r` Postgres | B1ms, 32 GB, 7-day backups | 0 with the student allowance, **18.13** without | $0.019 an hour × 730, plus 32 GB × $0.133; backups beyond the allowance $0.10 per GB-month (a demo database's are far under 1 GB) |
| `log-studio` | 30 days, 0.1 GB a day cap | 0 | ingestion free to 5 GB a month, then $2.88 per GB |
| `id-studio-acrpull` | | 0 | managed identities "at no extra cost" |
| Data out | | 0 | first 100 GB a month free, then $0.08 per GB |
| Azure OpenAI tokens | gpt-5-mini Global | 0 with `fake` (default); at most 6.10 with `azure` | 100,000 tokens a day × $2.00 per million output tokens |

**Total: $5.07 a month with the student allowance, $23.20 without it** (plus at most $6.10 if real AI is on).
At $23.20 a month, the $80 of credit lasts about 3.4 months. Each further product adds a web app and two
jobs, which share the same free grant, and a database on the same server.

## What needs Vishal's approval

1. **Spend (ask-first):** the shared resources. Without the allowance Postgres is $18.13 a month, over the
   $10 single-resource rule, and the projected total passes $80 in month four. Proposed question:

   > **Decision:** Approve the starter's Azure hosting?
   > **Context:** One shared Postgres (B1ms), one Basic registry, plus free Container Apps and logs. $5.07 a
   > month if your student "Free services" page lists PostgreSQL (and $0 if it lists Container Registry too
   > and we use Standard); $23.20 a month if not, so $80 lasts about 3.4 months.
   > **Options:** A) Approve as designed and do the one-time setup steps in infra/README.md (recommended)
   > B) Approve, but with the registry on Standard while the free allowance lasts (I must downgrade it before
   > month 12) C) Not yet: keep testing locally, create nothing.
   > **If no answer:** waits (spending money is ask-first).

2. **One-time setup only an Owner can do** (infra/README.md, about 10 minutes): check the "Free services"
   page; register the resource providers; add the `STUDIO_DB_SEED` secret; set `STUDIO_AZURE_APPROVED=yes`;
   after the first shared deploy, grant AcrPull with the one command the workflow prints.
3. **Not Vishal: the security gate** decides on decision 5 (Postgres reachable from Azure IPs) and on keeping
   the previous revision active (decision 9).

## How this meets SECURITY.md's deploy requirements (I7, I3, I4, D3, A3)

| Requirement | Here |
|---|---|
| Managed identity for image pulls | `id-studio-acrpull`, AcrPull, `lifecycle: None` |
| Key Vault or Container Apps secrets for the webhook secret and Stripe key | Container Apps secrets from secure parameters |
| Deploy principal scoped to `rg-ai-studio` | the existing Contributor service principal |
| Postgres not public, or firewalled to Container Apps egress; `sslmode=require` | **Partly.** TLS 1.3 with `verify-full` (stronger). Firewall is Azure IPs, a deviation explained in decision 5 |
| App role without DDL; migrations by a separate role and job | `<db>_app` and `<db>_migrator`; the migration job. Tested locally |
| Ingress `allowInsecure: false`; no public storage containers | yes; no storage account at all |
| Log Analytics retention of 30 days | yes, with immediate purge |
| I1 and I4 settings | proxy settings as in the image; HSTS checked by the smoke test; HTML CSP comes with board task 1 |
| Memory sized for the hashing bound (A3) | 1 GiB for 4 × 64 MiB slots plus about 150 MiB |
| Trivy scan in the deploy workflow | yes, pinned by digest |
| ENV=prod on every internet-facing deploy (I3) | yes, for the app and both jobs |
| Daily retention purge (D3) | the scheduled job |

## Failure modes

| What goes wrong | What happens | What to do |
|---|---|---|
| The student allowance doesn't apply | Postgres costs $18.13 a month | The T-2 report shows it. Stop/start the server outside demo hours, or move to a fallback (decision 4) |
| The credit runs out | Azure disables the subscription and every demo goes down | Expected for demos only. No customer may depend on this subscription (safety.md). Handover moves hosting |
| First request after 5 idle minutes | A cold start: image pull plus app start | Acceptable for demos; the smoke test allows 3 minutes |
| A migration isn't backward compatible | A rollback can't help, because the old code meets the new schema | Expand/contract rule (decision 9); reviewers check each migration |
| AcrPull not granted yet | The workflow stops early and prints the exact command | Vishal runs it once |
| A new CVE in the base image | Trivy fails the release | Rebuild later, or a justified `.trivyignore` entry; follow-up: pin and refresh the base image |
| Too many database connections | `too many clients` from Postgres | Per-role limits and small pools (decision 4); beyond about 3 products, connection pooling or a bigger SKU (approval) |
| Bots keep the app awake | Each wake costs at most about $0.006; always awake costs up to about $47 a month | Daily spend report; IP restrictions on ingress if it happens |

## Follow-ups (proposed board tasks)

1. **Serve the SPA from the backend** (decision 2): a multi-stage Dockerfile at the starter root; FastAPI
   serves `dist/assets` (immutable cache) and `index.html` (no-cache) with the HTML CSP; SPA fallback for
   `/verify-email`, `/reset-password`, `/accept-invite` and the billing return; API 404s stay JSON; tests;
   CI builds the new Dockerfile; then the workflow's `IMAGE_CONTEXT`, `DOCKERFILE` and `EXPECT_SPA=true`.
2. **Azure OpenAI through a managed identity** (decision 7): app change plus a per-product identity.
3. **Passwordless Postgres** (decision 5): Entra ID tokens as passwords via SQLAlchemy's `do_connect`, for
   the app and Alembic. Then `passwordAuth: Disabled` and no `STUDIO_DB_SEED`.
4. **Pin the base image by digest and refresh it on a schedule**; pin actions by commit SHA.
5. **Compile the Bicep in CI** on every push that touches `infra/` (no credentials needed).
6. **DATA.md and README:** add 7-day database backups and 30-day log retention to DATA.md. Point the README's
   "Not done yet" T-7 line at this ADR.
7. Only if the allowance doesn't apply: a stop/start schedule for Postgres.

## Sources (all read 2026-11-23)

- Container Apps billing (free grant, scale to zero, jobs, Dedicated management fee): https://learn.microsoft.com/en-us/azure/container-apps/billing
- Environment types, no environment cost on Consumption, 90-day idle deletion: https://learn.microsoft.com/en-us/azure/container-apps/environment
- Custom network: load balancer and public IPs billed: https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks
- Outbound IPs "might change over time": https://learn.microsoft.com/en-us/azure/container-apps/networking
- Ingress (TLS, HTTPS redirect, X-Forwarded-For rightmost hop): https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview
- Revisions and blue-green releases: https://learn.microsoft.com/en-us/azure/container-apps/revisions, https://learn.microsoft.com/en-us/azure/container-apps/blue-green-deployment
- Managed identities in Container Apps (identity endpoint, `identitySettings` lifecycle): https://learn.microsoft.com/en-us/azure/container-apps/managed-identity; image pulls: https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull
- Log destinations: https://learn.microsoft.com/en-us/azure/container-apps/log-options; retention: https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure
- Meter renames (November 2026): https://github.com/microsoft/azure-container-apps/issues/1886; maintenance-window charge report: https://learn.microsoft.com/en-us/answers/questions/6066720/is-a-planned-maintenance-window-honored-and-billed
- Outbound IP list incomplete (user report, May 2026): https://learn.microsoft.com/en-us/answers/questions/5879132/azure-container-app-outbound-address
- Prices: Azure Retail Prices API (https://prices.azure.com/api/retail/prices, documented at https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices), uksouth, queried 2026-11-23. The pricing pages at azure.microsoft.com/pricing didn't render figures
- Azure for Students free services and terms: https://azure.microsoft.com/en-us/free/students/, https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/, https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students
- Postgres firewall ("Allow Azure services" warning): https://learn.microsoft.com/en-us/azure/postgresql/security/security-firewall-rules
- Postgres TLS (verify-full, root CAs, TLS 1.3): https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls
- Postgres limits (35 user connections on B1ms, no PgBouncer on Burstable, 7-day stop): https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/concepts-limits
- ACR tiers: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus; roles and who may assign them: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-rbac-built-in-roles-overview; ABAC mode: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-rbac-abac-repository-permissions
- GHCR billing and tokens: https://docs.github.com/en/billing/concepts/product-billing/github-packages, https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- Static Web Apps needs Standard for a Container Apps backend: https://learn.microsoft.com/en-us/azure/static-web-apps/apis-container-apps
- Azure OpenAI with Entra ID: https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/managed-identity
- Managed identities cost nothing extra: https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview
- Bicep schemas: containerApps and jobs 2025-07-01, managedEnvironments 2025-07-01, flexibleServers 2024-08-01, registries 2025-11-01 (learn.microsoft.com/azure/templates)
- Trivy 0.76.2 image digest: Docker Hub tag list for aquasec/trivy (hub.docker.com)
