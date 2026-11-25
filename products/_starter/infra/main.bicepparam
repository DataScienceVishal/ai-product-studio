// Parameters for main.bicep. The deploy workflow exports every value below; the defaults only let
// `az bicep build-params` compile the file anywhere. A product copying the starter changes appName.
using './main.bicep'

// Azure for Students allows new resources only in francecentral, swedencentral, spaincentral, polandcentral and
// italynorth (ADR 0002, Region). rg-ai-studio is in uksouth, so never rely on resourceGroup().location.
param location = 'francecentral'

param appName = 'starter'

param image = readEnvironmentVariable('IMAGE', 'acrstudioznp96r.azurecr.io/starter:not-set')
param revisionSuffix = readEnvironmentVariable('REVISION_SUFFIX', 'not-set')
param liveRevisionName = readEnvironmentVariable('LIVE_REVISION', '')

param aiProvider = readEnvironmentVariable('AI_PROVIDER', 'fake')
param azureOpenAiEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT', '')
param azureOpenAiDeployment = readEnvironmentVariable('AZURE_OPENAI_DEPLOYMENT', 'gpt-5-mini')
// Optional explicit price (USD per million tokens); empty uses the price table in backend/app/aicost.py.
param aiPricePerMillionTokens = readEnvironmentVariable('AI_PRICE_PER_MILLION_TOKENS', '')
param billingProvider = readEnvironmentVariable('BILLING_PROVIDER', 'mock')
param mockCheckoutEnabled = readEnvironmentVariable('MOCK_CHECKOUT_ENABLED', 'false') == 'true'
param requireEmailVerification = readEnvironmentVariable('REQUIRE_EMAIL_VERIFICATION', 'true') == 'true'
param emailProvider = readEnvironmentVariable('EMAIL_PROVIDER', 'outbox')

// Entra by default (ADR 0003, phase 2): the server refuses password sign-in, so a deploy that forgot DB_AUTH
// must not produce password-mode apps. The deploy workflow also exports DB_AUTH=entra explicitly.
param dbAuth = readEnvironmentVariable('DB_AUTH', 'entra')

// The purge job stays on the live revision's image and email settings until the release passes.
param purgeImage = readEnvironmentVariable('PURGE_IMAGE', '')
param purgeRequireEmailVerification = readEnvironmentVariable('PURGE_REQUIRE_EMAIL_VERIFICATION', '')
param purgeEmailProvider = readEnvironmentVariable('PURGE_EMAIL_PROVIDER', '')

// Secrets: read from the workflow's environment at deploy time, sent to Azure as secure parameters, and
// never written to a file in the repository.
param databaseUrl = readEnvironmentVariable('DATABASE_URL_APP', '')
param migrationDatabaseUrl = readEnvironmentVariable('DATABASE_URL_MIGRATE', '')
param azureOpenAiApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY', '')
param billingWebhookSecret = readEnvironmentVariable('BILLING_WEBHOOK_SECRET', '')
param stripeSecretKey = readEnvironmentVariable('STRIPE_SECRET_KEY', '')
