#!/usr/bin/env bash
# ADR 0003 build slice 4 checks on the deploy workflow and jwt-oid.sh. No Azure, no network.
#
#   bash infra/test-deploy-workflow.sh [path/to/_starter-deploy.yml]
#
# These are text checks: they guard the shape (no password path left, token hygiene, step order). They
# can't show how Azure behaves; only the first real deploy can (README: first-deploy checklist).
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
wf="${1:-$here/../../../.github/workflows/_starter-deploy.yml}"
ci="$(dirname "$wf")/_starter-ci.yml"
failed=0
passed=0
ok() { passed=$((passed + 1)); echo "ok   $1"; }
bad() { failed=$((failed + 1)); echo "FAIL $1"; }
absent() { # description, extended regex that must not match the workflow (comments excluded)
  if grep -vE '^[[:space:]]*#' "$wf" | grep -qE -- "$2"; then bad "$1"; else ok "$1"; fi
}
present() { # description, extended regex that must match
  if grep -qE -- "$2" "$wf"; then ok "$1"; else bad "$1"; fi
}

[ -f "$wf" ] || { echo "no workflow at $wf"; exit 2; }

# ---- what must be gone ----------------------------------------------------------------------------------------
absent "never passes entra_stub (CI-only variable)" 'entra_stub'
absent "no PG_*_VERIFIER env" 'PG_[A-Z_]*VERIFIER'
absent "no scram verifier" 'scram'
absent "no STUDIO_DB_SEED" 'STUDIO_DB_SEED'
absent "no setup_database input or env" 'setup_database|SETUP_DATABASE'
absent "no migrator or app password variable" 'PG_(MIGRATOR|APP)_PASSWORD'
absent "PG_ADMIN_PASSWORD never goes to GITHUB_ENV or GITHUB_OUTPUT" 'PG_ADMIN_PASSWORD.*GITHUB_(ENV|OUTPUT)|GITHUB_(ENV|OUTPUT).*PG_ADMIN_PASSWORD'
absent "no psql run as the migrator" 'psql.*-U +"?\$\{?DB_NAME\}?_migrator'
absent "db-grants.sql is not called separately (db-setup.sql runs it)" 'psql.*db-grants\.sql|-f .*db-grants'
absent "no set -x (the token must never be traced)" 'set +-[a-z]*x'
# no live operator instruction to use the removed seed (starter ADR, reviews and NEXT.md are history and excluded)
root=$(cd "$here/../../.." && pwd)
for d in "$root/.github" "$root/products/_starter" "$root/playbooks" "$root/SETUP.md"; do [ -e "$d" ] || { echo "missing $d"; exit 2; }; done
live=$(grep -rIlE --exclude-dir=node_modules 'STUDIO_DB_SEED' "$root/.github" "$root/products/_starter" "$root/playbooks" "$root/SETUP.md" \
  | sed "s|^$root/||" \
  | grep -vE '^products/_starter/(ADR|reviews)/|^products/_starter/NEXT\.md$|^products/_starter/infra/test-deploy-workflow\.sh$' || true)
[ -z "$live" ] && ok "no live doc, workflow or script mentions STUDIO_DB_SEED" || bad "STUDIO_DB_SEED still in: $live"
[ ! -e "$here/scram_verifier.py" ] && ok "scram_verifier.py is deleted" || bad "scram_verifier.py is deleted"
if grep -q 'scram_verifier' "$ci"; then bad "CI infra job no longer compiles scram_verifier.py"; else ok "CI infra job no longer compiles scram_verifier.py"; fi

