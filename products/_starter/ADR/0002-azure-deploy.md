# ADR 0002: Azure deploy path for the starter

> **Superseded in part by ADR 0003 (passwordless Postgres via Entra ID): `STUDIO_DB_SEED` and derived database passwords are removed.**
> Every passage below about the seed, derived role passwords, `setup_database` or seed rotation is kept as history and
> marked "(superseded by ADR 0003)". Database sign-in is now described in `ADR/0003-entra-postgres.md` and the
> "Database sign-in" runbook in `infra/README.md`. The rest of this ADR still stands.

- Status: proposed (2026-11-23, board task T-7). Revised the same day after the T-7 review
  (`reviews/T-7-azure-deploy.md`): C1, C2, I1 to I5 and the conditions on decision 5 are addressed below.
  Nothing is created until Vishal approves the costs. Products inherit this design. Change it only with a
  new ADR.
- Files: `infra/` (Bicep, SQL, scripts, runbook) and `.github/workflows/_starter-deploy.yml`.
- Prices are estimates read for uksouth (the resource group region; resources are in francecentral, see "Region (T-61)") on 2026-11-23 from Microsoft's Retail Prices API and pricing docs
  (sources at the end). They change; the daily spend report (T-2) shows what is really billed.

## The picture

```
            GitHub Actions (_starter-deploy.yml, manual)                     the browser
            build ─► scan ─► push ─► deploy ─► migrate ─► smoke ─► traffic ─► purge job  │ https only
                               │        │         │                                      ▼
  rg-ai-studio (francecentral) ▼        ▼         ▼                       ┌──────────────────────────┐
  ┌──────────────────┐   ┌──────────────────────────────────────────┐   │ ca-starter (one origin)   │
  │ acrstudioznp96r  │◄──┤ cae-studio: Container Apps environment     │   │  /api, /livez, /healthz   │
  │ registry, Basic  │   │ Consumption profile only, scale to zero    ├──►│  (+ the built SPA after   │
  └──────────────────┘   │  ca-<slug>            web app, 0-1 replica │   │   T-16)                   │
   ▲ AcrPull             │  caj-<slug>-migrate   alembic upgrade head │   └────────────┬─────────────┘
  ┌┴─────────────────┐   │  caj-<slug>-purge     daily purge, on the  │                │ TLS 1.3,
  │ id-studio-acrpull│──►│                       live revision's image│                │ full cert check
  └──────────────────┘   └───────────────┬──────────────────────────┘                ▼
  ┌──────────────────┐                   │ console + system logs only  ┌──────────────────────────┐
  │ log-studio       │◄──────────────────┘ (no HTTP access logs)       │ psql-studio-znp96r        │
  │ 30 days, capped  │                                                 │ Postgres 16, B1ms, 32 GB  │
  └──────────────────┘                                                 │ one database per product  │
                                                                       │ sign-in log, 7 days       │
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
  2026 that these meters get clearer names from December ("Environment Management Hour" and others). A
  Microsoft Q&A thread (10 Nov 2026) reports the charge on a Consumption-only environment that had a
  maintenance window set. GPU profiles bill by the hour too.
- **The workflow checks what Azure will get, not just the source.** On every run, `infra/cost-guard.sh` reads
  the compiled templates. It refuses any workload profile type other than the literal `Consumption` (so a
  Dedicated or GPU profile, or a type set through a parameter, fails). It also refuses a custom network
  (`vnetConfiguration`, `infrastructureSubnetId`), any `Microsoft.Network` resource, a private endpoint and a
  maintenance window. A text search of the Bicep source runs as a second net. Neither can see a change made
  outside these templates, such as in the portal; the daily spend report (T-2) is the check for that.
- Environments idle for 90 days are deleted automatically. The daily purge job keeps this one active.
- `maxReplicas` is pinned to 1, because rate limits are in-process by default (ADR 0001, decision 8). That also caps the worst case
  at one replica's cost.
- Redis rate limits (T-15) are built but **Azure Cache for Redis is NOT provisioned**: it costs money, so it is
  ask-first, and no Redis resource is in the Bicep. With `RATE_LIMIT_REDIS_URL` unset the single-replica default
  keeps in-memory limits, unchanged. Before raising `maxReplicas` above 1: get approval, provision the cache,
  put the `rediss://` URL in a Container Apps secret, and set `RATE_LIMIT_REDIS_URL` from it. If Redis is down
  the app falls back to per-replica in-memory limits (warning logged), so auth never fails because of it.

### 2. One origin: the backend serves the built frontend

The session cookie is SameSite=Lax and the CSRF guard relies on CORS, so the browser must see the SPA and
`/api` on one origin.

| Option | Cost a month | Why not / why |
|---|---|---|
| **FastAPI serves `dist/` from the same container (chosen)** | $0 | One container, one origin, no extra hop. The ingress's X-Forwarded-For rule (the app trusts only the rightmost hop) stays true. Needs an app change: T-16 |
| nginx or Caddy sidecar in the same app, proxying `/api` | $0, but more vCPU and memory per active second | No app change, but a second image to build and scan, and the proxy must pass X-Forwarded-For through unchanged or every user shares one rate-limit bucket |
| Static Web Apps with a linked Container Apps backend | $9 per app (Standard plan is required) | A fee per product. SWA's proxy would probably become the rightmost X-Forwarded-For hop, which breaks the rate limits (not tested) |
| Azure Front Door Standard in front | $35 base fee | Over the $10 rule on its own |

