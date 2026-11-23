// One product on the shared studio platform (ADR 0002): the web app, its migration job and its daily
// retention purge. Deployed by .github/workflows/_starter-deploy.yml on every release.
//
//   browser ──https──► ca-<slug> (one origin: API now, the built frontend after T-16)
//                        ├─ revision being replaced (keeps 100% until the new one passes its smoke test)
//                        └─ new revision ca-<slug>--<suffix> (0% traffic when this template deploys)
//   caj-<slug>-migrate   manual job, this release's image: alembic upgrade head, before traffic moves
//   caj-<slug>-purge     scheduled job: python -m app.maintenance purge, daily. Jobs have no revisions, so
//                        it keeps the image and email settings of the revision that serves traffic
//                        (purge* parameters). The workflow moves it to the new release only after the
//                        public smoke test passes, and moves it back on every rollback.
//
// Secrets arrive as secure parameters and become Container Apps secrets referenced by name. No secret
// value is ever a plain environment variable or a literal in this file.

@description('Azure-safe product slug: lowercase letters, digits and hyphens, starting with a letter.')
@minLength(2)
@maxLength(19) // caj-<slug>-migrate has to stay under 32 characters
param appName string

@description('rg-ai-studio is in uksouth (SETUP.md step 3).')
param location string = resourceGroup().location

@description('This release\'s image by digest, for example acrstudioznp96r.azurecr.io/starter@sha256:...')
param image string

@description('Unique per deploy and starting with a letter. The new revision is ca-<slug>--<suffix>.')
param revisionSuffix string

@description('The revision that takes all traffic now. Empty on the first release.')
param liveRevisionName string = ''

// Shared resources from shared.bicep.
param environmentName string = 'cae-studio'
param registryName string = 'acrstudioznp96r'
param pullIdentityName string = 'id-studio-acrpull'

@description('fake (no cost) or azure. The workflow only offers these two values.')
param aiProvider string = 'fake'
param azureOpenAiEndpoint string = ''
param azureOpenAiDeployment string = 'gpt-5-mini'

@description('Tokens recorded for all tenants together per UTC day. Every call is checked against it with its upper-bound estimate, so the total stays under it: 100,000 costs at most $0.20 a day even if every token were output ($2.00 per million). Trials share half.')
param aiGlobalDailyTokens int = 100000

@description('mock or stripe (test mode only). The workflow only offers these two values.')
param billingProvider string = 'mock'

@description('The demo "Pay (test)" button, mock billing only. Off unless a demo needs it: it grants a paid plan for free (with the trial\'s AI allowance).')
param mockCheckoutEnabled bool = false

@description('True except for outbox-only demos. With outbox-only email nobody can verify, so true blocks AI, checkout and invitations (ADR 0002, "What a deployed demo can do"). The app refuses false once real email is sent.')
param requireEmailVerification bool = true

@description('outbox (no real email; the only provider today). A real provider needs approval and requireEmailVerification=true.')
param emailProvider string = 'outbox'

// What the purge job runs: the image and email settings of the revision that serves traffic now. Empty means
// this release's values (its first release, when nothing serves yet).
param purgeImage string = ''
param purgeRequireEmailVerification string = ''
param purgeEmailProvider string = ''

@description('Daily retention purge, as a cron expression in UTC.')
param purgeSchedule string = '17 3 * * *'

param cpu string = '0.5'
param memory string = '1Gi' // SECURITY.md re-test 3: 2 hashing slots peak at about 225 MiB

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

// Passed whenever the GitHub secret exists, whichever provider this release uses, so switching provider never
// deletes a secret that the previous revision (kept for rollback) still reads.
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
var verifyEmail = requireEmailVerification ? 'true' : 'false'
var purgeImageNow = empty(purgeImage) ? image : purgeImage
var purgeVerifyEmail = empty(purgeRequireEmailVerification) ? verifyEmail : purgeRequireEmailVerification
var purgeEmailProviderNow = empty(purgeEmailProvider) ? emailProvider : purgeEmailProvider
var notConfigured = 'not-configured' // placeholder for a secret no revision can use yet

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

// The web app, the migration job and the purge job use the same email rules, so the purge treats unverified
// accounts the way the app does. The purge job takes them from the revision that serves traffic.
var emailEnv = [
  {
    name: 'REQUIRE_EMAIL_VERIFICATION'
    value: verifyEmail
  }
  {
    name: 'EMAIL_PROVIDER'
    value: emailProvider
  }
]

var purgeEmailEnv = [
  {
    name: 'REQUIRE_EMAIL_VERIFICATION'
    value: purgeVerifyEmail
  }
  {
    name: 'EMAIL_PROVIDER'
    value: purgeEmailProviderNow
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

// Only this release's provider is wired into its environment. No empty values.
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

var webEnv = concat(commonEnv, webSettings, emailEnv, aiEnv, stripeEnv)

// Every secret is always defined, so no release removes one that an older revision still references
// (Microsoft: deactivate every revision that uses a secret before deleting it). Unused ones hold a placeholder.
var webSecrets = [
  {
    name: 'database-url'
    value: databaseUrl
  }
  {
    name: 'azure-openai-api-key'
    value: empty(azureOpenAiApiKey) ? notConfigured : azureOpenAiApiKey
  }
  {
    name: 'billing-webhook-secret'
    value: empty(billingWebhookSecret) ? notConfigured : billingWebhookSecret
  }
  {
    name: 'stripe-secret-key'
    value: empty(stripeSecretKey) ? notConfigured : stripeSecretKey
  }
]

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

var migrateEnv = concat(commonEnv, jobSettings, emailEnv)
var purgeEnv = concat(commonEnv, jobSettings, purgeEmailEnv)

var jobResources = {
  cpu: json('0.25')
  memory: '0.5Gi'
}

// First release: the only revision takes the traffic. Later releases: the live revision keeps 100% and the
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
              periodSeconds: 6
              timeoutSeconds: 3
              failureThreshold: 10 // up to a minute to start, inside the documented maximum of 10
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
      triggerType: 'Manual' // runs only when the workflow starts it, before traffic moves
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
          env: migrateEnv
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
      triggerType: 'Schedule' // runs on its own, so it follows the live revision (see the header)
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
          image: purgeImageNow
          command: [
            'python'
          ]
          args: [
            '-m'
            'app.maintenance'
            'purge'
          ]
          resources: jobResources
          env: purgeEnv
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
output purgeImage string = purgeImageNow
