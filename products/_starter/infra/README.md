# Azure deploy for the starter (and every product copied from it)

Why it looks like this, with costs and sources: `../ADR/0002-azure-deploy.md`. This file is the runbook.

```
   you ──► GitHub Actions: _starter-deploy (manual)
              1 build image ─► 2 scan (Trivy) ─► 3 sign in to Azure ─► 4 read the live release (stop on errors)
              5 push by digest ─► 6 deploy main.bicep: new revision at 0% traffic, purge job unchanged
              7 migration job (alembic upgrade head)
              8 smoke-test the new revision ─► 9 move 100% traffic ─► 10 smoke-test the public URL
              11 only now: the purge job gets the new image
                    └── fails after step 9? traffic AND the purge job go back to the old revision

   rg-ai-studio, uksouth
     shared.bicep (once)                          main.bicep (every release, per product)
     ├─ cae-studio          Container Apps env    ├─ ca-<slug>             web app, scales 0 to 1
     ├─ acrstudioznp96r     registry (Basic)      ├─ caj-<slug>-migrate    migrations, run by the workflow
     ├─ id-studio-acrpull   pulls images          └─ caj-<slug>-purge      retention purge, daily 03:17 UTC,
     ├─ log-studio          logs, 30 days                                  on the live revision's image
     └─ psql-studio-znp96r  Postgres B1ms ── database <db>, roles <db>_migrator and <db>_app
```

## Files

| File | What it is |
|---|---|
| `shared.bicep`, `shared.bicepparam` | the shared studio resources. Deployed once, with `deploy_shared` ticked |
| `modules/postgres.bicep` | the shared Postgres server, used by `shared.bicep` |
| `main.bicep`, `main.bicepparam` | one product: web app, migration job, purge job. Deployed on every release |
| `db-setup.sql`, `db-grants.sql` | create a product's database and its two roles (run by the workflow) |
| `scram_verifier.py` | turns a password into the SCRAM verifier `db-setup.sql` sends, so no password reaches the server |
| `live-release.sh` | reads what a release starts from; any Azure read error stops the release |
| `purge-job.sh` | keeps the purge job on the image and email settings of the revision that serves traffic |
| `cost-guard.sh` | refuses compiled templates with features that have a fixed charge |
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
   First-deploy check: the Entra admin's `principalName` (`postgresEntraAdminName`, default
   `sp-ai-studio-deployer`) is a guess. Read it back (`az postgres flexible-server microsoft-entra-admin list`
   or the portal) and confirm ARM accepted it and which Postgres role name it created. Use that name when granting
   the app and migrate roles.
6. **Run the workflow again** with only **setup_database** ticked. This is the first real release. Its only
   revision takes traffic as soon as it is ready, a minute before its migration has run, so for that minute
   the API answers errors. Harmless before anyone uses it; later releases never do this.

## Releasing

- Actions → `_starter-deploy` → Run workflow on `main`. Or from a studio run:
  `gh workflow run _starter-deploy.yml --ref main -f ai_provider=fake`, then `gh run list --workflow
  _starter-deploy.yml` and `gh run view <id> --log`.