- **HSTS:** the app already sends `Strict-Transport-Security: max-age=31536000; includeSubDomains` on every
  response when `COOKIE_SECURE=true`, which the deploy sets. The ingress doesn't add HSTS itself.
  The smoke test checks the header on every release.
- **CSP:** the app sends `default-src 'none'` with JSON today. HTML responses get the SPA policy from
  SECURITY.md I4: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;
  connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`. The built `index.html`
  has no inline script or style, so the policy holds. This is part of T-16.
- **HTTP:** the ingress redirects plain HTTP to HTTPS (`allowInsecure: false`) and serves TLS 1.2 or 1.3.
  The smoke test checks the redirect.
- Until T-16 lands, a deployed starter serves the API, probes and health only. A browser demo needs T-16.

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
- Every release pushes a new tag. 10 GiB holds dozens of images; an old-image cleanup is a follow-up.
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
- PostgreSQL 16 (CI and local development use 16), 7-day backups (deleted rows stay in them up to 7 days;
  DATA.md says so), no high availability, TLS 1.3 minimum.
- **Two roles per product**, created by `infra/db-setup.sql` and `db-grants.sql`:
  - `<db>_migrator` owns the tables and runs Alembic. Only the migration job has its password (superseded by ADR 0003).
  - `<db>_app` reads and writes rows only. The web app and the purge job use it. It can read
    `alembic_version` but not change it, so a compromised app can't make the next migration skip or repeat
    steps.
  - Each database revokes CONNECT from PUBLIC, so one product's roles can't open another product's database.
    They can still open the empty `postgres` database and read the catalog (names of databases and roles);
    that is metadata only and accepted.
  - Connection limits are 12 (app) and 3 (migrator). The server allows 35 user connections for everyone,
    and Burstable servers have no built-in PgBouncer. Each app replica pools at most 5 connections
    (`DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`).
  - (superseded by ADR 0003) **Passwords never reach the server.** The workflow sends SCRAM-SHA-256 verifiers made by
    `infra/scram_verifier.py`, which Postgres stores as given. A failed `ALTER ROLE` can only log a verifier.
    An empty or malformed value is refused before any statement could fail with it.
  - Tested on PostgreSQL 16.15 with a non-superuser admin, as on Azure: re-runnable; verifiers match
    Postgres's own (superseded by ADR 0003); six real migrations as the migrator under the jobs' prod settings; the purge as the app
    role; DDL and `alembic_version` writes refused for the app role; other roles refused CONNECT; no password
    in the server log, even after a forced failure.

### 5. Postgres network: public endpoint, Azure addresses only, strong sign-in (accepted for demos, with conditions)

SECURITY.md I7 asks for Postgres to be "not publicly reachable, or firewalled to Container Apps egress".
Neither is affordable or reliable here:

| Option | Problem |
|---|---|
| Private access (VNet integration) | Needs the custom network from decision 1: about $25.55 a month extra |
| Firewall rules for the environment's outbound IPs | Microsoft: outbound IPs "might change over time". In May 2026 a user saw traffic from an IP missing from the app's own list. Either way the database disappears without warning |
| **Allow Azure services (the 0.0.0.0 rule), chosen** | Effectively public: Microsoft says it allows "connections from the subscriptions of other customers", and any GitHub-hosted runner can reach the port |

**Accepted for private demos on these conditions** (T-7 review):

1. **Demo data only.** No real customer's or employee's personal data on the shared server. This ends at T-18
   (passwordless Entra ID sign-in, then `passwordAuth: Disabled`) or with private networking, whichever comes
   first, and it must end **before G4, before any handover, and before `unlock selling`**.
2. **The compensating controls stay as built:**
   - (superseded by ADR 0003) every password is 43 characters, 160 bits from HMAC-SHA256 of the role's name keyed by `STUDIO_DB_SEED`;
   - TLS 1.3 only, and every client uses `sslmode=verify-full` against Azure's current roots (DigiCert Global
     Root G2 and Microsoft RSA Root CA 2017, both in the image's CA bundle);
   - the server admin password exists only inside GitHub Actions runs, and no app or job has it;
   - the app role can't change the schema, each database is closed to other products' roles, and Azure
     Postgres has no superuser login.
3. (superseded by ADR 0003) **Passwords never reach the server** (SCRAM verifiers, decision 4), so nothing can log one.
4. **Sign-ins are audited.** Postgres logs every connection attempt with its source address and every failed
   sign-in (`log_connections`), and keeps its log files for 7 days (`logfiles.download_enable`,
   `logfiles.retention_days`). They stay on the server rather than going to `log-studio`, so a flood of failed
   attempts can't use up the workspace's daily cap and drop the app's own logs. `log_error_verbosity=terse`
   keeps error details, which can quote row values such as an email, out of those files. The runbook says how
   to read them.
5. **The address is not a secret,** and the connection limits (12 and 3) are a resource cap, not access control.

If any condition can't be met, the alternative is private networking at about $25.55 a month extra, which
needs Vishal's approval.

### 6. Secrets: Container Apps secrets, filled from GitHub, never in the template

| Secret | Comes from | Reaches the app as |
|---|---|---|
| `DATABASE_URL` (app role, migrator role) | derived in the workflow from `STUDIO_DB_SEED` (superseded by ADR 0003) | Container Apps secret `database-url`, referenced by `secretRef` |
| `AZURE_OPENAI_API_KEY` | the Actions secret (SETUP.md step 3), whenever it exists | secret `azure-openai-api-key`; wired into the app only with `ai_provider=azure` |
| `BILLING_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY` | the Actions secrets `STARTER_BILLING_WEBHOOK_SECRET` and `STARTER_STRIPE_SECRET_KEY`, whenever they exist | secrets `billing-webhook-secret`, `stripe-secret-key`; wired in only with `billing_provider=stripe` |

- Values travel as `@secure()` Bicep parameters, read from the workflow's environment by the `.bicepparam`
  files. Azure doesn't keep secure parameters in deployment history, and the workflow masks derived values (superseded by ADR 0003).
- **All four secrets always exist** on the web app, holding a placeholder (`not-configured`) until the Actions
  secret does. Only the chosen provider's environment variables reference them. So switching provider
  between releases never deletes a secret that the previous revision, kept for rollback, still reads.
  The exception is deleting a provider's Actions secret: the next release writes the placeholder, so rolling
  back to a revision that used the real value then fails. Delete one only when no kept revision uses that provider.
  Microsoft: "Before you delete a secret, deploy a new revision that no longer references the old secret.
  Then deactivate all revisions that reference the secret."
- A secret that isn't referenced by an environment variable is never visible inside a container. It is
  stored on the app resource, where anyone allowed `listSecrets` can read it: the deployer and Owners.
- Jobs get only their database URL. Microsoft warns that permission to start a job is permission to use its
  secrets, because a start can override the image; only the deployer and Owners hold it.
- **No Key Vault yet.** It would need one more resource and a role assignment that only an Owner can make,
  for no gain at this size. It becomes worth it when secrets must rotate without a redeploy (handover).
  Microsoft recommends Key Vault references over plain secret values in production, which this demo set-up
  is not.
- With the mock billing provider, no webhook secret is set and the app makes a random one per process. That
  is correct for one replica.
- (superseded by ADR 0003) **Rotating `STUDIO_DB_SEED`:** only `deploy_shared` sets the server admin password and only
  `setup_database` sets a product's role passwords. Rotation is therefore: new seed, then the starter's
  workflow with both ticked, then every other product's workflow with `setup_database` (runbook, "Rotating
  the database seed"). A revision released before the rotation holds the old password and can't be rolled
  back to afterwards. If the admin password and the seed disagree, the database step stops at once with a
  message that says so, instead of waiting 6 minutes.

### 7. Azure OpenAI: a key for now, a managed identity next

- **Now:** the key is a Container Apps secret (decision 6). Deploys default to `ai_provider=fake`, so nothing
  is spent until someone chooses `azure`. Even then `AI_GLOBAL_DAILY_TOKENS=98000` bounds the spend: every
  call reserves its upper-bound estimate and is refused if it would cross the budget, and since the R14 fix a
  call that was sent is never retried, so the tokens counted are the tokens billed. 98,000 tokens cost at
  most $0.196 a day even if every one were output ($2.00 per million). Trials together get half.
- **Built (T-17), not yet switched on:** `AZURE_OPENAI_AUTH=managed_identity` (default `key`) makes `ai.py` fetch
  a bearer token from the Container Apps identity endpoint (`IDENTITY_ENDPOINT` with `X-IDENTITY-HEADER`,
  api-version 2019-08-01, `AZURE_CLIENT_ID` for a user-assigned identity) and send `Authorization: Bearer`
  instead of `api-key`. Tokens are cached until 5 minutes before expiry; any failure is `AIUnavailable`, and
  neither token nor header is logged. The audience is `https://cognitiveservices.azure.com/.default`
  (the Azure OpenAI data-plane scope). Microsoft Learn documents both `https://cognitiveservices.azure.com` and `https://ai.azure.com` audiences; we use `cognitiveservices.azure.com`.
