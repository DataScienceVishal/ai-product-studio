# Review: p/_starter/T-18-bicep (ADR 0003 build slices 1 and 2)

- Commit reviewed: cc62daa, diff against origin/main (9dd2acd). Files: `infra/main.bicep`, `infra/modules/postgres.bicep`,
  `infra/shared.bicep`, `infra/test-bicep-identities.sh` (new), `.github/workflows/_starter-ci.yml`, `NEXT.md`.
- Read against ADR 0003 decisions 1, 2, 6 and 7 and `reviews/T-18-adr-security.md`.
- Reviewer: reviewer agent, 2026-11-24.

## Verdict: PASS (0 blocking, 6 non-blocking)

Slices 1 and 2 do what the ADR says, compile cleanly, and the new jq test fails for the mutations that matter
(13 of the 14 I tried). Password mode leaves every container's env as it is today. The non-blocking items are
mainly about handover and gaps in the test. None of them changes what would deploy today.

## Evidence

- **Compile (Bicep v0.32.4, linux-x64, downloaded from the GitHub release, sha256 `1264a3b7...4b40`):** `bicep build
  shared.bicep`, `bicep build main.bicep`, `bicep build-params shared.bicepparam` and `main.bicepparam` all succeed.
  The only warnings are the existing BCP081 "no types available" ones for `managedEnvironments`/`containerApps`/`jobs@2025-07-01`
  and `registries@2025-11-01` (also on main).
- **`test-bicep-identities.sh`:** all 18 checks `ok`, rc 0.
- **`cost-guard.sh`:** "2 template(s) use only the Consumption profile, no custom network and no fixed-charge
  features", rc 0.
- **CI run 45367710716** (`_starter-ci`, head cc62daa): **success**. frontend, infra, backend and image passed; e2e
  skipped (as on other push runs). The infra log shows "test-bicep-identities: all checks passed" and the cost-guard line.
- **Mutation test of the jq script.** I made each change to the Bicep source, rebuilt and counted FAIL lines:

  | Mutation | FAILs |
  |---|---|
  | migrate job given `webIdentity` (app identity) | 1 |
  | purge job given `migrateJobIdentity` | 1 |
  | DB identity lifecycle `Main` changed to `All` | 2 |
  | pull identity lifecycle `None` changed to `All` | 2 |
  | purge env takes `migrateDbAuthEnv` | 1 |
  | DB_AUTH env set unconditionally (`true ?`) | 2 |
  | migrate env missing `migrateDbAuthEnv` | 1 |
  | migrate AZURE_CLIENT_ID set to the app identity's clientId | 1 |
  | `activeDirectoryAuth: 'Disabled'` | 1 |
  | `postgresPasswordAuth` default `Disabled` in shared.bicep | 1 |
  | administrators `dependsOn` loses `serverSettings` | 1 |
  | administrators `principalType: 'User'` | 1 |
  | web gets a third identity (migrate) | 2 |
  | **shared.bicep stops passing `passwordAuth: postgresPasswordAuth` to the module** | **0** (N2) |

## Microsoft Learn checks (template references read 2026-11-24)

| Code | Learn | Result |
|---|---|---|
| `Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31`, name, location, tags | the 2023-01-31 reference | Correct |
| `identity.type: 'UserAssigned'` + `userAssignedIdentities` map on `containerApps` and `jobs@2025-07-01` | the jobs 2025-07-01 reference has `ManagedServiceIdentity` with `userAssignedIdentities` | Correct |
| `configuration.identitySettings[] { identity, lifecycle }` on the app and both jobs | jobs 2025-07-01 `IdentitySettings`: `identity` is "the resource ID of a user-assigned managed identity", `lifecycle` is `'All' 'Init' 'Main' 'None'` | Correct. The id strings are the same `.id` in both places, so they match |
| `authConfig { activeDirectoryAuth, passwordAuth, tenantId }` on `flexibleServers@2024-08-01` | `AuthConfig`: `activeDirectoryAuth` and `passwordAuth` take `'Disabled'`/`'Enabled'`, `tenantId` is a string | Correct |
| `flexibleServers/administrators@2024-08-01`: name `deployer().objectId`, `principalType: 'ServicePrincipal'`, `principalName`, `tenantId` | properties `principalName` (string), `principalType` (`'Group' 'ServicePrincipal' 'Unknown' 'User'`), `tenantId` (string); the name is the object id | Correct for the workflow SP. See N1 for an Owner user |

## ADR conformance

