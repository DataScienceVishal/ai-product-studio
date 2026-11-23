// Parameters for main.bicep. The deploy workflow exports every value below; the defaults only let
// `az bicep build-params` compile the file anywhere. A product copying the starter changes appName.
using './main.bicep'

param appName = 'starter'

param image = readEnvironmentVariable('IMAGE', 'acrstudioznp96r.azurecr.io/starter:not-set')
param revisionSuffix = readEnvironmentVariable('REVISION_SUFFIX', 'not-set')
param liveRevisionName = readEnvironmentVariable('LIVE_REVISION', '')

param aiProvider = readEnvironmentVariable('AI_PROVIDER', 'fake')
param azureOpenAiEndpoint = readEnvironmentVariable('AZURE_OPENAI_ENDPOINT', '')
param azureOpenAiDeployment = readEnvironmentVariable('AZURE_OPENAI_DEPLOYMENT', 'gpt-5-mini')
param billingProvider = readEnvironmentVariable('BILLING_PROVIDER', 'mock')

// Secrets: read from the workflow's environment at deploy time, sent to Azure as secure parameters, and
// never written to a file in the repository.
param databaseUrl = readEnvironmentVariable('DATABASE_URL_APP', '')
param migrationDatabaseUrl = readEnvironmentVariable('DATABASE_URL_MIGRATE', '')
param azureOpenAiApiKey = readEnvironmentVariable('AZURE_OPENAI_API_KEY', '')
param billingWebhookSecret = readEnvironmentVariable('BILLING_WEBHOOK_SECRET', '')
param stripeSecretKey = readEnvironmentVariable('STRIPE_SECRET_KEY', '')
