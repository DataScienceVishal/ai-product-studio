#!/usr/bin/env bash
# Every release asserts the database server's sign-in settings (ADR 0003, phase 2): Entra ID on, password off.
# A later default, a portal click or a stray deploy can't quietly reopen password sign-in.
#
# Needs RESOURCE_GROUP and PG_SERVER and a signed-in Azure CLI. AZ can name a stand-in for tests.
# Prints only the two setting values (no token, no secret). Fails closed: an unreadable or incomplete answer
# stops the release too.
set -euo pipefail

az_cli="${AZ:-az}"
: "${RESOURCE_GROUP:?RESOURCE_GROUP is not set}" "${PG_SERVER:?PG_SERVER is not set}"
errors="$(mktemp)"
trap 'rm -f "$errors"' EXIT

if ! json=$("$az_cli" postgres flexible-server show --resource-group "$RESOURCE_GROUP" --name "$PG_SERVER" \
  --query authConfig --output json --only-show-errors 2> "$errors"); then
  echo "::error::check-auth-config.sh: couldn't read the authConfig of $PG_SERVER, so the release stops: $(head -c 300 "$errors")"
  exit 1
fi
if ! entra=$(jq -er '.activeDirectoryAuth' <<< "$json" 2> /dev/null) || ! password=$(jq -er '.passwordAuth' <<< "$json" 2> /dev/null); then
  echo "::error::check-auth-config.sh: the authConfig of $PG_SERVER has no activeDirectoryAuth or passwordAuth value, so the release stops."
  exit 1
fi
if [ "$entra" != "Enabled" ] || [ "$password" != "Disabled" ]; then
  echo "::error::$PG_SERVER has activeDirectoryAuth=$entra and passwordAuth=$password; releases need Enabled and Disabled (ADR 0003, phase 2). Find who changed it in the Activity Log, then run this workflow with deploy_shared ticked."
  exit 1
fi
echo "$PG_SERVER: activeDirectoryAuth=Enabled, passwordAuth=Disabled."
