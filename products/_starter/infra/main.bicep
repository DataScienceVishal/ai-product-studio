// One product on the shared studio platform (ADR 0002): the web app, its migration job and its daily
// retention purge. Deployed by .github/workflows/_starter-deploy.yml on every release.
//
//   browser ──https──► ca-<slug> (one origin: API now, the built frontend after the SPA task)
//                        ├─ revision being replaced (keeps 100% until the new one passes its smoke test)
//                        └─ new revision ca-<slug>--<suffix> (0% traffic when this template deploys)
//   caj-<slug>-migrate   manual job: alembic upgrade head, run by the workflow before traffic moves
//   caj-<slug>-purge     scheduled job: python -m app.maintenance purge, daily
//
// Secrets arrive as secure parameters and become Container Apps secrets referenced by name. No secret
// value is ever a plain environment variable or a literal in this file.

@description('Azure-safe product slug: lowercase letters, digits and hyphens, starting with a letter.')
@minLength(2)
@maxLength(19) // caj-<slug>-migrate has to stay under 32 characters
param appName string

@description('rg-ai-studio is in uksouth (SETUP.md step 3).')
param location string = resourceGroup().location

@description('Image by digest, for example acrstudioznp96r.azurecr.io/starter@sha256:...')
param image string

@description('Unique per deploy and starting with a letter. The new revision is ca-<slug>--<suffix>.')
param revisionSuffix string

@description('The revision that takes all traffic now. Empty on the first deploy.')
param liveRevisionName string = ''

// Shared resources from shared.bicep.
param environmentName string = 'cae-studio'
param registryName string = 'acrstudioznp96r'
param pullIdentityName string = 'id-studio-acrpull'

@description('fake (no cost) or azure. The workflow only offers these two values.')
param aiProvider string = 'fake'
param azureOpenAiEndpoint string = ''
param azureOpenAiDeployment string = 'gpt-5-mini'

@description('Tokens for all tenants together per UTC day. 100,000 gpt-5-mini tokens cost at most $0.20 (all output at $2.00 per million).')
param aiGlobalDailyTokens int = 100000

@description('mock or stripe (test mode only). The workflow only offers these two values.')
param billingProvider string = 'mock'
param mockCheckoutEnabled bool = true

@description('Keep true. False only for outbox-only demos, after reading SECURITY.md A1.')
param requireEmailVerification bool = true

@description('Daily retention purge, as a cron expression in UTC.')
param purgeSchedule string = '17 3 * * *'

param cpu string = '0.5'
param memory string = '1Gi' // SECURITY.md A3: 4 hashing slots x 64 MiB plus about 150 MiB

@description('One replica until rate limits move to Redis (ADR 0001, decision 8; board task T-15).')
@minValue(1)
@maxValue(1)
param maxReplicas int = 1

@secure()
@description('Postgres URL for the app role (rows only). Used by the web app and the purge job.')
param databaseUrl string

@secure()
@description('Postgres URL for the migrator role (owns the tables). Used only by the migration job.')
param migrationDatabaseUrl string

@secure()
param azureOpenAiApiKey string = ''

@secure()
param billingWebhookSecret string = ''

@secure()
param stripeSecretKey string = ''

var tags = {
  studio: 'product'
  product: appName
  managedBy: 'bicep'
}
var webName = 'ca-${appName}'
var candidateRevision = '${webName}--${revisionSuffix}'
var useAzureAi = aiProvider == 'azure'
var useStripe = billingProvider == 'stripe'

resource cae 'Microsoft.App/managedEnvironments@2025-07-01' existing = {
  name: environmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: registryName
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: pullIdentityName
}

var appUrl = 'https://${webName}.${cae.properties.defaultDomain}'

var identity = {
  type: 'UserAssigned'
  userAssignedIdentities: {
    '${pullIdentity.id}': {}
  }
}

var registries = [
  {
    server: registry.properties.loginServer
    identity: pullIdentity.id
  }
]

// The pull identity is only for image pulls: code inside the containers can't get tokens for it.
var identitySettings = [
  {
    identity: pullIdentity.id
    lifecycle: 'None'
  }
]

var commonEnv = [
  {
    name: 'ENV'
    value: 'prod' // SECURITY.md I3: every internet-facing deploy runs ENV=prod
  }
  {
    name: 'APP_NAME'
    value: appName
  }
  {
    name: 'APP_BASE_URL'
    value: appUrl
  }
  {
    name: 'LOG_LEVEL'
    value: 'INFO'
  }
  {
    name: 'DATABASE_URL'
    secretRef: 'database-url'
  }
]

var webSettings = [
  {
    name: 'CORS_ORIGINS'
    value: '["${appUrl}"]'
  }
  {
    name: 'COOKIE_SECURE'
    value: 'true'
  }
  {
    name: 'TRUST_PROXY_HEADERS'
    value: 'true' // the image sets it too; the app reads only the hop the ingress adds
  }
  {
    name: 'REQUIRE_EMAIL_VERIFICATION'
    value: requireEmailVerification ? 'true' : 'false'
  }
  {
    name: 'AI_PROVIDER'
    value: useAzureAi ? 'azure' : 'fake'
  }
  {
    name: 'AZURE_OPENAI_DEPLOYMENT'
    value: azureOpenAiDeployment
  }
  {
    name: 'AI_GLOBAL_DAILY_TOKENS'
    value: string(aiGlobalDailyTokens)
  }
  {
    name: 'BILLING_PROVIDER'
    value: useStripe ? 'stripe' : 'mock'
  }
  {
    name: 'MOCK_CHECKOUT_ENABLED'
    value: mockCheckoutEnabled && !useStripe ? 'true' : 'false'
  }
  {
    name: 'DB_POOL_SIZE'
    value: '3' // the shared B1ms allows 35 user connections for every product together
  }
  {
    name: 'DB_MAX_OVERFLOW'
    value: '2'
  }
]