- **Not in Bicep, on purpose:** the only identity the infra attaches is the shared pull identity, with
  `lifecycle: None` so code in the containers can't get tokens for it (and it must not get an OpenAI role).
  A per-app identity plus a role assignment needs a design of its own and an Owner. Manual steps for Vishal
  (ask-first; do them only if the OpenAI resource is in `rg-ai-studio`, otherwise ask first):
  1. enable the app's system-assigned identity (or create a user-assigned one and attach it with default lifecycle);
  2. grant it "Cognitive Services OpenAI User" (`5e0bd9bd-7b93-4f28-af87-19fc36ad61bd`) on the Azure OpenAI resource only;
  3. set `AZURE_OPENAI_AUTH=managed_identity` (and `AZURE_CLIENT_ID` for a user-assigned identity); the key secret can then go.

### 8. Identities and permissions

- **Deployer (T-60, replaces the `AZURE_CREDENTIALS` service principal):** the user-assigned managed identity
  `id-github-deploy` in `rg-ai-studio`, Contributor on that group only. GitHub signs in with OIDC (`azure/login`
  with `client-id`, `tenant-id` and `subscription-id` from the secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and
  `AZURE_SUBSCRIPTION_ID`), so there is no stored password to leak or rotate. Jobs that sign in hold
  `permissions: id-token: write` at job level only. Cloud runs never hold Azure credentials.
