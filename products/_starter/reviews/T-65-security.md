# T-65 security gate: least-privilege deploy role

Reviewed: `origin/p/_starter/T-65-deploy-role` at 9fb4ed8. The later commit 1bc05f9 only adds a CI compile line. Static review only; nothing was applied to Azure.
Reviewer: security agent, 2026-11-25.

## Verdict: CHANGES (small)

The role meets its main goal. It cannot grant access to itself or anyone else, cannot write role definitions, cannot touch federated credentials, has no list*/sharedKeys/Key Vault/data actions, has no wildcards, is scoped to the resource group only and has a deterministic name. That is a real improvement over Contributor. Four things need changing before it counts as done:
- one likely missing action (the spend report would fail);
- the test misses the most dangerous secret-reading actions;
- the README test option is misleading and the check skips inherited roles;
- the persistence risk around `id-github-deploy` is not documented.

## Results per check

| # | Check | Result |
|---|---|---|
| 1 | No self or other escalation | PASS for RBAC escalation. Residual data-access and persistence paths are listed under M1 to M3 |
| 2 | notActions semantics | PASS. Every entry in `actions` is explicit, so notActions removes nothing today. It only guards against a future wildcard in this same role. It is not a deny across other assignments: while Contributor is still assigned it restricts nothing. The README wording on lines 124-127 suggests otherwise (L2) |
| 3 | assignableScopes and name | PASS. `[resourceGroup().id]` only (deploy-role.bicep:36-38). Name is `guid(resourceGroup().id, 'studio-deployer-role')` (line 28). The assignment name is a deterministic guid and `assign` defaults to false |
| 4 | Coverage | CHANGES. H1 below is likely missing. Everything else maps to a template type or an `az` step. Surplus is minor (L3) |
| 5 | Apply and rollback order | CHANGES (M4). No privilege gap: Contributor stays until the new role is assigned. But the "both roles" option proves nothing, and the leftover check ignores inherited roles |
| 6 | Test bites | PARTLY. 12 mutations tried in scratch copies (repo not touched). It catches: roleAssignments/write, a wildcard, dataActions, a wider scope, federatedIdentityCredentials/write, a removed jobs/start, a removed notActions auth write, and an extra delete. It **misses**: `Microsoft.App/containerApps/listSecrets/action`, `Microsoft.KeyVault/vaults/secrets/getSecret/action`, `Microsoft.OperationalInsights/workspaces/sharedKeys/action` and `Microsoft.App/containerApps/getAuthToken/action` (exec). All four pass with 64/64 (M5) |

## Findings, ranked

### H1 (deploy-breaking, not a hole): the action for `az resource list --resource-group` is likely missing
- Where: `deploy-role.bicep:57` grants `Microsoft.Resources/subscriptions/resources/read`. `scripts/azure_spend.py:210` runs `az resource list --resource-group`, which calls `GET /subscriptions/{s}/resourceGroups/{rg}/resources`. That call's operation is `Microsoft.Resources/subscriptions/resourceGroups/resources/read`.
- Impact: the inventory in the daily spend report gets AuthorizationFailed once Contributor is removed. The script degrades rather than crashes, but the report loses its UNLISTED check, which is the budget guard.
- Fix: add `'Microsoft.Resources/subscriptions/resourceGroups/resources/read'` (read only) and add it to `extra` in `test-deploy-role.sh:105`. Keep or drop the subscription-level entry; it is harmless either way.

### M1: `userAssignedIdentities/assign/action` also covers `id-github-deploy` itself (persistence outside GitHub OIDC)
- Where: `deploy-role.bicep:74`. SETUP.md:46 creates `id-github-deploy` inside `rg-ai-studio`.
- Impact: a malicious workflow on `main` can use `containerApps/write` or `jobs/write` to attach `id-github-deploy` to an app or job that runs attacker code. That gives standing deploy rights from inside Azure, including Postgres Entra admin (postgres.bicep:130 makes the deployer the admin). The access survives deleting the federated credential or rotating GitHub secrets. Contributor has the same problem today, so this is not a regression. But a role definition cannot narrow `assign/action` to particular identities, and ABAC conditions do not support this action.
- Fix: move `id-github-deploy` to a separate group, for example `rg-ai-studio-ci`. Federated credentials go with the identity, so this is an Owner step plus a client-id secret update. The role assigned on `rg-ai-studio` then cannot attach it. If the move is deferred, record it in SECURITY.md L2 as accepted residual risk.

### M2: the deployer can add any Entra principal as a Postgres admin, and can turn password sign-in back on
- Where: `deploy-role.bicep:129` (`administrators/write`) and `:121` (`flexibleServers/write`, which covers `passwordAuth` and `administratorLoginPassword`). `firewallRules/write` can also open `0.0.0.0-255.255.255.255`.
- Impact: lasting database access for an attacker's own principal, outside the pipeline. These actions are needed only when `deploy_shared` runs, not for an ordinary release.
- Fix (choose one, then document it): (a) split the role into a release role and a shared role. The release role has no Postgres server or administrator writes, no registry, environment or workspace writes, and keeps only the firewallRules write and delete. The shared role goes behind a GitHub environment with a required reviewer, using a second federated credential (SETUP.md:74-80 already describes how). Or (b) Vishal sets the Entra admin once by hand, `administrators/write` is dropped and `administrators/read` is kept. At minimum, list this in SECURITY.md L2 as residual risk.

