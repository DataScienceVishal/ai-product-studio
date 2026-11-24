#!/usr/bin/env bash
# Slice 3 CI check for db-setup.sql (ADR 0003): runs it against a local PostgreSQL 16 as a non-superuser
# CREATEROLE admin, with a stub "pgaadauth" schema standing in for Azure's Entra provider.
#
#   PGHOST=localhost PGUSER=studio PGPASSWORD=studio bash infra/test-db-setup.sh
#
# The superuser (PGUSER) only sets up and inspects. Everything under test runs as the admin role.
# Skips (exit 0) when psql or the server is missing, unless REQUIRE_PG=1. Creates and drops only objects
# ending in _t18s.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PGHOST="${PGHOST:-localhost}" PGPORT="${PGPORT:-5432}" PGUSER="${PGUSER:-studio}" PGPASSWORD="${PGPASSWORD:-studio}"
SU_PASSWORD="$PGPASSWORD"

if ! command -v psql >/dev/null || ! psql -X -qtAc 'select 1' postgres >/dev/null 2>&1; then
  if [ "${REQUIRE_PG:-}" = 1 ]; then echo "FAIL: psql or the server is not available"; exit 1; fi
  echo "SKIP: psql or a Postgres server is not available"; exit 0
fi
if [ "$(psql -X -qtAc 'show server_version_num' postgres | cut -c1-2)" -lt 16 ]; then
  echo "FAIL: PostgreSQL 16 or later is required"; exit 1
fi

ADMIN=adm_t18s
ADMIN_PASSWORD="t18s-$RANDOM-$RANDOM"
P1=p1_t18s
P2=p2_t18s
OID_APP=abcdef01-1111-4111-8111-111111111111
OID_MIG=22222222-2222-4222-8222-222222222222
OID_APP2=33333333-3333-4333-8333-333333333333
OID_MIG2=44444444-4444-4444-8444-444444444444
OID_OTHER=99999999-9999-4999-8999-999999999999

pass=0; fail=0
ok()   { pass=$((pass + 1)); echo "ok   - $1"; }
bad()  { fail=$((fail + 1)); echo "FAIL - $1"; [ -n "${2:-}" ] && echo "       $2"; }
su()   { PGPASSWORD="$SU_PASSWORD" psql -X -qtA -v ON_ERROR_STOP=1 -U "$PGUSER" "$@"; }
setup() {  # setup <db> <app_oid> <migrator_oid>  -> runs db-setup.sql as the admin
  local db=$1
  PGPASSWORD="$ADMIN_PASSWORD" psql -X -w -q -U "$ADMIN" -d postgres -v ON_ERROR_STOP=1 \
    -v entra_stub=1 -v db="$db" -v migrator="${db}_migrator" -v app="${db}_app" \
    -v app_oid="$2" -v migrator_oid="$3" -f "$here/db-setup.sql" 2>&1
}
expect_ok()   { local out; if out=$("$@" 2>&1); then ok "$DESC"; else bad "$DESC" "$out"; fi; }
expect_fail() {  # expect_fail <pattern> cmd...
  local pat=$1 out; shift
  if out=$("$@" 2>&1); then bad "$DESC (succeeded)"; elif grep -qi -- "$pat" <<<"$out"; then ok "$DESC"; else bad "$DESC" "$out"; fi
}
as_role() {  # as_role <role> <db> <sql>  (superuser session, SET ROLE to the role under test)
  PGPASSWORD="$SU_PASSWORD" psql -X -qtA -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$2" -c "SET ROLE \"$1\"; $3" 2>&1
}

cleanup() {
  su -d postgres -c "DROP DATABASE IF EXISTS $P1" -c "DROP DATABASE IF EXISTS $P2" >/dev/null 2>&1
  su -d postgres -c "DROP SCHEMA IF EXISTS pgaadauth_stub CASCADE" >/dev/null 2>&1
  for r in ${P1}_app ${P1}_migrator ${P2}_app ${P2}_migrator "$ADMIN"; do
    su -d postgres -c "DROP ROLE IF EXISTS $r" >/dev/null 2>&1
  done
}
trap cleanup EXIT
cleanup

