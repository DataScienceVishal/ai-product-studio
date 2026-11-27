-- One product's database and its two roles on the shared Postgres server (ADR 0003, decision 3).
-- The deploy workflow runs it as the server's Entra admin (the deploy service principal), connected to the
-- "postgres" database, where the pgaadauth functions live. The Entra token goes in PGPASSWORD, never in an argument:
--
--   PGPASSWORD=<entra token> psql -X -w -U <admin role> -d postgres -v ON_ERROR_STOP=1 \
--     -v db=<db> -v migrator=<db>_migrator -v app=<db>_app \
--     -v migrator_oid=<object id of id-<slug>-migrate> -v app_oid=<object id of id-<slug>-app> \
--     -f db-setup.sql
--
-- migrator  owns the tables and runs Alembic (DDL). Only the migration job's identity signs in as it.
-- app       reads and writes rows (DML only). The web app and the purge job's identity sign in as it.
--
-- Neither role ever has a password (PASSWORD NULL on every run): a role can only be entered with an Entra token
-- for the object id in its pgaadauth security label. Re-running re-maps the label, so a recreated identity
-- heals on the next release.
--
-- CI only (infra/test-db-setup.sh): -v entra_stub=<stub schema> writes the mapping to <schema>.principals instead of running
-- SECURITY LABEL, because a plain Postgres has no pgaadauth provider. Azure prints the function's columns as
-- principalType, objectId, isAdmin and this file uses them unquoted (folded to lower case), and the stub
-- assumes the same. The stub is found through the admin role's search_path, so keep calls unqualified.
-- The first real deploy must confirm that casing (security review N4).
--
-- Idempotent. Needs PostgreSQL 16 (GRANT ... WITH INHERIT FALSE, SET TRUE).
-- The checks below RAISE, so this script stops at the first error whatever flags the caller passes.
\set ON_ERROR_STOP on

-- 1. Both object ids must be lower-case UUIDs. The check can't fail, so a bad value is never part of a logged
-- error; only the fixed message below is.
\if :{?app_oid}
\else
  DO $$ BEGIN RAISE EXCEPTION 'app_oid is not set'; END $$;
\endif
\if :{?migrator_oid}
\else
  DO $$ BEGIN RAISE EXCEPTION 'migrator_oid is not set'; END $$;
\endif
SELECT :'app_oid' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' AS app_oid_ok,
       :'migrator_oid' ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' AS migrator_oid_ok \gset
\if :app_oid_ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'app_oid is not a lower-case UUID'; END $$;
\endif
\if :migrator_oid_ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'migrator_oid is not a lower-case UUID'; END $$;
\endif

-- 2. Roles, as before.
SELECT format('CREATE ROLE %I LOGIN', :'migrator')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migrator') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'app')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app') \gexec

-- 3. Connection limits keep one product from using up the B1ms server's 35 user connections. PASSWORD NULL
-- means no password can ever work for these roles, even while the server still allows password sign-in.
ALTER ROLE :"migrator" WITH LOGIN CONNECTION LIMIT 3 PASSWORD NULL;
ALTER ROLE :"app" WITH LOGIN CONNECTION LIMIT 12 PASSWORD NULL;

-- 4. Map each role to its identity as a service principal, never an admin.
\if :{?entra_stub}
  INSERT INTO :"entra_stub".principals (rolename, principaltype, objectid, tenantid, ismfa, isadmin)
  VALUES (:'migrator', 'service', :'migrator_oid', 'stub-tenant', 0, 0),
         (:'app', 'service', :'app_oid', 'stub-tenant', 0, 0)
  ON CONFLICT (rolename) DO UPDATE
    SET principaltype = EXCLUDED.principaltype, objectid = EXCLUDED.objectid, isadmin = 0;
\else
  SELECT format('SECURITY LABEL FOR "pgaadauth" ON ROLE %I IS %L', :'migrator', 'aadauth,oid=' || :'migrator_oid' || ',type=service') \gexec
  SELECT format('SECURITY LABEL FOR "pgaadauth" ON ROLE %I IS %L', :'app', 'aadauth,oid=' || :'app_oid' || ',type=service') \gexec
\endif

-- 5. Check what the server now believes: right object id, a service principal, not an admin; and no admin
-- other than the role running this script (admin drift, security review N1).
SELECT NOT EXISTS (SELECT 1 FROM pgaadauth_list_principals(false) p
                    WHERE p.rolename = :'migrator' AND p.objectid = :'migrator_oid'
                      AND lower(p.principaltype) = 'service' AND p.isadmin = 0) AS migrator_bad,
       NOT EXISTS (SELECT 1 FROM pgaadauth_list_principals(false) p
                    WHERE p.rolename = :'app' AND p.objectid = :'app_oid'
                      AND lower(p.principaltype) = 'service' AND p.isadmin = 0) AS app_bad,
       EXISTS (SELECT 1 FROM pgaadauth_list_principals(true) p
                WHERE p.rolename <> current_user) AS other_admin \gset
\if :migrator_bad
  DO $$ BEGIN RAISE EXCEPTION 'the migrator role is not mapped to migrator_oid as a non-admin service principal'; END $$;
\endif
\if :app_bad
  DO $$ BEGIN RAISE EXCEPTION 'the app role is not mapped to app_oid as a non-admin service principal'; END $$;
\endif
\if :other_admin
  DO $$ BEGIN RAISE EXCEPTION 'an Entra admin other than the deploy principal exists on this server'; END $$;
\endif

-- 6. The database. Only this product's roles may connect: other products on the same server can't reach its data.
SELECT format('CREATE DATABASE %I', :'db')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db') \gexec
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO :"migrator", :"app";

-- 7. Let this admin act as the migrator (PostgreSQL 16 syntax), then run db-grants.sql as the migrator so its
-- default privileges and alembic_version belong to the migrator.
GRANT :"migrator" TO CURRENT_USER WITH INHERIT FALSE, SET TRUE;

\connect :"db"
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO :"migrator";
GRANT USAGE ON SCHEMA public TO :"app";
SET ROLE :"migrator";
\ir db-grants.sql
RESET ROLE;
