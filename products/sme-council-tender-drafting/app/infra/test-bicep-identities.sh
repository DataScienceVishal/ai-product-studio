#!/usr/bin/env bash
# Assertions on the compiled templates for ADR 0003 build slices 1 and 2 (identities, Entra auth, admin).
#
#   test-bicep-identities.sh shared.json main.json
#
# `az bicep build` turns Bicep variables and expressions into ARM expression strings, so the checks resolve
# "[variables('x')]" one level and then test the expression text. They guard the structure, not Azure's
# behaviour: only the first real deploy can show that (ADR 0003, decision 6).
set -euo pipefail

[ "$#" -eq 2 ] || { echo "usage: test-bicep-identities.sh <shared.json> <main.json>" >&2; exit 2; }
shared=$1
main=$2
failed=0
check() { # description, jq filter (must be true), file
  if jq -e "$2" "$3" >/dev/null 2>&1; then
    echo "ok   $1"
  else
    echo "::error::test-bicep-identities: FAIL $1"
    failed=$((failed + 1))
  fi
}

# ---- main.bicep, slice 1 ------------------------------------------------------------------------------------------
# res($r): the value, or the variable it names when it is "[variables('name')]".
DEFS='. as $t
  | def res($r): if ($r | type) == "string" and ($r | test("^\\[variables\\(.[A-Za-z0-9]+.\\)\\]$"))
                 then $t.variables[$r | capture("variables\\(.(?<n>[A-Za-z0-9]+).\\)").n] else $r end;
  def named($type; $n): [$t.resources[] | select(.type == $type and (.name | contains($n)))];
  def ids($r): (res($r.identity).userAssignedIdentities | keys);
  def sets($r): res($r.properties.configuration.identitySettings);'

check "two user-assigned identities, id-<slug>-app and id-<slug>-migrate, API 2023-01-31" \
  "$DEFS"'
  ([$t.resources[] | select(.type == "Microsoft.ManagedIdentity/userAssignedIdentities")] as $i
   | ($i | length == 2) and ($i | all(.apiVersion == "2023-01-31"))
     and ($i | map(.name) | map(contains("id-{0}-app")) | any)
     and ($i | map(.name) | map(contains("id-{0}-migrate")) | any))' "$main"

PICK_ca='[$t.resources[] | select(.type == "Microsoft.App/containerApps")][0]'
PICK_purge='[$t.resources[] | select(.type == "Microsoft.App/jobs" and (.name | contains("purge")))][0]'
PICK_cancels='[$t.resources[] | select(.type == "Microsoft.App/jobs" and (.name | contains("cancels")))][0]'
PICK_migrate='[$t.resources[] | select(.type == "Microsoft.App/jobs" and (.name | contains("migrate")))][0]'
for spec in "ca:app:migrate" "purge:app:migrate" "cancels:app:migrate" "migrate:migrate:app"; do
  IFS=: read -r key db other <<<"$spec"
  eval "pick=\$PICK_$key"
  check "$key: exactly the pull identity and id-<slug>-$db are attached" \
    "$DEFS $pick"' as $r
    | (ids($r) | length == 2)
      and (ids($r) | map(contains("pullIdentityName")) | any)
      and (ids($r) | map(contains("id-{0}-'"$db"'")) | any)
      and (ids($r) | map(contains("id-{0}-'"$other"'")) | any | not)' "$main"
  check "$key: pull lifecycle None, id-<slug>-$db lifecycle Main, nothing else" \
    "$DEFS $pick"' as $r
    | (sets($r) | length == 2)
      and (sets($r) | map(select(.identity | contains("pullIdentityName"))) | (length == 1) and (.[0].lifecycle == "None"))
      and (sets($r) | map(select(.identity | contains("id-{0}-'"$db"'"))) | (length == 1) and (.[0].lifecycle == "Main"))' "$main"
done