- **Update (T-65, not applied yet): least-privilege role instead of Contributor.** `infra/deploy-role.bicep` defines
  the custom role "Studio Deployer (rg-ai-studio)": an explicit action list for what the workflows deploy and run, no
  role assignment or definition writes, no federated credentials, one delete (the runner's temporary Postgres firewall
  rule), assignable on `rg-ai-studio` only. A compromised `main` workflow can then no longer grant itself access or
  delete the registry or database. It is a file for Vishal to deploy once and swap for Contributor
  (`infra/README.md`, "Least-privilege deploy role (T-65)"). Until he does, this section's "Contributor" is still true.
  The registry decision above (`LegacyRegistryPermissions`) is why the role lists `registries/push/write` and `pull/read`.
- **Subject format (found on the first live run, 2026-11-24):** GitHub sends the immutable-ID subject `repo:<owner>@<owner-id>/<repo>@<repo-id>:...`, so the readable `repo:DataScienceVishal/ai-product-studio:...` form never matches (AADSTS700213). The credential must use the IDs shown in azure/login's "Federated token details" log line.
- **The federated credential trusts one subject:** `repo:DataScienceVishal@102427114/ai-product-studio@1468636475:ref:refs/heads/main`
  (issuer `https://token.actions.githubusercontent.com`, audience `api://AzureADTokenExchange`). So the sign-in
  works from `main` only, and the sign-in jobs start with a step that fails with a clear message elsewhere.
  **A job with `environment: <name>` gets the subject `...:environment:<name>` instead, and its login fails.**
  The GitHub ID token lasts about 5 minutes and the CLI replays it for each token of a new resource
  (azure/login issue 372, AADSTS700024), so the deploy job signs in again before the registry push and before
  the database step, which come long after the first sign-in.
  No job uses `environment:` today. If one is added (see the follow-up below), add a second federated
  credential for `repo:DataScienceVishal@102427114/ai-product-studio@1468636475:environment:<name>` first (command in SETUP.md step 3).
- Contributor can't create role assignments (that needs Owner or Role Based Access Control Administrator)
  and can't register resource providers. So Vishal does three things once, in Cloud Shell (infra/README.md):
  register the providers, grant AcrPull to the pull identity, and later the Azure OpenAI role (T-17).
- **Gates in the workflow:** it deploys only with the three OIDC secrets set, the repository variable
  `STUDIO_AZURE_APPROVED=yes` (Vishal's approval of `state/BUDGET.md`), and a run on `main` (reviewed code
  only). Otherwise it compiles the Bicep and stops with a notice.
- **The main-only check guards against accidents, not against a determined branch.** Repository secrets are
  readable by workflows on any branch, and a branch can edit the workflow. The real boundary is a GitHub
  environment holding the deploy secrets with a main-only deployment-branch rule. With OIDC the federated
  subject adds a second, Azure-side boundary: only runs on `main` can get a token at all, even if a branch reads
  the (non-secret) IDs. The limit: anyone who can push a workflow change to `main` can still get a Contributor
  token, and `main` has no review rule yet (studio state files go straight to it). Follow-up: a ruleset or
  CODEOWNERS rule requiring review for `.github/workflows/**` and `products/*/infra/**`. The repository is
  public, so GitHub Free does allow environments; the plan question above is settled.
  GitHub Free can't use environments in private repositories ("Users with GitHub Free plans can only
  configure environments for public repositories"); GitHub Pro can, and the GitHub Student Developer Pack
  includes Pro. Which plan this account has is not checked yet: a question for Vishal, then a follow-up.

### 9. Releases: a new revision gets traffic only after it passes

