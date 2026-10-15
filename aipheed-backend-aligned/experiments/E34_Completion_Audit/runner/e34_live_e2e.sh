#!/usr/bin/env bash
# E34: run the E31 live end-to-end suite against a REAL running backend built from <backend_dir>.
# usage: SP=<scratch dir> runner/e34_live_e2e.sh <backend_dir> <port> <label>
# Fresh SQLite DB in $SP, random SECRET_KEY and admin password (never printed), alembic migrations, admin account,
# staged alerts, uvicorn on <port>; then pytest tests/test_e31_e2e_live.py; the server is stopped at the end.
set -u
BD=$(cd "$1" && pwd); PORT=$2; LABEL=$3
HERE=$(cd "$(dirname "$0")/.." && pwd)
E31=$(cd "$HERE/../E31_Chapter1_Completion" && pwd)
PY=${PY:-/c/Users/admin/aipheed/backend/venv/Scripts/python.exe}
: "${SP:?set SP}"
LOG="$HERE/runs/e2e_${LABEL}.log"
DB="$SP/e34_${LABEL}.db"; rm -f "$DB"
export DATABASE_URL="sqlite+aiosqlite:///$DB"
export SECRET_KEY=$("$PY" -c "import secrets;print(secrets.token_hex(32))")
export AIPHEED_ADMIN_PASSWORD=$("$PY" -c "import secrets;print(secrets.token_urlsafe(18))")
EMAIL="e2e.${LABEL}@calabarzon.da.gov.ph"
cd "$BD"
{ echo "== $LABEL backend=$BD port=$PORT $(date -Iseconds)"; "$PY" -B -m alembic upgrade head 2>&1 | tail -2; } > "$LOG"
"$PY" -B scripts/create_admin.py --email "$EMAIL" --name "E2E $LABEL" >> "$LOG" 2>&1
"$PY" -B scripts/stage_alerts_e31.py >> "$LOG" 2>&1
"$PY" -B -m uvicorn app.main:app --port "$PORT" > "$SP/uvicorn_${LABEL}.log" 2>&1 &
SRV=$!
for i in $(seq 1 90); do curl -sf "http://127.0.0.1:$PORT/api/v1/health" > /dev/null && break; sleep 1; done
curl -s "http://127.0.0.1:$PORT/api/v1/health" >> "$LOG"; echo >> "$LOG"
cd "$E31"; export AIPHEED_TEST_BACKEND="$BD"
AIPHEED_E2E_URL="http://127.0.0.1:$PORT" AIPHEED_E2E_ADMIN_EMAIL="$EMAIL" AIPHEED_E2E_ADMIN_PASSWORD="$AIPHEED_ADMIN_PASSWORD" \
  "$PY" -B -m pytest -c tests/pytest.ini tests/test_e31_e2e_live.py -q -rA 2>&1 | grep -v "^$" | tail -30 >> "$LOG"
RC=${PIPESTATUS[0]}
kill $SRV 2>/dev/null; sleep 2; taskkill //F //PID $SRV > /dev/null 2>&1
echo "exit=$RC" >> "$LOG"
tail -25 "$LOG"
