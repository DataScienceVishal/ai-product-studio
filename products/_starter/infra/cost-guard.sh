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
#   - a template with an aiGlobalDailyTokens parameter whose default gives tokens a day x price per million x 30
#     above AI_MONTHLY_BUDGET_USD (default 6.10, the Azure OpenAI line in state/BUDGET.md). The price is the
#     explicit AI_PRICE_PER_MILLION_TOKENS / aiPricePerMillionTokens if set, else the table price of the deployment
#     in AZURE_OPENAI_DEPLOYMENT (backend/app/aicost.py); with AI_PROVIDER=azure an unknown deployment and no
#     explicit price is refused. The deploy workflow passes AI_PROVIDER, AZURE_OPENAI_DEPLOYMENT and the optional
#     AI_PRICE_PER_MILLION_TOKENS; none of them is printed.
set -euo pipefail

AI_MONTHLY_BUDGET_USD="${AI_MONTHLY_BUDGET_USD:-6.10}"
AICOST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../backend/app/aicost.py"
command -v python3 >/dev/null 2>&1 || { echo "::error::cost-guard: python3 is needed for the AI cost rule" >&2; exit 2; }
[ -f "$AICOST" ] || { echo "::error::cost-guard: backend/app/aicost.py is missing" >&2; exit 2; }

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

  # Tokens a day x price per million x 30 must stay within the monthly AI budget. The rule lives in one place,
  # backend/app/aicost.py (the app enforces it at startup too). The price is, in order: AI_PRICE_PER_MILLION_TOKENS
  # from the environment, the template's aiPricePerMillionTokens default, or the price table's entry for the
  # deployment the workflow deploys (AZURE_OPENAI_DEPLOYMENT, else the template default). With AI_PROVIDER=azure
  # an unknown deployment and no explicit price fails; with any other provider and no explicit price nothing is
  # spent, so nothing is checked. The deployment name comes from a secret: it is never printed.
  tokens=$(jq -r '.parameters.aiGlobalDailyTokens.defaultValue // empty' "$template")
  tpl_price=$(jq -r '.parameters.aiPricePerMillionTokens.defaultValue // empty' "$template")
  tpl_deployment=$(jq -r '.parameters.azureOpenAiDeployment.defaultValue // empty' "$template")
  has_params=$(jq -r '(.parameters // {}) | if has("aiGlobalDailyTokens") or has("aiPricePerMillionTokens") then "yes" else "no" end' "$template")
  if [ "$has_params" = yes ]; then
    price="${AI_PRICE_PER_MILLION_TOKENS:-$tpl_price}"
    deployment="${AZURE_OPENAI_DEPLOYMENT:-$tpl_deployment}"
    if [ -z "$tokens" ]; then
      report "$name" "aiGlobalDailyTokens must exist with a default to check the AI budget"
    elif [ -n "$price" ] || [ "${AI_PROVIDER:-}" = azure ]; then
      if ! out=$(python3 -I "$AICOST" check --deployment "$deployment" --price "$price" --tokens "$tokens" --budget "$AI_MONTHLY_BUDGET_USD" 2>&1); then
        report "$name" "$out"
      fi
    fi
  fi
done

if [ "$problems" -gt 0 ]; then
  echo "cost-guard: $problems problem(s); see ADR 0002 before changing this check."
  exit 1
fi
echo "cost-guard: $# template(s) use only the Consumption profile, no custom network and no fixed-charge features."