1. Build the image, then scan it with Trivy (decision 12). Both happen before the Azure sign-in.
2. **Read the live release, failing closed** (`infra/live-release.sh`). Only "the app doesn't exist" (the
   Azure CLI's exit code 3, or `ResourceNotFound`) means a first release. Any other error, or traffic split
   between revisions, stops the run, because guessing "first release" would give an untested revision all
   the traffic before its migration and smoke test, with no rollback.
3. Push to the registry and deploy by digest.
4. Deploy `main.bicep`. The app is in multiple-revision mode: the live revision keeps 100% of traffic and the
   new revision `ca-<slug>--r<run>a<attempt>-<sha>` starts at 0%. The purge job keeps the live revision's
   image and email settings (decision 10).
5. **Migrations run as a separate job** (`caj-<slug>-migrate`, `alembic upgrade head`, as the migrator), never
   in the web process. The workflow waits for it to succeed.
6. Smoke-test the new revision at its own address (`infra/smoke.sh`): `/livez`, `/healthz` with
   `"db":"ok"`, HSTS, and the HTTP-to-HTTPS redirect.
7. Move all traffic to it, then smoke-test the public address.
8. Only then point the purge job at the new image and settings (`infra/purge-job.sh follow`).
9. **Rollback:** if the traffic move, the public smoke test or the purge-job move fails, or the run is
   cancelled after traffic moved, traffic and the purge job go back to the previous revision. If anything
   fails earlier, traffic never moved, the purge job was never changed, and the new revision is deactivated.
   The previous revision stays active at 0% (no replicas, no cost) for an instant manual rollback with the
   `rollback_to` input, which also points the purge job back at it. Older revisions are deactivated and can
   be re-activated the same way.

**What happens to the database schema on a rollback: nothing.** A rollback moves traffic and the purge job; it
never runs a downgrade, because a downgrade can delete data. Alembic applies a release's pending migrations in
one transaction, so a migration that fails leaves the schema exactly as it was. But once a release's
migrations have succeeded they stay, even if that release is then rolled back: the older code runs on the
newer schema. So **every migration must work with the previous release's code**: add first, and drop or rename
only in a later release (expand, then contract). Reviewers check this on every migration.

- Probes: startup and liveness use `/livez` (no database, so a busy pool never restarts the replica).
  Readiness uses `/healthz` (checks the database). The startup probe allows a minute (6 seconds × 10, within
  the documented maximum of 10 failures). `TRUST_PROXY_HEADERS=true` with uvicorn's `--no-proxy-headers`, as
  the image already does.
- **The first release** has no previous revision: its only revision takes traffic as soon as it is ready,
  which is a minute before its migration has run. For that minute the API answers errors. That is harmless
  before anyone uses it, and later releases never do this.
- Caveats about the previous revision, while it stays active: it is reachable at its own revision address
  until the next release, and it keeps its own in-process rate-limit counters, so it is a second bucket for
  anyone who knows that address. After a security fix, release again so the vulnerable revision is retired.
  After a seed rotation it can't reach the database (decision 6) (superseded by ADR 0003).

### 10. Retention purge as a scheduled job that follows the live revision

`caj-<slug>-purge` runs `python -m app.maintenance purge` daily at 03:17 UTC, as the app role (DELETE is
enough), with one retry. It costs about 450 vCPU-seconds a month, inside the free grant.

- **Jobs have no revisions,** so a job is only as safe as the image it runs, and this job deletes data. It
  always runs the image and email settings of the web revision that serves traffic. A release deploys it with
  the live revision's values (read in step 2 of decision 9), moves it to the new release only after the public
  smoke test passes, and every rollback moves it back. On a first release it starts on that release's image,
  because there is nothing to protect yet.
- **Same email rules as the web app.** The web app and both jobs get the same `REQUIRE_EMAIL_VERIFICATION` and
  `EMAIL_PROVIDER`, so the purge treats unverified accounts the way the app does. Today the app deletes
  unverified accounts only once real email is sent, and email is outbox-only, so the purge deletes no account
  either way.
- Its database URL is refreshed on every release, because a seed rotation in the same run has already changed
  the password (superseded by ADR 0003).
- The migration job is different: it runs only when the workflow starts it, before traffic moves, and it keeps
  the image of the latest release attempt.

### 11. Logs

- The environment sends exactly two categories, `ContainerAppConsoleLogs` (what the code prints) and
  `ContainerAppSystemLogs` (revisions, replicas, probes, image pulls), through a diagnostic setting to
  `log-studio`.
- **It never uses the `allLogs` group,** because that also turns on `ContainerAppHTTPLogs`, the ingress
  access log. Microsoft says its `Path` column may contain query strings with tokens, and it would hold
  client IP addresses. The starter's email links carry tokens in the query string (`/verify-email?token=`,
  `/reset-password?token=`, `/accept-invite?token=`), and once T-16 serves the frontend those requests pass
  the ingress. Leaving the category out also keeps bot traffic from eating the daily cap.
- This is the "azure-monitor" destination. Microsoft's October 2026 Container Apps update (GitHub issue #1886)
  says to "plan your migration from the Log Analytics logging destination to Azure Monitor"; the log-options
  page still calls Log Analytics the default.
- 30-day retention with `immediatePurgeDataOn30Days` (SECURITY.md D3; 31 days are included in the ingestion
  price anyway). A daily cap of 0.1 GB, so at most about 3 GB a month, inside the free 5 GB. A day that hits
  the cap loses the rest of that day's logs; that is acceptable for demos.
- What the logs hold is in DATA.md: ids, not personal data. Postgres's own logs stay on the server (decision 5).

### 12. Cost and supply-chain guards

- `infra/cost-guard.sh` refuses compiled templates with features that have a fixed charge (decision 1).
- Scale to zero, one replica at most, storage autogrow off, the AI daily token cap, and `ai_provider=fake`
  by default.
- Trivy 0.76.2, pinned by digest, fails the release on fixable HIGH or CRITICAL vulnerabilities. It reads a
  saved image tarball rather than the Docker socket, before any Azure sign-in, so it can't see credentials.
  A justified exception goes in `<product>/.trivyignore`.
- Both base images (`node:22-slim`, `python:3.12-slim`) are pinned by digest; `.github/dependabot.yml` proposes
  digest refreshes weekly (patch-level only: new Node majors and Python minors are ignored). Each product
  copied from the starter needs its own Dependabot docker entry.