# --- fixture: a non-superuser admin (CREATEROLE, CREATEDB) and the stub schema -------------------------------
su -d postgres <<SQL
CREATE ROLE $ADMIN LOGIN CREATEROLE CREATEDB PASSWORD '$ADMIN_PASSWORD';
CREATE SCHEMA pgaadauth_stub;
CREATE TABLE pgaadauth_stub.principals (rolename name PRIMARY KEY, principaltype text, objectid text,
                                        tenantid text, ismfa integer, isadmin integer);
-- the admin itself, as Azure lists it: the one admin allowed
INSERT INTO pgaadauth_stub.principals VALUES ('$ADMIN', 'service', '$OID_OTHER', 'stub-tenant', 0, 1);
-- like the real function: false = everyone, true = admins only
CREATE FUNCTION pgaadauth_stub.pgaadauth_list_principals(admin_only boolean)
RETURNS TABLE (rolename name, principaltype text, objectid text, tenantid text, ismfa integer, isadmin integer)
LANGUAGE sql STABLE AS \$\$
  SELECT p.rolename, p.principaltype, p.objectid, p.tenantid, p.ismfa, p.isadmin
    FROM pgaadauth_stub.principals p WHERE NOT admin_only OR p.isadmin = 1 \$\$;
GRANT USAGE ON SCHEMA pgaadauth_stub TO $ADMIN;
GRANT SELECT, INSERT, UPDATE ON pgaadauth_stub.principals TO $ADMIN;
GRANT EXECUTE ON FUNCTION pgaadauth_stub.pgaadauth_list_principals(boolean) TO $ADMIN;
ALTER ROLE $ADMIN SET search_path = pgaadauth_stub, public;
SQL
[ "$(su -d postgres -c "select rolsuper from pg_roles where rolname='$ADMIN'")" = f ] || { echo "FIXTURE: admin is a superuser"; exit 1; }

# --- tests ------------------------------------------------------------------------------------------------------
DESC="first run succeeds as a non-superuser admin"; expect_ok setup $P1 $OID_APP $OID_MIG
DESC="second run succeeds (re-runnable)";            expect_ok setup $P1 $OID_APP $OID_MIG
DESC="a second product sets up beside the first";    expect_ok setup $P2 $OID_APP2 $OID_MIG2

pw=$(su -d postgres -c "select count(*) from pg_authid where rolname in ('${P1}_app','${P1}_migrator') and rolpassword is null")
[ "$pw" = 2 ] && ok "rolpassword IS NULL for both roles" || bad "rolpassword IS NULL for both roles" "got $pw"

lim=$(su -d postgres -c "select string_agg(rolname || '=' || rolconnlimit, ',' order by rolname) from pg_roles where rolname like '${P1}_%'")
[ "$lim" = "${P1}_app=12,${P1}_migrator=3" ] && ok "connection limits 12 (app) and 3 (migrator)" || bad "connection limits" "$lim"

map=$(su -d postgres -c "select string_agg(rolename || ':' || objectid || ':' || isadmin, ',' order by rolename) from pgaadauth_stub.principals where rolename like '${P1}_%'")
[ "$map" = "${P1}_app:$OID_APP:0,${P1}_migrator:$OID_MIG:0" ] && ok "roles are mapped to their oids as non-admins" || bad "mapping" "$map"

# a changed oid re-maps on the next run (a recreated identity heals)
setup $P1 $OID_OTHER $OID_MIG >/dev/null
setup $P1 $OID_APP $OID_MIG >/dev/null
[ "$(su -d postgres -c "select objectid from pgaadauth_stub.principals where rolename='${P1}_app'")" = "$OID_APP" ] \
  && ok "re-running re-maps the label" || bad "re-running re-maps the label"

for badoid in "not-a-uuid" "${OID_APP^^}" "" "$OID_APP' OR 1=1 --"; do
  DESC="malformed app oid refused: '${badoid:0:20}'"
  expect_fail "not a lower-case UUID" setup $P1 "$badoid" $OID_MIG
done
DESC="malformed migrator oid refused"; expect_fail "not a lower-case UUID" setup $P1 $OID_APP "12345"
# a bad oid must not have changed the mapping
[ "$(su -d postgres -c "select objectid from pgaadauth_stub.principals where rolename='${P1}_app'")" = "$OID_APP" ] \
  && ok "a refused oid left the mapping alone" || bad "a refused oid left the mapping alone"

