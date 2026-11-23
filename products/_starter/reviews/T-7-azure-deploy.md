# Review: T-7 Azure deploy design for the starter

- Branch `vishal/blissful-cray-v1s3ys` at `f074262` (checked with `git log`). T-7 is commits `3b66b5b` and `f074262`.
- Scope: `ADR/0002-azure-deploy.md`, `infra/` (all nine files), `.github/workflows/_starter-deploy.yml`, the planned
  rows in `state/BUDGET.md`.
- Reviewer, 2026-11-23. Nothing was deployed: no Azure CLI, no Bicep and no credentials here. I checked the files
  against Microsoft's docs and ran local tests on an export of `f074262`.

## Verdict: CHANGES

The design is careful and mostly right. Every resource type and API version exists. The secret handling is clean, the
SQL role split works as described, smoke.sh catches every failure I tried, and every price matches Microsoft's
Retail Prices API.

Three things must change before this merges:

1. **C1. With the shipped defaults, the daily purge deletes every demo account on day 31.** The security gate flagged
   these defaults for T-7, and the final commit doesn't address them. (I reproduced it.)
2. **C2. The purge job gets the new image before the release has passed.** A failed release or a rollback leaves the
   data-deleting job on code that never passed the smoke test.
3. **C3. `allLogs` also turns on the ingress HTTP access logs**, which hold client IPs and full URLs with query strings.
   That contradicts the ADR and DATA.md.

All three are small changes in T-7's own files.

## Critical issues (fix before merge)

### C1. Deploy defaults: the purge deletes live demo accounts, and the demo can't use AI
- **Where:**
  - `infra/main.bicep:247-258`: `jobSettings`/`jobEnv` never pass `REQUIRE_EMAIL_VERIFICATION` to the jobs, so the
    purge job always uses the app default (`true`).
  - `infra/main.bicep:48`: `requireEmailVerification = true`.
  - `infra/main.bicep:45`: `mockCheckoutEnabled = true`.
  - ADR decisions 6, 10 and 11 say nothing about any of this.
- **Why it matters:**
  - Email is outbox-only, so no owner can ever verify. `maintenance.py` deletes every tenant whose owner is unverified
    and older than 30 days (SECURITY.md R13, still open).
  - SECURITY.md re-test 2, "For T-7", listed exactly these defaults: `requireEmailVerification = true` (R13),
    `mockCheckoutEnabled = true` (R15) and the 100,000 budget (R12).
- **Evidence:** I ran `python -m app.maintenance purge` with the job environment exactly as main.bicep builds it, as
  the app role, after migrations had run as the migrator. The seed was an unverified owner, 31 days old, with a
  session created an hour earlier.

  | Job environment | Result |
  |---|---|
  | A. main.bicep defaults | `"unverified_accounts": 1`. Tenant and live session gone. |
  | B. Web app deployed with `requireEmailVerification=false` | The same deletion, because the job's env doesn't change. |
  | C. Job given `REQUIRE_EMAIL_VERIFICATION=false` | Nothing purged. Tenant and session kept. |

  Live, with main.bicep's web env (`ENV=prod`, app role), a new owner can sign up and write notes. But all of these
  answer `403 email_not_verified`, and the link only reaches the in-memory outbox:
  - `POST /api/notes/{id}/summarize`
  - `/api/billing/checkout`
  - `/api/team/invitations`

  So the deployed demo can't show the AI feature. And if someone turns verification off to make it usable, the
  `mockCheckoutEnabled = true` default gives anyone with the URL a free Pro plan. One such tenant can then use the
  whole daily AI budget (R15). The app's default for mock checkout is `false` (R3 fix); the deploy turns it back on.
- **Fix:**
  1. In `jobSettings`, set `REQUIRE_EMAIL_VERIFICATION` for the jobs explicitly.
     - Until R13's app fix lands, use `'false'`, with a comment: with outbox-only email nobody can verify, so the
       unverified purge must not run. This fails safe: unverified accounts are kept.
     - After R13 lands, pass the web app's value.
  2. `param mockCheckoutEnabled bool = false`. Add a workflow input `mock_checkout` (default false), the same way as
     `ai_provider`.
  3. ADR: add a short "what a deployed demo can do" note. With outbox email, choose per demo:
     - verification on: sign-up and notes only;
     - verification off: AI works for anyone with the URL, cost is capped by `AI_GLOBAL_DAILY_TOKENS`, and R12 applies.

     Optionally add `require_email_verification` as a workflow input.

