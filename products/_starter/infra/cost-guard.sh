#!/usr/bin/env bash
# Refuses compiled templates that would start a fixed Container Apps or network charge (ADR 0002, decisions 1
# and 12). It reads what `az bicep build` produced, so values set through parameters, variables or modules are
# checked too, not just the source text.
#
#   cost-guard.sh shared.json main.json
#
# Refused:
#   - any workload profile type other than the literal "Consumption": Dedicated and GPU profiles bill per
#     hour, and an expression (a parameter) can't be checked here;
#   - a custom network for the environment (vnetConfiguration, infrastructureSubnetId): about $25.55 a month;
#   - any Microsoft.Network resource, private endpoint or planned maintenance window ($0.10 an hour each).
set -euo pipefail

[ "$#" -ge 1 ] || { echo "usage: cost-guard.sh <compiled template.json>..." >&2; exit 2; }
problems=0
report() {
  echo "::error::cost-guard: $1: $2"
  problems=$((problems + 1))
}

for template in "$@"; do
  name=$(basename "$template")
  jq empty "$template" || { report "$name" "not valid JSON"; continue; }

  profiles=$(jq -r '[.. | objects | select(has("workloadProfileType")) | .workloadProfileType | select(. != "Consumption") | tostring] | unique | join(", ")' "$template")
  [ -z "$profiles" ] || report "$name" "workload profile type other than Consumption: $profiles"

  networks=$(jq -r '[.. | objects | to_entries[] | select(.key == "vnetConfiguration" or .key == "infrastructureSubnetId") | .key] | unique | join(", ")' "$template")
  [ -z "$networks" ] || report "$name" "a custom network for the environment: $networks"

  types=$(jq -r '[.. | objects | select((.type | type) == "string") | .type | select(test("^Microsoft\\.Network/|maintenanceConfigurations|privateEndpoint"; "i"))] | unique | join(", ")' "$template")
  [ -z "$types" ] || report "$name" "billable resource type: $types"
done

if [ "$problems" -gt 0 ]; then
  echo "cost-guard: $problems problem(s); see ADR 0002 before changing this check."
  exit 1
fi
echo "cost-guard: $# template(s) use only the Consumption profile, no custom network and no fixed-charge features."
