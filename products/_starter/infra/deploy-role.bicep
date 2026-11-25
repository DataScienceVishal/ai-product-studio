// Least-privilege custom role for the GitHub OIDC deploy identity `id-github-deploy` (T-65, ADR 0002 decision 8).
// It replaces the built-in Contributor role on rg-ai-studio. NOT APPLIED YET: Vishal (Owner) creates it once,
// see "Least-privilege deploy role (T-65)" in infra/README.md.
//
//   az deployment group create -g rg-ai-studio -f deploy-role.bicep                      # role only
//   az deployment group create -g rg-ai-studio -f deploy-role.bicep \
//     -p assign=true deployPrincipalId=<principalId of id-github-deploy>                  # role + assignment
//
// What it cannot do, by construction:
//   - grant itself or anyone else access: no Microsoft.Authorization/roleAssignments/write or roleDefinitions/write
//     (only read), and notActions repeats the deny so a later wildcard added by mistake still can't write them;
//   - touch anything outside rg-ai-studio: assignableScopes is this group only;
//   - register resource providers (needs subscription scope), create the group, or change locks and policy.
// A missing action makes a deploy fail with AuthorizationFailed naming the action; it is never a silent hole.
// Add that one action here, redeploy this file, and note it in the README. Do not add wildcards.
// test-deploy-role.sh checks this file without Azure.
targetScope = 'resourceGroup'

@description('Name shown in the portal. Role names must be unique in the tenant.')
param roleName string = 'Studio Deployer (rg-ai-studio)'

@description('Create the role assignment to the deploy identity too. Needs an Owner or User Access Administrator; default false.')
param assign bool = false

@description('Object (principal) id of id-github-deploy: az identity show -g rg-ai-studio -n id-github-deploy --query principalId -o tsv. Only used when assign is true.')
param deployPrincipalId string = ''

var roleDefinitionName = guid(resourceGroup().id, 'studio-deployer-role')

