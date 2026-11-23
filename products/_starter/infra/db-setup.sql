-- One product's database and its two roles on the shared Postgres server (ADR 0002, decision 4).
-- The deploy workflow runs it as the server admin, connected to the "postgres" database:
--
--   PGPASSWORD=<admin> PG_MIGRATOR_VERIFIER=... PG_APP_VERIFIER=... \
--     psql -v ON_ERROR_STOP=1 -v db=<db> -v migrator=<db>_migrator -v app=<db>_app -f db-setup.sql
--
-- migrator  owns the tables and runs Alembic (DDL). Only the migration job has its password.
-- app       reads and writes rows (DML only). The web app and the purge job use it.
--
-- Passwords never reach the server: the workflow sends SCRAM-SHA-256 verifiers made by scram_verifier.py,
-- which Postgres stores as given. A failed statement can only ever log a verifier, never a password. They
-- come from environment variables (\getenv, psql 15 or later), never a command line.
--
-- Idempotent: a second run sets the same passwords again (with new salts). After a seed rotation, that is how
-- the new passwords are applied.

\getenv migrator_verifier PG_MIGRATOR_VERIFIER
\getenv app_verifier PG_APP_VERIFIER
\if :{?migrator_verifier}
\else
  DO $$ BEGIN RAISE EXCEPTION 'PG_MIGRATOR_VERIFIER is not set'; END $$;
\endif
\if :{?app_verifier}
\else
  DO $$ BEGIN RAISE EXCEPTION 'PG_APP_VERIFIER is not set'; END $$;
\endif

-- Refuse anything that isn't a SCRAM verifier (an empty value would clear the password). The check itself can't
-- fail, so the value is never part of a logged error; only the fixed message below is.
SELECT :'migrator_verifier' ~ '^SCRAM-SHA-256\$[0-9]+:[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+$' AS migrator_ok,
       :'app_verifier' ~ '^SCRAM-SHA-256\$[0-9]+:[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+$' AS app_ok \gset
\if :migrator_ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'PG_MIGRATOR_VERIFIER is not a SCRAM-SHA-256 verifier'; END $$;
\endif
\if :app_ok
\else
  DO $$ BEGIN RAISE EXCEPTION 'PG_APP_VERIFIER is not a SCRAM-SHA-256 verifier'; END $$;
\endif

SELECT format('CREATE ROLE %I LOGIN', :'migrator')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migrator') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'app')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app') \gexec

-- Connection limits keep one product from using up the B1ms server's 35 user connections.
ALTER ROLE :"migrator" WITH LOGIN CONNECTION LIMIT 3 PASSWORD :'migrator_verifier';
ALTER ROLE :"app" WITH LOGIN CONNECTION LIMIT 12 PASSWORD :'app_verifier';

SELECT format('CREATE DATABASE %I', :'db')
 WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'db') \gexec

-- Only this product's roles may connect: other products on the same server can't reach its data.
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO :"migrator", :"app";

\connect :"db"
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO :"migrator";
GRANT USAGE ON SCHEMA public TO :"app";
