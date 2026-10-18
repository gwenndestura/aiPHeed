"""Local preview of AIPHEED_LEAD2_MODEL=e56 on a SCRATCH SQLite database (never backend/aipheed.db), API on port 8003,
clock 2026-10-17 09:00 PHT (dashboard target 2027-Q1). Runs alongside other sessions' previews on 8001/8082.

    <backend venv python> -B runner/serve_local_e55.py
"""
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
db = Path(tempfile.gettempdir()) / "aipheed_e56_preview.db"
env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", SECRET_KEY=secrets.token_hex(32),
           CORS_ORIGINS="http://localhost:8083,http://127.0.0.1:8083", AIPHEED_LEAD2_MODEL="e56",
           AIPHEED_NOW=os.environ.get("AIPHEED_NOW", "2026-10-17T09:00:00"))
subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
sys.exit(subprocess.call([sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--port", "8003"], cwd=BACKEND, env=env))
