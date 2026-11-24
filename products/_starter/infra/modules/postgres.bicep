// The studio's one shared Postgres server: Burstable B1ms, one database per product (ADR 0002, decision 4).
// Created by shared.bicep. The SKU, the 32 GB of storage and autogrow-off are what the Azure for Students
// free allowance covers (750 hours of B1MS, 32 GB storage and 32 GB backup a month, for 12 months).
// Changing any of them changes the bill: update state/BUDGET.md and ask Vishal first.

@description('Globally unique server name.')
param serverName string

param location string

@description('Server admin login. Only the deploy workflow uses it, to create product databases and roles.')
param adminLogin string = 'studioadmin'

@secure()
@description('Server admin password. The deploy workflow derives it from the STUDIO_DB_SEED secret.')
param adminPassword string

@description('Open the firewall to Azure IP addresses (the 0.0.0.0 rule). ADR 0002, decision 5 explains why.')
param allowAzureServices bool = true

@description('Password sign-in. Enabled while phase 1 of ADR 0003 runs (the Entra admin is added after the server exists); phase 2 flips this to Disabled, in shared.bicepparam and here, as its own change.')
@allowed([
  'Enabled'
  'Disabled'
])
#disable-next-line secure-secrets-in-params
param passwordAuth string = 'Enabled'

@description('Postgres role name of the Entra admin (the deploy service principal, SETUP.md step 3). The workflow reads the real value back.')
param entraAdminName string = 'sp-ai-studio-deployer'

param tags object = {}

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16' // matches CI and local development
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    authConfig: {
      // flexibleServers 2024-08-01 AuthConfig: activeDirectoryAuth, passwordAuth, tenantId
      // https://learn.microsoft.com/azure/templates/microsoft.dbforpostgresql/2024-08-01/flexibleservers
      activeDirectoryAuth: 'Enabled'
      passwordAuth: passwordAuth
      tenantId: tenant().tenantId
    }
    storage: {
      storageSizeGB: 32
      autoGrow: 'Disabled' // growth past 32 GB would leave the free allowance without anyone noticing
      tier: 'P4'
    }
    backup: {
      backupRetentionDays: 7 // deleted rows stay in backups for up to 7 days (DATA.md says so)
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

// Server parameters (all dynamic: no restart). The port is reachable from Azure addresses (ADR 0002,
// decision 5), so every sign-in attempt is logged, and the server keeps its logs for download.
var serverParameters = [
  {
    name: 'ssl_min_protocol_version'
    value: 'TLSv1.3' // Microsoft's "best configuration"; require_secure_transport is on by default
  }
  {
    name: 'log_connections'
    value: 'on' // the default, pinned: logs each attempt with its source address, and failed sign-ins
  }
  {
    name: 'log_error_verbosity'
    value: 'terse' // no DETAIL lines, which can quote row values such as an email in a unique-key error
  }
  {
    name: 'logfiles.download_enable'
    value: 'on' // keep server logs for download; they stay out of log-studio and its daily cap
  }
  {
    name: 'logfiles.retention_days'
    value: '7' // the maximum Azure allows
  }
]

@batchSize(1) // the server accepts one change at a time
resource serverSettings 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = [for setting in serverParameters: {
  parent: server
  name: setting.name
  properties: {
    value: setting.value
    source: 'user-override'
  }
}]

resource azureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = if (allowAzureServices) {
  parent: server
  name: 'allow-azure-services'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
  dependsOn: [
    serverSettings // after the parameters, for the same reason
  ]
}

// ADR 0003, decision 2: the deploy service principal is the Entra admin. The name is the principal's object id;
// deployer() is whoever runs the deployment, so deploy shared resources only from the workflow.
// https://learn.microsoft.com/azure/templates/microsoft.dbforpostgresql/2024-08-01/flexibleservers/administrators
// https://learn.microsoft.com/azure/azure-resource-manager/bicep/bicep-functions-deployment#deployer
resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2024-08-01' = {
  parent: server
  name: deployer().objectId
  properties: {
    principalType: 'ServicePrincipal'
    principalName: entraAdminName
    tenantId: tenant().tenantId
  }
  dependsOn: [
    serverSettings // the server takes one change at a time
    azureServices
  ]
}

output serverName string = server.name
output host string = server.properties.fullyQualifiedDomainName
