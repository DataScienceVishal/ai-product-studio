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
# The cancels job needs both Stripe secrets defined whatever its provider is (main.bicep always defines them),
# because `follow` can switch its provider without a Bicep deploy.
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

for name in $jobs; do
  job="caj-$PRODUCT-$name"
  want_billing=mock # only the cancels job calls the payment provider
  [ "$name" = "cancels" ] && want_billing=$billing
  "$az_cli" containerapp job update --resource-group "$RESOURCE_GROUP" --name "$job" --container-name "$name" \
    --image "$image" --set-env-vars "REQUIRE_EMAIL_VERIFICATION=$verify" "EMAIL_PROVIDER=$provider" "BILLING_PROVIDER=$want_billing" \
    --only-show-errors --output none || fail "couldn't update $job"

  now=$("$az_cli" containerapp job show --resource-group "$RESOURCE_GROUP" --name "$job" --output json --only-show-errors) \
    || fail "couldn't read $job back"
  got=$(jq -r --arg n "$name" '[.properties.template.containers[] | select(.name == $n) | .image][0] // ""' <<<"$now")
  [ "$got" = "$image" ] || fail "$job still runs '$got', not '$image'"
  got_billing=$(jq -r --arg n "$name" '[.properties.template.containers[] | select(.name == $n) | .env[]? | select(.name == "BILLING_PROVIDER") | .value][0] // ""' <<<"$now")
  [ "$got_billing" = "$want_billing" ] || fail "$job has BILLING_PROVIDER='$got_billing', not '$want_billing'"
  echo "$job now runs $image (REQUIRE_EMAIL_VERIFICATION=$verify, EMAIL_PROVIDER=$provider, BILLING_PROVIDER=$want_billing), as $revision does."
done
