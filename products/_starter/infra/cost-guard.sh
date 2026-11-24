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
#   - any Microsoft.Network resource, private endpoint or planned maintenance window ($0.10 an hour each);
#   - a template with aiGlobalDailyTokens and aiPricePerMillionTokens parameters whose defaults give
#     tokens a day x price per million x 30 above AI_MONTHLY_BUDGET_USD (default 6.10, the Azure OpenAI line in
#     state/BUDGET.md). The deploy workflow doesn't override either parameter (see main.bicepparam).
set -euo pipefail

AI_MONTHLY_BUDGET_USD="${AI_MONTHLY_BUDGET_USD:-6.10}"

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

  # Tokens a day x price per million x 30 must stay within the monthly AI budget (jq does the arithmetic).
  tokens=$(jq -r '.parameters.aiGlobalDailyTokens.defaultValue // empty' "$template")
  price=$(jq -r '.parameters.aiPricePerMillionTokens.defaultValue // empty' "$template")
  if [ -n "$tokens" ] || [ -n "$price" ]; then
    if [ -z "$tokens" ] || [ -z "$price" ]; then
      report "$name" "needs both aiGlobalDailyTokens and aiPricePerMillionTokens defaults to check the AI budget"
    else
      over=$(jq -rn --arg t "$tokens" --arg p "$price" --argjson b "$AI_MONTHLY_BUDGET_USD" \
        '(($t | tonumber) * ($p | tonumber) * 30 / 1000000) as $m | if $m > $b then ($m * 100 | round / 100 | tostring) else empty end' 2>/dev/null) \
        || { report "$name" "AI cap or price is not a number: tokens=$tokens price=$price"; continue; }
      [ -z "$over" ] || report "$name" "$tokens tokens a day x \$$price per million x 30 = \$$over a month, over the \$$AI_MONTHLY_BUDGET_USD AI budget"
    fi
  fi
done

if [ "$problems" -gt 0 ]; then
  echo "cost-guard: $problems problem(s); see ADR 0002 before changing this check."
  exit 1
fi
echo "cost-guard: $# template(s) use only the Consumption profile, no custom network and no fixed-charge features."
