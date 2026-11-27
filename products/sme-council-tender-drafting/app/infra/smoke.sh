#!/usr/bin/env bash
# Smoke test for a deployed product (ADR 0002, decision 9). The deploy workflow runs it twice: against the
# new revision's own address before it gets any traffic, and against the public address afterwards.
#
#   infra/smoke.sh https://ca-starter.<environment-domain>
#   infra/smoke.sh --local http://127.0.0.1:8000     # a local server: skips the https-only checks
#
# Checks, in order:
#   1. /livez answers 200 (waits up to 3 minutes, for a start from zero replicas)
#   2. /healthz answers 200 with "db":"ok" (the app reaches its database)
#   3. responses carry Strict-Transport-Security (the prod settings took effect)
#   4. plain http:// is redirected to https:// (ingress allowInsecure: false)
#   5. only with EXPECT_SPA=true: / is the app's HTML, with a CSP that allows scripts from 'self' only
set -euo pipefail

local_mode=false
if [ "${1:-}" = "--local" ]; then
  local_mode=true
  shift
fi
base="${1:?usage: smoke.sh [--local] <base-url>}"
base="${base%/}"
if ! $local_mode; then
  case "$base" in
    https://*) ;;
    *) echo "smoke: the address must start with https://" >&2; exit 2 ;;
  esac
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
fail() {
  echo "::error::smoke test failed for $base: $*"
  exit 1
}

# 1. Liveness. A revision at zero replicas has to pull the image and start first.
for attempt in $(seq 1 36); do
  if curl -fsS --max-time 10 -o "$tmp/livez" "$base/livez" 2>/dev/null; then
    break
  fi
  [ "$attempt" -lt 36 ] || fail "/livez didn't answer within 3 minutes"
  sleep 5
done

# 2. Readiness, retried briefly: the first database connection can lag behind a cold start.
for attempt in $(seq 1 6); do
  code=$(curl -sS --max-time 15 -D "$tmp/headers" -o "$tmp/healthz" -w '%{http_code}' "$base/healthz" 2>/dev/null || true)
  if [ "$code" = "200" ] && grep -q '"db":"ok"' "$tmp/healthz"; then
    break
  fi
  [ "$attempt" -lt 6 ] || fail "/healthz answered ${code:-nothing}: $(head -c 200 "$tmp/healthz" 2>/dev/null || true)"
  sleep 5
done

if ! $local_mode; then
  # 3. HSTS is set by the app itself (COOKIE_SECURE=true in prod); the ingress doesn't add it.
  grep -qi '^strict-transport-security: *max-age=' "$tmp/headers" || fail "no Strict-Transport-Security header"

  # 4. Plain http has to be redirected, never served.
  plain=$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "http://${base#https://}/livez" 2>/dev/null || true)
  case "$plain" in
    301|302|307|308) ;;
    *) fail "http:// answered ${plain:-nothing} instead of redirecting to https" ;;
  esac
fi

# 5. The frontend, once the backend serves it (proposed board task; the workflow sets EXPECT_SPA).
if [ "${EXPECT_SPA:-false}" = "true" ]; then
  code=$(curl -sS --max-time 15 -D "$tmp/spa-headers" -o "$tmp/index.html" -w '%{http_code}' "$base/" 2>/dev/null || true)
  [ "$code" = "200" ] || fail "/ answered ${code:-nothing}"
  grep -qi '^content-type: *text/html' "$tmp/spa-headers" || fail "/ isn't HTML"
  grep -qi "^content-security-policy:.*script-src 'self'" "$tmp/spa-headers" || fail "/ has no CSP limiting scripts to 'self'"
  grep -q '<div id="root">' "$tmp/index.html" || fail "/ isn't the app's index.html"
fi

echo "smoke test passed: $base"
