// Parameters for shared.bicep. The names are fixed, so state/BUDGET.md can list them before they exist;
// the random suffix keeps the two globally unique names (registry, Postgres) free. If Azure says a name is
// taken, change the suffix here, in main.bicep's registryName default and in the deploy workflow's env block.
using './shared.bicep'

param registryName = 'acrstudioznp96r'
param registrySku = 'Basic'
param postgresServerName = 'psql-studio-znp96r'
param postgresAllowAzureServices = true

// Never written here: the deploy workflow derives it from the STUDIO_DB_SEED secret and exports it.
param postgresAdminPassword = readEnvironmentVariable('PG_ADMIN_PASSWORD', '')

// Only Vishal, with Owner, runs shared.bicep with GRANT_PULL_ROLE=true (infra/README.md, setup step 4).
param grantPullRole = readEnvironmentVariable('GRANT_PULL_ROLE', 'false') == 'true'
