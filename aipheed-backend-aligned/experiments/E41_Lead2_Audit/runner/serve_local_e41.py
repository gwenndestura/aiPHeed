"""Local preview with the E41 Lead-2 candidate enabled (AIPHEED_LEAD2_MODEL=e41) on a SCRATCH SQLite database, never
backend/aipheed.db. The clock defaults to 2026-10-15 09:00 PHT so the forecast target is 2027-Q1.

    <backend venv python> -B runner/serve_local_e41.py [e38|e41]      (port E41_API_PORT, default 8001)
"""
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
db = Path(tempfile.gettempdir()) / "aipheed_e41_preview.db"
env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{db.as_posix()}", SECRET_KEY=secrets.token_hex(32),
           CORS_ORIGINS="http://localhost:8080,http://127.0.0.1:8080,http://localhost:8082,http://127.0.0.1:8082",
           AIPHEED_LEAD2_MODEL=(sys.argv[1] if len(sys.argv) > 1 else "e41"),
           AIPHEED_NOW=os.environ.get("AIPHEED_NOW", "2026-10-15T09:00:00"))
subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
sys.exit(subprocess.call([sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--port", os.environ.get("E41_API_PORT", "8001")], cwd=BACKEND, env=env))