# ---- the database step ----------------------------------------------------------------------------------------
step="$(awk '/^      - name: Product database and roles/{f=1;print;next} f&&/^      - name: /{exit} f{print}' "$wf")"
[ -n "$step" ] && ok "the database step exists" || bad "the database step exists"
has() { grep -qE -- "$2" <<< "$step" && ok "$1" || bad "$1"; }
has_not() { grep -qE -- "$2" <<< "$step" && bad "$1" || ok "$1"; }
has "runs on every release (no if: on the step)" '^      - name: Product database and roles \(every release'
has_not "no if: condition on the step" '^        if:'
has "connects to the postgres database" 'psql -X -w -U "\$admin" -d postgres'
has "admin role name is read back, not hard-coded" 'principalName'
has "fails when there are other Entra admins (drift)" 'Entra admins besides the deploy principal'
has "token comes from az (oss-rdbms)" 'az account get-access-token --resource-type oss-rdbms'
has "token only through PGPASSWORD" 'PGPASSWORD="\$t" psql'
has_not "token never in an argument" '(psql|az|curl)[^|]*(\$t\b|\$\{t\}|\$token)'
has "token is masked" '::add-mask::\$t'
has "initial token is masked" '::add-mask::\$token'
# the empty check must come before the mask (an empty mask does nothing)
empty_line=$(grep -nE '\[ -z "\$token" \]' <<< "$step" | head -1 | cut -d: -f1)
mask_line=$(grep -nE '::add-mask::\$token' <<< "$step" | head -1 | cut -d: -f1)
if [ -n "$empty_line" ] && [ -n "$mask_line" ] && [ "$empty_line" -lt "$mask_line" ]; then ok "token emptiness is checked before masking"; else bad "token emptiness is checked before masking"; fi
has "retry loop checks the helper's own token is non-empty" '\[ -z "\$t" \]'
has "tls verify-full" 'PGSSLMODE=verify-full'
has "host comes only from PG_SERVER" 'PGHOST="\$PG_SERVER\.postgres\.database\.azure\.com"'
has "ON_ERROR_STOP=1" '-v ON_ERROR_STOP=1'
for v in db migrator app app_oid migrator_oid; do has "passes -v $v" "-v $v="; done
has "runs db-setup.sql" '-f "\$PRODUCT_DIR/infra/db-setup\.sql"'
has "validates the oids as lower-case UUIDs" '\[0-9a-f\]\{8\}-.*\[0-9a-f\]\{12\}'
has "checks both oids against the pattern" '\$app_oid.*\$uuid.*\$migrator_oid.*\$uuid'
has "decodes the token's oid with jwt-oid.sh" 'infra/jwt-oid\.sh'

# ---- order: roles exist before the migration job needs them, identities exist before roles are labelled ----------
names="$(grep -nE '^      - name: ' "$wf" | sed 's/^\([0-9]*\):      - name: /\1 /')"
line() { grep -m1 -F -- "$1" <<< "$names" | cut -d' ' -f1; }
d=$(line "Deploy the app and jobs"); s=$(line "Product database and roles"); m=$(line "Migrate the database")
if [ -n "$d" ] && [ -n "$s" ] && [ -n "$m" ] && [ "$d" -lt "$s" ] && [ "$s" -lt "$m" ]; then ok "order: deploy main.bicep, database step, migration"; else bad "order: deploy main.bicep, database step, migration"; fi
present "firewall rule is removed even when a step fails" "^        if: always\(\) && steps\.dbsetup\.outcome != 'skipped'$"
present "database step has the id the cleanup step tests" '^        id: dbsetup$'
present "bad admin name and missing admin have separate errors" 'has characters this workflow doesn.t allow'

# S1: run the real run_psql with a stub az and psql. Its stdout is redirected to /dev/null, as in the retry loop;
# the mask line must still reach the runner's own stdout (the old code printed it into the redirect).
fn=$(awk '/^ *run_psql\(\) \{/{f=1} f{print} f&&/^ *\}$/{exit}' "$wf")
fd=$(grep -E '^ *exec 3>&1' "$wf" | head -1)
stub=$(mktemp -d)
printf '#!/bin/sh\necho TOKEN-ATTEMPT-1\n' > "$stub/az"; printf '#!/bin/sh\necho psql-output\n' > "$stub/psql"; chmod +x "$stub/az" "$stub/psql"
runner_out=$(PATH="$stub:$PATH" admin=u bash -c "$fd"$'\n'"$fn"$'\n''run_psql -tAc "select 1" > /dev/null 2>&1' 2>&1 || true)
rm -rf "$stub"
grep -qxF '::add-mask::TOKEN-ATTEMPT-1' <<< "$runner_out" && ok "per-attempt token is masked on the runner's stdout even when psql output is redirected" || bad "per-attempt token is masked on the runner's stdout even when psql output is redirected"

