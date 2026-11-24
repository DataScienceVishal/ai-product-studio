# ADR 0003: Passwordless Postgres sign-in with Microsoft Entra ID

- Status: accepted. Build slices 1 to 6 done (slice 6, phase 2: password sign-in `Disabled` and the every-release
  `authConfig` check, 2026-11-24); slice 7 (OIDC) waits for Q-8. Proposed 2026-11-24, board task T-18. Supersedes the password parts of ADR 0002 decisions 4, 5
  (condition 1), 6 (`DATABASE_URL`, seed rotation) and 9 (the seed caveats). Everything else in 0002 stands.
  Revised 2026-11-24 after the security gate (`reviews/T-18-adr-security.md`): B1 to B3 fixed, N1 to N11 folded in.
- Builds on the app side being written in parallel: `DB_AUTH=entra` makes the app and `migrations/env.py`
  fetch a token for `https://ossrdbms-aad.database.windows.net` from the Container Apps identity endpoint
  (`ManagedIdentityToken`, `AZURE_CLIENT_ID`) and pass it as the password in SQLAlchemy `do_connect`. The URL
  has no password and keeps `sslmode=verify-full`. `DB_AUTH=password` (default) stays for local and CI.
- Nothing exists in Azure yet (`state/BUDGET.md`: all "planned"), so there is no live data to migrate. The
  password sign-in is off from the first deploy (decision 2).

## The picture

```
 GitHub Actions (deploy SP sp-ai-studio-deployer, Contributor on rg-ai-studio)
   │ az account get-access-token --resource-type oss-rdbms      (token = password, 5-60 min)
   ▼
 psql as the Entra admin ──► db-setup.sql: roles, labels, grants ──┐
                                                                    ▼
 ┌ cae-studio ─────────────────────────────────┐   ┌ psql-studio-znp96r ────────────────────┐
 │ ca-<slug>         ── id-<slug>-app ─────────┼──►│ role <db>_app      (DML, limit 12)      │
 │ caj-<slug>-purge  ── id-<slug>-app ─────────┼──►│   label: oid of id-<slug>-app           │
 │ caj-<slug>-migrate── id-<slug>-migrate ─────┼──►│ role <db>_migrator (owns tables, lim 3) │
 │ (all three also: id-studio-acrpull, lifecycle None, for image pulls only)            │
 └─────────────────────────────────────────────┘   │ admin: the deploy SP (Entra)            │
   each container: IDENTITY_ENDPOINT ─► token        │ passwordAuth: Enabled ─► Disabled       │
   for its own identity only                         └─────────────────────────────────────────┘
```

A token is a password that Entra issues, signs and expires. Postgres checks that the token is for its
audience (shared by every Azure Postgres server), from our tenant, and for the object id written on the
role; the last two are what make it ours. No long-lived *database* secret exists; the deploy SP's own
credential is the one that remains (decision 5).

## Decisions

### 1. Identities: two user-assigned identities per product, created by main.bicep

| Option | Why not / why |
|---|---|
| System-assigned identity on each app and job | Three identities per product; an object id only exists after the resource does, and changes if it is recreated |
| One identity for app, purge and migrator | The web process could then sign in as the table owner (DDL). Breaks 0002's two-role model |
| **`id-<slug>-app` (web + purge) and `id-<slug>-migrate` (migration job only), chosen** | Matches the two database roles one to one. Stable object ids across releases and rollbacks |

- **Bicep** (`main.bicep`, every release, idempotent): `Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31`
  named `id-<slug>-app` and `id-<slug>-migrate`. Each resource gets the pull identity plus exactly one DB
  identity in `identity.userAssignedIdentities`, and `identitySettings` keeps the pull identity on
  `lifecycle: None` and gives the DB identity `lifecycle: Main` (main containers only; the default is `All`).
  - `ca-<slug>` and `caj-<slug>-purge`: `id-<slug>-app`, env `DB_AUTH=entra`, `AZURE_CLIENT_ID=<app clientId>`.
  - `caj-<slug>-migrate`: `id-<slug>-migrate`, env `DB_AUTH=entra`, `AZURE_CLIENT_ID=<migrate clientId>`.
  - Outputs: both identities' `principalId` (the object id Postgres maps) and `clientId`.