check "dbAuth parameter allows password and entra, defaults to entra" \
  '.parameters.dbAuth.defaultValue == "entra" and (.parameters.dbAuth.allowedValues | sort) == ["entra","password"]' "$main"
# Bicep inlines the env arrays into each resource, so look at the container env expression itself.
ENV_ca='[$t.resources[] | select(.type == "Microsoft.App/containerApps")][0].properties.template.containers[0].env'
ENV_purge='[$t.resources[] | select(.type == "Microsoft.App/jobs" and (.name | contains("purge")))][0].properties.template.containers[0].env'
ENV_cancels='[$t.resources[] | select(.type == "Microsoft.App/jobs" and (.name | contains("cancels")))][0].properties.template.containers[0].env'
ENV_migrate='[$t.resources[] | select(.type == "Microsoft.App/jobs" and (.name | contains("migrate")))][0].properties.template.containers[0].env'
check "useEntra is dbAuth == entra" \
  '.variables.useEntra | contains("parameters('"'"'dbAuth'"'"')") and contains("'"'"'entra'"'"'")' "$main"
for spec in "ca:app:migrate" "purge:app:migrate" "cancels:app:migrate" "migrate:migrate:app"; do
  IFS=: read -r key db other <<<"$spec"
  eval "envp=\$ENV_$key"
  check "$key env: DB_AUTH=entra and the id-<slug>-$db client id, only when dbAuth is entra" \
    ". as \$t | $envp"' | tostring as $e
     | ($e | contains("if(variables('"'"'useEntra'"'"'), createArray(createObject('"'"'name'"'"', '"'"'DB_AUTH'"'"', '"'"'value'"'"', '"'"'entra'"'"'), createObject('"'"'name'"'"', '"'"'AZURE_CLIENT_ID'"'"'"))
       and ($e | contains("userAssignedIdentities'"'"', format('"'"'id-{0}-'"$db"''"'"'"))
       and ($e | contains("id-{0}-'"$other"'") | not)
       and ($e | contains("), createArray())"))' "$main"
done
# T-176: the cancels job is the purge job's twin with a different command, schedule and billing settings.
check "cancels job: python -m app.maintenance cancels, container 'cancels', same image variable as the purge job" \
  "$DEFS"'
  named("Microsoft.App/jobs"; "cancels")[0].properties.template.containers[0] as $c
  | named("Microsoft.App/jobs"; "purge")[0].properties.template.containers[0] as $p
  | ($c.name == "cancels") and ($c.command == ["python"]) and ($c.args == ["-m","app.maintenance","cancels"])
    and ($c.image == $p.image) and ($c.image | contains("purgeImageNow"))' "$main"
check "cancels job: schedule job on the Consumption plan, cron from cancelsSchedule defaulting to every 30 minutes" \
  "$DEFS"'
  named("Microsoft.App/jobs"; "cancels")[0] as $j
  | ($j.properties.workloadProfileName == "Consumption")
    and ($j.properties.configuration.triggerType == "Schedule")
    and ($j.properties.configuration.scheduleTriggerConfig.cronExpression == "[parameters('"'"'cancelsSchedule'"'"')]")
    and ($t.parameters.cancelsSchedule.defaultValue == "*/30 * * * *")
    and ($j.properties.configuration.scheduleTriggerConfig.parallelism == 1)' "$main"
check "cancels job: replica timeout fits the sweep and is shorter than the schedule (no overlap), one retry" \
  "$DEFS"'
  named("Microsoft.App/jobs"; "cancels")[0].properties.configuration as $c
  | ($c.replicaTimeout >= 600) and ($c.replicaTimeout < 1800) and ($c.replicaRetryLimit == 1)' "$main"
check "cancels job env: billing provider follows cancelsUseStripe, AI stays fake, no AI key" \
  ". as \$t | $ENV_cancels"' | tostring as $e
   | ($e | contains("BILLING_PROVIDER")) and ($e | contains("cancelsUseStripe"))
     and ($e | contains("AI_PROVIDER")) and ($e | contains("azure-openai-api-key") | not)' "$main"
check "cancels job secrets: defined, so the app's database-url reference resolves" \
  "$DEFS"'
  named("Microsoft.App/jobs"; "cancels")[0].properties.configuration | has("secrets")' "$main"
# T-177 (infra review S2): every secretRef of the cancels job and of the web app names a secret that the same resource
# defines. The cancels job defines both Stripe secrets whatever its provider is (a rollback's purge-job.sh follow can
# switch it without a Bicep deploy) but references them only for stripe (cancelsUseStripe), because mock billing rejects
# the placeholder webhook secret (review C1). The provider comes from the live revision (purgeBillingProvider). Not run locally: needs the compiled JSON, CI runs it.
# Compiled variables are either objects or expression strings, so look at the JSON text and follow variables('x') names.
EXPAND='def expand($x; $d): ($x | tostring) as $s
  | if $d == 0 then $s else $s + ([$s | scan("variables\\(.([A-Za-z0-9]+).\\)") | .[0]] | unique
      | map(. as $n | if $t.variables[$n] != null then expand($t.variables[$n]; $d - 1) else "" end) | join(" ")) end;
  def refs($x): [expand($x; 4) | scan("secretRef[\\\\\"'"'"']*[:,] *[\\\\\"'"'"']*([a-z0-9-]+)") | .[0]] | unique;'
check "cancels job: every secretRef (env resolved through the variables) names one of its secrets" \
  "$DEFS"'
  '"$EXPAND"'
  named("Microsoft.App/jobs"; "cancels")[0] as $j
  | (res($j.properties.configuration.secrets) | map(.name)) as $names
  | refs($j.properties.template.containers[0].env) as $refs
  | ($refs | length >= 3) and ($refs | all(. as $r | $names | index($r)))' "$main"
check "cancels job: both Stripe secrets always defined; their env refs only under cancelsUseStripe, which follows purgeBillingProvider" \
  "$DEFS"'
  '"$EXPAND"'
  named("Microsoft.App/jobs"; "cancels")[0] as $j
  | (res($j.properties.configuration.secrets) | tostring) as $s
  | expand($j.properties.template.containers[0].env; 4) as $e
  | ($s | contains("billing-webhook-secret") and contains("stripe-secret-key") and (contains("seStripe") | not))
    and (refs($j.properties.template.containers[0].env) | index("billing-webhook-secret") != null and index("stripe-secret-key") != null)
    and ($e | contains("cancelsUseStripe"))
    and ($t.variables.cancelsStripeEnv | tostring | contains("cancelsUseStripe"))
    and ($t.variables.cancelsUseStripe | contains("cancelsBillingNow"))
    and ($t.variables.cancelsBillingNow | contains("purgeBillingProvider"))' "$main"
check "web app: every secretRef in its env names one of its secrets" \
  "$DEFS"'
  '"$EXPAND"'
  ([$t.resources[] | select(.type == "Microsoft.App/containerApps")][0]) as $ca
  | (res($ca.properties.configuration.secrets) | map(.name)) as $names
  | refs($ca.properties.template.containers[0].env) as $refs
  | ($refs | length >= 3) and ($refs | all(. as $r | $names | index($r)))' "$main"
check "output cancelsJobName exists" '.outputs | has("cancelsJobName")' "$main"

check "outputs: client ids and principal ids of both identities" \
  '(.outputs | keys) as $k | ["appIdentityClientId","appIdentityPrincipalId","migrateIdentityClientId","migrateIdentityPrincipalId"] | all(. as $o | $k | index($o))' "$main"

# ---- shared.bicep and modules/postgres.bicep, slice 2 --------------------------------------------------------------
PG='[.resources[] | select(.type == "Microsoft.Resources/deployments" and .name == "studio-postgres")][0].properties.template'
check "server authConfig: Entra enabled, tenantId set, passwordAuth from a parameter" \
  "$PG"' | [.resources[] | select(.type == "Microsoft.DBforPostgreSQL/flexibleServers")][0].properties.authConfig
   | .activeDirectoryAuth == "Enabled" and .tenantId == "[tenant().tenantId]" and .passwordAuth == "[parameters('"'"'passwordAuth'"'"')]"' "$shared"
check "passwordAuth defaults to Disabled (phase 2), allows only Enabled or Disabled" \
  "$PG"' | (.parameters.passwordAuth.defaultValue == "Disabled") and (.parameters.passwordAuth.allowedValues | sort) == ["Disabled","Enabled"]' "$shared"
check "shared.bicep passwordAuth parameter defaults to Disabled" \
  '.parameters.postgresPasswordAuth.defaultValue == "Disabled"' "$shared"
# the parameter files: shared.bicepparam says Disabled out loud, and nothing in them turns it back on
bp="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if grep -qE "^param postgresPasswordAuth = 'Disabled'" "$bp/shared.bicepparam" && ! grep -qE "postgresPasswordAuth *= *'Enabled'" "$bp/shared.bicepparam"; then
  echo "ok   shared.bicepparam sets postgresPasswordAuth to Disabled"
else
  failed=$((failed + 1)); echo "::error::test-bicep-identities: FAIL shared.bicepparam sets postgresPasswordAuth to Disabled"
fi
if grep -qE "readEnvironmentVariable\('DB_AUTH', 'entra'\)" "$bp/main.bicepparam"; then
  echo "ok   main.bicepparam defaults dbAuth to entra"
else
  failed=$((failed + 1)); echo "::error::test-bicep-identities: FAIL main.bicepparam defaults dbAuth to entra"
fi
check "shared.bicep passes passwordAuth, entraAdminName and entraAdminType to the postgres module" \
  '[.resources[] | select(.type == "Microsoft.Resources/deployments" and .name == "studio-postgres")][0].properties.parameters
   | (.passwordAuth.value == "[parameters('"'"'postgresPasswordAuth'"'"')]")
     and (.entraAdminName.value == "[parameters('"'"'postgresEntraAdminName'"'"')]")
     and (.entraAdminType.value == "[parameters('"'"'postgresEntraAdminType'"'"')]")' "$shared"
check "postgresEntraAdminType allows ServicePrincipal, User, Group and defaults to ServicePrincipal" \
  '.parameters.postgresEntraAdminType.defaultValue == "ServicePrincipal" and (.parameters.postgresEntraAdminType.allowedValues | sort) == ["Group","ServicePrincipal","User"]' "$shared"
check "module entraAdminType allows ServicePrincipal, User, Group and defaults to ServicePrincipal (direct callers)" \
  "$PG"' | (.parameters.entraAdminType.defaultValue == "ServicePrincipal") and (.parameters.entraAdminType.allowedValues | sort) == ["Group","ServicePrincipal","User"]' "$shared"
check "administrators child: the deployer, typed by entraAdminType, in our tenant, API 2024-08-01" \
  "$PG"' | [.resources[] | select(.type == "Microsoft.DBforPostgreSQL/flexibleServers/administrators")] as $a
   | ($a | length == 1)
     and ($a[0].apiVersion == "2024-08-01")
     and ($a[0].name | contains("deployer().objectId"))
     and ($a[0].properties.principalType == "[parameters('"'"'entraAdminType'"'"')]")
     and ($a[0].properties.tenantId == "[tenant().tenantId]")' "$shared"
check "administrators depend on the server settings and the firewall rule (one change at a time)" \
  "$PG"' | [.resources[] | select(.type == "Microsoft.DBforPostgreSQL/flexibleServers/administrators")][0].dependsOn
   | (map(contains("firewallRules")) | any) and (map(contains("serverSettings")) | any)' "$shared"

if [ "$failed" -gt 0 ]; then
  echo "test-bicep-identities: $failed check(s) failed" >&2
  exit 1
fi
echo "test-bicep-identities: all checks passed"
