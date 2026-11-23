-- Run as the product's migrator role, in the product's own database, right after db-setup.sql:
--
--   PGPASSWORD=<migrator> psql -v ON_ERROR_STOP=1 -v app=<db>_app -d <db> -U <db>_migrator -f db-grants.sql
--
-- Tables and sequences that the migrator creates from now on (every Alembic migration) are readable and
-- writable by the app role, which can't change the schema. The GRANTs cover anything that already exists.
-- Idempotent.

SET client_min_messages = warning; -- no "already exists, skipping" notice on re-runs

-- Alembic's own bookkeeping table, created here with the layout Alembic expects so the app role can be kept
-- read-only on it. Alembic uses an existing table as it is; it never rewrites it.
CREATE TABLE IF NOT EXISTS alembic_version (
  version_num VARCHAR(32) NOT NULL,
  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"app";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"app";

-- A compromised app must not be able to make the next migration skip or repeat steps.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON alembic_version FROM :"app";
