#!/usr/bin/env bash
# Runs the end-to-end test: fresh database, migrations, API on :8000, built frontend on :4173.
# Needs Postgres reachable at E2E_DATABASE_URL (a database the script can drop and create).
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
db_url="${E2E_DATABASE_URL:-postgresql+psycopg://studio:studio@localhost:5432/starter_e2e}"
python="${PYTHON:-$here/backend/.venv/bin/python}"
logs="${E2E_LOG_DIR:-$(mktemp -d)}"
api_port="${E2E_API_PORT:-8000}"
web_port="${E2E_WEB_PORT:-4173}"

admin_url="${db_url%/*}/postgres"
db_name="${db_url##*/}"
"$python" - "$admin_url" "$db_name" <<'PY'
import sys
from sqlalchemy import create_engine, text
engine = create_engine(sys.argv[1], isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    conn.execute(text(f'DROP DATABASE IF EXISTS "{sys.argv[2]}" WITH (FORCE)'))
    conn.execute(text(f'CREATE DATABASE "{sys.argv[2]}"'))
PY

cd "$here/backend"
DATABASE_URL="$db_url" "$python" -m alembic upgrade head >"$logs/migrate.log" 2>&1
ENV=dev DATABASE_URL="$db_url" COOKIE_SECURE=false APP_BASE_URL="http://127.0.0.1:$web_port" \
  CORS_ORIGINS="[\"http://127.0.0.1:$web_port\"]" AI_PROVIDER=fake BILLING_PROVIDER=mock LOG_LEVEL=INFO \
  REQUIRE_EMAIL_VERIFICATION=false \
  "$python" -m uvicorn app.main:app --host 127.0.0.1 --port "$api_port" >"$logs/api.log" 2>&1 &
api_pid=$!
cd "$here/frontend"
[ -d dist ] || npx vite build >"$logs/build.log" 2>&1
API_URL="http://127.0.0.1:$api_port" npx vite preview --host 127.0.0.1 --port "$web_port" --strictPort >"$logs/web.log" 2>&1 &
web_pid=$!
trap 'kill $api_pid $web_pid 2>/dev/null || true' EXIT

for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$web_port/healthz" >/dev/null 2>&1; then break; fi
  sleep 0.5
done
curl -fsS "http://127.0.0.1:$web_port/healthz" >/dev/null || { echo "servers did not start; logs in $logs"; cat "$logs/api.log" | tail -20; exit 1; }

E2E_BASE_URL="http://127.0.0.1:$web_port" E2E_SCREENSHOT="$logs/failure.png" node "$here/tests/e2e/core_flow.cjs"
echo "logs: $logs"