### M3: deploy-inherent code execution. Unavoidable, but say so
- `containerApps/write` and `jobs/write` with `jobs/start` let a workflow run any image with any environment under the app or migrate identity. That code can read the Container Apps secrets as environment variables and reach the database. A deploy role cannot avoid this. The real control is on the GitHub side: who can push to `main`, branch protection and CODEOWNERS on `.github/`, and the subject being pinned to `refs/heads/main` (SETUP.md:51).
- `listSecrets`, `getAuthToken` (exec), `sharedKeys`, `listCredentials` and `workspaces/query/read` are correctly absent, so nothing can read secrets or logs through the API alone.
- Fix: add one line to SECURITY.md L2 saying the remaining risk is "push to main = run code with app identities", and name the GitHub controls that cover it.

### M4: README apply steps
- `README.md:137`: "run one release with both roles first" proves nothing, because Contributor hides every missing action. Fix: delete that sentence, or say it only checks that the assignment exists.
- `README.md:141`: `az role assignment list --assignee ... --scope "$SCOPE"` does not show subscription-level or management-group assignments. Fix: add `--include-inherited --all`, or run a second list with no scope, and say that no Contributor or Owner may remain at any scope.
- `README.md:168`: the `AZURE_COST_CREDENTIALS` service principal fallback is a second identity this role does not cover. Fix: tell Vishal to check its assignments too (Cost Management Reader on the group only), or delete it once OIDC works.
- Rollback (README "Rolling back") is correct and fast. Leaving the unassigned custom role in place grants nothing.

### M5: the test misses the secret-reading actions the role says it excludes
- Where: `test-deploy-role.sh:61` only checks for names ending in `/listcredentials/action` and `/listkeys/action`.
- Fix: replace that check with a deny pattern list (case-insensitive), so no action may match:
  - `/list[a-z]*secrets?/action`, `/listkeys`, `/listcredentials`, `/sharedkeys/`
  - `/getauthtoken/action`, `/exec/action`
  - `^microsoft.keyvault/`
  - `/generatecredentials/action`, `/regeneratekey`
  - `/federatedidentitycredentials/`
  - `^microsoft.authorization/(?!roleassignments/read$|roledefinitions/read$)`

  Better still, pin the exact action set: compare `actions` to a sorted list held in the test. Any added action then fails CI until a reviewer updates both files, which turns surplus actions into a review event.
- Also `test-deploy-role.sh:86` hard-codes three Bicep files. Fix: glob `*.bicep` and `modules/*.bicep`, excluding `deploy-role.bicep`, so a new module is covered automatically. The `extra` list (line 105) is hand-written, not parsed from `az` calls in the workflows. That is acceptable, but say so in the header.

### L1: unverified operation names (failure risk only)
The Microsoft.App async polling names (`locations/*OperationResults|OperationStatuses/read`), `jobs/executions/read`, `Microsoft.CostManagement/query/read` and the diagnostic setting's check on the destination workspace could not be confirmed here. Microsoft's docs do not say whether a diagnostic setting that sends to Log Analytics needs `workspaces/sharedKeys/action` on the workspace. If Azure asks for it on `caeLogs`, prefer `Microsoft.OperationalInsights/workspaces/write`, which is already granted. Add `sharedKeys` only with a written reason, because it exposes the workspace ingestion key. The README Risks section already covers this kind of failure.

### L2: wording
`deploy-role.bicep:10-11, 140` and `README.md:124-127` present notActions as the reason the role "can't grant access". The reason is that the write actions are not in `actions`. notActions is not a deny and has no effect on other role assignments. Fix: reword as "not granted; notActions only guards against a future wildcard in this role".

### L3: surplus with no clear use (low impact)
- `Microsoft.Resources/subscriptions/read`: it cannot match anything when the role is assigned at group scope. Harmless.
- `registries/write` and `workspaces/write` are needed only for the shared deploy. Through them a workflow could set `adminUserEnabled: true` (it cannot read the password without listCredentials), cut log retention, or turn off immediate purge. These belong in the shared role if M2(a) is taken.
- The spend workflow runs as the deploy identity. A reader-only identity for `azure-spend.yml` (Cost Management Reader plus Reader on the group) would keep deploy rights out of a scheduled job.

## Evidence
- `bash products/_starter/infra/test-deploy-role.sh` on the branch: `64 passed, 0 failed`.
- Mutation runs in scratch copies (the test takes the infra directory as an argument):
  - caught: roleAssignments write (3 FAIL), `jobs/*` (2 FAIL), dataActions (1), subscription scope (1), FIC write (1), jobs/start removed (1), notActions auth write removed (1), containerApps/delete (1);
  - not caught (64/64 pass): listSecrets, Key Vault getSecret, sharedKeys, getAuthToken.
- Every `az` call in `_starter-deploy.yml` was mapped to an action, along with azure_spend.py (cost query and resource list) and every `resource` in main.bicep, shared.bicep and modules/postgres.bicep. Only H1 has no action.
