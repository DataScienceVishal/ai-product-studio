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

@description('How the app and jobs sign in to Postgres (ADR 0003). entra (the default): DB_AUTH=entra and AZURE_CLIENT_ID are set, so each container takes a token from its own identity. password: legacy fallback only, the URLs carry a password and no identity env is set; it works only if password sign-in is re-enabled on the server, which is Disabled by default. The two identities below exist and are attached in both modes ($0).')
@allowed([
  'password'
  'entra'
])
param dbAuth string = 'entra'

@description('fake (no cost) or azure. The workflow only offers these two values.')
param aiProvider string = 'fake'
param azureOpenAiEndpoint string = ''
param azureOpenAiDeployment string = 'gpt-5-mini'

@description('auto (responses if the endpoint ends in /openai/v1/responses, else chat), chat or responses. Same default as the app.')
@allowed([
  'auto'
  'chat'
  'responses'
])
param azureOpenAiApi string = 'auto'

@description('Optional explicit blended price in USD per million tokens of the deployment in azureOpenAiDeployment. Empty (the default) means the app and cost-guard.sh use the price table in backend/app/aicost.py (gpt-5.4-pro is estimated at 180); a deployment not in the table needs this set. An explicit value overrides the table. cost-guard.sh and the app refuse tokens a day x price x 30 above the $6.10 monthly AI budget.')
param aiPricePerMillionTokens string = ''

@description('Tokens recorded for all tenants together per UTC day. Every call is checked against it with its upper-bound estimate, so the total stays under it. At the gpt-5-mini price (2.00 per million) 100,000 tokens cost at most $0.20 a day (about $6.00 a month), the budget in state/BUDGET.md. A pricier deployment needs a lower cap: size it as 6.10 / (30 x price) x 1,000,000; the app and cost-guard.sh refuse a cap that costs more. Trials share half.')
// Sizing: a call reserves 287 + note bytes + 17 + 1,200 (+1,500 on the Responses API only) before it runs, then settles to actual use,
// so cap / reservation is a floor on calls, not a daily limit. Until selling is unlocked all tenants share the trial half. See README, "Sizing the daily AI cap".
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

// ADR 0003, decision 1: one database identity per database role. id-<slug>-app is for the web app and the purge
// job (role <db>_app), id-<slug>-migrate for the migration job only (role <db>_migrator). No Azure role
// assignment is needed for Postgres Entra sign-in, and managed identities cost nothing.
// https://learn.microsoft.com/azure/templates/microsoft.managedidentity/2023-01-31/userassignedidentities
resource appIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${appName}-app'
  location: location
  tags: tags
}

resource migrateIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${appName}-migrate'
  location: location
  tags: tags
}

// Each resource gets the pull identity plus exactly one database identity.
var webIdentity = {
  type: 'UserAssigned'
  userAssignedIdentities: {
    '${pullIdentity.id}': {}
    '${appIdentity.id}': {}
  }
}

var migrateJobIdentity = {
  type: 'UserAssigned'
  userAssignedIdentities: {
    '${pullIdentity.id}': {}
    '${migrateIdentity.id}': {}
  }
}

var registries = [
  {
    server: registry.properties.loginServer
    identity: pullIdentity.id
  }
]

// The pull identity is only for image pulls: code inside the containers can't get tokens for it. The database
// identity is available to the main containers only (lifecycle Main; the default All also covers init containers).
// identitySettings, lifecycle values All, Init, Main, None:
// https://learn.microsoft.com/azure/templates/microsoft.app/2025-07-01/containerapps#property-values
// and https://learn.microsoft.com/azure/container-apps/managed-identity
var webIdentitySettings = [
  {
    identity: pullIdentity.id
    lifecycle: 'None'
  }
  {
    identity: appIdentity.id
    lifecycle: 'Main'
  }
]

var migrateIdentitySettings = [
  {
    identity: pullIdentity.id
    lifecycle: 'None'
  }
  {
    identity: migrateIdentity.id
    lifecycle: 'Main'
  }
]

// DB_AUTH=entra makes the app fetch a token for its own identity (AZURE_CLIENT_ID picks the user-assigned one).
// In the legacy password mode neither variable is set, so the app falls back to its default (DB_AUTH=password);
// that only works if password sign-in is re-enabled on the server (it is Disabled by default).
var useEntra = dbAuth == 'entra'
var appDbAuthEnv = useEntra ? [
  {
    name: 'DB_AUTH'
    value: 'entra'
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: appIdentity.properties.clientId
  }
] : []
var migrateDbAuthEnv = useEntra ? [
  {
    name: 'DB_AUTH'
    value: 'entra'
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: migrateIdentity.properties.clientId
  }
] : []

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
    name: 'AZURE_OPENAI_API'
    value: azureOpenAiApi
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

// Only an explicit price is passed; empty means the app looks the deployment up in its price table (app/aicost.py).
var aiPriceEnv = empty(aiPricePerMillionTokens) ? [] : [
  {
    name: 'AI_PRICE_PER_MILLION_TOKENS'
    value: aiPricePerMillionTokens
  }
]
var webEnv = concat(commonEnv, webSettings, emailEnv, aiEnv, aiPriceEnv, stripeEnv, appDbAuthEnv)

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

var migrateEnv = concat(commonEnv, jobSettings, emailEnv, migrateDbAuthEnv)
var purgeEnv = concat(commonEnv, jobSettings, purgeEmailEnv, appDbAuthEnv)

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
  identity: webIdentity
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
      identitySettings: webIdentitySettings
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
  identity: migrateJobIdentity
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
      identitySettings: migrateIdentitySettings
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
  identity: webIdentity
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
      identitySettings: webIdentitySettings
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
output dbAuth string = dbAuth
output appIdentityName string = appIdentity.name
output appIdentityClientId string = appIdentity.properties.clientId
output appIdentityPrincipalId string = appIdentity.properties.principalId // the object id Postgres maps to <db>_app
output migrateIdentityName string = migrateIdentity.name
output migrateIdentityClientId string = migrateIdentity.properties.clientId
output migrateIdentityPrincipalId string = migrateIdentity.properties.principalId // maps to <db>_migrator