# ---- URLs and Bicep wiring --------------------------------------------------------------------------------------
present "app URL has no password" 'DATABASE_URL_APP="postgresql\+psycopg://\$\{DB_NAME\}_app@\$\{host\}:5432/'
present "migrator URL has no password" 'DATABASE_URL_MIGRATE="postgresql\+psycopg://\$\{DB_NAME\}_migrator@\$\{host\}:5432/'
present "URLs use verify-full" 'sslmode=verify-full'
present "host built from PG_SERVER only" 'host="\$PG_SERVER\.postgres\.database\.azure\.com"'
present "DB_AUTH=entra exported for the deploy" 'export DB_AUTH=entra'
n=$(grep -cE '^[[:space:]]*(export )?DATABASE_URL[A-Z_]*=' "$wf")
[ "$n" = 2 ] && ok "exactly two writers of DATABASE_URL_* (host pinning)" || bad "exactly two writers of DATABASE_URL_* (host pinning), found $n"
if grep -qE "readEnvironmentVariable\('DB_AUTH'" "$here/main.bicepparam"; then ok "main.bicepparam reads DB_AUTH"; else bad "main.bicepparam reads DB_AUTH"; fi
grep -qE "readEnvironmentVariable\('DB_AUTH', 'entra'\)" "$here/main.bicepparam" && ok "dbAuth default is entra (password sign-in is off, phase 2)" || bad "dbAuth default is entra (password sign-in is off, phase 2)"
present "oids come from the main.bicep outputs" 'appIdentityPrincipalId'
present "migrator oid from the outputs" 'migrateIdentityPrincipalId'
if grep -q '^output appIdentityPrincipalId' "$here/main.bicep" && grep -q '^output migrateIdentityPrincipalId' "$here/main.bicep"; then ok "main.bicep has both principal id outputs"; else bad "main.bicep has both principal id outputs"; fi

# ---- phase 1 admin password (B3): made and used inside the deploy_shared step only ----------------------------------
shared="$(awk '/^      - name: Shared studio resources/{f=1;print;next} f&&/^      - name: /{exit} f{print}' "$wf")"
grep -q 'openssl rand' <<< "$shared" && ok "deploy_shared makes a random admin password" || bad "deploy_shared makes a random admin password"
mask=$(grep -n '::add-mask::\$PG_ADMIN_PASSWORD' <<< "$shared" | head -1 | cut -d: -f1)
use=$(grep -n 'az deployment group create' <<< "$shared" | head -1 | cut -d: -f1)
if [ -n "$mask" ] && [ -n "$use" ] && [ "$mask" -lt "$use" ]; then ok "admin password is masked before use"; else bad "admin password is masked before use"; fi