DESC="missing oid variable refused"
expect_fail "app_oid is not set" env PGPASSWORD="$ADMIN_PASSWORD" psql -X -w -q -U "$ADMIN" -d postgres -v ON_ERROR_STOP=1 \
  -v entra_stub=1 -v db=$P1 -v migrator=${P1}_migrator -v app=${P1}_app -v migrator_oid=$OID_MIG -f "$here/db-setup.sql"

# label/oid mismatch: a trigger makes the stored oid differ from the one asked for, as a failed label would
su -d postgres <<SQL
CREATE FUNCTION pgaadauth_stub.skew() RETURNS trigger LANGUAGE plpgsql AS \$\$
BEGIN NEW.objectid := '$OID_OTHER'; RETURN NEW; END \$\$;
CREATE TRIGGER skew BEFORE INSERT OR UPDATE ON pgaadauth_stub.principals
  FOR EACH ROW WHEN (NEW.rolename = '${P1}_app') EXECUTE FUNCTION pgaadauth_stub.skew();
SQL
DESC="label/oid mismatch raises"; expect_fail "app role is not mapped to app_oid" setup $P1 $OID_APP $OID_MIG
su -d postgres -c "DROP TRIGGER skew ON pgaadauth_stub.principals; DROP FUNCTION pgaadauth_stub.skew()"

# an Entra admin besides the deploy principal fails the check
su -d postgres -c "INSERT INTO pgaadauth_stub.principals VALUES ('rogue_t18s','user','$OID_OTHER','stub-tenant',0,1)"
DESC="an Entra admin other than the deploy principal raises"; expect_fail "other than the deploy principal" setup $P1 $OID_APP $OID_MIG
su -d postgres -c "DELETE FROM pgaadauth_stub.principals WHERE rolename = 'rogue_t18s'"
DESC="setup works again once the rogue admin is gone"; expect_ok setup $P1 $OID_APP $OID_MIG

# privileges, as the roles (superuser session with SET ROLE: the roles have no password to sign in with)
DESC="app role is refused CREATE TABLE";   expect_fail "permission denied" as_role ${P1}_app $P1 "CREATE TABLE t_t18s (id int)"
DESC="migrator can create a table";        expect_ok as_role ${P1}_migrator $P1 "CREATE TABLE t_t18s (id int)"
DESC="app can write a table the migrator made (default privileges)"
expect_ok as_role ${P1}_app $P1 "INSERT INTO t_t18s VALUES (1); UPDATE t_t18s SET id = 2; DELETE FROM t_t18s"
DESC="app role is refused DROP TABLE";     expect_fail "must be owner" as_role ${P1}_app $P1 "DROP TABLE t_t18s"
DESC="app role is refused INSERT into alembic_version"
expect_fail "permission denied" as_role ${P1}_app $P1 "INSERT INTO alembic_version VALUES ('x')"
DESC="app role is refused DELETE from alembic_version"
expect_fail "permission denied" as_role ${P1}_app $P1 "DELETE FROM alembic_version"
DESC="app role can read alembic_version";  expect_ok as_role ${P1}_app $P1 "SELECT * FROM alembic_version"
owner=$(su -d $P1 -c "select tableowner from pg_tables where tablename='alembic_version'")
[ "$owner" = "${P1}_migrator" ] && ok "alembic_version is owned by the migrator" || bad "alembic_version owner" "$owner"

# CONNECT: only a product's own roles, not PUBLIC and not another product's roles
chk() { su -d postgres -c "select has_database_privilege('$1','$2','CONNECT')"; }
[ "$(chk ${P2}_app $P1)" = f ] && [ "$(chk ${P2}_migrator $P1)" = f ] \
  && ok "another product's roles are refused CONNECT" || bad "another product's roles are refused CONNECT"
[ "$(chk ${P1}_app $P1)" = t ] && [ "$(chk ${P1}_migrator $P1)" = t ] && [ "$(chk ${P1}_app $P2)" = f ] \
  && ok "own roles may CONNECT, and only to their own database" || bad "own roles may CONNECT"
acl=$(su -d postgres -c "select datacl::text from pg_database where datname='$P1'")
grep -q '^{=' <<<"$acl" && bad "PUBLIC still holds privileges on the database" "$acl" || ok "PUBLIC holds nothing on the database"

echo
echo "passed: $pass  failed: $fail"
[ "$fail" = 0 ]
