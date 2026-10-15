#!/usr/bin/env bash
# E34: visual check of the PROMOTED app: backend/ (scratch DB) + frontend/ dev server, headless Edge screenshots.
# usage: SP=<scratch dir> runner/e34_screenshots.sh
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd)
ROOT=/c/Users/admin/aipheed
PY=$ROOT/backend/venv/Scripts/python.exe
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
OUT="$HERE/runs/screenshots"; mkdir -p "$OUT"
: "${SP:?set SP}"
DB="$SP/e34_shots.db"; rm -f "$DB"
export DATABASE_URL="sqlite+aiosqlite:///$DB"
export SECRET_KEY=$("$PY" -c "import secrets;print(secrets.token_hex(32))")
export CORS_ORIGINS="http://localhost:8091,http://127.0.0.1:8091"
cd "$ROOT/backend" && "$PY" -B -m alembic upgrade head > /dev/null 2>&1
"$PY" -B -m uvicorn app.main:app --port 8033 > "$SP/uvicorn_shots.log" 2>&1 &
BE=$!
cd "$ROOT/frontend" && VITE_API_BASE_URL=http://localhost:8033 npx vite --port 8091 --strictPort > "$SP/vite_shots.log" 2>&1 &
FE=$!
for i in $(seq 1 90); do curl -sf http://127.0.0.1:8033/api/v1/health > /dev/null && curl -sf http://localhost:8091/ > /dev/null && break; sleep 1; done
for page in "dashboard" "da-brief" "news"; do
  "$EDGE" --headless=new --disable-gpu --hide-scrollbars --window-size=1600,1000 --virtual-time-budget=15000 \
    --user-data-dir="$SP/edge_profile_$page" --screenshot="$(cygpath -w "$OUT/$page.png")" "http://localhost:8091/$page" > /dev/null 2>&1
  for i in $(seq 1 60); do [ -s "$OUT/$page.png" ] && break; sleep 1; done   # the Edge launcher returns before the shot
  sleep 2; echo "$page $(stat -c %s "$OUT/$page.png" 2>/dev/null)"
done
grep -E "GET /api/v1" "$SP/uvicorn_shots.log" | awk '{print $(NF-3), $(NF-2), $(NF-1), $NF}' | sort | uniq -c | sort -rn | head -30 > "$OUT/api_calls.txt"
cat "$OUT/api_calls.txt"
taskkill //F //T //PID $FE > /dev/null 2>&1; taskkill //F //T //PID $BE > /dev/null 2>&1
kill $FE $BE 2>/dev/null
