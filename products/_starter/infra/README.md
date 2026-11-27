# Azure deploy for the starter (and every product copied from it)

Why it looks like this, with costs and sources: `../ADR/0002-azure-deploy.md`. This file is the runbook.

```
   you ──► GitHub Actions: _starter-deploy (manual)
              1 build image ─► 2 scan (Trivy) ─► 3 sign in to Azure ─► 4 read the live release (stop on errors)
              5 push by digest ─► 6 deploy main.bicep: new revision at 0% traffic, purge and cancels jobs unchanged
              6b database step: psql as the Entra admin (the deploy principal, token as password) runs
                 db-setup.sql: roles, identity mapping, grants (every release, no secret)
              7 migration job (alembic upgrade head)
              8 smoke-test the new revision ─► 9 move 100% traffic ─► 10 smoke-test the public URL
              11 only now: the purge and cancels jobs get the new image
                    └── fails after step 9? traffic AND both jobs go back to the old revision

   rg-ai-studio (group metadata in uksouth; resources in francecentral)
     shared.bicep (once)                          main.bicep (every release, per product)
     ├─ cae-studio          Container Apps env    ├─ ca-<slug>             web app, scales 0 to 1
     ├─ acrstudioznp96r     registry (Basic)      ├─ caj-<slug>-migrate    migrations, run by the workflow
     ├─ id-studio-acrpull   pulls images          ├─ caj-<slug>-purge      retention purge, daily 03:17 UTC,
     ├─ log-studio          logs, 30 days                                  on the live revision's image
     │                                              └─ caj-<slug>-cancels    retries failed subscription cancels,
     └─ psql-studio-znp96r  Postgres B1ms ──                                 every 30 min (T-176), same image
                        database <db>, roles <db>_migrator and <db>_app
```

## Files

| File | What it is |
|---|---|
| `shared.bicep`, `shared.bicepparam` | the shared studio resources. Deployed once, with `deploy_shared` ticked |
| `modules/postgres.bicep` | the shared Postgres server, used by `shared.bicep` |
| `main.bicep`, `main.bicepparam` | one product: web app, migration job, purge job, cancels job. Deployed on every release |
| `db-setup.sql`, `db-grants.sql` | create a product's database and its two passwordless roles, mapped to the product's identities (run by the workflow; keep the two files side by side) |
| `jwt-oid.sh` | prints the object id inside an Entra token (stdin), so the workflow can find its own Entra admin entry |
| `deploy-role.bicep`, `test-deploy-role.sh` | the least-privilege custom role for the deploy identity (T-65, not applied yet) and its static check |
| `test-db-setup.sh`, `test-deploy-workflow.sh`, `test-bicep-identities.sh` | checks that run without Azure (CI) |
| `live-release.sh` | reads what a release starts from; any Azure read error stops the release |
| `purge-job.sh` | keeps the purge job and the cancels job on the image and email settings of the revision that serves traffic |
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
3. **Add one setting in GitHub** (repo → Settings → Secrets and variables → Actions): the variable
   (Variables tab, not Secrets) `STUDIO_AZURE_APPROVED` = `yes`. This is your approval. Without it the
   workflow only checks the templates. There is no database secret: sign-in is Microsoft Entra (ADR 0003).
4. **First run:** Actions → `_starter-deploy` → Run workflow on `main`, with **deploy_shared** ticked. It also
   makes the deploy principal the server's Entra admin and sets a random, throwaway admin password that
   nobody ever sees. It creates the shared resources (Postgres takes 5 to 10 minutes). It then
   stops at "Shared resources exist and the app can pull images" and prints one command.
5. **Grant image pulls.** Run that printed command in Cloud Shell. It looks like:
   ```bash
   az role assignment create --assignee-object-id <principal id> --assignee-principal-type ServicePrincipal \
     --role AcrPull --scope /subscriptions/<sub>/resourceGroups/rg-ai-studio/providers/Microsoft.ContainerRegistry/registries/acrstudioznp96r
   ```
   First-deploy check: the Entra admin's `principalName` (`postgresEntraAdminName`, default
   `id-github-deploy`) is a guess. Read it back (`az postgres flexible-server microsoft-entra-admin list`
   or the portal) and confirm ARM accepted it and which Postgres role name it created. Use that name when granting
   the app and migrate roles (the deploy workflow signs in to Postgres as that role).
