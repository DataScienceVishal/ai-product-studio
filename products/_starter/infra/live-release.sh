#!/usr/bin/env bash
# What a release starts from (ADR 0002, decision 9), read once from Azure. Prints lines for $GITHUB_ENV:
#   FIRST_RELEASE=true|false, LIVE_REVISION=<the revision with 100% of the traffic>, and the purge job's
#   PURGE_* settings (taken from that revision, see purge-job.sh).
#
# Fails closed. Only "the app doesn't exist" (Azure CLI exit code 3, or ResourceNotFound) means a first
# release. Any other error stops the release: guessing "first release" would give an untested revision all
# the traffic before its migration and smoke test, with no rollback.
#
# Needs RESOURCE_GROUP and PRODUCT, and a signed-in Azure CLI. AZ can name a stand-in for tests.
set -euo pipefail

az_cli="${AZ:-az}"
: "${RESOURCE_GROUP:?RESOURCE_GROUP is not set}" "${PRODUCT:?PRODUCT is not set}"
app="ca-$PRODUCT"
errors="$(mktemp)"
trap 'rm -f "$errors"' EXIT

fail() {
  echo "::error::live-release.sh: $*" >&2
  exit 1
}

set +e
json=$("$az_cli" containerapp show --resource-group "$RESOURCE_GROUP" --name "$app" --output json --only-show-errors 2> "$errors")
status=$?
set -e
if [ "$status" -ne 0 ]; then
  if [ "$status" -eq 3 ] || grep -q "ResourceNotFound" "$errors"; then
    echo "$app doesn't exist yet: this is its first release." >&2
    printf 'FIRST_RELEASE=true\nLIVE_REVISION=\n'
    exit 0
  fi
  fail "couldn't read $app (exit $status), so the release stops instead of guessing: $(head -c 300 "$errors")"
fi

pinned=$(jq -r '[.properties.configuration.ingress.traffic[]? | select(.weight == 100 and (.revisionName // "") != "")][0].revisionName // ""' <<< "$json")
to_latest=$(jq -r '[.properties.configuration.ingress.traffic[]? | select(.weight == 100 and .latestRevision == true)] | length' <<< "$json")
ready=$(jq -r '.properties.latestReadyRevisionName // ""' <<< "$json")

if [ -n "$pinned" ]; then
  live="$pinned"
elif [ "$to_latest" -ge 1 ] && [ -n "$ready" ]; then
  live="$ready" # after a first release, traffic follows "latest" rather than a name
elif [ "$to_latest" -ge 1 ]; then
  # The app exists, but its first release never became ready: nothing serves, so start over as a first release.
  echo "::warning::$app exists but none of its revisions has ever been ready; releasing it as a first release." >&2
  printf 'FIRST_RELEASE=true\nLIVE_REVISION=\n'
  exit 0
else
  fail "no revision of $app has 100% of the traffic (split or unreadable), so the release stops. Move all traffic to one revision first, for example with rollback_to."
fi

[[ "$live" =~ ^${app}--[a-z0-9-]+$ ]] || fail "unexpected live revision name '$live'"
printf 'FIRST_RELEASE=false\nLIVE_REVISION=%s\n' "$live"
AZ="$az_cli" bash "$(dirname "$0")/purge-job.sh" settings "$live"
