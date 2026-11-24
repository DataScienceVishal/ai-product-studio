// Parameters for shared.bicep. The names are fixed, so state/BUDGET.md can list them before they exist;
// the random suffix keeps the two globally unique names (registry, Postgres) free. If Azure says a name is
// taken, change the suffix here, in main.bicep's registryName default and in the deploy workflow's env block.
using './shared.bicep'

param registryName = 'acrstudioznp96r'
param registrySku = 'Basic'
param postgresServerName = 'psql-studio-znp96r'
param postgresAllowAzureServices = true

// Never written here: deploy_shared makes a random one inside its own step (phase 1 only, ADR 0003) and exports it there.
param postgresAdminPassword = readEnvironmentVariable('PG_ADMIN_PASSWORD', '')

// The deployer can't create role assignments: Vishal grants AcrPull once (infra/README.md, setup step 5).
// An Owner deploying shared.bicep directly (for example at handover) can set GRANT_PULL_ROLE=true instead.
param grantPullRole = readEnvironmentVariable('GRANT_PULL_ROLE', 'false') == 'true'