6. **Run the workflow again** with nothing ticked. This is the first real release. It deploys, then creates
   the database and roles as the Entra admin, then migrates. Its only revision takes traffic as soon as it is
   ready, before the roles and migration exist, so for that minute the API answers errors. Harmless before
   anyone uses it; later releases never do this.
7. **Phase 2 (ADR 0003, decision 2) is in force:** `postgresPasswordAuth` is `Disabled` in `shared.bicepparam`
   and as the default in `shared.bicep` and `modules/postgres.bicep`, and `dbAuth` defaults to `entra`. Every
   release runs `check-auth-config.sh` (before the image is pushed) and stops unless the server shows
   `activeDirectoryAuth=Enabled` and `passwordAuth=Disabled`. The server is created with passwords off from the first
   `deploy_shared`. If the Entra admin step fails there, nobody can sign in, but the admin is set through the
   management plane, so fix the cause and re-run `deploy_shared`. Check with
   `az postgres flexible-server microsoft-entra-admin list --resource-group rg-ai-studio --server-name <server>`:
   it must list exactly the deploy service principal.

## Releasing

- Actions → `_starter-deploy` → Run workflow on `main`. Or from a studio run:
  `gh workflow run _starter-deploy.yml --ref main -f ai_provider=fake`, then `gh run list --workflow
  _starter-deploy.yml` and `gh run view <id> --log`.