resource deployerRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: roleDefinitionName
  properties: {
    roleName: roleName
    description: 'Deploys the studio Bicep templates and releases through GitHub Actions on one resource group. Cannot manage role assignments or role definitions.'
    type: 'CustomRole'
    assignableScopes: [
      resourceGroup().id
    ]
    permissions: [
      {
        actions: [
          // ---- ARM deployments: `az deployment group create` (studio-shared, <product>-r<n>-a<n>) ------------------------
          // Deploy workflow steps "Deploy shared resources" and "Deploy the release". `az` creates the deployment,
          // polls its operations and operationStatuses; Bicep validates first. whatIf/validate cover `--what-if` and
          // future `validate` runs.
          'Microsoft.Resources/deployments/read'
          'Microsoft.Resources/deployments/write'
          'Microsoft.Resources/deployments/validate/action'
          'Microsoft.Resources/deployments/whatIf/action'
          'Microsoft.Resources/deployments/operations/read'
          'Microsoft.Resources/deployments/operationStatuses/read'
          // No deployments/delete and no deployments/cancel: the workflow never removes or cancels a deployment.

          // ---- Resource group reads: azure/login, `az resource list` (scripts/azure_spend.py), deployments ------------
          'Microsoft.Resources/subscriptions/read'
          'Microsoft.Resources/subscriptions/resourceGroups/read'
          'Microsoft.Resources/subscriptions/resources/read'
          // `az resource list --resource-group` (scripts/azure_spend.py inventory) reads resources under the group.
          'Microsoft.Resources/subscriptions/resourceGroups/resources/read'

          // ---- Cost reads: azure-spend.yml / scripts/azure_spend.py POSTs a Cost Management query at RG scope ----------
          'Microsoft.CostManagement/query/action'
          'Microsoft.CostManagement/query/read'

          // ---- Role reads only: "Shared resources exist and the app can pull images" runs `az role assignment list`
          // on the registry. Read, never write: AcrPull is granted once by Vishal (README step 5). ---------------------
          'Microsoft.Authorization/roleAssignments/read'
          'Microsoft.Authorization/roleDefinitions/read'

          // ---- Managed identities: shared.bicep (id-studio-acrpull), main.bicep (id-<app>-app, id-<app>-migrate), -----
          // `az identity show`. assign/action is needed to attach an identity to a container app or job.
          // No federatedIdentityCredentials: the workflows never create or change them (SETUP.md does, by hand).
          // Must not let the deployer add a trust to its own identity.
          'Microsoft.ManagedIdentity/userAssignedIdentities/read'
          'Microsoft.ManagedIdentity/userAssignedIdentities/write'
          'Microsoft.ManagedIdentity/userAssignedIdentities/assign/action'

          // ---- Container Registry: shared.bicep (registry, Basic, LegacyRegistryPermissions), `az acr show`, ----------
          // `az acr login` and `docker push` in "Build, scan and push the image". In LegacyRegistryPermissions mode the
          // token exchange checks these two control-plane actions (ADR 0002 decision 3). No listCredentials: the admin
          // user is disabled and nothing reads registry passwords.
          'Microsoft.ContainerRegistry/registries/read'
          'Microsoft.ContainerRegistry/registries/write'
          'Microsoft.ContainerRegistry/registries/push/write'
          'Microsoft.ContainerRegistry/registries/pull/read'
          'Microsoft.ContainerRegistry/locations/operationResults/read'

          // ---- Container Apps environment: shared.bicep (cae), main.bicep (existing reference), `az containerapp env show`.
          // join/action is needed to put an app or job into the environment.
          'Microsoft.App/managedEnvironments/read'
          'Microsoft.App/managedEnvironments/write'
          'Microsoft.App/managedEnvironments/join/action'
          // Async operation polling for the three Microsoft.App types.
          'Microsoft.App/locations/containerappOperationResults/read'
          'Microsoft.App/locations/containerappOperationStatuses/read'
          'Microsoft.App/locations/managedEnvironmentOperationResults/read'
          'Microsoft.App/locations/managedEnvironmentOperationStatuses/read'
          'Microsoft.App/locations/jobOperationResults/read'
          'Microsoft.App/locations/jobOperationStatuses/read'

          // ---- Container app: main.bicep (web), release steps: `az containerapp show`, `ingress traffic set` (a write), -
          // `revision show|list|activate|deactivate` (candidate checks, rollback, "Clean up old revisions").
          // Deactivate is not a delete: it keeps the revision's history. No listSecrets: no step reads secret values.
          'Microsoft.App/containerApps/read'
          'Microsoft.App/containerApps/write'
          'Microsoft.App/containerApps/revisions/read'
          'Microsoft.App/containerApps/revisions/activate/action'
          'Microsoft.App/containerApps/revisions/deactivate/action'

          // ---- Container Apps jobs: main.bicep (migrate, purge), "Run the migration job": `az containerapp job start` ----
          // and `job execution show`.
          'Microsoft.App/jobs/read'
          'Microsoft.App/jobs/write'
          'Microsoft.App/jobs/start/action'
          'Microsoft.App/jobs/executions/read'

          // ---- Postgres flexible server: modules/postgres.bicep (server, configurations, firewallRules, administrators), -
          // `az postgres flexible-server show`, `firewall-rule create` (runner IP for db-setup, "Database setup") and
          // `az rest GET .../administrators` (find the Entra admin). Databases are made by db-setup.sql over a normal
          // connection, so no databases/* actions.
          'Microsoft.DBforPostgreSQL/flexibleServers/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/write'
          'Microsoft.DBforPostgreSQL/flexibleServers/configurations/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/configurations/write'
          'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules/write'
          // The one delete kept: the always-run step removes the temporary rule gh-run-<run id> (security: no standing
          // database exposure). Scoped to this action type only; the server itself cannot be deleted.
          'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules/delete'
          'Microsoft.DBforPostgreSQL/flexibleServers/administrators/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/administrators/write'
          'Microsoft.DBforPostgreSQL/locations/azureAsyncOperation/read'
          'Microsoft.DBforPostgreSQL/locations/operationResults/read'

          // ---- Log Analytics and diagnostics: shared.bicep (workspace, diagnostic setting on the environment) ------------
          // No sharedKeys/action: the environment logs through azure-monitor, not a workspace key.
          'Microsoft.OperationalInsights/workspaces/read'
          'Microsoft.OperationalInsights/workspaces/write'
          'Microsoft.Insights/diagnosticSettings/read'
          'Microsoft.Insights/diagnosticSettings/write'
        ]
        // Defence in depth: these are not in `actions`, and stay denied even if a wildcard is added by mistake.
        notActions: [
          'Microsoft.Authorization/*/write'
          'Microsoft.Authorization/*/delete'
          'Microsoft.Authorization/elevateAccess/action'
          'Microsoft.Authorization/locks/*'
          'Microsoft.Authorization/policyAssignments/*'
          'Microsoft.Resources/subscriptions/resourceGroups/delete'
          'Microsoft.Resources/subscriptions/resourceGroups/write'
          'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials/*'
        ]
        dataActions: []
        notDataActions: []
      }
    ]
  }
}

// Optional: give the role to id-github-deploy. Skipped unless assign=true. Needs Owner (Authorization write).
resource deployerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (assign) {
  name: guid(resourceGroup().id, deployerRole.id, deployPrincipalId)
  properties: {
    roleDefinitionId: deployerRole.id
    principalId: deployPrincipalId
    principalType: 'ServicePrincipal'
    description: 'T-65: least-privilege deploy role for GitHub Actions (instead of the built-in broad role).'
  }
}

output roleDefinitionId string = deployerRole.id
output assigned bool = assign