# ---- phase 2: every release asserts authConfig (ADR 0003) -------------------------------------------------------------
auth="$(awk '/^      - name: Database sign-in is Entra only/{f=1;print;next} f&&/^      - name: /{exit} f{print}' "$wf")"
[ -n "$auth" ] && ok "the authConfig step exists" || bad "the authConfig step exists"
grep -qE '^        if:' <<< "$auth" && bad "the authConfig step has no if: condition" || ok "the authConfig step has no if: condition"
grep -qF 'infra/check-auth-config.sh' <<< "$auth" && ok "the step runs check-auth-config.sh" || bad "the step runs check-auth-config.sh"
a=$(line "Database sign-in is Entra only"); p=$(line "Push the image"); dp=$(line "Deploy the app and jobs")
if [ -n "$a" ] && [ -n "$p" ] && [ -n "$dp" ] && [ "$a" -lt "$p" ] && [ "$a" -lt "$dp" ]; then ok "order: authConfig check before the image push and the deploy"; else bad "order: authConfig check before the image push and the deploy"; fi
# the script against a stub az: only Enabled + Disabled passes; anything else, or no answer, fails closed
cac="$here/check-auth-config.sh"
stubdir=$(mktemp -d)
mkstub() { printf '#!/bin/sh\n%s\n' "$1" > "$stubdir/az"; chmod +x "$stubdir/az"; }
run_cac() { AZ="$stubdir/az" RESOURCE_GROUP=rg PG_SERVER=psql-x bash "$cac" 2>&1; }
mkstub 'echo "{\"activeDirectoryAuth\":\"Enabled\",\"passwordAuth\":\"Disabled\",\"tenantId\":\"t\"}"'
run_cac > /dev/null && ok "authConfig check passes for Entra Enabled + password Disabled" || bad "authConfig check passes for Entra Enabled + password Disabled"
mkstub 'echo "{\"activeDirectoryAuth\":\"Enabled\",\"passwordAuth\":\"Enabled\"}"'
run_cac > /dev/null && bad "authConfig check fails when passwordAuth is Enabled" || ok "authConfig check fails when passwordAuth is Enabled"
mkstub 'echo "{\"activeDirectoryAuth\":\"Disabled\",\"passwordAuth\":\"Disabled\"}"'
run_cac > /dev/null && bad "authConfig check fails when Entra is Disabled" || ok "authConfig check fails when Entra is Disabled"
mkstub 'echo "{\"tenantId\":\"t\"}"'
run_cac > /dev/null && bad "authConfig check fails when the settings are missing" || ok "authConfig check fails when the settings are missing"
mkstub 'echo null'
run_cac > /dev/null && bad "authConfig check fails on a null answer" || ok "authConfig check fails on a null answer"
mkstub 'echo "boom" >&2; exit 1'
run_cac > /dev/null && bad "authConfig check fails when az fails" || ok "authConfig check fails when az fails"
rm -rf "$stubdir"
bash -n "$cac" && ok "bash -n check-auth-config.sh" || bad "bash -n check-auth-config.sh"