- Inputs:
  - `ai_provider`: `fake` (default, no cost) or `azure`. `azure` needs the `AZURE_OPENAI_*` secrets from
    SETUP.md step 3. It spends tokens, capped at 98,000 a day for all tenants together.
  - `billing_provider`: `mock` (default) or `stripe`, which is test mode only and needs the
    `STARTER_BILLING_WEBHOOK_SECRET` and `STARTER_STRIPE_SECRET_KEY` secrets.
    The Stripe webhook endpoint must be subscribed to `checkout.session.completed`,
    `checkout.session.async_payment_succeeded`, `customer.subscription.created`, `.updated` and `.deleted`;
    without the two checkout events paying customers stay on the trial (see the product README, Billing).
  - `require_email_verification`: off by default **while email is outbox-only**, because nobody can receive
    the link. On, a demo can only sign up and write notes. Off, it can also use the AI, check out and invite
    (invitation links can't be delivered either). Turn it on, and keep it on, as soon as a real email provider
    exists: the app then refuses to start without it.
  - `mock_checkout`: shows the demo "Pay (test)" button. Off by default: it gives a paid plan away (with the
    trial's AI allowance).
  - `deploy_shared`: only when `shared.bicep` changes, and only from the starter's workflow. Shared changes
    can cost money, so ask first.
- The run summary shows the public address, the new revision, the image digest, the previous revision and
  whether the purge and cancels jobs moved to the new image.

**Rule for migrations:** each migration must work with the code of the release before it. Add columns
first and drop them in a later release. A rollback moves traffic and the purge and cancels jobs; it never changes the
database. If a migration fails, Alembic rolls back all of that release's migrations together, so the schema
stays as it was.

## Least-privilege deploy role (T-65)

> **Status: written, NOT APPLIED.** `id-github-deploy` still holds the built-in Contributor role on `rg-ai-studio`.
> Nothing here has run against Azure. Until Vishal does the steps below, nothing changes.

`deploy-role.bicep` defines a custom role, "Studio Deployer (rg-ai-studio)", assignable on `rg-ai-studio` only. It
lists the exact actions the deploy and spend workflows use, each commented with the step that needs it. It can't
grant access (read-only on role assignments and definitions, `Microsoft.Authorization/*/write` in `notActions`), can't touch
federated credentials, can't register providers or delete the group, and has one delete: the runner's temporary
Postgres firewall rule. `bash infra/test-deploy-role.sh` checks all this without Azure (it runs in CI).

### Vishal's one-time steps (Cloud Shell, you are Owner)

1. Create the role and give it to the identity (the role is created first, so the identity briefly has both):
   ```bash
   cd products/_starter/infra   # or paste the file into Cloud Shell
   PRINCIPAL=$(az identity show -g rg-ai-studio -n id-github-deploy --query principalId -o tsv)
   az deployment group create -g rg-ai-studio --name studio-deploy-role -f deploy-role.bicep \
     -p assign=true deployPrincipalId="$PRINCIPAL"
   ```
2. Prove the new role works before removing the old one: remove Contributor, then run the deploy workflow once
   from `main` (with `deploy_shared` ticked once, since that touches the most resource types), see "Risks" below
   for what a failure looks like. Don't test with both roles assigned: Contributor hides every missing action, so that run proves nothing.
   ```bash
   SCOPE=$(az group show -n rg-ai-studio --query id -o tsv)
   az role assignment delete --assignee "$PRINCIPAL" --role Contributor --scope "$SCOPE"
   az role assignment list --assignee "$PRINCIPAL" --all --include-inherited -o table   # only "Studio Deployer ..." should remain (also checks Contributor given higher up)
   ```
3. Tell the studio it is applied, so ADR 0002, SECURITY.md and this section can drop "not applied".

### Residual risks (security review T-65, accepted for now)

- `containerApps/write` and `jobs/write` let the deployer run any image with the app's identities. That is what a
  deploy role is for; the control is who can change workflows on `main` (T-62: `production` environment with a
  required reviewer, ruleset on `.github/workflows/**`).
- `userAssignedIdentities/assign/action` also covers `id-github-deploy` itself, because it lives in `rg-ai-studio`:
  a malicious workflow could attach it to an app and keep deploy rights after the federated credential is removed.
  Contributor allows the same today. Fix later (T-69): move `id-github-deploy` to its own resource group.
- `flexibleServers/write`, `administrators/write` and firewall rules are only needed for the shared deploy
  (`deploy_shared`). T-69 splits them into a separate shared role behind the reviewed environment.
- The spend report uses its own read-only identity `id-github-spend` (Reader + Cost Management Reader on
  `rg-ai-studio`; SETUP.md step 3) when `AZURE_SPEND_CLIENT_ID` is set. Until then it falls back to the deploy
  identity, then to the `AZURE_COST_CREDENTIALS` service principal, which this role does not cover. Removing that
  fallback is the follow-up after one green run with the spend identity.
- Once the spend identity is live, both `Microsoft.CostManagement/query/action` and `Microsoft.CostManagement/query/read`
  in `deploy-role.bicep` can be dropped (the deploy identity no longer runs the cost query). Not changed yet.

### The cancels job (T-176)

`caj-<slug>-cancels` runs `python -m app.maintenance cancels` every 30 minutes (`cancelsSchedule`, UTC cron). It
retries subscription cancels that failed after a new checkout replaced a lapsed subscription, so they finish even
when the tenant has no more billing events, or was deleted. It is the purge job's twin: same image (the `purge*`
parameters), same app identity and database URL (rows only), same follow-the-live-revision rule (`purge-job.sh`).
It differs in three ways: it gets this release's `BILLING_PROVIDER` and the two Stripe secrets, which are always defined
(a placeholder when unset; it calls the payment provider, the purge job does not); the replica timeout is 15 minutes (each cancel can take about 17 s),
shorter than the schedule so runs never overlap; and it never calls the AI. Cost: job execution seconds only
(`state/BUDGET.md`). The deploy role's `jobs/write` already covers it. To see failures, search the logs for
`pending cancel could not be processed` (ERROR). A rollback restores the cancels job's billing provider too: `purge-job.sh follow`
copies `BILLING_PROVIDER` from the revision that serves traffic (the purge job stays on `mock`).

The 10th failed attempt on a row logs one `pending cancel needs operator` line (CRITICAL). The log line is at most once, so the
table is the source of truth. Rows that need an operator:

```sql
SELECT id, ref, attempts FROM pending_cancels WHERE attempts >= 10;
```
Cancel the subscription by hand at the provider, then delete the row.

## Rolling back

```bash
az role assignment create --assignee-object-id "$PRINCIPAL" --assignee-principal-type ServicePrincipal \
  --role Contributor --scope "$SCOPE"
```
Contributor is back at once (allow a few minutes for Azure to pick it up). Leave the custom role in place; it does
nothing unassigned. To remove it too: `az role assignment delete` the "Studio Deployer" assignment, then
`az role definition delete --name "Studio Deployer (rg-ai-studio)"`.

### Adding a missing action

A failed step says `AuthorizationFailed ... does not have authorization to perform action '<X>'`. Add exactly `<X>`
to `actions` in `deploy-role.bicep`, with a comment naming the step, rerun `test-deploy-role.sh` and step 1's
deployment (it updates the same role, because the name is a fixed guid). Never add a wildcard.
A new resource type in the templates fails `test-deploy-role.sh` until its actions are added.

### Risks (written from the templates and `az` commands, not seen running)

- **Unsure, likely fine:** the `Microsoft.App/locations/*OperationResults|OperationStatuses/read` and
  `Microsoft.DBforPostgreSQL/locations/*` and `Microsoft.ContainerRegistry/locations/operationResults/read` entries
  (async polling) are listed from Azure's provider operation list; if one is not needed it is harmless, and if a
  different one is needed the error names it.
- **Unsure:** `Microsoft.CostManagement/query/action` and `/read`. The spend report posts a query at resource group scope;
  Azure documents the `query/action` form, so both are kept. If `azure-spend.yml` uses the separate
  `AZURE_COST_CREDENTIALS` fallback, that identity is not covered by this role.
- **Unsure:** Postgres `administrators/write` may also ask for an action on the identity (the Entra admin is the deploy
  identity itself); the error would say so. The first Entra admin creation is the likeliest place.
- **Not included on purpose:** `listSecrets`, `listCredentials`, `sharedKeys`, `federatedIdentityCredentials`, `databases/*`,
  `roleAssignments/write` (shared.bicep `pullRole` stays off, `grantPullRole=false`: AcrPull is still Vishal's one-time
  step), deployment deletes, resource group writes. If `GRANT_PULL_ROLE=true` is ever used the deploy will fail on purpose.
- Contributor also allowed things the templates don't use (for example deleting resources). Anything a future
  feature needs shows up as one named `AuthorizationFailed`, a failed deploy rather than a security hole.
- Azure caches role changes for up to about 10 minutes per token: after step 2 sign in again (a new run does).

## Rolling back

- Automatic: if anything fails after traffic moved (the public smoke test, the traffic move itself, or moving
  the purge and cancels jobs), traffic and both jobs go back to the previous revision in the same run. If anything
  fails before that, traffic never moved and the jobs were never changed.
- By hand: run the workflow with `rollback_to` set to a revision name from an earlier run summary, such as
  `ca-starter--r12a1-1a2b3c4`. It re-activates that revision, smoke-tests it, moves all traffic to it, then
  points the purge and cancels jobs at its image.
- The database stays on the newest migration either way (the rule above).
- The previous revision stays active with 0% traffic, which costs nothing while it has no replicas. Until the
  next release it is reachable at its own revision address, and it keeps its own in-process rate-limit
  counters, so it is a second bucket for anyone who knows that address. After a security fix, release once
  more so the vulnerable revision is retired.

## Database sign-in (Entra, ADR 0003)

There is nothing to rotate: no database password exists for the app or the migrator. Each release signs in to
Postgres as the deploy principal (its Entra token is the password, passed only through `PGPASSWORD` and
masked) and re-applies `db-setup.sql`. The roles `<db>_app` and `<db>_migrator` have `PASSWORD NULL` and are
mapped to the object ids of `id-<slug>-app` and `id-<slug>-migrate`, so only a token for that identity works.

- **Cut a role off at once:** as the admin, `ALTER ROLE <db>_app NOLOGIN`. To replace an identity: `NOLOGIN`
  first (cached managed-identity tokens live up to 24 hours), delete the identity, then release: it
  recreates it with a new object id, re-labels the role and sets `LOGIN`.
- **The deploy principal was recreated** (new object id): run `deploy_shared` so it becomes an admin, remove
  the old `administrators` entry through ARM (the release stops while any other admin is listed), and from the
  old admin run `GRANT <role> TO <new admin> WITH ADMIN OPTION` for every product role (PostgreSQL 16 only
  gives ADMIN OPTION to the creator), then `ALTER DATABASE ... OWNER TO` the new admin role.

### First-deploy checklist (only Azure can show these; record the answers in the T-18 review)

1. The Contributor deploy principal can create the `administrators` child (`deployer()`).
2. An Entra admin may run `SECURITY LABEL FOR "pgaadauth"` and `GRANT <role> TO CURRENT_USER WITH INHERIT
   FALSE, SET TRUE` (fallback: `pgaadauth_create_principal_with_oid`).
3. `pgaadauth_list_principals`: the column casing, `principalType` is exactly `service` for a managed identity,
   `(true)` lists the deploy principal under the name `current_user` returns and nothing else, an unqualified
   call resolves to Azure's function, and a new label replaces the old mapping.
4. Container Apps jobs get a user-assigned token with `lifecycle: Main`; `/healthz` says `"db":"ok"`.
5. `rolpassword IS NULL` for both roles, and a sign-in as `<db>_app` with the migrator identity's token is refused.
6. The deploy step finishes on a first release while `/healthz` is down. The web container's readiness probe is
   `/healthz`, which checks the database, and on a first release the roles only exist after the database step. If
   `main.bicep` fails there ("Operation expired" or no ready replica), do not retry the same run. Fallback: run
   once with the readiness probe path temporarily set to `/livez` (or the probe removed), let the database step
   create the roles, then release again with `/healthz` restored. Record which case happened in the T-18 review.

## Making a product from the starter

1. Copy this folder with the product. Leave `shared.bicep` and `modules/` as they are: the shared resources
   already exist. Never tick `deploy_shared` from a product's workflow.
2. In `main.bicepparam`, set `appName` to the product slug: lowercase letters, digits and hyphens, at most
   19 characters.
3. Copy the workflow to `.github/workflows/<slug>-deploy.yml` and change the env block: `PRODUCT`,
   `PRODUCT_DIR`, `DB_NAME` (letters, digits and underscores), and the `STARTER_*` Stripe secret names.
4. Add rows for `ca-<slug>`, `caj-<slug>-migrate`, `caj-<slug>-purge` and `caj-<slug>-cancels` to `state/BUDGET.md` before the first
   release. The database step runs on every release, so there is nothing to tick.

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
| "AZURE_CLIENT_ID, ... secrets aren't all set" notice | no OIDC secrets | SETUP.md step 3 |
| "AZURE_CLIENT_ID is set but AZURE_TENANT_ID or AZURE_SUBSCRIPTION_ID is missing" error | half the OIDC secrets were added | add the missing secret (SETUP.md step 3) |
| "AADSTS700213" or "No matching federated identity record" at sign-in | the run is not on `main`, or the job uses `environment:` | run from main; or add a federated credential for that subject (SETUP.md step 3) |
| "need Vishal's approval first" notice | `STUDIO_AZURE_APPROVED` isn't `yes` | setup step 3 |
| "deploys run from main only" notice | dispatched on another branch | merge after review, then run on `main` |
| `MissingSubscriptionRegistration` | resource providers not registered | setup step 2 |
| "can't pull images yet" | AcrPull not granted | setup step 5 |
| "couldn't read ca-<slug> ... instead of guessing" | an Azure error (throttling, an expired sign-in) | run it again; nothing was changed |
| "no revision ... has 100% of the traffic" | traffic was split by hand | `rollback_to` the revision that should serve, then release |
| "main.bicep's identity object ids are missing" | the deploy step's outputs lack the two principal ids | check `main.bicep` outputs `appIdentityPrincipalId`, `migrateIdentityPrincipalId` |
| "has Entra admins besides the deploy principal" | someone added an admin (Bicep never removes one) | remove the extra `administrators` entry through ARM, release again |
| "has characters this workflow doesn't allow" (the Entra admin name) | `postgresEntraAdminName` holds something outside letters, digits and `_ . @ - ` or is over 63 characters | set it to `id-github-deploy` (an Owner's UPN when the type is `User`) and run with `deploy_shared` ticked |
| "is not an Entra admin of psql-studio-..." or "refused the deploy principal's token" | `deploy_shared` never ran since T-18, or the principal was recreated | run with `deploy_shared` ticked |
| Trivy fails | a fixable HIGH or CRITICAL vulnerability in the image | rebuild later (new base image), or add the CVE id to `<product>/.trivyignore` with a comment saying why |
| Migration job `Failed` | a migration error; the old revision still serves and the schema is unchanged | read `ContainerAppConsoleLogs` in `log-studio`, fix, release again |
| "The purge job couldn't be pointed back" | an Azure error during a rollback | run `rollback_to` with the revision that serves traffic |
| `/healthz` answers `"db":"down"` | role not mapped to the identity, or the server is stopped | release again (re-applies the mapping); start the server |
| A name "is already in use" | someone else owns `acrstudioznp96r` or `psql-studio-znp96r` | change the suffix in `shared.bicepparam`, `main.bicep` and the workflow env |
| A charge named "Environment Management Hour" | a Dedicated profile, private endpoint or maintenance window got added | remove it; see ADR decision 1 |
| "Couldn't remove the firewall rule gh-run-..." warning | an Azure error after the database step | delete the rule with the command in the warning |

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
`postgresEntraAdminName` to the role name they want, otherwise ARM rejects or mislabels the admin. When `postgresEntraAdminType` is `User`,
`postgresEntraAdminName` must be the Owner's UPN (for example `owner@business.com`).
