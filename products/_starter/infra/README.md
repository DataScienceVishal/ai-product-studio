# Azure deploy for the starter (and every product copied from it)

Why it looks like this, with costs and sources: `../ADR/0002-azure-deploy.md`. This file is the runbook.

```
   you ──► GitHub Actions: _starter-deploy (manual)
              1 build image ─► 2 scan (Trivy) ─► 3 sign in to Azure ─► 4 push by digest
              5 deploy main.bicep: new revision, 0% traffic
              6 migration job (alembic upgrade head)
              7 smoke-test the new revision ─► 8 move 100% traffic ─► 9 smoke-test the public URL
                                                    └── fails? traffic goes back to the old revision

   rg-ai-studio, uksouth
     shared.bicep (once)                          main.bicep (every release, per product)
     ├─ cae-studio          Container Apps env    ├─ ca-<slug>             web app, scales 0 to 1
     ├─ acrstudioznp96r     registry (Basic)      ├─ caj-<slug>-migrate    migrations, run by the workflow
     ├─ id-studio-acrpull   pulls images          └─ caj-<slug>-purge      retention purge, daily 03:17 UTC
     ├─ log-studio          logs, 30 days
     └─ psql-studio-znp96r  Postgres B1ms ── database <db>, roles <db>_migrator and <db>_app
```

## Files

| File | What it is |
|---|---|
| `shared.bicep`, `shared.bicepparam` | the shared studio resources. Deployed once, with `deploy_shared` ticked |
| `modules/postgres.bicep` | the shared Postgres server, used by `shared.bicep` |
| `main.bicep`, `main.bicepparam` | one product: web app, migration job, purge job. Deployed on every release |
| `db-setup.sql`, `db-grants.sql` | create a product's database and its two roles (run by the workflow) |
| `smoke.sh` | the release smoke test; also runs against a local server with `--local` |
| `../../../.github/workflows/_starter-deploy.yml` | the only way anything here reaches Azure |

Secrets are never written in these files. The `.bicepparam` files read them from the workflow's environment,
and Azure receives them as secure parameters that become Container Apps secrets.

## Before the first deploy (Vishal, once, about 10 minutes)

Nothing here costs money until step 4. Do the steps only after approving the costs in `state/BUDGET.md`.

1. **Check the free allowance.** In the Azure portal, search for **Free services**. If it lists *Azure
   Database for PostgreSQL* (750 hours of B1MS), Postgres is free for those 12 months. Tell the studio what
   the page shows, including *Container Registry* if it's there.
2. **Register the resource providers.** The deployer can't do this, because it can only touch
   `rg-ai-studio`. In Cloud Shell (Bash):
   ```bash
   for ns in Microsoft.App Microsoft.ContainerRegistry Microsoft.DBforPostgreSQL \
             Microsoft.OperationalInsights Microsoft.ManagedIdentity Microsoft.Insights; do
     az provider register --namespace "$ns"
   done
   ```
3. **Add two settings in GitHub** (repo → Settings → Secrets and variables → Actions):
   - Secret `STUDIO_DB_SEED`: 64 random hex characters, for example from `openssl rand -hex 32` in Cloud
     Shell. Every database password is derived from it, so nobody ever types or stores one. Don't paste it
     anywhere else.
   - Variable (Variables tab, not Secrets) `STUDIO_AZURE_APPROVED` = `yes`. This is your approval. Without
     it the workflow only checks the templates.
4. **First run:** Actions → `_starter-deploy` → Run workflow on `main`, with **deploy_shared** and
   **setup_database** ticked. It creates the shared resources (Postgres takes 5 to 10 minutes). It then
   stops at "Shared resources exist and the app can pull images" and prints one command.
5. **Grant image pulls.** Run that printed command in Cloud Shell. It looks like:
   ```bash
   az role assignment create --assignee-object-id <principal id> --assignee-principal-type ServicePrincipal \
     --role AcrPull --scope /subscriptions/<sub>/resourceGroups/rg-ai-studio/providers/Microsoft.ContainerRegistry/registries/acrstudioznp96r
   ```
6. **Run the workflow again** with only **setup_database** ticked. This is the first real release.

## Releasing

- Actions → `_starter-deploy` → Run workflow on `main`. Or from a studio run:
  `gh workflow run _starter-deploy.yml --ref main -f ai_provider=fake`, then `gh run list --workflow
  _starter-deploy.yml` and `gh run view <id> --log`.