- Node 22 reaches end of life in April 2027 and the Dependabot ignore blocks Node majors (so Node 24 never
  arrives by itself), so the move to a newer Node LTS must be planned by February 2027. Check the first
  Dependabot docker PR is digest-only (same tag, new `sha256`), which proves the ignore rules work.
- Not yet: actions by commit SHA (T-30), and the `postgres:16` CI service image, which Dependabot doesn't scan.

## What a deployed demo can do (email is outbox-only)

No email provider is approved yet, so every email goes to the in-memory outbox: a verification link reaches
nobody. That decides what `require_email_verification` does in a deployed demo:

| `require_email_verification` | Sign-up, notes | AI summaries | Checkout | Invitations |
|---|---|---|---|---|
| on | yes | no: `403 email_not_verified`, and nobody can verify | no (`403`) | no (`403`) |
| **off (the workflow's default while email is outbox-only)** | yes | yes, within the trial's caps and the trials' half of the daily budget | yes, if `mock_checkout` is on or with Stripe test mode | created, but the link never leaves the outbox, so nobody can accept |

**Decision: deploy demos with verification off while email is outbox-only.**
- The AI is what a demo exists to show. With verification on and outbox email, nothing protective is gained:
  it blocks every account the same way.
- The account pre-hijacking path that verification guards against (SECURITY.md A1) needs the victim to reset
  their password by email, and an invited member needs the emailed link to join. Outbox-only, neither can
  happen.
- The purge deletes unverified accounts only once real email is sent, and trial AI needs verification only
  when verification is required. Those are the app's current rules (SECURITY.md re-test 3).
- Cost stays bounded. Anyone with the address can use the AI, but all trials together share half of
  `AI_GLOBAL_DAILY_TOKENS`: a few dozen typical summaries a day, costing at most $0.10. The sign-up throttles
  (20 a day per address, 200 new trials a day studio-wide) apply.
- `mock_checkout` stays off unless a demo needs the paid-plan flow. It gives a paid plan away, though mock
  plans keep the trial's AI allowance (R15).
- **The day a real email provider is approved, verification goes on and stays on.** The app refuses to start
  with verification off once real email is sent, so a deploy that forgets fails loudly. The template's own
  default is already on, for any deploy outside the workflow.
- Stripe test-mode demos: R17 is fixed (Stripe plans use the trial pool), but they still need a Stripe test
  account, which is ask-first.

## AI cost guard tied to the deployed model (T-91)

The token cap only bounds money at a given price, and the deployment comes from the `AZURE_OPENAI_DEPLOYMENT` secret, which
`state/BUDGET.md` says is gpt-5.4-pro. One rule (`backend/app/aicost.py`, stdlib only): `AI_GLOBAL_DAILY_TOKENS` x 31 x price
must be at most `AI_MONTHLY_BUDGET_USD` (6.10, the approved BUDGET.md line, checked over a 31-day month). The price comes from a small table by
deployment name (estimates, conservative: output prices); an explicit `AI_PRICE_PER_MILLION_TOKENS` can only raise a known
deployment's price and is required for an unknown one. Each product copied from the starter gets its own 6.10 default, but all
draw on one credit and one OpenAI deployment, so the product lines in `state/BUDGET.md` must add up. The app applies it at startup with `AI_PROVIDER=azure`
(the fake provider costs nothing and needs no price); `infra/cost-guard.sh` runs the same file in the workflow's check job with the
deployment the release will use, before any Azure sign-in. Only the global cap is used because every call is reserved against it.

The name-based check can be wrong, because deployment names are free text (T-100 M1). So the app also checks the model each reply
reports (`AzureOpenAI._check_reported_model`, table lookup by longest prefix with the date suffix dropped, `aicost.reported_model_price`).
A dearer model, or an unknown or missing one when no explicit price was set, logs one error (model name only) and sets the provider's
`disabled` flag for the process. The call that exposed it is recorded as normal; later summarise calls get 503 `ai_budget_reached`
(the exhausted-budget code the frontend already handles) until the config is fixed and the app restarts. An unknown model with an explicit
price is accepted, since that price is what the operator declared and the startup check used. The deploy-time check stays name-based.

## Monthly cost

Estimates (figures read for uksouth, checked against francecentral), one demo product plus the shared pieces.

| Resource | Settings | $ a month | Worked out from |
|---|---|---|---|
| `cae-studio` environment | Consumption profile only, no network of its own | 0 | no environment fee without Dedicated profiles, private endpoints or maintenance windows |
| `ca-starter` web app | 0.5 vCPU, 1 GiB, 0 to 1 replicas | 0 for the first ~100 active hours, then 0.076 per active hour | grant ÷ size; 0.5 × $0.000034 + 1 × $0.000004 per second |
| `caj-starter-migrate`, `caj-starter-purge` | 0.25 vCPU, 0.5 GiB, about a minute a run | 0 | inside the grant |
| Requests | | 0 | first 2 million a month free |
| `acrstudioznp96r` registry | Basic, 10 GiB included | 5.07 | $0.1666 a day; extra storage $0.10 per GB-month |
| `psql-studio-znp96r` Postgres | B1ms, 32 GB, 7-day backups, 7 days of server logs | 0 with the student allowance, **18.13** without | $0.019 an hour × 730, plus 32 GB × $0.133; backups and the server logs (which move to backup storage after an hour) beyond the allowance cost $0.10 per GB-month, and a demo's are far under 1 GB |
| `log-studio` | 30 days, 0.1 GB a day cap | 0 | ingestion free to 5 GB a month, then $2.88 per GB |
| `id-studio-acrpull` | | 0 | managed identities "at no extra cost" |
| Data out | | 0 | first 100 GB a month free, then $0.08 per GB |
| Azure OpenAI tokens | gpt-5-mini Global | 0 with `fake` (default); at most 6.10 with `azure` | 98,000 tokens a day × $2.00 per million × 31 days = $6.08, if every token were output; with gpt-5.4-pro (BUDGET.md) the guard allows only about 1,093 tokens a day, below one call, so AI is effectively off |

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
   page; register the resource providers; add the `STUDIO_DB_SEED` secret (superseded by ADR 0003); set `STUDIO_AZURE_APPROVED=yes`;
   after the first shared deploy, grant AcrPull with the one command the workflow prints.
3. **A smaller question (reversible):** does this GitHub account have Pro (for example through the Student
   Developer Pack)? If yes, the deploy secrets move into a main-only environment (decision 8).
4. **Not Vishal: the security gate** confirms decision 5's conditions and keeping the previous revision active
   (decision 9).

## How this meets SECURITY.md's deploy requirements (I7, I3, I4, D3, A3)

| Requirement | Here |
|---|---|
| Managed identity for image pulls | `id-studio-acrpull`, AcrPull, `lifecycle: None` |
| Key Vault or Container Apps secrets for the webhook secret and Stripe key | Container Apps secrets from secure parameters, always defined (decision 6) |
| Deploy principal scoped to `rg-ai-studio` | the existing Contributor service principal |
| Postgres not public, or firewalled to Container Apps egress; `sslmode=require` | **Accepted with conditions (decision 5).** TLS 1.3 with `verify-full` (stronger); firewall is Azure addresses; demo data only until T-18 or private networking |
| App role without DDL; migrations by a separate role and job | `<db>_app` and `<db>_migrator`; the migration job. Tested locally |
| Ingress `allowInsecure: false`; no public storage containers | yes; no storage account at all |
| Log Analytics retention of 30 days | yes, with immediate purge; no HTTP access logs (decision 11) |
| I1 and I4 settings | proxy settings as in the image; HSTS checked by the smoke test; HTML CSP comes with T-16 |
| Memory sized for the hashing bound (A3) | 1 GiB, where 2 hashing slots peak at about 225 MiB (re-test 3) |
| Trivy scan in the deploy workflow | yes, pinned by digest |
| ENV=prod on every internet-facing deploy (I3) | yes, for the app and both jobs |
| Daily retention purge (D3) | the scheduled job, on the live revision's image and email settings |

## Failure modes

| What goes wrong | What happens | What to do |
|---|---|---|
| The student allowance doesn't apply | Postgres costs $18.13 a month | The T-2 report shows it. Stop/start the server outside demo hours, or move to a fallback (decision 4) |
| The credit runs out | Azure disables the subscription and every demo goes down | Expected for demos only. No customer may depend on this subscription (safety.md). Handover moves hosting |
| An Azure read error at the start of a release | The release stops before anything changes | Run it again (decision 9, step 2) |
| First request after 5 idle minutes | A cold start: image pull plus app start | Acceptable for demos; the smoke test allows 3 minutes |
| A migration fails | Alembic rolls back that release's migrations; the old revision keeps serving | Fix and release again |
| A migration isn't backward compatible | A rollback can't help, because the old code meets the new schema | Expand/contract rule (decision 9); reviewers check each migration |
| A release passes but the purge job can't be moved | Traffic and the purge job go back to the previous revision | Run it again |
| A rollback can't move the purge job back | The run says so | `rollback_to` the revision that serves traffic |
| (superseded by ADR 0003) The seed changes without `deploy_shared` | The database step stops at once and says why | Rotation procedure (decision 6) |
| AcrPull not granted yet | The workflow stops early and prints the exact command | Vishal runs it once |
| A new CVE in the base image | Trivy fails the release | Rebuild later, or a justified `.trivyignore` entry; T-19 pins and refreshes the base image |
| Too many database connections | `too many clients` from Postgres | Per-role limits and small pools (decision 4); beyond about 3 products, connection pooling or a bigger SKU (approval) |
| Bots keep the app awake | Each wake costs at most about $0.006; always awake costs up to about $47 a month | Daily spend report; IP restrictions on ingress if it happens |
| Someone tries passwords on the database | Each attempt is logged on the server for 7 days | Read the server logs (runbook); T-18 removes passwords |

## Follow-ups

Already on the board: T-16 (serve the SPA from the backend: needed before any browser demo), T-17 (Azure
OpenAI through a managed identity), T-18 (passwordless Postgres, which ends decision 5's conditions), T-19
(pin the base image and actions), T-20 (compile the Bicep in CI). New:

1. After Vishal answers the plan question, optionally add a main-only GitHub environment and `environment:` to
   the deploy and rollback jobs (decision 8). This needs the extra federated credential described there first.
2. A registry cleanup that keeps the last few images per product (decision 3).
3. Only if the allowance doesn't apply: a stop/start schedule for Postgres.
4. The starter README's "Not done yet" line still describes T-7 as pending; point it at this ADR when T-7 merges.

## Sources (all read 2026-11-23)

- Container Apps billing (free grant, scale to zero, jobs, Dedicated management fee): https://learn.microsoft.com/en-us/azure/container-apps/billing
- Environment types, no environment cost on Consumption, 90-day idle deletion: https://learn.microsoft.com/en-us/azure/container-apps/environment
- Custom network: load balancer and public IPs billed: https://learn.microsoft.com/en-us/azure/container-apps/custom-virtual-networks
- Outbound IPs "might change over time": https://learn.microsoft.com/en-us/azure/container-apps/networking
- Ingress (TLS, HTTPS redirect, X-Forwarded-For rightmost hop): https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview
- Revisions and blue-green releases: https://learn.microsoft.com/en-us/azure/container-apps/revisions, https://learn.microsoft.com/en-us/azure/container-apps/blue-green-deployment
- Managed identities in Container Apps (identity endpoint, `identitySettings` lifecycle): https://learn.microsoft.com/en-us/azure/container-apps/managed-identity; image pulls: https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull
- Secrets (deleting a referenced secret, `listSecrets`, starting a job uses its secrets, Key Vault in production): https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets
- Log destinations and categories: https://learn.microsoft.com/en-us/azure/container-apps/log-options; the HTTP log table: https://learn.microsoft.com/en-us/azure/azure-monitor/reference/tables/containerapphttplogs; retention: https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure
- Container Apps October 2026 updates (meter renames, logging destination): https://github.com/microsoft/azure-container-apps/issues/1886; maintenance-window charge report: https://learn.microsoft.com/en-us/answers/questions/6066720/is-a-planned-maintenance-window-honored-and-billed
- Outbound IP list incomplete (user report, May 2026): https://learn.microsoft.com/en-us/answers/questions/5879132/azure-container-app-outbound-address
- Prices: Azure Retail Prices API (https://prices.azure.com/api/retail/prices, documented at https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices), read for uksouth (resources are in francecentral; see "Region (T-61)"), queried 2026-11-23. The pricing pages at azure.microsoft.com/pricing didn't render figures
- Azure for Students free services and terms: https://azure.microsoft.com/en-us/free/students/, https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/, https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students
- Postgres firewall ("Allow Azure services" warning): https://learn.microsoft.com/en-us/azure/postgresql/security/security-firewall-rules
- Postgres TLS (verify-full, root CAs, TLS 1.3): https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls
- Postgres limits (35 user connections on B1ms, no PgBouncer on Burstable, 7-day stop): https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/concepts-limits
- Postgres logging (log_connections and log_error_verbosity on PG 16, server log capture for 1 to 7 days): https://learn.microsoft.com/en-us/azure/postgresql/parameters/parameters-reporting-logging-what-log, https://learn.microsoft.com/en-us/azure/postgresql/monitor/how-to-configure-server-logs, https://learn.microsoft.com/en-us/azure/postgresql/monitor/concepts-logging
- Azure CLI exit code 3 for a missing resource in `show` commands: the azure-cli README and command guidelines (github.com/Azure/azure-cli)
- ACR tiers: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-skus; roles and who may assign them: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-rbac-built-in-roles-overview; ABAC mode: https://learn.microsoft.com/en-us/azure/container-registry/container-registry-rbac-abac-repository-permissions
- GHCR billing and tokens: https://docs.github.com/en/billing/concepts/product-billing/github-packages, https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
- GitHub environments by plan: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- Static Web Apps needs Standard for a Container Apps backend: https://learn.microsoft.com/en-us/azure/static-web-apps/apis-container-apps
- Azure OpenAI with Entra ID: https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/managed-identity
- Managed identities cost nothing extra: https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview
- Bicep schemas: containerApps and jobs 2025-07-01, managedEnvironments 2025-07-01, flexibleServers 2024-08-01, registries 2025-11-01 (learn.microsoft.com/azure/templates)
- Trivy 0.76.2 image digest: Docker Hub tag list for aquasec/trivy (hub.docker.com)

## Region (T-61)

Azure for Students only allows new resources in `francecentral`, `swedencentral`, `spaincentral`, `polandcentral`
and `italynorth`. `rg-ai-studio` is in `uksouth`, which is not on the list, and `main.bicep` and `shared.bicep`
default `location` to `resourceGroup().location`, so a deploy would have been refused by policy. Both
`.bicepparam` files now set `location = 'francecentral'` explicitly, and the deploy workflow's `az deployment group
create` calls take the values from those files, so nothing falls back to uksouth. The resource group's own region
only holds its metadata, so resources in `francecentral` inside a `uksouth` group are fine. `francecentral` was
chosen from the allowed list because it is the nearest to the UK and has every service used here (Container Apps
consumption, Postgres Flexible Server Burstable, ACR Basic, Log Analytics). Moving to another allowed region means
changing `location` in both param files and nothing else. Prices differ slightly by region; the francecentral figures were checked against the Azure Retail Prices API
(T-61 report) and belong in `state/BUDGET.md`.