# ---- jwt-oid.sh on fake tokens ----------------------------------------------------------------------------------
b64url() { base64 -w0 | tr '+/' '-_' | tr -d '='; }
jwt() { printf '%s.%s.sig' "$(printf '{"alg":"none"}' | b64url)" "$(printf '%s' "$1" | b64url)"; }
oid_of() { printf '%s' "$1" | bash "$here/jwt-oid.sh" 2> /dev/null; }
got=$(oid_of "$(jwt '{"oid":"ABCDEF01-1111-4111-8111-111111111111","tid":"t"}')")
[ "$got" = "abcdef01-1111-4111-8111-111111111111" ] && ok "jwt-oid reads and lower-cases the oid" || bad "jwt-oid reads the oid (got '$got')"
# payload lengths of every residue mod 4, so each padding case runs
for pad in 'a' 'ab' 'abc' 'abcd'; do
  got=$(oid_of "$(jwt "{\"oid\":\"11111111-2222-4333-8444-555555555555\",\"x\":\"$pad\"}")")
  [ "$got" = "11111111-2222-4333-8444-555555555555" ] && ok "jwt-oid handles base64url padding ($pad)" || bad "jwt-oid handles base64url padding ($pad)"
done
got=$(oid_of "$(jwt '{"x":"/>>?"}')"); [ -z "$got" ] && ok "jwt-oid fails without an oid claim" || bad "jwt-oid fails without an oid claim"
printf '' | bash "$here/jwt-oid.sh" > /dev/null 2>&1 && bad "jwt-oid fails on an empty token" || ok "jwt-oid fails on an empty token"
printf 'notajwt' | bash "$here/jwt-oid.sh" > /dev/null 2>&1 && bad "jwt-oid fails on a non-JWT" || ok "jwt-oid fails on a non-JWT"
out=$(printf 'a.%s.c' "$(printf 'not json' | b64url)" | bash "$here/jwt-oid.sh" 2>&1 >/dev/null || true)
grep -q 'not json' <<< "$out" && bad "jwt-oid errors don't echo the token" || ok "jwt-oid errors don't echo the token"

# ---- T-60: OIDC sign-in, no stored credential, main only -------------------------------------------------------------
absent "no stored AZURE_CREDENTIALS or creds: input" 'AZURE_CREDENTIALS|creds:'
absent "no environment: on any job (it would change the OIDC subject)" '^    environment:'
present "uses client-id from the secret" 'client-id: \$\{\{ secrets\.AZURE_CLIENT_ID \}\}'
present "uses tenant-id from the secret" 'tenant-id: \$\{\{ secrets\.AZURE_TENANT_ID \}\}'
present "uses subscription-id from the secret" 'subscription-id: \$\{\{ secrets\.AZURE_SUBSCRIPTION_ID \}\}'
logins=$(grep -c 'uses: azure/login@' "$wf")
loginjobs=2 # deploy and rollback
tokens=$(grep -cE '^      id-token: write' "$wf")
[ "$logins" -ge "$loginjobs" ] && [ "$tokens" = "$loginjobs" ] && ok "each of the $loginjobs login jobs has its own id-token: write ($logins sign-ins)" || bad "each login job has its own id-token: write (sign-ins $logins, grants $tokens)"
if grep -E '^permissions:' -A3 "$wf" | grep -q 'id-token'; then bad "id-token is not granted at workflow level"; else ok "id-token is not granted at workflow level"; fi
guards=$(grep -c 'Only from main (the Azure sign-in trusts main only)' "$wf")
[ "$guards" = "$logins" ] && ok "every login job refuses to run off main" || bad "every login job refuses to run off main"
# the guard step must come before the sign-in
g1=$(grep -n 'Only from main (the Azure' "$wf" | head -1 | cut -d: -f1); l1=$(grep -n 'uses: azure/login@' "$wf" | head -1 | cut -d: -f1)
[ -n "$g1" ] && [ "$g1" -lt "$l1" ] && ok "the main-only guard runs before the sign-in" || bad "the main-only guard runs before the sign-in"
# a fresh sign-in directly precedes the database step and the registry push (the OIDC assertion lasts ~5 minutes)
prev_step() { grep -nE '^      - name: ' "$wf" | grep -F -B1 -- "$1" | head -1 | sed 's/^[0-9]*:      - name: //'; }
for s in "Product database and roles" "Push the image"; do
  prev_step "$s" | grep -q '^Sign in to Azure' && ok "a fresh Azure sign-in directly precedes: $s" || bad "a fresh Azure sign-in directly precedes: $s"
done
# no oss-rdbms token before the sign-in that precedes the database step
dbl=$(grep -n 'name: Product database and roles' "$wf" | head -1 | cut -d: -f1)
firsttok=$(grep -n 'get-access-token --resource-type oss-rdbms' "$wf" | head -1 | cut -d: -f1)
lastlogin=$(grep -n 'uses: azure/login@' "$wf" | awk -F: -v d="$dbl" '$1<d{l=$1} END{print l}')
[ -n "$lastlogin" ] && [ "$lastlogin" -lt "$dbl" ] && [ "$dbl" -lt "$firsttok" ] && [ $((dbl - lastlogin)) -le 12 ] && ok "the database token is first requested right after a sign-in" || bad "the database token is first requested right after a sign-in"

# ---- T-104: the deploy gate over every secret, approval and branch combination ------------------------------------
for expr in \
  "HAS_AZURE: \${{ secrets.AZURE_CLIENT_ID != '' && secrets.AZURE_TENANT_ID != '' && secrets.AZURE_SUBSCRIPTION_ID != '' }}" \
  "HAS_DEPLOY_ID: \${{ secrets.AZURE_CLIENT_ID != '' }}" \
  "APPROVED: \${{ vars.STUDIO_AZURE_APPROVED }}"; do
  grep -qF "          $expr" "$wf" && ok "deploy gate: env ${expr%%:*} built from the right secret or variable" || bad "deploy gate: env ${expr%%:*} built from the right secret or variable"
done
gate="$(mktemp)"
awk '/- name: Credentials, approval and branch/{f=1;next} f&&/run: \|/{r=1;next} r&&/^      - name:|^  [a-z_]+:$/{exit} r' "$wf" | sed 's/^          //' > "$gate"
if ! [ -s "$gate" ] || ! grep -q 'go=' "$gate"; then
  bad "deploy gate: could not extract the 'Credentials, approval and branch' run block"
else
  gate_out() { # deploy_id tenant_sub approved(value) on_main -> go=true / go=false / fail
    local out rc
    out="$(mktemp)"
    HAS_DEPLOY_ID=$([ "$1" = 1 ] && echo true || echo false) HAS_AZURE=$([ "$1" = 1 ] && [ "$2" = 1 ] && echo true || echo false) \
      APPROVED="$3" GITHUB_REF=$([ "$4" = 1 ] && echo refs/heads/main || echo refs/heads/x) \
      PRODUCT_DIR=products/_starter GITHUB_OUTPUT="$out" bash -e "$gate" >/dev/null 2>&1; rc=$?
    if [ $rc -ne 0 ]; then echo fail; else sed -n 's/^go=//p' "$out"; fi
    rm -f "$out"
  }
  g_bad=0; g_n=0
  # Approval values: only the exact "yes" approves. "" is the real default (variable unset); "no", "Yes" and
  # "yes " must not approve either.
  for d in 0 1; do for t in 0 1; do for a in yes "" no Yes "yes "; do for m in 0 1; do
    g_n=$((g_n+1))
    if [ $d = 1 ] && [ $t = 0 ]; then exp=fail          # client id without tenant/subscription: broken, fail loudly
    elif [ $d = 1 ] && [ "$a" = yes ] && [ $m = 1 ]; then exp=true
    else exp=false; fi                                   # fresh setup, unapproved or off main: notice, no deploy
    got=$(gate_out $d $t "$a" $m)
    [ "$got" = "$exp" ] || { g_bad=$((g_bad+1)); echo "  deploy gate deploy_id=$d tenant_sub=$t approved='$a' on_main=$m: want $exp, got $got"; }
  done; done; done; done
  [ "$g_n" = 40 ] && [ "$g_bad" = 0 ] && ok "deploy gate: matches the 40-row truth table (half-set client id fails, deploys only when all hold)" || bad "deploy gate: matches the 40-row truth table ($g_bad wrong)"
fi
rm -f "$gate"
# The gate's answer must reach the jobs that sign in: the job output comes from the step, and both jobs need it.
grep -qF '      go: ${{ steps.gate.outputs.go }}' "$wf" && ok "deploy gate: check job output go comes from the gate step" || bad "deploy gate: check job output go comes from the gate step"
grep -qxF "    if: needs.check.outputs.go == 'true' && inputs.rollback_to == ''" "$wf" && grep -qxF "    if: needs.check.outputs.go == 'true' && inputs.rollback_to != ''" "$wf" && [ "$(grep -cE "^    if: .*needs\.check\.outputs\.go" "$wf")" = 2 ] && ok "deploy gate: deploy and rollback both require go == 'true'" || bad "deploy gate: deploy and rollback both require go == 'true'"

# ---- azure-spend.yml ----------------------------------------------------------------------------------------------
sp="$(dirname "$wf")/azure-spend.yml"
if [ -f "$sp" ]; then
  grep -vE '^[[:space:]]*#' "$sp" | grep -qE 'AZURE_CREDENTIALS' && bad "azure-spend: no AZURE_CREDENTIALS" || ok "azure-spend: no AZURE_CREDENTIALS"
  grep -q 'client-id: \${{ secrets.AZURE_CLIENT_ID }}' "$sp" && ok "azure-spend: signs in by OIDC" || bad "azure-spend: signs in by OIDC"
  grep -q 'client-id: \${{ secrets.AZURE_SPEND_CLIENT_ID }}' "$sp" && ok "azure-spend: spend sign-in uses AZURE_SPEND_CLIENT_ID" || bad "azure-spend: spend sign-in uses AZURE_SPEND_CLIENT_ID"
  grep -q "if: env.AZURE_MODE == 'spend'" "$sp" && ok "azure-spend: the spend sign-in is conditional on its mode" || bad "azure-spend: the spend sign-in is conditional on its mode"
  ms=$(grep -n 'mode=spend' "$sp" | head -1 | cut -d: -f1); mo=$(grep -n 'mode=oidc' "$sp" | head -1 | cut -d: -f1)
  [ -n "$ms" ] && [ -n "$mo" ] && [ "$ms" -lt "$mo" ] && ok "azure-spend: spend mode is chosen before oidc" || bad "azure-spend: spend mode is chosen before oidc"
  # The job-level flags the script reads must be built from the right secrets (the truth table below assumes these).
  for expr in \
    "HAS_SPEND: \${{ secrets.AZURE_SPEND_CLIENT_ID != '' && secrets.AZURE_TENANT_ID != '' && secrets.AZURE_SUBSCRIPTION_ID != '' }}" \
    "HAS_SPEND_ID: \${{ secrets.AZURE_SPEND_CLIENT_ID != '' }}" \
    "HAS_OIDC: \${{ secrets.AZURE_CLIENT_ID != '' && secrets.AZURE_TENANT_ID != '' && secrets.AZURE_SUBSCRIPTION_ID != '' }}" \
    "HAS_DEPLOY_ID: \${{ secrets.AZURE_CLIENT_ID != '' }}" \
    "HAS_COST_SP: \${{ secrets.AZURE_COST_CREDENTIALS != '' }}"; do
    grep -qF "      $expr" "$sp" && ok "azure-spend: env ${expr%%:*} built from the right secrets" || bad "azure-spend: env ${expr%%:*} built from the right secrets"
  done
  # Run the real sign-in choice script over every secret combination (truth table), not just grep its text.
  choose="$(mktemp)"
  awk '/- name: Work out the Azure sign-in/{f=1;next} f&&/run: \|/{r=1;next} r&&/^      - name:/{exit} r' "$sp" | sed 's/^          //' > "$choose"
  if ! [ -s "$choose" ] || ! grep -q 'AZURE_MODE=' "$choose"; then
    bad "azure-spend: could not extract the 'Work out the Azure sign-in' run block"
  else
    got_mode() { # spend_id tenant_sub deploy_id cost_sp on_main -> actual mode (+ ",azure" if HAS_AZURE=true) or "fail"
      local env_file rc hs=false ho=false
      env_file="$(mktemp)"
      [ "$1" = 1 ] && [ "$2" = 1 ] && hs=true
      [ "$3" = 1 ] && [ "$2" = 1 ] && ho=true
      # Actions runs a bare run: step as `bash -e {0}`.
      HAS_SPEND_ID=$([ "$1" = 1 ] && echo true || echo false) HAS_SPEND=$hs HAS_OIDC=$ho \
        HAS_DEPLOY_ID=$([ "$3" = 1 ] && echo true || echo false) \
        HAS_COST_SP=$([ "$4" = 1 ] && echo true || echo false) ON_MAIN=$([ "$5" = 1 ] && echo true || echo false) \
        GITHUB_REF=refs/heads/x GITHUB_ENV="$env_file" bash -e "$choose" >/dev/null 2>&1; rc=$?
      if [ $rc -ne 0 ]; then echo fail
      else echo "$(sed -n 's/^AZURE_MODE=//p' "$env_file")$(grep -qx 'HAS_AZURE=true' "$env_file" && echo ,azure)"; fi
      rm -f "$env_file"
    }
    # Tenant and subscription share one bit (tenant_sub). That is safe because the env-flag checks above prove
    # HAS_SPEND and HAS_OIDC each need both secrets, so "tenant only" behaves exactly like "neither".
    tt_bad=0; tt_n=0
    for a in 0 1; do for t in 0 1; do for d in 0 1; do for c in 0 1; do for m in 0 1; do
      tt_n=$((tt_n+1))
      if { [ $a = 1 ] || [ $d = 1 ]; } && [ $t = 0 ]; then exp=fail      # a client id without tenant/subscription
      elif [ $a = 1 ] && [ $m = 1 ]; then exp=spend,azure
      elif [ $d = 1 ] && [ $m = 1 ]; then exp=oidc,azure
      elif [ $a = 1 ] || [ $d = 1 ]; then exp=fail                         # OIDC off main
      elif [ $c = 1 ]; then exp=sp,azure
      else exp=none; fi
      got=$(got_mode $a $t $d $c $m)
      [ "$got" = "$exp" ] || { tt_bad=$((tt_bad+1)); echo "  sign-in choice spend_id=$a tenant_sub=$t deploy_id=$d cost_sp=$c on_main=$m: want $exp, got $got"; }
    done; done; done; done; done
    [ "$tt_n" = 32 ] && [ "$tt_bad" = 0 ] && ok "azure-spend: sign-in choice matches the 32-row truth table (spend > oidc > sp > none, loud failures)" || bad "azure-spend: sign-in choice matches the 32-row truth table ($tt_bad wrong)"
  fi
  rm -f "$choose"
  [ "$(grep -c 'creds:' "$sp")" = 1 ] && grep -q 'creds: \${{ secrets.AZURE_COST_CREDENTIALS }}' "$sp" && ok "azure-spend: the only creds: is the temporary AZURE_COST_CREDENTIALS fallback" || bad "azure-spend: the only creds: is the temporary AZURE_COST_CREDENTIALS fallback"
  grep -q "if: env.AZURE_MODE == 'oidc'" "$sp" && grep -q "if: env.AZURE_MODE == 'sp'" "$sp" && ok "azure-spend: each sign-in is conditional on its mode" || bad "azure-spend: each sign-in is conditional on its mode"
  awk '/^permissions:/{f=1;next} f&&/^[^ ]/{exit} f' "$sp" | grep -q 'id-token' && bad "azure-spend: id-token not at workflow level" || ok "azure-spend: id-token not at workflow level"
  awk '/^permissions:/{f=1;next} f&&/^[^ ]/{exit} f' "$sp" | grep -q 'contents: read' && ok "azure-spend: workflow-level contents: read" || bad "azure-spend: workflow-level contents: read"
  [ "$(grep -cE '^      id-token: write' "$sp")" = 1 ] && ok "azure-spend: id-token: write on the job" || bad "azure-spend: id-token: write on the job"
  grep -q 'refs/heads/main' "$sp" && grep -q "ON_MAIN" "$sp" && ok "azure-spend: main guard" || bad "azure-spend: main guard"
  grep -E "if: failure\(\)" "$sp" | grep -q "ON_MAIN == 'true'" && ok "azure-spend: no failure ping for runs off main" || bad "azure-spend: no failure ping for runs off main"
else
  bad "azure-spend.yml exists"
fi
# no workflow that can sign in to Azure may be triggered by untrusted events
for f in "$(dirname "$wf")"/*.yml; do
  if grep -qE 'azure/login@' "$f"; then
    if grep -vE '^[[:space:]]*#' "$f" | grep -qE '^[[:space:]]*(issue_comment|issues|workflow_run|pull_request_target|pull_request|push):'; then bad "$(basename "$f"): signs in to Azure but has a forbidden trigger"; else ok "$(basename "$f"): no forbidden trigger (issue_comment, issues, workflow_run, pull_request[_target], push)"; fi
  fi
done

# location is explicit (T-61)
for f in main shared; do
  grep -qE "^param location = 'francecentral'" "$here/$f.bicepparam" && ok "$f.bicepparam sets location = francecentral" || bad "$f.bicepparam sets location = francecentral"
done

# ---- syntax tools, when present -----------------------------------------------------------------------------------
bash -n "$here/jwt-oid.sh" && ok "bash -n jwt-oid.sh" || bad "bash -n jwt-oid.sh"
if command -v actionlint > /dev/null; then
  actionlint "$wf" && ok "actionlint" || bad "actionlint"
else
  echo "skip actionlint (not installed)"
fi

echo "passed: $passed  failed: $failed"
[ "$failed" = 0 ]
