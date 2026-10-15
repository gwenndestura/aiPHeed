"""Local preview of the promoted app with the E36 record: backend/ on port 8000 against a SCRATCH SQLite database
(never backend/aipheed.db), CORS for the Vite dev server on 8080, a random SECRET_KEY.

    <backend venv python> -B runner/serve_local.py
"""
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
db = Path(tempfile.gettempdir()) / "aipheed_e36_preview.db"
env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", SECRET_KEY=secrets.token_hex(32),
           CORS_ORIGINS="http://localhost:8080,http://127.0.0.1:8080")
subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
sys.exit(subprocess.call([sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--port", "8000"], cwd=BACKEND, env=env))