### C2. The purge and migration jobs get the new image before the release has passed
- **Where:**
  - `infra/main.bicep:415-460`: the purge job's `image: image` is at line 445.
  - Workflow: the deploy step (`_starter-deploy.yml:264-302`) updates the web app and both jobs in one deployment.
    The failure steps (341-355) and the `rollback` job (381-429) touch only web revisions.
- **Why it matters:**
  - Jobs have no revisions. After the deploy step, `caj-starter-purge` runs the new image at the next 03:17 UTC run,
    whether or not the migration ran or the smoke test passed.
  - If the migration fails, the new code runs against the old schema.
  - If a release is rolled back because the new code is wrong, the purge, which deletes rows as the app role every day,
    keeps running the wrong code. `rollback_to` doesn't revert it.
  - This breaks ADR decision 9's promise that only code that passed gets to run.
- **Fix:** promote the purge job only after the public smoke test passes, and roll it back with the web app.
  - Add a `purgeImage` parameter. Its default is the live revision's image, which the workflow already knows from
    `az containerapp revision show --query properties.template.containers[0].image`.
  - Add a final step after the public smoke test: `az containerapp job update -n caj-$PRODUCT-purge --image "$IMAGE"`.
  - In both rollback paths, set the purge image back to the target revision's image.
  - The migration job can stay as it is: it only runs when the workflow starts it.