- **The purge job shares the app identity** because it signs in as `<db>_app` with identical privileges; a
  third identity would add a role and connection budget without removing any privilege. Once T-17 grants
  the OpenAI role to this identity, the purge job could call OpenAI too; it runs with `AI_PROVIDER=fake`, so
  its code never does (security N5).
- **T-17 reuses `id-<slug>-app`.** `AZURE_CLIENT_ID` already names it, so the later "Cognitive Services
  OpenAI User" grant (Owner, ADR 0002 decision 7) goes to this identity. No second app identity.
- **Rights:** Contributor on `rg-ai-studio` covers creating identities and attaching them
  (`userAssignedIdentities/assign/action`). Postgres Entra sign-in needs **no Azure role assignment**, so,
  unlike AcrPull or OpenAI, no Owner step.
- **Cost: $0.** Managed identities have no charge (Entra managed identities overview).
- Caveat kept from 0002 decision 6: anyone who can start a job with an override can run code with that job's
  identity. Only the deployer and Owners can.

### 2. Server: Entra on, the deploy SP as Entra admin, then passwords off

- `postgres.bicep`: `authConfig: { activeDirectoryAuth: 'Enabled', passwordAuth: <param>, tenantId: tenant().tenantId }`.
- **Entra admin = the deploy service principal**, as a child resource, exactly like Microsoft's own Bicep sample:

  ```bicep
  resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2024-08-01' = {
    parent: server
    name: deployer().objectId            // the SP running the deployment
    properties: { principalType: 'ServicePrincipal', principalName: entraAdminName, tenantId: tenant().tenantId }
    dependsOn: [ serverSettings, azureServices ]   // the server takes one change at a time
  }
  ```
  `entraAdminName` defaults to `sp-ai-studio-deployer` (SETUP.md step 3). It becomes the admin's Postgres
  role name; the workflow reads the real value back rather than trusting the default (decision 4).

| Admin option | Why not / why |
|---|---|
| An Entra group (members: deploy SP, Vishal) | Creating a group is a new directory object outside `rg-ai-studio`, needs Graph rights the SP doesn't have, and some university tenants forbid it. Vishal would have to do it: ask-first, for little gain |
| Vishal's own user | Every release would need him signed in |
| **The deploy SP, chosen** | Already exists and already holds the same power today (it carries `STUDIO_DB_SEED`). No new account, nothing outside the RG |

- **Does the SP have the rights?** Creating `administrators` is an ARM write on a resource in
  `rg-ai-studio`, inside Contributor; it needs no Graph permission from the caller. To verify on the first
  deploy (decision 6), because Microsoft's page says CLI and SDK support for admin management is "coming
  soon" while the ARM API and Bicep reference already have it.
- **Deploy shared resources only from the workflow.** `deployer()` would make whoever deploys an admin; a
  run from Cloud Shell would add Vishal as an admin with the wrong `principalType`.
- **Passwords are off from the first deploy (phase 2 is the starting state).** Servers are created with
  `passwordAuth: Disabled`; there is no interim phase with both methods on. The Entra admin is set through the
  ARM management plane (the `administrators` child, written by the deploy service principal), which does not
  need password sign-in, so re-running `deploy_shared` recovers a failed admin step on a server nobody can
  enter by password. Only `studioadmin` has a password; it is **random per `deploy_shared` run**, made and
  used only inside that step (decision 4), never kept, and unusable while password sign-in is off. App and
  migrator roles have no password at all. Enabling Entra on an existing server restarts it (Microsoft FAQ);
  on a fresh server that is moot.
- **Phase 2 must stay done.** The phase 2 PR sets `Disabled` both in `shared.bicepparam` and as the module's
  default, and from then on **every release** reads `az postgres flexible-server show --query authConfig` and
  fails unless `passwordAuth == 'Disabled'` and `activeDirectoryAuth == 'Enabled'`. A later default, a
  portal click or a stray deploy can't quietly reopen password sign-in while real data is there.
