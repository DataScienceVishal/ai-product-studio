#!/usr/bin/env bash
# Keeps the scheduled purge job and cancels job (T-176) on the revision that serves traffic (ADR 0002, decision 10).
# Container Apps jobs have no revisions, so the job that deletes data must never run a release's code before
# that release has passed. The deploy workflow calls this after the public smoke test, and on every rollback.
#
#   purge-job.sh settings <revision>   print PURGE_IMAGE=..., PURGE_REQUIRE_EMAIL_VERIFICATION=...,
#                                      PURGE_EMAIL_PROVIDER=... and PURGE_BILLING_PROVIDER=... for that web revision
#                                      (for $GITHUB_ENV; every value is checked against a strict pattern first)
#   purge-job.sh follow <revision>     point caj-<product>-purge and caj-<product>-cancels at that revision's image and
#                                      email settings, and caj-<product>-cancels also at its BILLING_PROVIDER (mock when the
#                                      revision has none). The purge job never calls the payment provider: it stays on mock.
#                                      Each job is read back and its image and billing provider verified.
#                                      Idempotent and safe to re-run: if one job update fails, run it again (a rollback does).
#
# The cancels job has both Stripe secrets defined whatever its provider is (main.bicep always defines them), because
# `follow` can switch its provider without a Bicep deploy. `follow` also adds the two secretRef env variables
# (BILLING_WEBHOOK_SECRET, STRIPE_SECRET_KEY) for stripe and removes them for mock, because a mock job must not get
# the placeholder secret (the app rejects it). Bicep sets the same provider and references from PURGE_BILLING_PROVIDER.
#
# Needs RESOURCE_GROUP and PRODUCT, and a signed-in Azure CLI. AZ can name a stand-in for tests.
set -euo pipefail

az_cli="${AZ:-az}"
command="${1:-}"
revision="${2:-}"
: "${RESOURCE_GROUP:?RESOURCE_GROUP is not set}" "${PRODUCT:?PRODUCT is not set}"
app="ca-$PRODUCT"
jobs="purge cancels" # job caj-$PRODUCT-<name>, whose container is called <name> too

fail() {
  echo "::error::purge-job.sh: $*" >&2
  exit 1
}

case "$command" in settings | follow) ;; *) echo "usage: purge-job.sh settings|follow <revision>" >&2; exit 2 ;; esac
[[ "$revision" =~ ^${app}--[a-z][a-z0-9-]{0,40}[a-z0-9]$ ]] || fail "'$revision' isn't a revision of $app"

json=$("$az_cli" containerapp revision show --resource-group "$RESOURCE_GROUP" --name "$app" --revision "$revision" \
  --output json --only-show-errors) || fail "couldn't read revision $revision"

web='.properties.template.containers[] | select(.name == "web")'
image=$(jq -r "[$web | .image][0] // \"\"" <<<"$json")
# Revisions made before these settings existed fall back to the app's own defaults.
verify=$(jq -r "[$web | .env[]? | select(.name == \"REQUIRE_EMAIL_VERIFICATION\") | .value][0] // \"true\"" <<<"$json")
provider=$(jq -r "[$web | .env[]? | select(.name == \"EMAIL_PROVIDER\") | .value][0] // \"outbox\"" <<<"$json")
billing=$(jq -r "[$web | .env[]? | select(.name == \"BILLING_PROVIDER\") | .value][0] // \"mock\"" <<<"$json")

# Everything printed below ends up in $GITHUB_ENV or a command line, so accept only the expected shapes.
[[ "$image" =~ ^[a-z0-9][a-z0-9.-]*\.azurecr\.io/[a-z0-9._/-]+(@sha256:[0-9a-f]{64}|:[A-Za-z0-9._-]{1,128})$ ]] \
  || fail "revision $revision has an unexpected image '$image'"
[[ "$verify" =~ ^(true|false)$ ]] || fail "revision $revision has REQUIRE_EMAIL_VERIFICATION='$verify'"
[[ "$provider" =~ ^[a-z][a-z0-9_-]{0,30}$ ]] || fail "revision $revision has EMAIL_PROVIDER='$provider'"
[[ "$billing" =~ ^(mock|stripe)$ ]] || fail "revision $revision has BILLING_PROVIDER='$billing'"

