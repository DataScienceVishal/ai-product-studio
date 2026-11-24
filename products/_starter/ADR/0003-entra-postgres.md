# ADR 0003: Passwordless Postgres sign-in with Microsoft Entra ID

- Status: proposed (2026-11-24, board task T-18). Supersedes the password parts of ADR 0002 decisions 4, 5
  (condition 1), 6 (`DATABASE_URL`, seed rotation) and 9 (the seed caveats). Everything else in 0002 stands.
- Builds on the app side being written in parallel: `DB_AUTH=entra` makes the app and `migrations/env.py`
  fetch a token for `https://ossrdbms-aad.database.windows.net` from the Container Apps identity endpoint
  (`ManagedIdentityToken`, `AZURE_CLIENT_ID`) and pass it as the password in SQLAlchemy `do_connect`. The URL
  has no password and keeps `sslmode=verify-full`. `DB_AUTH=password` (default) stays for local and CI.
- Nothing exists in Azure yet (`state/BUDGET.md`: all "planned"), so there is no live data to migrate. The
  two phases below happen in the first real deploy session.

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
audience, from our tenant, and for the object id written on the role. Nothing long-lived exists to leak.

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
  third identity would add a role and connection budget without removing any privilege.
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
- **Phase 1 (first shared deploy): both methods on.** The admin is a child of the server, so it can only be
  added after the server exists; keeping `passwordAuth: Enabled` for that first deploy avoids a server nobody
  can enter if the admin step fails. Only `studioadmin` has a password, and it is now **random per
  `deploy_shared` run** (`openssl rand -base64 32`, masked, never stored). An Owner or Contributor can reset
  it through ARM if ever needed, so nothing is lost by not keeping it. App and migrator roles have no password
  from the start.
- **Phase 2 (same session, after the starter's first Entra release passes its smoke tests):**
  `postgresPasswordAuth=Disabled`, run `deploy_shared` again. Enabling Entra on an existing server restarts
  it (Microsoft FAQ); on a fresh server that is moot.
- **Nothing here needs Vishal.** User-assigned identities are Azure resources in `rg-ai-studio` at $0, of the
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
   ever work for these roles, even in phase 1.
4. `SECURITY LABEL … 'aadauth,oid=<oid>,type=service'` (never `admin`). Re-running re-maps, so a recreated
   identity heals on the next release.
5. Check: `SELECT objectid, principaltype FROM pgaadauth_list_principals(false) WHERE rolename = …` must equal
   the oid and `service`, or `RAISE EXCEPTION`. Names called unqualified: `pg_catalog` is searched first, so on
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
- **URLs:** `postgresql+psycopg://<db>_app@<host>:5432/<db>?sslmode=verify-full&sslrootcert=…` (and
  `<db>_migrator` for the job). Still stored in the `database-url` secret, so older revisions' secret
  references never break (0002 decision 6), but it no longer contains anything secret.
- **Dead after this, delete in the build:** `STUDIO_DB_SEED` and the "Derive the database passwords" step;
  `infra/scram_verifier.py`, its syntax check in the workflow and its tests; the verifier checks in
  `db-setup.sql`; `PG_*_PASSWORD`; the seed warning in the rollback step; the seed parts of `infra/README.md`
  (setup step 3, "Rotating the database seed"). `adminPassword` stays as a random per-run value until phase 2.
- **Rollback (0002 decision 9):** unchanged mechanics. Identities are not tied to revisions, so the previous
  revision keeps signing in after a rollback. The old caveat "after a seed rotation it can't reach the
  database" is gone. New caveat: no revision built before T-18 can be rolled back to (none exist in Azure).
- **Replaces seed rotation:** there is nothing to rotate; tokens expire by themselves. To cut a role off at
  once: `ALTER ROLE … NOLOGIN` as the admin. To replace an identity: delete it; the next release recreates
  it with a new object id and `db-setup.sql` re-labels the role.
- **Token lifetimes:** psql tokens 5 to 60 minutes; managed-identity tokens up to 24 hours. Postgres checks
  the token at sign-in only, so pooled connections outlive it; each new connection takes the cached token.

### 5. Firewall: keep the 0.0.0.0 rule; this ends decision 5's condition 1

- **Keep "Allow Azure services".** Private networking is still about $25.55 a month (0002 decision 5).
- **Residual risk, stated plainly:** the port is still reachable from any Azure tenant and any GitHub runner.
  What changes is what an attacker needs: not a guessable or leaked password, but a token signed by Entra,
  for our server's audience, from our tenant, for one of three object ids. Remaining risks: a pre-auth bug in
  Azure's Postgres front end or TLS stack (Microsoft patches); connection floods using up the 35 slots (a
  nuisance for demos, logged by `log_connections`); a stolen identity token, valid up to 24 hours (needs code
  execution in our container, or the `IDENTITY_HEADER`); the deploy SP's client secret in GitHub, which now
  is the DB admin (it already was, via the seed). OIDC federation for the SP would remove that secret: a follow-up.