- Inputs:
  - `ai_provider`: `fake` (default, no cost) or `azure`. `azure` needs the `AZURE_OPENAI_*` secrets from
    SETUP.md step 3 and spends tokens, capped at 100,000 a day.
  - `billing_provider`: `mock` (default) or `stripe`, which is test mode only and needs the
    `STARTER_BILLING_WEBHOOK_SECRET` and `STARTER_STRIPE_SECRET_KEY` secrets.
  - `setup_database`: tick it on a product's first release, or after `STUDIO_DB_SEED` changes.
  - `deploy_shared`: only when `shared.bicep` changes. Shared changes can cost money, so ask first.
- The run summary shows the public address, the new revision, the image digest and the previous revision.

**Rule for migrations:** each migration must work with the code of the release before it. Add columns
first and drop them in a later release. A rollback moves traffic; it never downgrades the database.

## Rolling back

- Automatic: if the new revision fails its public smoke test, traffic goes back to the previous revision in
  the same run. If anything fails before that, traffic never moved.
- By hand: run the workflow with `rollback_to` set to a revision name from an earlier run summary, such as
  `ca-starter--r12a1-1a2b3c4`. It re-activates that revision, smoke-tests it, then moves all traffic to it.
- The previous revision stays active with 0% traffic, which costs nothing while it has no replicas. It is
  reachable at its own revision address until the next release. After a security fix, release once more so
  the vulnerable revision is retired.

## Making a product from the starter

1. Copy this folder with the product. Leave `shared.bicep` and `modules/` as they are: the shared resources
   already exist. Never tick `deploy_shared` from a product's workflow.
2. In `main.bicepparam`, set `appName` to the product slug: lowercase letters, digits and hyphens, at most
   19 characters.
3. Copy the workflow to `.github/workflows/<slug>-deploy.yml` and change the env block: `PRODUCT`,
   `PRODUCT_DIR`, `DB_NAME` (letters, digits and underscores), and the `STARTER_*` Stripe secret names.
4. Add rows for `ca-<slug>`, `caj-<slug>-migrate` and `caj-<slug>-purge` to `state/BUDGET.md` before the first
   release, which runs with `setup_database` ticked.

## Costs

The estimates and their sources are in the ADR. In short: about $5.07 a month with the student free
allowance and $23.20 without it, for the shared pieces plus one product. Each product shares the same
Container Apps free grant (about 100 active hours a month at 0.5 vCPU and 1 GiB).

Rules the templates keep. Breaking one changes the bill:
- The environment has only the Consumption profile: no Dedicated profile, private endpoint or planned
  maintenance window, each of which costs about $73 a month. The workflow checks for them.
- Postgres stays B1ms with 32 GB and autogrow off: the free allowance covers exactly that.
- The web app scales to zero, with at most one replica.
- The logs keep 30 days, capped at 0.1 GB a day.

## When something goes wrong

| You see | Likely cause | Fix |
|---|---|---|
| "AZURE_CREDENTIALS isn't set" notice | no deployer secret | SETUP.md step 3 |
| "need Vishal's approval first" notice | `STUDIO_AZURE_APPROVED` isn't `yes` | setup step 3 |
| "deploys run from main only" notice | dispatched on another branch | merge after review, then run on `main` |
| `MissingSubscriptionRegistration` | resource providers not registered | setup step 2 |
| "can't pull images yet" | AcrPull not granted | setup step 5 |
| "doesn't exist yet: run this first deploy with setup_database" | first release of a product | tick `setup_database` |
| Trivy fails | a fixable HIGH or CRITICAL vulnerability in the image | rebuild later (new base image), or add the CVE id to `<product>/.trivyignore` with a comment saying why |
| Migration job `Failed` | a migration error; the old revision still serves | read `ContainerAppConsoleLogs` in `log-studio`, fix, release again |
| `/healthz` answers `"db":"down"` | wrong database password, or the server is stopped | re-run with `setup_database`; start the server |
| A name "is already in use" | someone else owns `acrstudioznp96r` or `psql-studio-znp96r` | change the suffix in `shared.bicepparam`, `main.bicep` and the workflow env |
| A charge named "Environment Management Hour" | a Dedicated profile, private endpoint or maintenance window got added | remove it; see ADR decision 1 |

## Checks you can run without Azure

```bash
# against a local server (see the starter README): skips the https-only checks
bash products/_starter/infra/smoke.sh --local http://127.0.0.1:8000
```

The workflow's first job compiles all four Bicep files on every run, even without credentials. Nothing here
has run against Azure yet: the first real run is the real test of the templates.

## At handover

The business deploys `shared.bicep` into its own subscription with an Owner account, setting
`GRANT_PULL_ROLE=true` so the AcrPull role is created too. It then deploys `main.bicep`. With a real budget,
switch Postgres to private networking and move secrets to Key Vault (ADR decisions 5 and 6).
