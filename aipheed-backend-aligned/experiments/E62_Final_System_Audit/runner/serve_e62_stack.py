"""E62 preview stack in one process: API on 8062 (AIPHEED_LEAD2_MODEL=e58, scratch SQLite DB) + the approved frontend
(unchanged) on 8092. For local verification only; nothing is deployed."""
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path("C:/Users/admin/aipheed/backend")
db = Path(tempfile.gettempdir()) / "aipheed_e62_preview_8062.db"
api_env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", SECRET_KEY=secrets.token_hex(32),
               CORS_ORIGINS="http://localhost:8092,http://127.0.0.1:8092", AIPHEED_LEAD2_MODEL="e58")
api_env.pop("AIPHEED_NOW", None)
subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=api_env, check=True)
api = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--port", "8062"], cwd=BACKEND, env=api_env)
npm = "npm.cmd" if os.name == "nt" else "npm"
fe_env = dict(os.environ, VITE_API_BASE_URL="http://localhost:8062")
try:
    code = subprocess.call([npm, "run", "dev", "--", "--port", "8092", "--strictPort"], cwd="C:/Users/admin/aipheed/frontend",
                           env=fe_env)
finally:
    api.terminate()
sys.exit(code)
