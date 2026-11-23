// Shared studio resources (ADR 0002). Created once, after Vishal approves the costs in state/BUDGET.md, by
// the deploy workflow with deploy_shared ticked. Every product's main.bicep uses them by name.
//
//   log-studio (Log Analytics) <── diagnostic setting ── cae-studio (Container Apps environment)
//   acrstudio... (registry) <── AcrPull ── id-studio-acrpull (pulls images for every app and job)
//   psql-studio-... (Postgres B1ms, one database per product)
//
// Cost guard: never give the environment a Dedicated workload profile, a planned maintenance window or a
// private endpoint. Each starts a flat $0.10 an hour (about $73 a month) charge. The deploy workflow
// refuses templates that contain them.

param location string = 'uksouth'

param environmentName string = 'cae-studio'
param logAnalyticsName string = 'log-studio'
param pullIdentityName string = 'id-studio-acrpull'

@description('Globally unique registry name: letters and digits only.')
param registryName string

@description('Basic is about $5 a month. Standard is free for 12 months only while the student allowance lasts, then about $20.')
@allowed([
  'Basic'
  'Standard'
])
param registrySku string = 'Basic'

@description('Globally unique Postgres server name.')
param postgresServerName string

@secure()
param postgresAdminPassword string

param postgresAllowAzureServices bool = true

@description('Create the AcrPull role assignment here. Needs Owner, so only Vishal sets it; the Contributor deployer leaves it false.')
param grantPullRole bool = false

var tags = {
  studio: 'shared'
  managedBy: 'bicep'
  decision: 'products/_starter/ADR/0002-azure-deploy.md'
}

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30 // SECURITY.md D3; 31 days are included in the ingestion price
    features: {
      immediatePurgeDataOn30Days: true // really gone after 30 days (privacy), not "up to 31"
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: json('0.1') // at most about 3 GB a month, inside the free 5 GB
    }
  }
}

resource cae 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor' // routed by the diagnostic setting below; no shared key in the environment
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption' // the only profile: pay per second, scale to zero
      }
    ]
    zoneRedundant: false
  }
}

resource caeLogs 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'to-log-studio'
  scope: cae
  properties: {
    workspaceId: logs.id
    logs: [
      {
        categoryGroup: 'allLogs' // container console output and system logs
        enabled: true
      }
    ]
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' = {
  name: registryName
  location: location
  tags: tags
  sku: {
    name: registrySku
  }
  properties: {
    adminUserEnabled: false // apps pull with the managed identity, never a shared password
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled' // Basic can't restrict networks; pulls and pushes still need Entra ID
    roleAssignmentMode: 'LegacyRegistryPermissions' // so the Contributor deployer can push (ADR 0002, decision 3)
  }
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: pullIdentityName
  location: location
  tags: tags
}

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d' // built-in AcrPull

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (grantPullRole) {
  name: guid(registry.id, pullIdentity.id, acrPullRoleId)
  scope: registry
  properties: {
    principalId: pullIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'studio-postgres'
  params: {
    serverName: postgresServerName
    location: location
    adminPassword: postgresAdminPassword
    allowAzureServices: postgresAllowAzureServices
    tags: tags
  }
}

output environmentName string = cae.name
output environmentDefaultDomain string = cae.properties.defaultDomain
output registryName string = registry.name
output registryLoginServer string = registry.properties.loginServer
output registryId string = registry.id
output pullIdentityPrincipalId string = pullIdentity.properties.principalId
output postgresHost string = postgres.outputs.host
