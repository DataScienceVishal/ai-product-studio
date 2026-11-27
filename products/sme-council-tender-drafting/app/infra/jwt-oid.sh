#!/usr/bin/env bash
# Print the "oid" claim (the caller's object id) of a JWT read from standard input. It only decodes, it
# does not verify the signature: the token came from `az account get-access-token` and the use is to learn
# which Entra admin entry is ours (ADR 0003, decision 4). The token is read from stdin, never an argument.
# Exits 1 with nothing on stdout when the input is empty, is not a JWT or has no oid.
set -euo pipefail
token=$(cat)
token=${token//[$'\r\n ']/}
[ -n "$token" ] || { echo "jwt-oid: empty token" >&2; exit 1; }
payload=$(printf '%s' "$token" | cut -d. -f2)
[ -n "$payload" ] || { echo "jwt-oid: not a JWT" >&2; exit 1; }
payload=$(printf '%s' "$payload" | tr '_-' '/+')
case $(( ${#payload} % 4 )) in 2) payload="$payload==" ;; 3) payload="$payload=" ;; 1) echo "jwt-oid: bad length" >&2; exit 1 ;; esac
oid=$(printf '%s' "$payload" | base64 -d 2>/dev/null | jq -er '.oid' 2>/dev/null) || { echo "jwt-oid: no oid claim" >&2; exit 1; }
printf '%s\n' "${oid,,}"
