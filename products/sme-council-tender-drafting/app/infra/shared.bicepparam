// Parameters for shared.bicep. The names are fixed, so state/BUDGET.md can list them before they exist;
// the random suffix keeps the two globally unique names (registry, Postgres) free. If Azure says a name is
// taken, change the suffix here, in main.bicep's registryName default and in the deploy workflow's env block.
using './shared.bicep'

// Azure for Students allows new resources only in francecentral, swedencentral, spaincentral, polandcentral and
// italynorth (ADR 0002, Region). rg-ai-studio is in uksouth, so never rely on resourceGroup().location.
param location = 'francecentral'

param registryName = 'acrstudioznp96r'
param registrySku = 'Basic'
param postgresServerName = 'psql-studio-znp96r'
param postgresAllowAzureServices = true
// Phase 2 of ADR 0003: password sign-in is off. Every release asserts this (infra/check-auth-config.sh).
param postgresPasswordAuth = 'Disabled'

// Never written here: deploy_shared makes a random one inside its own step (ADR 0003) and exports it there.
// Azure requires one at server creation; password sign-in is disabled, so it is unusable.
param postgresAdminPassword = readEnvironmentVariable('PG_ADMIN_PASSWORD', '')

// The deployer can't create role assignments: Vishal grants AcrPull once (infra/README.md, setup step 5).
// An Owner deploying shared.bicep directly (for example at handover) can set GRANT_PULL_ROLE=true instead.
param grantPullRole = readEnvironmentVariable('GRANT_PULL_ROLE', 'false') == 'true'

// The Postgres Entra admin is whoever deploys: since T-60 that is the managed identity id-github-deploy
// (GitHub signs in as it through OIDC), a ServicePrincipal in Postgres terms. Its name must match the identity.
param postgresEntraAdminName = 'id-github-deploy'
