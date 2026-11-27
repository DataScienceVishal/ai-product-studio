#!/usr/bin/env bash
# Runs the end-to-end test: fresh database, migrations, API on :8000, built frontend on :4173.
# Needs Postgres reachable at E2E_DATABASE_URL (a database the script can drop and create).
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
db_url="${E2E_DATABASE_URL:-postgresql+psycopg://studio:studio@localhost:5432/starter_e2e}"
python="${PYTHON:-$here/backend/.venv/bin/python}"
logs="${E2E_LOG_DIR:-$(mktemp -d)}"
mkdir -p "$logs"
api_port="${E2E_API_PORT:-8000}"
web_port="${E2E_WEB_PORT:-4173}"

port_free() { ! (echo > "/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
for port in "$api_port" "$web_port"; do  # a stale server on these ports would answer for the new one
  port_free "$port" || { echo "port $port is already in use: stop that server or pick E2E_API_PORT/E2E_WEB_PORT"; exit 2; }
done

admin_url="${db_url%/*}/postgres"
db_name="${db_url##*/}"
case "$db_name" in  # this script drops the database it is given, so refuse anything not named for e2e
  *e2e*) ;;
  *) echo "refusing to drop '$db_name': E2E_DATABASE_URL must name a database containing 'e2e'"; exit 2 ;;
esac
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
  REQUIRE_EMAIL_VERIFICATION=false MOCK_CHECKOUT_ENABLED=true AI_WORKER_THREADS=2 \
  setsid "$python" -m uvicorn e2e_app:app --app-dir "$here/tests/e2e" --host 127.0.0.1 --port "$api_port" >"$logs/api.log" 2>&1 &
api_pid=$!
web_pid=""
trap 'kill -- -"$api_pid" ${web_pid:+-"$web_pid"} 2>/dev/null || true' EXIT  # set as soon as a server runs
cd "$here/frontend"
npx vite build >"$logs/build.log" 2>&1  # always test the current code, never an old build
API_URL="http://127.0.0.1:$api_port" setsid npx vite preview --host 127.0.0.1 --port "$web_port" --strictPort >"$logs/web.log" 2>&1 &
web_pid=$!
# Each server runs in its own process group (setsid), so the trap stops npx's child node process too.

for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$web_port/healthz" >/dev/null 2>&1; then break; fi
  sleep 0.5
done
curl -fsS "http://127.0.0.1:$web_port/healthz" >/dev/null || { echo "servers did not start; logs in $logs"; cat "$logs/api.log" | tail -20; exit 1; }

fixtures="$logs/fixtures"
"$python" "$here/tests/e2e/make_fixtures.py" "$fixtures"
E2E_BASE_URL="http://127.0.0.1:$web_port" E2E_SCREENSHOT="$logs/tender-failure.png" E2E_FIXTURES="$fixtures" PYTHON="$python" \
  node "$here/tests/e2e/tender_flow.cjs"
status=0
E2E_BASE_URL="http://127.0.0.1:$web_port" E2E_SCREENSHOT="$logs/failure.png" node "$here/tests/e2e/core_flow.cjs" || status=$?
echo "logs: $logs"
exit $status
