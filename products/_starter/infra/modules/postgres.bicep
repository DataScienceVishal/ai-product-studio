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
      activeDirectoryAuth: 'Disabled' // follow-up: passwordless Entra ID sign-in for the apps
      passwordAuth: 'Enabled'
    }
    storage: {
      storageSizeGB: 32
      autoGrow: 'Disabled' // growth past 32 GB would leave the free allowance without anyone noticing
      tier: 'P4'
    }
    backup: {
      backupRetentionDays: 7 // deleted rows stay restorable for 7 days: DATA.md must say so
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

// TLS 1.3 only, Microsoft's "best configuration". require_secure_transport is already on by default.
resource tlsMinimum 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: server
  name: 'ssl_min_protocol_version'
  properties: {
    value: 'TLSv1.3'
    source: 'user-override'
  }
}

resource azureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = if (allowAzureServices) {
  parent: server
  name: 'allow-azure-services'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
  dependsOn: [
    tlsMinimum // the server accepts one change at a time
  ]
}

output serverName string = server.name
output host string = server.properties.fullyQualifiedDomainName