- **Decision 1, identity separation:** `ca-<slug>` and `caj-<slug>-purge` get `pullIdentity` + `id-<slug>-app`.
  `caj-<slug>-migrate` gets `pullIdentity` + `id-<slug>-migrate`. Neither side gets the other's identity. The pull
  identity is `None` and the DB identity is `Main`, everywhere. In entra mode the app and purge get the app clientId
  and migrate gets the migrate clientId. The mutation table confirms each of these is guarded.
- **Password mode behaves as before:** `appDbAuthEnv`/`migrateDbAuthEnv` compile to
  `if(variables('useEntra'), createArray(...), createArray())`. With the default `dbAuth='password'` (and
  `main.bicepparam` doesn't set it), `concat` adds nothing, so the env of the web app, migrate and purge is identical
  to main. DATABASE_URL secrets are unchanged. ARM's `if` evaluates only the branch it takes, and the identity
  exists in both modes anyway, so the `reference()` to clientId is safe. New outputs are additive: the workflow reads
  only `candidateRevision` and `appFqdn` by key. The identity attachment is application-scoped configuration, not a
  revision change. Contributor (`*` actions) covers creating identities and the `assign/action` needed to attach them.
- **Decision 2:** authConfig and the admin child match the ADR snippet line for line, including
  `dependsOn: [serverSettings, azureServices]`.
- **Decision 6, slice CI checks:** both are present (the identity/lifecycle jq checks and admin-depends-on-settings-and-firewall).
- **Decision 7, cost:** $0. The two identities need $0 rows in `state/BUDGET.md` (N5).

## Non-blocking

1. **N1. `principalType` is hard-coded to `ServicePrincipal`, but `deployer()` is whoever deploys.** The
   `shared.bicepparam` comment and `infra/README.md` "At handover" both say an **Owner account** deploys
   `shared.bicep` (with `GRANT_PULL_ROLE=true`). In that case `deployer().objectId` is a *user*, so the ARM call
   either fails or registers a user as `ServicePrincipal` named `sp-ai-studio-deployer`. The comment in
   postgres.bicep ("deploy shared resources only from the workflow") contradicts the README. Fix: add a
   `postgresEntraAdminType` param (default `ServicePrincipal`) next to `postgresEntraAdminName`, or update the
   README handover steps to set both. This doesn't affect the studio deploy, which uses the SP.
2. **N2. The test misses a dropped module wiring.** If shared.bicep stopped passing
   `passwordAuth: postgresPasswordAuth`, the test would still pass (0 FAILs above). Then phase 2's
   `shared.bicepparam` flip would silently never reach the server; only the module default would catch it. Add a check that the
   `studio-postgres` deployment's `parameters.passwordAuth.value == "[parameters('postgresPasswordAuth')]"`, and
   the same for `entraAdminName`.
3. **N3. `principalName` is not asserted, and its default is a guess.** `sp-ai-studio-deployer` must equal the SP's
   real display name, or at least it becomes the Postgres role name the workflow has to use. The ADR has slice 4 read it back.
   Add it to the "only the first real deploy can verify" list: does ARM accept a `principalName` that differs from the
   Graph display name, and which role name does it create?
4. **N4. Slice 2 changes the first `deploy_shared` even in password mode.** From this merge on, the first shared
   deploy enables Entra (a server restart on existing servers) and creates the admin. If the Contributor SP is
   refused, `deploy_shared` fails and blocks T-7's first deploy, not just T-18. The ADR's failure-mode row covers
   this (Vishal adds the admin in the portal). NEXT.md mentions the side effect. Put it in the hand-off to whoever
   runs the first deploy too.
5. **N5. BUDGET rows.** ADR decision 7: add `id-starter-app` and `id-starter-migrate` ($0, "planned") to
   `state/BUDGET.md` on main when this merges.
6. **N6. `dbAuth=entra` is not usable before slice 4.** The app refuses a DATABASE_URL that carries a password
   (`validate_entra_url`), and the URLs still carry one. So flipping `dbAuth` by hand today would break the release.
   The param description implies this ("the workflow flips this in slice 4"). Saying "do not set entra before
   slice 4: the URLs still carry passwords" outright would make it safe.

## Tests

The jq checks test structure on the compiled JSON, not Azure's behaviour, and the script header says so honestly.
Each check failed when the protection it claims was mutated, apart from N2. The string-match approach (`contains`
on ARM expression text) is brittle across Bicep versions, but it is pinned by CI's `az bicep` and a change shows up
as a loud failure rather than a silent pass. Acceptable.