- **Nothing in the build needs Vishal.** (Ending decision 5's condition 1 does: Q-8, decision 5.) User-assigned identities are Azure resources in `rg-ai-studio` at $0, of the
  same kind as `id-studio-acrpull`, already approved under Q-5; they are not accounts for people or
  third-party services. No groups, no directory changes, nothing outside the RG. Afterwards he may delete
  the `STUDIO_DB_SEED` secret (tidy-up, not a decision).

### 3. Roles: keep `<db>_app` and `<db>_migrator`, label them with the identities' object ids

| Option | Why not / why |
|---|---|
| `pgaadauth_create_principal('<name>', …)` | Looks the principal up by display name; for identities that is the identity name, and the role must then be called that |
| `pgaadauth_create_principal_with_oid('<db>_app', oid, 'service', false, false)` | Works, but creates the role through Azure's function, so it is unclear whether our admin gets `ADMIN OPTION` on it (needed for step 4 below). Fallback |
| **Plain `CREATE ROLE`, then `SECURITY LABEL FOR "pgaadauth" ON ROLE … IS 'aadauth,oid=<oid>,type=service'`, chosen** | Microsoft documents it for "an existing PostgreSQL role". Same role names, owners and grants as today; one idempotent path for create and re-map; PostgreSQL 16 gives the creating admin `ADMIN OPTION` |

`db-setup.sql` (run by the Entra admin, connected to `postgres`, where the `pgaadauth` functions live):

1. Refuse `app_oid` / `migrator_oid` (psql variables from the workflow) unless they match a lowercase UUID.
2. `CREATE ROLE <db>_migrator LOGIN` and `<db>_app LOGIN` if missing (as today).
3. `ALTER ROLE … WITH LOGIN CONNECTION LIMIT 3 | 12 PASSWORD NULL`: limits unchanged, and no password can
   ever work for these roles.
4. `SECURITY LABEL … 'aadauth,oid=<oid>,type=service'` (never `admin`). Re-running re-maps, so a recreated
   identity heals on the next release.
5. Check: `pgaadauth_list_principals(false)` for each role must give the oid, `service` and `isadmin = 0`, or
   `RAISE EXCEPTION`; and `pgaadauth_list_principals(true)` must list no admin but the deploy SP's role (N1).
   Learn prints the columns as `principalType`, `objectId`, `isAdmin`; the SQL uses unquoted names (which
   fold to lowercase) and the first deploy confirms the real casing; the CI stub notes this assumption (N4). Names called unqualified: `pg_catalog` is searched first, so on
   Azure the real functions win; CI puts stubs in another schema on `search_path`.
6. `CREATE DATABASE` if missing, `REVOKE ALL … FROM PUBLIC`, `GRANT CONNECT` to the two roles (as today).
7. `GRANT <db>_migrator TO CURRENT_USER WITH INHERIT FALSE, SET TRUE` (PostgreSQL 16 syntax). Then
   `\connect <db>`, schema grants as today, `SET ROLE <db>_migrator`, `\ir db-grants.sql`, `RESET ROLE`.
   `db-grants.sql` is unchanged; it now runs as the migrator via `SET ROLE` instead of the migrator's
   password, so `ALTER DEFAULT PRIVILEGES` and `alembic_version` are still the migrator's. The admin gains
   nothing it couldn't already do (it owns the database).

The admin role itself gets no connection limit (it is used once per release, by one psql).

### 4. The workflow: token for the admin step, no seed

- **Order change:** the database step moves **after** the `main.bicep` deploy (which creates the identities
  and outputs their object ids) and **before** the migration job. On a first release the only revision gets
  traffic before the roles exist; that is the same harmless "first minute answers errors" as 0002 decision 9.
- **Run it on every release** and drop the `setup_database` input and the "first release needs the database
  set up" step: it is idempotent, takes under a minute, needs no secret, and re-applies mappings and limits.
- Step outline (existing firewall-rule and always-run cleanup steps unchanged):

  ```bash
  oid_app=$(jq -r .appIdentityPrincipalId.value "$RUNNER_TEMP/outputs.json")      # likewise the migrator
  me=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv \
       | cut -d. -f2 | base64 -d 2>/dev/null | jq -r .oid)  # pad base64url first; no Graph call needed
  admin=$(az rest --method get --url "https://management.azure.com${server_id}/administrators?api-version=2024-08-01" \
       --query "value[?name=='$me'].properties.principalName | [0]" -o tsv)
  # inside the 6-minute retry loop, a fresh token per attempt:
  export PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv)
  echo "::add-mask::$PGPASSWORD"
  psql -X -w -U "$admin" -d postgres -v ON_ERROR_STOP=1 -v db=… -v app=… -v migrator=… \
       -v app_oid="$oid_app" -v migrator_oid="$oid_migrator" -f db-setup.sql
  ```
  The token goes only through `PGPASSWORD` (Microsoft's documented way; it is too long for a prompt). The
  "password doesn't match the seed" branch becomes "the deploy SP is not an Entra admin: run deploy_shared".
- **Token hygiene (N11):** fail if the token is empty *before* `::add-mask::` (an empty mask does nothing); no
  `set -x` in the step; the token never goes into an `az`, `curl` or `psql` argument, only `PGPASSWORD`.
- **Admin drift (N1):** the same step fails if `.../administrators` lists any object id other than the
  deployer's (incremental Bicep never removes one).
- **Admin password (B3):** generated **inside** the `deploy_shared` step, masked before any use, handed to
  `az deployment group create` only through that step's own environment (`readEnvironmentVariable()` in
  `shared.bicepparam` into the `@secure()` param, passed through untransformed), and never written to
  `$GITHUB_ENV`, `$GITHUB_OUTPUT`, a file or a command-line argument. Today's `PG_ADMIN_PASSWORD` in
  `$GITHUB_ENV` goes. Azure wants 3 of 4 character classes, so append a fixed `Aa1!` to
  `openssl rand -base64 32` (N10).
- **Host pinning (B2):** the workflow builds every database URL's host only from `PG_SERVER`
  (`$PG_SERVER.postgres.database.azure.com`); no input, variable or other step may set `DATABASE_URL`.
- **URLs:** `postgresql+psycopg://<db>_app@<host>:5432/<db>?sslmode=verify-full&sslrootcert=…` (and
  `<db>_migrator` for the job). Still stored in the `database-url` secret, so older revisions' secret
  references never break (0002 decision 6), but it no longer contains anything secret.
- **Dead after this, delete in the build:** `STUDIO_DB_SEED` and the "Derive the database passwords" step;
  `infra/scram_verifier.py`, its syntax check in the workflow and its tests; the verifier checks in
  `db-setup.sql`; `PG_*_PASSWORD`; the seed warning in the rollback step; the seed parts of `infra/README.md`
  (setup step 3, "Rotating the database seed"). `adminPassword` stays as a random per-run value.
- **Rollback (0002 decision 9):** unchanged mechanics. Identities are not tied to revisions, so the previous
  revision keeps signing in after a rollback. The old caveat "after a seed rotation it can't reach the
  database" is gone. New caveat: no revision built before T-18 can be rolled back to (none exist in Azure).
- **Replaces seed rotation:** there is nothing to rotate; tokens expire by themselves. To cut a role off at
  once: `ALTER ROLE … NOLOGIN` as the admin (instant, per Learn). To replace an identity, in this order:
  `NOLOGIN` first (cached managed-identity tokens live up to 24 hours and Azure can't force a refresh), then
  delete the identity, then release: it recreates it with a new object id, re-labels the role and sets `LOGIN`.
- **Token lifetimes:** psql tokens 5 to 60 minutes; managed-identity tokens up to 24 hours. Postgres checks
  the token at sign-in only, so pooled connections outlive it; each new connection takes the cached token.

### 5. Firewall: keep the 0.0.0.0 rule; this ends decision 5's condition 1

- **Keep "Allow Azure services".** Private networking is still about $25.55 a month (0002 decision 5).
- **Residual risk, stated plainly:** the port is still reachable from any Azure tenant and any GitHub runner.
  What changes is what an attacker needs: not a guessable or leaked password, but a token signed by Entra.
- **What binds a token to us (B2):** not the audience. `https://ossrdbms-aad.database.windows.net` is one
  shared audience for *every* Azure Database for PostgreSQL server. Only our tenant, the token's object id and
  the label on our role tie it to this server. So a token sent to any other host can be replayed against ours
  for its lifetime. `verify-full` stops a network attacker, but not a wrong host name that is itself a valid
  `*.postgres.database.azure.com` server. Hence host pinning (decision 4): the host comes only from `PG_SERVER`.
- **Remaining risks:** a pre-auth bug in Azure's Postgres front end or TLS stack (Microsoft patches);
  connection floods using up the 35 slots, which can also delay the release's db step (the 6-minute retry
  covers it; logged by `log_connections`); a stolen identity token, valid up to 24 hours (needs code execution
  in our container, or the `IDENTITY_HEADER`, or a misdirected host as above).
- **The biggest one (B1): the deploy SP's credential is now the DB admin credential.** `AZURE_CREDENTIALS` is a
  repository secret, and ADR 0002 decision 8 says any branch's workflow can read it; the main-only check
  "guards against accidents, not against a determined branch". Studio agents push every hour and may meet
  prompt injection (CLAUDE.md section 10). So one injected or mistaken workflow edit could dump every product
  database. The seed had the same weakness, but "demo data only" made it harmless, and this ADR removes that
  control. The SP can also reset `studioadmin`, flip `passwordAuth` and add firewall rules as Contributor.
- **Decision 5 condition 1 ends only when all of these hold:**
  1. phase 2 done and enforced on every release (decision 2), a `studioadmin` password sign-in refused;
  2. the first-deploy evidence in decision 6, recorded in the T-18 review, and the security gate's PASS;
  3. **and one of:** (a) the deploy SP signs in by **OIDC federation**, with no client secret, and a federated
     credential whose subject is limited to `main` (or a main-only GitHub environment), plus branch protection
     or an environment rule so no studio run can change `.github/workflows/**` on `main` without review; or
     (b) Vishal's explicit written acceptance of this risk, recorded in `state/DECISIONS.md`.
  Adding a federated credential to the app registration is a directory change, so it is **ask-first**: it
  depends on Vishal's answer to question **Q-8** (queued by the Studio Lead). Until Q-8 is answered with (a)
  done or (b) given, the shared server stays demo data only. Nothing in this ADR creates the credential.
- That is what 0002 named as the end of "demo data only". It does **not** make the student subscription a
  production host: safety.md's "no customer depends on this subscription" and handover still move hosting.

### 6. Build steps (small slices, each green in CI)

| # | Slice | CI check |
|---|---|---|
| 1 | `main.bicep`: two identities, attachments, `identitySettings`, `DB_AUTH`/`AZURE_CLIENT_ID`, outputs | `az bicep build`; a jq test on the compiled JSON: web and purge have only pull + app identity, migrate only pull + migrate, pull is `None`, DB identity `Main` |
| 2 | `postgres.bicep` / `shared.bicep`: `authConfig` with `tenantId`, `passwordAuth` param (default `Enabled`), `administrators` child | `az bicep build`; jq: admin depends on settings and firewall |
| 3 | `db-setup.sql` as in decision 3 | Local PG16 with a non-superuser CREATEROLE admin and a stub schema (`pgaadauth_list_principals` reading a table; the label branch behind `\if :{?entra_stub}` writes to that table). Assert: re-runnable, `rolpassword IS NULL`, limits 12/3, bad oid refused, mismatch raises, app refused DDL and `alembic_version` writes, other products refused CONNECT |
| 4 | Workflow: phase 1 password kept step-local (B3), step reorder, token with hygiene checks, readback, admin-drift check, oids, password-free URLs with the host from `PG_SERVER` only; remove `setup_database` | `actionlint`, `shellcheck`; the token-oid decode unit-tested on a fake JWT; grep: no `PG_ADMIN_PASSWORD` in `$GITHUB_ENV`, no other writer of `DATABASE_URL` |
| 5 | Delete `scram_verifier.py` and seed docs; README runbook "Entra sign-in"; one line in ADR 0002 pointing here | tests still green; grep finds no `STUDIO_DB_SEED` |
| 6 (done) | Phase 2 flip as its own PR: `Disabled` in `shared.bicepparam` **and** as the module default, plus the every-release `authConfig` assertion (`infra/check-auth-config.sh`, workflow step before the image push) | `az bicep build`; the assertion tested against stubbed `az` output for both values (`test-deploy-workflow.sh`) |
| 7 | Only after Q-8: OIDC login (`azure/login` with `client-id`/`tenant-id`/`subscription-id`, `permissions: id-token: write`), `azure/login` pinned by commit SHA (N9) | `actionlint` |

**Only the first real deploy can verify** (record results in the T-18 review): the Contributor SP can create
the `administrators` child with `deployer()`; the role name for the admin (readback); `SECURITY LABEL` and
`GRANT … TO CURRENT_USER` are allowed for an Entra admin on Azure (fallback: `pgaadauth_create_principal_with_oid`
on the still-empty roles); Container Apps jobs hand out user-assigned tokens with `lifecycle: Main`; the
app's `/healthz` says `"db":"ok"`; the `pgaadauth_list_principals` column casing (N4); after phase 2,
re-deploying with `administratorLoginPassword` still set is accepted and `studioadmin` is refused. Also the
security review's list: the server was created with `passwordAuth: Disabled` (first deploy, not flipped later); `authConfig` shows `passwordAuth: Disabled` and `activeDirectoryAuth: Enabled`; a
sign-in as `<db>_app` with the migrator identity's token is refused; the administrators list holds only the
deploy SP; `rolpassword IS NULL` for both roles on Azure.

### 7. Cost

$0 a month delta. Two identities per product ($0), no new SKU, no Key Vault, no private networking. Entra
sign-in is a server setting, not a meter. `state/BUDGET.md` gains two $0 rows per product when built
(`id-starter-app`, `id-starter-migrate`); the total is unchanged.

## Failure modes

| What goes wrong | What happens | What to do |
|---|---|---|
| Admin creation refused for the SP | `deploy_shared` fails at the admin step; password sign-in is already disabled on the server | Vishal adds the SP as Entra admin in the portal (Authentication pane), then re-run |
| `SECURITY LABEL` refused on Azure | `db-setup.sql` stops before any grant | Switch to `pgaadauth_create_principal_with_oid` on the empty roles (first deploy only) |
| The deploy SP is recreated (new object id) (N2) | The next `deploy_shared` adds the new SP as admin; the old admin entry and role stay and still own every product database | Runbook: `ALTER DATABASE … OWNER TO` the new admin role, delete the old `administrators` entry through ARM, then `DROP ROLE` the old one |
| Connection flood on the 35 slots (N7) | The admin has no reserved slot, so the release's db step waits | The 6-minute retry covers it; if not, release again later |
| `passwordAuth` found `Enabled` after phase 2 | Every release fails at the `authConfig` check | Find out who changed it (Activity Log), run `deploy_shared` |
| Identity endpoint down | New connections fail, `/healthz` not ready, old pooled ones work | The release stops before traffic moves; retry |
| Role mapped to a stale oid | Sign-in fails; `db-setup.sql`'s check raises on the next release | It re-labels on every release |
| Phase 2 locks out a forgotten client | Password clients refused | Intended. Break-glass only: a logged manual run that re-enables password auth, logged in state/DECISIONS.md and never allowed with real data; the every-release check then fails until it is set back to Disabled (security R1) |

## Follow-ups (not blocking)

- An Activity Log alert on writes to the server's `authConfig`, `administrators` and `firewallRules` would
  catch a misused SP (N6). Check that activity-log alerts are $0 before adding.
- `backend/app/dbauth.py` docstring wording (N8: the user is `<db>_app`, managed-identity tokens last up to
  24 hours): for the T-18 app review.

## Sources (all read 2026-11-24; page "updated" dates in brackets)

- Entra auth concepts: admins (user, group, SP, managed identity; several allowed), three auth modes, restart on enabling, token lifetimes: https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts [2026-09-06]
- Configure and connect, `az account get-access-token --resource-type oss-rdbms`, token through `PGPASSWORD`, 5 to 60 minute validity: https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure [2026-09-06]
- `pgaadauth_create_principal(_with_oid)`, `pgaadauth_list_principals`, `SECURITY LABEL FOR "pgaadauth"`, CLI "coming soon": https://learn.microsoft.com/en-us/azure/postgresql/security/security-manage-entra-users [2026-09-06]
- Managed identity sign-in, functions only in the `postgres` database: https://learn.microsoft.com/en-us/azure/postgresql/security/security-connect-with-managed-identity [2026-07-16]
- `flexibleServers/administrators` 2024-08-01 (sample uses `deployer().objectId`, `tenant().tenantId`): https://learn.microsoft.com/en-us/azure/templates/microsoft.dbforpostgresql/2024-08-01/flexibleservers/administrators [2026-10-20]
- `deployer()`: https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-functions-deployment [2026-10-28]
- Container Apps identities, `identitySettings` lifecycle (`All` default), `client_id`: https://learn.microsoft.com/en-us/azure/container-apps/managed-identity [2026-02-13]
- Managed identities cost nothing extra, and the 0.0.0.0 rule's meaning: as cited in ADR 0002 (read 2026-11-23)
