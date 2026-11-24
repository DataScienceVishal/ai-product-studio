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

jq -en --arg b "$AI_MONTHLY_BUDGET_USD" '($b | tonumber? // null) | . != null and . > 0' >/dev/null 2>&1 \
  || { echo "::error::cost-guard: AI_MONTHLY_BUDGET_USD must be a number above 0, got: $AI_MONTHLY_BUDGET_USD" >&2; exit 2; }
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
  has_params=$(jq -r '(.parameters // {}) | if has("aiGlobalDailyTokens") or has("aiPricePerMillionTokens") then "yes" else "no" end' "$template")
  if [ "$has_params" = yes ]; then
    if [ -z "$tokens" ] || [ -z "$price" ]; then
      report "$name" "aiGlobalDailyTokens and aiPricePerMillionTokens must both exist with defaults to check the AI budget"
    else
      # prints bad, nonpositive, "ok <monthly cost>" or "over <monthly cost>" (cost rounded to 2 decimals)
      verdict=$(jq -rn --arg t "$tokens" --arg p "$price" --argjson b "$AI_MONTHLY_BUDGET_USD" '
        (($t | tonumber? // null) as $tk | ($p | tonumber? // null) as $pr
         | if $tk == null or $pr == null then "bad"
           elif $tk <= 0 or $pr <= 0 then "nonpositive"
           else ($tk * $pr * 30 / 1000000) as $m
             | (if $m > $b then "over " else "ok " end) + ($m | tostring) end)' 2>/dev/null) || verdict=bad
      case "$verdict" in
        bad) report "$name" "AI cap or price is not a number: tokens=$tokens price=$price" ;;
        nonpositive) report "$name" "AI cap and price must both be above 0: tokens=$tokens price=$price" ;;
        over*) cost=$(printf '%.2f' "${verdict#over }")
               report "$name" "$tokens tokens a day x \$$price per million x 30 = \$$cost a month, over the \$$(printf '%.2f' "$AI_MONTHLY_BUDGET_USD") AI budget" ;;
      esac
    fi
  fi
done

if [ "$problems" -gt 0 ]; then
  echo "cost-guard: $problems problem(s); see ADR 0002 before changing this check."
  exit 1
fi
echo "cost-guard: $# template(s) use only the Consumption profile, no custom network and no fixed-charge features."
