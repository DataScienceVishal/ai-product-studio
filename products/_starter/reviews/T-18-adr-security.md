# T-18 security gate: ADR 0003 (passwordless Postgres with Entra ID)

- Reviewed: `products/_starter/ADR/0003-entra-postgres.md` at 3d431ee on `p/_starter/T-18-adr`, against ADR 0002
  decisions 4 to 10, `infra/*` (postgres.bicep, shared.bicep(param), main.bicep, db-setup.sql, README),
  `.github/workflows/_starter-deploy.yml`, CLAUDE.md sections 6 and 10, and the app side on
  `origin/p/_starter/T-18-app` (fb5daf7: `backend/app/dbauth.py`, `db.py`, `config.py`, `maintenance.py`,
  `migrations/env.py`).
- Reviewer: security agent, 2026-11-24. Design review only: nothing exists in Azure yet (`state/BUDGET.md`),
  so **nothing is exposed now** and nothing needs an urgent ping.

## Verdict: CHANGES (3 blocking, 11 non-blocking)

The design is sound and a clear improvement on the seed passwords: no long-lived DB secret, roles that can
never take a password, oid-pinned mappings re-applied every release, and identity separation that matches the
two-role model. The blocking items are about the threat model being stated precisely and about making "phase 2
done" stay done. They do not change the architecture.

## Microsoft Learn checks (read 2026-11-24)