- **Decision 5 condition 1 ends when all of these hold:** phase 2 done (`passwordAuth: Disabled` confirmed by
  `az postgres flexible-server show`), a password sign-in attempt refused, and the security gate's PASS. That
  is what 0002 named as the end of "demo data only". It does **not** make the student subscription a
  production host: safety.md's "no customer depends on this subscription" and handover still move hosting.

### 6. Build steps (small slices, each green in CI)

| # | Slice | CI check |
|---|---|---|
| 1 | `main.bicep`: two identities, attachments, `identitySettings`, `DB_AUTH`/`AZURE_CLIENT_ID`, outputs | `az bicep build`; a jq test on the compiled JSON: web and purge have only pull + app identity, migrate only pull + migrate, pull is `None`, DB identity `Main` |
| 2 | `postgres.bicep` / `shared.bicep`: `authConfig` with `tenantId`, `passwordAuth` param (default `Enabled`), `administrators` child | `az bicep build`; jq: admin depends on settings and firewall |
| 3 | `db-setup.sql` as in decision 3 | Local PG16 with a non-superuser CREATEROLE admin and a stub schema (`pgaadauth_list_principals` reading a table; the label branch behind `\if :{?entra_stub}` writes to that table). Assert: re-runnable, `rolpassword IS NULL`, limits 12/3, bad oid refused, mismatch raises, app refused DDL and `alembic_version` writes, other products refused CONNECT |
| 4 | Workflow: random admin password, step reorder, token, readback, oids, password-free URLs; remove `setup_database` | `actionlint`, `shellcheck`; the token-oid decode unit-tested on a fake JWT |
| 5 | Delete `scram_verifier.py` and seed docs; README runbook "Entra sign-in"; one line in ADR 0002 pointing here | tests still green; grep finds no `STUDIO_DB_SEED` |
| 6 | Phase 2 flip (`passwordAuth: Disabled`) as its own PR | `az bicep build` |

**Only the first real deploy can verify** (record results in the T-18 review): the Contributor SP can create
the `administrators` child with `deployer()`; the role name for the admin (readback); `SECURITY LABEL` and
`GRANT … TO CURRENT_USER` are allowed for an Entra admin on Azure (fallback: `pgaadauth_create_principal_with_oid`
on the still-empty roles); Container Apps jobs hand out user-assigned tokens with `lifecycle: Main`; the
app's `/healthz` says `"db":"ok"`; after phase 2, re-deploying with `administratorLoginPassword` still set
is accepted and `studioadmin` is refused.

### 7. Cost

$0 a month delta. Two identities per product ($0), no new SKU, no Key Vault, no private networking. Entra
sign-in is a server setting, not a meter. `state/BUDGET.md` gains two $0 rows per product when built
(`id-starter-app`, `id-starter-migrate`); the total is unchanged.

## Failure modes

| What goes wrong | What happens | What to do |
|---|---|---|
| Admin creation refused for the SP | `deploy_shared` fails in phase 1; password auth still on | Vishal adds the SP as Entra admin in the portal (Authentication pane), then re-run |
| `SECURITY LABEL` refused on Azure | `db-setup.sql` stops before any grant | Switch to `pgaadauth_create_principal_with_oid` on the empty roles (first deploy only) |
| Identity endpoint down | New connections fail, `/healthz` not ready, old pooled ones work | The release stops before traffic moves; retry |
| Role mapped to a stale oid | Sign-in fails; `db-setup.sql`'s check raises on the next release | It re-labels on every release |
| Phase 2 locks out a forgotten client | Password clients refused | Intended; re-enable for one run via the param if truly needed |

## Sources (all read 2026-11-24; page "updated" dates in brackets)

- Entra auth concepts: admins (user, group, SP, managed identity; several allowed), three auth modes, restart on enabling, token lifetimes: https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts [2026-09-06]
- Configure and connect, `az account get-access-token --resource-type oss-rdbms`, token through `PGPASSWORD`, 5 to 60 minute validity: https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure [2026-09-06]
- `pgaadauth_create_principal(_with_oid)`, `pgaadauth_list_principals`, `SECURITY LABEL FOR "pgaadauth"`, CLI "coming soon": https://learn.microsoft.com/en-us/azure/postgresql/security/security-manage-entra-users [2026-09-06]
- Managed identity sign-in, functions only in the `postgres` database: https://learn.microsoft.com/en-us/azure/postgresql/security/security-connect-with-managed-identity [2026-07-16]
- `flexibleServers/administrators` 2024-08-01 (sample uses `deployer().objectId`, `tenant().tenantId`): https://learn.microsoft.com/en-us/azure/templates/microsoft.dbforpostgresql/2024-08-01/flexibleservers/administrators [2026-10-20]
- `deployer()`: https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-functions-deployment [2026-10-28]
- Container Apps identities, `identitySettings` lifecycle (`All` default), `client_id`: https://learn.microsoft.com/en-us/azure/container-apps/managed-identity [2026-02-13]
- Managed identities cost nothing extra, and the 0.0.0.0 rule's meaning: as cited in ADR 0002 (read 2026-11-23)