- Inputs:
  - `ai_provider`: `fake` (default, no cost) or `azure`. `azure` needs the `AZURE_OPENAI_*` secrets from
    SETUP.md step 3. It spends tokens, capped at 100,000 a day for all tenants together.
  - `billing_provider`: `mock` (default) or `stripe`, which is test mode only and needs the
    `STARTER_BILLING_WEBHOOK_SECRET` and `STARTER_STRIPE_SECRET_KEY` secrets.
  - `require_email_verification`: off by default **while email is outbox-only**, because nobody can receive
    the link. On, a demo can only sign up and write notes. Off, it can also use the AI, check out and invite
    (invitation links can't be delivered either). Turn it on, and keep it on, as soon as a real email provider
    exists: the app then refuses to start without it.
  - `mock_checkout`: shows the demo "Pay (test)" button. Off by default: it gives a paid plan away (with the
    trial's AI allowance).
  - `setup_database`: tick it on a product's first release, or when rotating the seed (below).
  - `deploy_shared`: only when `shared.bicep` changes, and only from the starter's workflow. Shared changes
    can cost money, so ask first.
- The run summary shows the public address, the new revision, the image digest, the previous revision and
  whether the purge job moved to the new image.

**Rule for migrations:** each migration must work with the code of the release before it. Add columns
first and drop them in a later release. A rollback moves traffic and the purge job; it never changes the
database. If a migration fails, Alembic rolls back all of that release's migrations together, so the schema
stays as it was.

## Rolling back

- Automatic: if anything fails after traffic moved (the public smoke test, the traffic move itself, or moving
  the purge job), traffic and the purge job go back to the previous revision in the same run. If anything
  fails before that, traffic never moved and the purge job was never changed.
- By hand: run the workflow with `rollback_to` set to a revision name from an earlier run summary, such as
  `ca-starter--r12a1-1a2b3c4`. It re-activates that revision, smoke-tests it, moves all traffic to it, then
  points the purge job at its image.
- The database stays on the newest migration either way (the rule above).
- The previous revision stays active with 0% traffic, which costs nothing while it has no replicas. Until the
  next release it is reachable at its own revision address, and it keeps its own in-process rate-limit
  counters, so it is a second bucket for anyone who knows that address. After a security fix, release once
  more so the vulnerable revision is retired.

## Rotating the database seed

Every database password comes from `STUDIO_DB_SEED`. The server admin password is set only by `deploy_shared`,
and each product's role passwords only by `setup_database`.

1. Vishal replaces the `STUDIO_DB_SEED` secret.
2. Run the **starter's** workflow with **deploy_shared** and **setup_database** both ticked. The admin password
   changes first, then the starter's roles, then its release goes out with the new passwords.
3. Run every other product's workflow with **setup_database** ticked. Until it runs, a product keeps working
   on its old passwords.

During each run, the revision being replaced can't open new database connections once its roles have the
new password, so expect a few minutes of errors. Revisions released before the rotation can't be rolled back
to afterwards: they hold the old passwords.

If the admin password and the seed disagree, the database step stops at once with "The server admin password
doesn't match STUDIO_DB_SEED": run step 2 again.

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
- The environment has only the literal Consumption profile and no network of its own: no Dedicated or GPU
  profile, private endpoint or planned maintenance window (each about $73 a month), and no custom network
  (about $25.55 a month). `cost-guard.sh` checks the compiled templates on every run.
- Postgres stays B1ms with 32 GB and autogrow off: the free allowance covers exactly that.
- The web app scales to zero, with at most one replica.
- The logs keep 30 days, capped at 0.1 GB a day.

## Reading the logs

- **App and jobs:** `log-studio`, tables `ContainerAppConsoleLogs` (what the code prints) and
  `ContainerAppSystemLogs` (revisions, probes, image pulls). The ingress's HTTP access log is deliberately
  not collected: it would store client IPs and full URLs, including sign-in tokens from email links.
- **Database sign-ins:** Postgres logs every connection attempt and every failed sign-in, and keeps the files
  for 7 days. They stay on the server, so a flood of failed attempts can't use up `log-studio`'s daily cap:
  ```bash
  az postgres flexible-server server-logs list --resource-group rg-ai-studio --server-name psql-studio-znp96r
  az postgres flexible-server server-logs download --resource-group rg-ai-studio --server-name psql-studio-znp96r --name <file>
  grep "password authentication failed" <file>   # the "connection received" line with the same session id has the address
  ```

## When something goes wrong

| You see | Likely cause | Fix |
|---|---|---|
| "AZURE_CREDENTIALS isn't set" notice | no deployer secret | SETUP.md step 3 |
| "need Vishal's approval first" notice | `STUDIO_AZURE_APPROVED` isn't `yes` | setup step 3 |
| "deploys run from main only" notice | dispatched on another branch | merge after review, then run on `main` |
| `MissingSubscriptionRegistration` | resource providers not registered | setup step 2 |
| "can't pull images yet" | AcrPull not granted | setup step 5 |
| "couldn't read ca-<slug> ... instead of guessing" | an Azure error (throttling, an expired sign-in) | run it again; nothing was changed |
| "no revision ... has 100% of the traffic" | traffic was split by hand | `rollback_to` the revision that should serve, then release |
| "has no working release yet: run this first release with setup_database" | first release of a product | tick `setup_database` |
| "The server admin password doesn't match STUDIO_DB_SEED" | the seed changed without `deploy_shared` | rotating the seed, step 2 |
| Trivy fails | a fixable HIGH or CRITICAL vulnerability in the image | rebuild later (new base image), or add the CVE id to `<product>/.trivyignore` with a comment saying why |
| Migration job `Failed` | a migration error; the old revision still serves and the schema is unchanged | read `ContainerAppConsoleLogs` in `log-studio`, fix, release again |
| "The purge job couldn't be pointed back" | an Azure error during a rollback | run `rollback_to` with the revision that serves traffic |
| `/healthz` answers `"db":"down"` | wrong database password, or the server is stopped | re-run with `setup_database`; start the server |
| A name "is already in use" | someone else owns `acrstudioznp96r` or `psql-studio-znp96r` | change the suffix in `shared.bicepparam`, `main.bicep` and the workflow env |
| A charge named "Environment Management Hour" | a Dedicated profile, private endpoint or maintenance window got added | remove it; see ADR decision 1 |
| "Couldn't remove the firewall rule gh-run-..." warning | an Azure error after a database setup | delete the rule with the command in the warning |

## Checks you can run without Azure

```bash
# against a local server (see the starter README): skips the https-only checks
bash products/_starter/infra/smoke.sh --local http://127.0.0.1:8000
# a compiled template (az bicep build --file main.bicep --outfile main.json)
bash products/_starter/infra/cost-guard.sh main.json
```

The workflow's first job compiles all four Bicep files and runs `cost-guard.sh` on every run, even without
credentials. Nothing here has run against Azure yet: the first real run is the real test of the templates.

## At handover

The business deploys `shared.bicep` into its own subscription with an Owner account, setting
`GRANT_PULL_ROLE=true` so the AcrPull role is created too. It then deploys `main.bicep`. Before any real
customer data arrives, Postgres must move to private networking or passwordless sign-in (T-18), and secrets
should move to Key Vault (ADR decisions 5 and 6).

`shared.bicep` makes whoever deploys it the Postgres Entra admin (`deployer()`). The default type is
`ServicePrincipal`, which fits the studio workflow. An Owner user deploying at handover must also set
`postgresEntraAdminType` to `User` (or `Group`), for example `--parameters postgresEntraAdminType=User`, and
`postgresEntraAdminName` to the role name they want, otherwise ARM rejects or mislabels the admin.