| ADR claim | Learn says | Result |
|---|---|---|
| Entra admin can be a service principal; several allowed; added via ARM `administrators` child | "The Microsoft Entra administrator can be a Microsoft Entra user, Microsoft Entra group, service principal, or managed identity"; "You can configure multiple Microsoft Entra administrators concurrently" ([concepts](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts)); "Create or delete Microsoft Entra administrators using Azure portal or Azure Resource Manager (ARM) API", CLI/SDK "coming soon" ([manage](https://learn.microsoft.com/en-us/azure/postgresql/security/security-manage-entra-users)) | Correct |
| Microsoft's Bicep sample uses `deployer().objectId` | Sample: `name: deployer().objectId`, `principalType: 'ServicePrincipal'`, `tenantId: tenant().tenantId`; `principalName` is an optional string ([administrators 2024-08-01](https://learn.microsoft.com/en-us/azure/templates/microsoft.dbforpostgresql/2024-08-01/flexibleservers/administrators)). `deployer()` returns the initiating principal's `objectId`; UPN "may be empty for service principals" ([deployer()](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-functions-deployment)) | Correct |
| Entra admin = same power as the password admin | "Gets the same privileges as the original PostgreSQL administrator"; "When you set the administrator, you add a new user ... with full administrator permissions"; "Don't use the Microsoft Entra administrator for regular database operations" ([configure](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure)) | Correct; ADR uses it only for db-setup, as advised |
| `SECURITY LABEL FOR "pgaadauth" ON ROLE ... IS 'aadauth,oid=<oid>,type=service'` for an existing role; omit `admin` | Syntax `'aadauth,oid=<objectId>,type=<objectType>,admin'`; `type` is `user`, `group` or `service` ("for applications or managed identities"); `admin` "set to present or absent. If present ... can manage other Microsoft Entra ID roles" ([manage](https://learn.microsoft.com/en-us/azure/postgresql/security/security-manage-entra-users)) | Correct. Who may set it: "Only Microsoft Entra administrator users can create or enable users for Microsoft Entra ID-based authentication" ([configure](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure)); our admin is one, so allowed in principle; on-Azure check kept in decision 6 |
| `pgaadauth_create_principal_with_oid(roleName, objectId, objectType, isAdmin, isMfa)` fallback | Signature matches exactly | Correct |
| `pgaadauth_list_principals(false)` columns | `TABLE(rolename name, principalType text, objectId text, tenantId text, isMfa integer, isAdmin integer)`; `false` returns admins and non-admins | `rolename` correct; see N4 on `principaltype` casing |
| Mapping is by object id, not name | "matches access tokens to the database role by using the user's unique Microsoft Entra user ID, as opposed to using the username" ([concepts](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts)) | Correct: role names `<db>_app` / `<db>_migrator` work |
| Token through `PGPASSWORD`, `--resource-type oss-rdbms`, 5 to 60 minutes | All three stated ([configure](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure)) | Correct |
| Managed-identity tokens up to 24 h | "Tokens for system-assigned managed identities are valid for up to 24 hours" ([concepts](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts)); Container Apps back end caches tokens "per resource URI for around 24 hours. ... Forcing a token refresh isn't supported" ([Container Apps MI](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)) | Correct (and matters for revocation, N3) |
| Enabling Entra restarts the server | "the PGAadAuth extension is enabled and the server restarts" ([concepts](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts)) | Correct |
| `identitySettings` lifecycle, default `All`, `None` for pull-only | "`All`: ... This value is the default setting"; "`None`: ... only used for ACR image pull" (API 2024-02-02-preview and later; main.bicep uses 2025-07-01) ([Container Apps MI](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)) | Correct. The page only shows container apps; jobs are listed under "only the first real deploy can verify", rightly |
| `@secure()` values not in deployment history | "The value for a secure parameter isn't saved to the deployment history and isn't logged"; redaction "doesn't apply to a value that a Bicep file transforms or derives from the secure value" ([Bicep parameters](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/parameters)) | Correct, as long as `adminPassword` is passed straight through (postgres.bicep does) |
| "a token ... for our server's audience" (decision 5) | The token "is targeted to the Azure Database for PostgreSQL service"; one resource, `https://ossrdbms-aad.database.windows.net`, for every server ([configure](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-configure)) | **Wrong**: see B2 |
| Deleted principal | "can still sign in until the token expires ... If you also remove the user from Azure Database for PostgreSQL, this access is revoked immediately"; deleted principal "remains as a PostgreSQL role ... Database administrators need to transfer ownership and drop roles manually" ([concepts](https://learn.microsoft.com/en-us/azure/postgresql/security/security-entra-concepts)) | ADR's NOLOGIN advice is right; see N2, N3 |

## App side matches the ADR

`dbauth.py`: `DB_RESOURCE = "https://ossrdbms-aad.database.windows.net"`; `validate_entra_url` refuses a password in
the URL, a missing user and anything but `sslmode=verify-full`; `build_token_provider(client_id)` passes
`AZURE_CLIENT_ID` as `client_id` to the Container Apps endpoint (`maintenance.py` and `env.py` pass it too); the
token goes in only via `do_connect` and errors log the exception class only. That is what ADR 0003 says.
Two wording mismatches for the app review (N8).

## Answers to the seven questions

1. **Deploy SP as Entra admin.** Least privilege is acceptable *relative to today*: the SP is Contributor on
   `rg-ai-studio`, so it can already reset `studioadmin`, flip `passwordAuth`, add firewall rules, read
   Container Apps secrets and start jobs with overrides. Being Entra admin adds no power it lacks; it removes
   the seed. An attacker with the SP's client secret gets: full DB admin over every product database (direct
   token sign-in from any Azure address or a firewall rule it creates), plus everything Contributor gives. The
   real exposure is where that secret lives (B1). **Ask-first:** no issue. The admin entry is an ARM child
   resource of a server inside `rg-ai-studio`; no Graph write, no new directory object, no account for a person
   or third party. The user-assigned identities are RG resources at $0 of the kind already approved under Q-5.
   The group option is correctly rejected as ask-first. The failure-mode fallback (Vishal adds the SP in the
   portal) is Vishal acting, which is fine.
2. **Phase 1 password.** 32 random bytes, used by nobody, passed as `@secure()`: not in deployment history (Learn,
   above), not in `az ... --output none` output. It is "never stored" only if the build keeps it step-local:
   today's workflow writes `PG_ADMIN_PASSWORD` to `$GITHUB_ENV`, which persists to every later step (B3).
   Exposure window: from the first `deploy_shared` until the phase 2 PR is merged and run. Since nobody knows a
   256-bit password and every product role is `PASSWORD NULL`, the practical risk in the window is negligible;
   the risk that matters is phase 2 silently reverting later (B3).
3. **Role mapping.** `CREATE ROLE` + `SECURITY LABEL` is documented for existing roles and keeps names, owners
   and grants; the label omits `admin`, so neither role can manage Entra roles. `PASSWORD NULL` means password
   sign-in always fails for both roles even while `passwordAuth` is on. A non-superuser Entra admin is the only
   principal Learn says may enable Entra roles, so it is the right caller; that `SECURITY LABEL` and the PG16
   `GRANT ... TO CURRENT_USER WITH INHERIT FALSE, SET TRUE` are accepted on Azure is correctly left to the
   first deploy with a documented fallback (`pgaadauth_create_principal_with_oid` on the still-empty roles).
   The oid regex before interpolation closes injection into the label literal. No role ends with a password
   except `studioadmin` until phase 2 (and it stays unusable after).
4. **Token through `PGPASSWORD`.** Microsoft's documented way. `::add-mask::` straight after assignment, nothing
   echoed, a fresh token per attempt, `psql -X -w`, and the error snippets (`head -c 300 psql.err`) never contain
   the password. The `me=` decode reads only the claims; `jq`/`base64` errors don't print input. Fine, with N11.
5. **0.0.0.0 rule.** The residual list is honest about the network (pre-auth bugs, slot floods, stolen MI
   token) but has one factual error (B2) and understates the credential path (B1). With B1 resolved, ending
   decision 5 condition 1 after phase 2 + this PASS is justified for G4/handover on this subscription, and the
   ADR rightly keeps "the student subscription is not a production host".
6. **Identity separation.** Two identities for two roles is right. Purge sharing `id-<slug>-app` adds no DB
   privilege. Once T-17 grants "Cognitive Services OpenAI User" to that identity, the purge job can also call
   OpenAI (same image, same daily cap): acceptable, noted (N5). Limits 12/3 are kept, enforced by
   `ALTER ROLE ... CONNECTION LIMIT` every release; the admin has none, which is fine for one psql per release.
7. **Missing.** See B1 to B3 and N1 to N3: admin drift, a recreated deploy SP, and revocation timing.

## Blocking

**B1. Decision 5 must state the credential path and gate condition 1 on it.** The deploy SP's client secret
(`AZURE_CREDENTIALS`) is now the DB admin credential. ADR 0002 decision 8 says repository secrets are readable
by workflows on any branch and the main-only check "guards against accidents, not against a determined branch".
Studio agents push branches (and state to `main`) every hour, and CLAUDE.md section 10 assumes they can meet
prompt injection. So once real personal data is on the server, one injected or mistaken workflow edit can dump
every product database. This was equally true of the seed, but condition 1 ("demo data only") was the control
that made it harmless, and this ADR removes that control. Required: add this to the residual-risk list, and make
the end of condition 1 also require **one** of (a) OIDC federation for the deploy SP with a subject limited to
`main` (plus a GitHub environment or branch protection on `.github/workflows/**`, so `main` itself isn't
writable by any run), or (b) Vishal's explicit acceptance recorded in `state/DECISIONS.md`. Creating a federated
credential on the app registration is a directory change: ask-first, so queue it as a question now.

**B2. Correct the audience claim.** "a token signed by Entra, for our server's audience" is wrong: the audience
is one shared resource for every Azure Database for PostgreSQL server. What binds a token to us is tenant + oid
+ our role's label. Say so, and add the consequence: a token handed to any other host is replayable against our
server for its lifetime. `verify-full` stops network attackers but not a wrong host name that is itself a valid
`*.postgres.database.azure.com` server. Add: the workflow builds the URL host only from `PG_SERVER`, and nothing
else may set `DATABASE_URL`.

**B3. Pin the phase 1 password handling and make phase 2 stick.** Add to decision 4 / build slice 4: the random
`studioadmin` password is generated **inside** the `deploy_shared` step, masked before any use, handed to
`az deployment group create` only through that step's environment (`readEnvironmentVariable` into the
`@secure()` param), never written to `$GITHUB_ENV`, `$GITHUB_OUTPUT`, a file or a command-line argument, and
never transformed in Bicep. Add to slice 6: the phase 2 PR sets `passwordAuth` to `Disabled` in
`shared.bicepparam` *and* as the module default, and from then on every release asserts
`authConfig.passwordAuth == 'Disabled'` (fail the release otherwise), so a later default or manual change can't
silently reopen password sign-in while real data is there.

## Non-blocking

- **N1. Admin drift.** Bicep incremental mode never removes admins. In the db step, fail (or warn loudly) if
  `.../administrators` lists anyone but the deployer's oid, and if `pgaadauth_list_principals(true)` lists any
  role but the admin. Add `isadmin = 0` to the step 5 check for the app and migrator roles.
- **N2. Recreated deploy SP (new oid).** Add a failure-mode row: the next `deploy_shared` adds the new SP as
  admin; the old admin entry and role remain (Learn: "transfer ownership and drop roles manually"), and the old
  role owns every product database (decision 3 step 6). Runbook: `ALTER DATABASE ... OWNER TO` the new admin,
  delete the old `administrators` entry via ARM, `DROP ROLE` the old one.
- **N3. Revocation order.** "To replace an identity: delete it" leaves the old oid working until the next
  release re-labels the role, up to 24 h of cached MI tokens. Runbook: `ALTER ROLE ... NOLOGIN` first (instant,
  per Learn), then delete, then release.
- **N4. Column casing.** Learn prints `principalType`; the ADR selects `principaltype`. Probably fine (unquoted
  identifiers fold), but a quoted camelCase column would make step 5 fail. Add it to the first-deploy checks,
  and don't let the CI stub encode the assumption without a note.
- **N5. Purge job and OpenAI.** Under T-17 the purge job inherits the OpenAI role through the shared identity.
  Accept and note it in decision 1, or give purge `AI_PROVIDER=fake` so its code never calls OpenAI.
- **N6. Alerting (free).** An Activity Log alert on writes to `flexibleServers` `authConfig`, `administrators`
  and `firewallRules` would catch a misused SP. Optional, $0 for activity-log alerts. Check before adding.
- **N7. Slot floods.** Pre-auth connections count against the 35 slots and the admin has no reserved slot, so a
  flood can delay the release db step. The 6-minute retry covers it; mention it in the failure table.
- **N8. App wording (for the T-18-app review).** `dbauth.py`'s docstring says the user is "e.g. the managed
  identity's name" (ADR: `<db>_app`, mapped by label) and "Tokens live 5 to 60 minutes" (MI tokens up to 24 h).
  Behaviour is right; fix the text.
- **N9. `azure/login@v2` by tag.** It now handles a DB-admin credential. Pin it by commit SHA, as Trivy is pinned
  by digest (pre-existing).
- **N10. Password complexity.** Azure needs 3 of 4 character classes; `openssl rand -base64 32` misses digits in
  under 0.1% of runs. Append a fixed `Aa1!` or retry until valid. Reliability, not security.
- **N11. Token hygiene.** Fail if the token is empty before `::add-mask::` (an empty mask is a no-op), keep
  `set -x` out of the step, and don't put the token in any `az`/`curl` argument.

## Gate evidence still owed (first real deploy, record in the T-18 review)

Everything listed in ADR 0003 decision 6's "Only the first real deploy can verify", plus: `az postgres
flexible-server show --query authConfig` showing `passwordAuth: Disabled` and `activeDirectoryAuth: Enabled`;
a `studioadmin` password sign-in refused; a sign-in as `<db>_app` with the *migrator* identity's token refused;
the administrators list containing only the deploy SP; `rolpassword IS NULL` for both roles on Azure. Decision 5
condition 1 ends only when these and B1 hold.

## Re-check (ad40007, 2026-11-24): PASS

Re-checked only what this review raised, plus anything the edits introduced.

- **B1 fixed.** Decision 5 now names the deploy SP credential as the biggest residual risk. Condition 1 ends only
  with phase 2 enforced, the first-deploy evidence, this PASS, **and** either (a) OIDC limited to `main` plus
  workflow protection or (b) Vishal's written acceptance. It is tied to Q-8, which is open in `state/QUESTIONS.md`
  on `main`. Until then the server stays demo data only, and the ADR creates no federated credential (ask-first
  respected). Slice 7 waits for Q-8.
- **B2 fixed.** The audience is described as shared by every server; tenant, oid and label are what bind a token
  to us; the replay consequence is stated; the host comes only from `PG_SERVER`, and a slice 4 grep checks this.
- **B3 fixed.** The phase 1 password stays inside the step (never in `$GITHUB_ENV`/`$GITHUB_OUTPUT`, a file or an
  argument, and is not transformed). Phase 2 sets `Disabled` in both the bicepparam and the module default, and
  every release asserts `passwordAuth == Disabled` and `activeDirectoryAuth == Enabled`, tested in slice 6.
- **N1 to N11:** all folded in (admin drift in both ARM and `pgaadauth_list_principals(true)`, `isadmin = 0`, SP
  recreation row, NOLOGIN-first order, casing check, purge on `AI_PROVIDER=fake`, alert as a follow-up, flood row,
  dbauth wording sent to the app review, SHA pin in slice 7, `Aa1!` suffix, token hygiene).
- **New, non-blocking (R1).** One failure-mode row still says "re-enable [password auth] for one run via the param
  if truly needed", but the new every-release assertion would then fail every release. Reword it: re-enabling is
  a deliberate break-glass step that stops releases until it is reverted. Record it in DECISIONS.md, and it is
  not allowed while real data is on the server.

The architecture gate passes. The first-deploy evidence and Q-8 still gate the end of decision 5 condition 1.
