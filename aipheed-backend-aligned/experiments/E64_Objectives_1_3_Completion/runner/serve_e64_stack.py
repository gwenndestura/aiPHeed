"""E64 preview stack in one process: API on 8064 (AIPHEED_LEAD2_MODEL=e64, scratch SQLite DB) + the approved frontend
(unchanged) on 8094. For local verification only; nothing is deployed."""
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path("C:/Users/admin/aipheed/backend")
db = Path(tempfile.gettempdir()) / "aipheed_e62_preview_8064.db"
api_env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", SECRET_KEY=secrets.token_hex(32),
               CORS_ORIGINS="http://localhost:8094,http://127.0.0.1:8094", AIPHEED_LEAD2_MODEL="e64")
api_env.pop("AIPHEED_NOW", None)
subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=api_env, check=True)
api = subprocess.Popen([sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--port", "8064"], cwd=BACKEND, env=api_env)
npm = "npm.cmd" if os.name == "nt" else "npm"
fe_env = dict(os.environ, VITE_API_BASE_URL="http://localhost:8064")
try:
    code = subprocess.call([npm, "run", "dev", "--", "--port", "8094", "--strictPort"], cwd="C:/Users/admin/aipheed/frontend",
                           env=fe_env)
finally:
    api.terminate()
sys.exit(code)