if [ "$command" = "settings" ]; then
  printf 'PURGE_IMAGE=%s\nPURGE_REQUIRE_EMAIL_VERIFICATION=%s\nPURGE_EMAIL_PROVIDER=%s\nPURGE_BILLING_PROVIDER=%s\n' \
    "$image" "$verify" "$provider" "$billing"
  exit 0
fi

stripe_names="BILLING_WEBHOOK_SECRET STRIPE_SECRET_KEY"
for name in $jobs; do
  job="caj-$PRODUCT-$name"
  want_billing=mock # only the cancels job calls the payment provider
  [ "$name" = "cancels" ] && want_billing=$billing
  extra=()
  if [ "$name" = "cancels" ] && [ "$want_billing" = "stripe" ]; then
    # The secrets are always defined on the job (main.bicep); only the references follow the provider.
    extra=("BILLING_WEBHOOK_SECRET=secretref:billing-webhook-secret" "STRIPE_SECRET_KEY=secretref:stripe-secret-key")
  elif [ "$name" = "cancels" ]; then
    # Mock billing must not carry a Stripe reference: its settings reject the placeholder secret. Remove only the
    # ones that exist (the CLI may refuse to remove an absent variable), in a call of its own.
    before=$("$az_cli" containerapp job show --resource-group "$RESOURCE_GROUP" --name "$job" --output json --only-show-errors) \
      || fail "couldn't read $job"
    present=$(jq -r --arg n "$name" '[.properties.template.containers[] | select(.name == $n) | .env[]? | select(.name == "BILLING_WEBHOOK_SECRET" or .name == "STRIPE_SECRET_KEY") | .name] | join(" ")' <<<"$before")
    if [ -n "$present" ]; then
      # shellcheck disable=SC2086 # names are fixed words from jq's filter above
      "$az_cli" containerapp job update --resource-group "$RESOURCE_GROUP" --name "$job" --container-name "$name" \
        --remove-env-vars $present --only-show-errors --output none || fail "couldn't remove the Stripe references from $job"
    fi
  fi
  "$az_cli" containerapp job update --resource-group "$RESOURCE_GROUP" --name "$job" --container-name "$name" \
    --image "$image" --set-env-vars "REQUIRE_EMAIL_VERIFICATION=$verify" "EMAIL_PROVIDER=$provider" "BILLING_PROVIDER=$want_billing" ${extra[@]+"${extra[@]}"} \
    --only-show-errors --output none || fail "couldn't update $job"

  now=$("$az_cli" containerapp job show --resource-group "$RESOURCE_GROUP" --name "$job" --output json --only-show-errors) \
    || fail "couldn't read $job back"
  got=$(jq -r --arg n "$name" '[.properties.template.containers[] | select(.name == $n) | .image][0] // ""' <<<"$now")
  [ "$got" = "$image" ] || fail "$job still runs '$got', not '$image'"
  got_billing=$(jq -r --arg n "$name" '[.properties.template.containers[] | select(.name == $n) | .env[]? | select(.name == "BILLING_PROVIDER") | .value][0] // ""' <<<"$now")
  [ "$got_billing" = "$want_billing" ] || fail "$job has BILLING_PROVIDER='$got_billing', not '$want_billing'"
  # Stripe references: exactly the right secretRefs on the cancels job with stripe, none anywhere else.
  refs=$(jq -r --arg n "$name" '[.properties.template.containers[] | select(.name == $n) | .env[]? | select(.name == "BILLING_WEBHOOK_SECRET" or .name == "STRIPE_SECRET_KEY") | "\(.name)=\(.secretRef // "")"] | sort | join(" ")' <<<"$now")
  want_refs=""
  [ "$name" = "cancels" ] && [ "$want_billing" = "stripe" ] && want_refs="BILLING_WEBHOOK_SECRET=billing-webhook-secret STRIPE_SECRET_KEY=stripe-secret-key"
  [ "$refs" = "$want_refs" ] || fail "$job has Stripe references '$refs', not '$want_refs'"
  echo "$job now runs $image (REQUIRE_EMAIL_VERIFICATION=$verify, EMAIL_PROVIDER=$provider, BILLING_PROVIDER=$want_billing), as $revision does."
done
