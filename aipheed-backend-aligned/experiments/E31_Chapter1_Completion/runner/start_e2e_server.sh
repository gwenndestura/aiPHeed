#!/usr/bin/env bash
# Start the E31 backend for live end-to-end tests: python, port, SQLite path from the environment.
# usage: SP=<scratch dir> runner/start_e2e_server.sh [port]
set -e
cd "$(dirname "$0")/../backend_dev"
PY=${PY:-/c/Users/admin/aipheed/backend/venv/Scripts/python.exe}
PORT=${1:-8031}
export DATABASE_URL="sqlite+aiosqlite:///${SP:?set SP}/e31_e2e.db"
export SECRET_KEY=${SECRET_KEY:-$("$PY" -c "import secrets;print(secrets.token_hex(32))")}
"$PY" -B -m alembic upgrade head
exec "$PY" -B -m uvicorn app.main:app --port "$PORT"
