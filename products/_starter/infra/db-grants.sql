-- Run as the product's migrator role, in the product's own database, right after db-setup.sql:
--
--   PGPASSWORD=<migrator> psql -v ON_ERROR_STOP=1 -v app=<db>_app -d <db> -U <db>_migrator -f db-grants.sql
--
-- Tables and sequences that the migrator creates from now on (every Alembic migration) are readable and
-- writable by the app role, which can't change the schema. The GRANTs cover anything that already exists.
-- Idempotent.

ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"app";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"app";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"app";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"app";