// Only with real AI: no empty values, and no key at all in a fake-AI deploy.
var aiEnv = useAzureAi ? [
  {
    name: 'AZURE_OPENAI_ENDPOINT'
    value: azureOpenAiEndpoint
  }
  {
    name: 'AZURE_OPENAI_API_KEY'
    secretRef: 'azure-openai-api-key'
  }
] : []

var stripeEnv = useStripe ? [
  {
    name: 'BILLING_WEBHOOK_SECRET'
    secretRef: 'billing-webhook-secret'
  }
  {
    name: 'STRIPE_SECRET_KEY'
    secretRef: 'stripe-secret-key'
  }
] : []

var webEnv = concat(commonEnv, webSettings, aiEnv, stripeEnv)

var databaseSecret = [
  {
    name: 'database-url'
    value: databaseUrl
  }
]

var aiKeySecret = useAzureAi ? [
  {
    name: 'azure-openai-api-key'
    value: azureOpenAiApiKey
  }
] : []

var stripeSecrets = useStripe ? [
  {
    name: 'billing-webhook-secret'
    value: billingWebhookSecret
  }
  {
    name: 'stripe-secret-key'
    value: stripeSecretKey
  }
] : []

var webSecrets = concat(databaseSecret, aiKeySecret, stripeSecrets)

// Jobs never call the AI or the payment provider, so they get neither key.
var jobSettings = [
  {
    name: 'AI_PROVIDER'
    value: 'fake'
  }
  {
    name: 'BILLING_PROVIDER'
    value: 'mock'
  }
]

var jobEnv = concat(commonEnv, jobSettings)

var jobResources = {
  cpu: json('0.25')
  memory: '0.5Gi'
}

// First deploy: the only revision takes the traffic. Later deploys: the live revision keeps 100% and the
// new one starts at 0%; the workflow moves traffic only after the new revision passes its smoke test.
var traffic = empty(liveRevisionName) ? [
  {
    latestRevision: true
    weight: 100
  }
] : [
  {
    revisionName: liveRevisionName
    weight: 100
  }
  {
    revisionName: candidateRevision
    weight: 0
  }
]

resource web 'Microsoft.App/containerApps@2025-07-01' = {
  name: webName
  location: location
  tags: tags
  identity: identity
  properties: {
    environmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Multiple'
      maxInactiveRevisions: 10
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false // http is redirected to https; TLS 1.2 or 1.3 at the ingress
        traffic: traffic
      }
      registries: registries
      identitySettings: identitySettings
      secrets: webSecrets
    }
    template: {
      revisionSuffix: revisionSuffix
      containers: [
        {
          name: 'web'
          image: image
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: webEnv
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/livez'
                port: 8000
              }
              initialDelaySeconds: 1
              periodSeconds: 2
              timeoutSeconds: 2
              failureThreshold: 30 // up to a minute to start
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/livez' // no database: a busy pool never gets the replica restarted
                port: 8000
              }
              periodSeconds: 30
              timeoutSeconds: 5
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/healthz' // checks the database
                port: 8000
              }
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 3
              successThreshold: 1
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0 // scale to zero: no charge while nobody uses the demo
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

resource migrate 'Microsoft.App/jobs@2025-07-01' = {
  name: 'caj-${appName}-migrate'
  location: location
  tags: tags
  identity: identity
  properties: {
    environmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaTimeout: 600
      replicaRetryLimit: 0 // a failed migration stops the release; it is never retried blindly
      registries: registries
      identitySettings: identitySettings
      secrets: [
        {
          name: 'database-url'
          value: migrationDatabaseUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'migrate'
          image: image
          command: [
            'alembic'
          ]
          args: [
            'upgrade'
            'head'
          ]
          resources: jobResources
          env: jobEnv
        }
      ]
    }
  }
}

resource purge 'Microsoft.App/jobs@2025-07-01' = {
  name: 'caj-${appName}-purge'
  location: location
  tags: tags
  identity: identity
  properties: {
    environmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Schedule'
      scheduleTriggerConfig: {
        cronExpression: purgeSchedule
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaTimeout: 300
      replicaRetryLimit: 1
      registries: registries
      identitySettings: identitySettings
      secrets: [
        {
          name: 'database-url'
          value: databaseUrl
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'purge'
          image: image
          command: [
            'python'
          ]
          args: [
            '-m'
            'app.maintenance'
            'purge'
          ]
          resources: jobResources
          env: jobEnv
        }
      ]
    }
  }
}

output appUrl string = appUrl
output appFqdn string = web.properties.configuration.ingress.fqdn
output candidateRevision string = candidateRevision
output migrateJobName string = migrate.name
output purgeJobName string = purge.name
