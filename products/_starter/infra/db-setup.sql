-- One product's database and its two roles on the shared Postgres server (ADR 0002, decision 4).
-- The deploy workflow runs it as the server admin, connected to the "postgres" database:
--
--   PGPASSWORD=<admin> PG_MIGRATOR_PASSWORD=... PG_APP_PASSWORD=... \
--     psql -v ON_ERROR_STOP=1 -v db=<db> -v migrator=<db>_migrator -v app=<db>_app -f db-setup.sql
--
-- migrator  owns the tables and runs Alembic (DDL). Only the migration job has its password.
-- app       reads and writes rows (DML only). The web app and the purge job use it.
--
-- Idempotent: a second run only sets the passwords again, which is how a seed rotation is applied.
-- The passwords come from environment variables (\getenv, psql 15 or later), never a command line.

\getenv migrator_password PG_MIGRATOR_PASSWORD
\getenv app_password PG_APP_PASSWORD
\if :{?migrator_password}
\else
  DO $$ BEGIN RAISE EXCEPTION 'PG_MIGRATOR_PASSWORD is not set'; END $$;
\endif
\if :{?app_password}
\else
  DO $$ BEGIN RAISE EXCEPTION 'PG_APP_PASSWORD is not set'; END $$;
\endif

SELECT format('CREATE ROLE %I LOGIN', :'migrator')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migrator') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'app')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app') \gexec

-- Connection limits keep one product from using up the B1ms server's 35 user connections.
ALTER ROLE :"migrator" WITH LOGIN CONNECTION LIMIT 3 PASSWORD :'migrator_password';
ALTER ROLE :"app" WITH LOGIN CONNECTION LIMIT 12 PASSWORD :'app_password';

SELECT format('CREATE DATABASE %I', :'db')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db') \gexec

-- Only this product's roles may connect: other products on the same server can't reach its data.
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO :"migrator", :"app";

\connect :"db"
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO :"migrator";
GRANT USAGE ON SCHEMA public TO :"app";