### C3. `categoryGroup: 'allLogs'` also ships ingress HTTP access logs (client IPs, full URLs)
- **Where:**
  - `infra/shared.bicep:90`: the comment says "container console output and system logs".
  - It contradicts ADR decision 11 (`0002-azure-deploy.md:222` "console and system logs", `:228` "Logs hold ids,
    not personal data") and `DATA.md:20` ("never emails, names, note text, tokens").
- **Why it matters:**
  - `allLogs` is every category. For `microsoft.app/managedenvironments` that includes `ContainerAppHTTPLogs`.
    Microsoft: "The ingress layer emits these logs when HTTP logging is enabled through diagnostic settings."
  - Microsoft's table reference for `ContainerAppHTTPLogs` says the `Path` column "may contain query string parameters
    that include sensitive values such as authentication tokens", and `XForwardedFor` "contains end-user client IP
    addresses; treat as personally identifiable information".
  - The starter's email links carry tokens in the query string: `/verify-email?token=`, `/reset-password?token=` and
    `/accept-invite?token=`. Once T-16 serves the SPA from this origin, they pass through the ingress. Reset tokens
    (30 minutes), verification tokens (48 hours) and invitation tokens (7 days) would then sit in `log-studio` for
    30 days, readable by anything with log access, including the deployer service principal.
  - Client IPs and user agents for every request are personal data that DATA.md and the privacy notice don't list.
  - Every bot request also counts against the 0.1 GB daily cap. When the cap is hit, the rest of the day's console
    logs are lost, and those are the logs the runbook points to for migration failures.
- **Fix:** name the two categories instead of the group:
  ```bicep
  logs: [
    { category: 'ContainerAppConsoleLogs', enabled: true }
    { category: 'ContainerAppSystemLogs', enabled: true }
  ]
  ```

## Important (fix before the first real deploy)

### I1. A transient Azure read error turns a release into a "first deploy" with no gate
- **Where:** `_starter-deploy.yml:282-287`. Both `az containerapp show` calls end in `2> /dev/null || true`.
- **Why it matters:** if both reads fail, for example on throttling or a token refresh:
  - `LIVE_REVISION` is empty, so main.bicep uses `latestRevision: true`.
  - The untested revision gets 100% as soon as it is ready, before migrations and the smoke test.
  - The rollback steps are skipped, because they need `LIVE_REVISION`.
- **Fix:**
  - Decide "first deploy" with an existence check that tells `ResourceNotFound` apart from other errors.
  - If the app exists and no live revision can be read, fail the run.

### I2. The seed-rotation procedure doesn't work as documented
- **Where:**
  - `infra/README.md:77`: "tick it ... after `STUDIO_DB_SEED` changes".
  - Workflow input description, line 31.
  - `db-setup.sql:10`.
- **Why it matters:**
  - Only `shared.bicep` (`deploy_shared`) sets the server admin password.
  - With a new seed and only `setup_database`, the admin login fails. The loop at lines 241-250 swallows psql's error
    and reports "Couldn't reach ... after 6 minutes", which points at the network instead.
  - After a successful rotation, the previous revision, kept for instant rollback, still holds the old app password.
    So rollback to it fails.
- **Fix:**
  - Document rotation as `deploy_shared` + `setup_database`, then a release, and say the previous revision can't be
    used for rollback afterwards.
  - Make the wait loop stop at once, with a clear message, when psql's stderr says `password authentication failed`.

### I3. The billable-feature guard is weaker than the ADR says
- **Where:** `_starter-deploy.yml:93-99`. The ADR (`:49`, `:233`) says "the workflow refuses any template that does".
- **What the grep misses:**
  - a custom network (`vnetConfiguration`, `infrastructureSubnetId`): the $25.55 a month the ADR itself identifies;
  - GPU consumption profiles: their type starts with `Consumption-`, so `'[^C]` passes them;
  - any profile type set through a parameter or variable.
- **Fix:** keep the grep, and also check the compiled JSON in `$RUNNER_TEMP` with jq:
  - every `workloadProfileType` is the literal `"Consumption"`;
  - there is no `vnetConfiguration`, `maintenanceConfigurations` or `Microsoft.Network/*` resource.

  Or soften the ADR's wording.

### I4. Switching provider between releases deletes a secret that the live and rollback revisions still use
- **Where:** `infra/main.bicep:226-244`. Secrets exist only for the chosen provider.
- **Why it matters:**
  - A release that switches `ai_provider` from azure to fake, or `billing_provider` from stripe to mock, removes
    `azure-openai-api-key` or the Stripe secrets in the same deployment. The live revision, and the previous one kept
    for rollback, still reference them.
  - Microsoft says: "Before you delete a secret, deploy a new revision that no longer references the old secret. Then
    deactivate all revisions that reference the secret."
  - With scale to zero, a cold start of the old revision, or `rollback_to` it, can then fail.
- **Fix:** always define all four secrets, with a placeholder value when unused, and vary only the env references. Or
  document that a provider switch can't be rolled back.

## Suggestions

1. **Deploy secrets behind a GitHub environment.**
   - Repository secrets (`AZURE_CREDENTIALS`, and now `STUDIO_DB_SEED`) are available to workflows on any branch. A
     branch can edit the workflow and drop the "main only" check, so that check guards against accidents only.
   - An environment with a "main only" deployment-branch rule is the real boundary. That matters in a studio where
     agents push branches (CLAUDE.md section 10).
   - First check that Vishal's GitHub plan offers environments for this repository. If it doesn't, say so in the ADR.
2. **db-setup.sql password handling:**
   - A failed `ALTER ROLE ... PASSWORD '...'` writes the full statement to the server log, plaintext included. I
     reproduced this on PG 16 with a canary value (`log_min_error_statement=error`, the default).
     - Send a SCRAM verifier computed client-side (`SCRAM-SHA-256$4096:...`) instead.
     - Do this before any Postgres logs are shipped (suggestion 4).
   - `\if :{?var}` checks only that the variable is defined. An empty `PG_APP_PASSWORD` passes and clears the password
     (NOTICE "empty string is not a valid password, clearing password", exit 0; reproduced). Check the length too.
3. **The app role has INSERT, UPDATE and DELETE on `alembic_version`** (reproduced), so a compromised app could make
   the next migration job skip or repeat migrations. Revoke those three after migrating, or accept it and say so.
4. **Failed sign-ins are invisible on a public endpoint.** Add a Postgres diagnostic setting for connection logs to
   `log-studio`, inside the cap, after suggestion 2.
5. **The firewall-rule cleanup hides failures** (`_starter-deploy.yml:262`, `2> /dev/null || true`).
   - Print a `::warning::` with the rule name, so a leftover rule gets noticed.
   - Low impact while the 0.0.0.0 rule exists, because GitHub-hosted runners are Azure addresses anyway.
6. **Startup probe `failureThreshold: 30`** (`main.bicep:326`).
   - The ARM reference says "Maximum value is 10", but Microsoft's own default probes use 240 (startup) and 48
     (readiness), so 30 is very likely accepted.
   - If the first deploy rejects it, use `periodSeconds: 6` with `failureThreshold: 10`.
7. **The first release is live before its migration.** With `latestRevision: true`, revision 1 takes traffic as soon as
   it is ready, before the migration job runs, so it answers 500s for a minute. That's harmless before launch; say so
   in the README.
8. **ADR accuracy:**
   - The "$0.20 a day" cap (`:172`) isn't strict while R14 is open: a retry can record 2× an estimate.
   - The "Microsoft's November 2026 update recommends azure-monitor" claim (`:223`) isn't on the cited log-options
     page, which calls Log Analytics the default. Cite the real source or drop the claim.
9. **Smaller items:**
   - Product roles can connect to the shared `postgres` database and list every database and role (PUBLIC's default
     CONNECT; reproduced).
   - Every release pushes a new tag, and Basic includes 10 GiB, so add an ACR cleanup later.
   - The workflow's apt fallback for psql could install a client older than 15, and `\getenv` needs 15 or later.
     Check `psql --version`.
   - While the previous revision is active, it is a second in-process rate-limit bucket for anyone who knows its
     address. Mention this next to the existing caveat.

## Decision 5, "Allow Azure services" for Postgres: accept for private demos, with conditions

The 0.0.0.0 rule is effectively public: Microsoft's own warning says "including connections from the subscriptions of
other customers", and any GitHub-hosted runner can reach the port. Private access costs about $25.55 a month, which is
over the $10 rule and a third of the credit in one month. For demos with no real customer data, I'd accept the 0.0.0.0
rule, on these conditions:

1. **Demo data only.** No real customer or employee personal data on the shared server. This ends at T-18 (Entra ID
   only, `passwordAuth: Disabled`) or private networking, whichever comes first. It must end before G4, before handover
   and before `unlock selling`.
2. **Keep the compensating controls as built.** I verified them:
   - 43-character derived passwords (160 bits from HMAC-SHA256);
   - TLS 1.3 minimum with `sslmode=verify-full`, against Azure's current roots (DigiCert Global Root G2 and Microsoft
     RSA Root CA 2017, both in the image's Debian bundle);
   - the admin password only inside Actions runs;
   - no DDL for the app role (8 of 8 attempts refused);
   - per-database CONNECT (another product's roles get "permission denied for database").
3. **Fix suggestion 2 before suggestion 4**, then add login auditing, so attacks on the open port are visible.
4. **Don't rely on the address being secret.** A connection limit of 12 and 3 per role is a resource cap, not access
   control.

## Release paths, walked through

| Path | What happens | OK? |
|---|---|---|
| First run (`deploy_shared` + `setup_database`) | The shared resources are created. The run stops at the AcrPull check and prints the exact command | yes, as the runbook says |
| First release (`setup_database`) | Database and roles are created (tested). Revision 1 takes traffic before migrating. No rollback exists | yes (suggestion 7) |
| Normal release | Zero-traffic candidate, then migrate, smoke the candidate, shift traffic, smoke the public address, retire older revisions | yes, except the jobs (C2) |
| Failed migration | Alembic runs all migrations in one transaction (env.py), so the schema is unchanged. The candidate is deactivated and the old revision keeps serving | yes, except purge (C2) |
| Failed candidate smoke test | The shift is skipped (`outcome == 'skipped'`) and the candidate is deactivated | yes, except purge (C2) |
| Failed public smoke test | Traffic goes back to the live revision and the candidate is deactivated | yes, except purge (C2) |
| Re-run | New tag and suffix (attempt number). The live revision is re-read from Azure | yes, except I1 |
| `rollback_to` | The input is regex-checked and passed through env (no injection). Then activate, smoke, shift, smoke | yes, except C2 and I4 |
| Seed rotation | Not as documented | no (I2) |

## Verified correct (evidence)

**Checks the brief asked for:**

| Check | Result |
|---|---|
| Resource types and API versions exist | yes: all 9, from Microsoft's "all versions" pages (table below) |
| Secure parameters never in outputs | yes: no output in either template carries one |
| Container Apps secrets referenced correctly | yes: every `secretRef` has a matching secret, and jobs get only their own database URL |
| AcrPull through the managed identity | yes: `registries[].identity` is the resource id. `lifecycle: None` is Microsoft's documented setting for "a managed identity that is only used for ACR image pull" (apps and jobs). The workflow checks the role assignment |
| Jobs | yes: the manual migration job (no retry, 600 s) and the scheduled purge (`17 3 * * *`, one retry). The image problem is C2 |
| HTTPS only | yes: `allowInsecure: false` ("HTTP connections are automatically redirected to HTTPS"), checked by smoke.sh |
| Probes | yes: `/livez` for startup and liveness, `/healthz` for readiness. See suggestion 6 |
| At most one replica | yes: `@minValue(1) @maxValue(1)` |
| Prod validator | yes, live: the web app (port 8600), `alembic upgrade head` and the purge job all start with `ENV=prod` and main.bicep's env, with `TRUST_PROXY_HEADERS` from the image |
| Postgres module | yes: v16, B1ms, 32 GB P4, autogrow off, 7-day backups, TLS 1.3, the 0.0.0.0 rule ("does the equivalent of Allow public access from any Azure service"). The admin password meets Azure's complexity rules and contains no 3-character part of `studioadmin` |
| Workflow guards | yes: `workflow_dispatch` only, credentials present, `STUDIO_AZURE_APPROVED == yes`, `refs/heads/main`. See I3 and suggestion 1 |
| Order of steps | build, scan (from a tarball, before sign-in), push by digest, zero-traffic revision, migrate, smoke, shift, smoke, rollback |
| Secrets in logs or on command lines | none found. Passwords travel in env (`PGPASSWORD=` prefix, `\getenv`, `readEnvironmentVariable`) and are masked before `GITHUB_ENV`. Only labels and names go on argv. On a forced auth failure, the app log has 0 lines with the password |
| `runner` context in job-level env | not used. actionlint 1.7.12: 0 errors (shellcheck isn't installed, so I read the `run:` blocks by hand) |

**API versions:**

| Type | Version | Exists | Properties checked |
|---|---|---|---|
| `Microsoft.App/containerApps` | 2025-07-01 | yes | `identitySettings`, `registries[].identity`, ingress, `traffic.latestRevision`, probes |
| `Microsoft.App/jobs` | 2025-07-01 | yes | `identitySettings`, `manualTriggerConfig`, `scheduleTriggerConfig` |
| `Microsoft.App/managedEnvironments` | 2025-07-01 | yes | `appLogsConfiguration.destination: 'azure-monitor'` |
| `Microsoft.ContainerRegistry/registries` | 2025-11-01 | yes | `roleAssignmentMode`: `AbacRepositoryPermissions` or `LegacyRegistryPermissions`. In ABAC mode, "privileged roles such as Owner, Contributor ... grant only control plane permissions", so pinning Legacy is right |
| `Microsoft.DBforPostgreSQL/flexibleServers`, `/configurations`, `/firewallRules` | 2024-08-01 | yes | version `'16'`, `authConfig`, `storage.autoGrow`, `network.publicNetworkAccess` |
| `Microsoft.OperationalInsights/workspaces` | 2023-09-01 | yes | |
| `Microsoft.ManagedIdentity/userAssignedIdentities` | 2023-01-31 | yes | |
| `Microsoft.Insights/diagnosticSettings` | 2021-05-01-preview | yes | categories: see C3 |
| `Microsoft.Authorization/roleAssignments` | 2022-04-01 | yes | |

**CLI flags** match the current az reference:
- `postgres flexible-server firewall-rule create|delete --server-name <server> --name <rule>`
- `containerapp job execution show --job-execution-name`
- `containerapp ingress traffic set --revision-weight name=weight`
- `containerapp revision activate|deactivate|show --revision [--name]`

**Prices** (Retail Prices API, uksouth, 2026-11-23). All match the ADR:

| Item | Price |
|---|---|
| ACR Basic | $0.1666 a day, so $5.07 a month |
| ACR Standard | $0.6666 a day, so $20.28 a month |
| Container Apps | vCPU $0.000034 a second, memory $0.000004 a GiB-second |
| "Environment Management Hour", "Planned Maintenance Hour", "Private Endpoint" | $0.10 an hour each (new meters, effective 2026-11-01) |
| Postgres B1MS | $0.019 an hour |
| Postgres storage | $0.133 a GB-month |
| Postgres backup (LRS) | $0.10 a GB-month |
| Log Analytics ingestion | $0 up to 5 GB, then $2.88 a GB |
| Data out | free up to 100 GB, then $0.08 a GB |
| Standard static IP | $0.005 an hour |
| Load balancer rules (included) | $0.025 an hour |
| GPT-5 mini Global | output $2.00 per million tokens, input $0.25 |

The arithmetic checks out: $13.87 + $4.26 = $18.13, plus $5.07 = $23.20 a month, so $80 lasts about 3.4 months.

**Student allowance:** Microsoft's Azure for Students page says "Free monthly amounts of 20+ popular services for 12
months (new Azure customers only)". The list includes:
- 12 months: "Azure Database for PostgreSQL: 750 hours of Flexible Server: Burstable B1MS Instance, 32 GB storage, and
  32 GB backup storage";
- 12 months: "Azure Container Registry: 1 Standard tier registry";
- always free: "Azure Container Apps: 180,000 vCPU seconds, 360,000 GiB seconds, and 2 million requests".

The ADR's claims are right, including the new-customer caveat. Vishal's "Free services" check is the right gate.

**Other docs:**
- Ingress: "HTTP requests to port 80 are automatically redirected", and "only the rightmost IP is provided by Azure
  Container Apps".
- Environments are deleted after 90 idle days.
- A custom network adds 1 or 2 static IPs and a load balancer.
- Trivy `0.76.2` on Docker Hub has index digest `sha256:8f6bb947…768fb`, the one pinned.

**SQL**, on local PG 16.15, with a non-superuser `CREATEDB CREATEROLE` admin and passwords made by the workflow's own
`derive()`:
- Both scripts run twice cleanly.
- The setup refuses when a password variable is unset.
- Five migrations ran as the migrator under the job env, and all tables are migrator-owned. A re-run was a no-op.
- The app role has DML on every table. The purge ran as the app role.
- 8 of 8 DDL attempts were refused, including temp tables, schemas and functions.
- Another product's roles get CONNECT refused.
- Connection limits are 12 and 3.

**smoke.sh** against the app (8600) and a fake ingress (4673: TLS proxied, plain HTTP redirected):

| Case | Result |
|---|---|
| `--local` | passes |
| https mode | passes (HSTS present, http gets 301) |
| http URL without `--local` | exit 2 |
| Ingress serves plain http | fails: "answered 200 instead of redirecting" |
| `COOKIE_SECURE=false` | fails: no HSTS |
| Database unreachable | fails after 26 s: `/healthz answered 503 ... "db":"down"` |
| `EXPECT_SPA=true` | fails: `/ answered 404` |

The database URL's TLS options parse into psycopg's `sslmode=verify-full` and `sslrootcert`.

**Backend suite at `f074262`:** 132 passed in 24.6 s, on database `t7rev_test`.

**`state/BUDGET.md`:** every billable resource is listed with an estimate that matches the API. The rows say "planned
(needs approval)", and Q-5 is queued as an ask-first question. This follows safety.md (only `rg-ai-studio`, $80 total,
ask first over $10 a month). The custom-network option, which would create a resource group outside `rg-ai-studio`, is
rejected.

## Method and gaps

- I tested an export of `f074262` in the session scratchpad.
- Every database and role was prefixed `t7rev_` and dropped afterwards. The test servers on 8600 and 4673 are stopped.
- Not tested: real ARM validation (no Bicep CLI or credentials), real Container Apps ingress, ACR pulls, and Azure's
  Postgres admin role (simulated with a `CREATEDB CREATEROLE` role).
- T-20 (compile the Bicep in CI) and the first real deploy will be the first runs of the templates. Expect small fixes.
