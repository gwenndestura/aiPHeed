r"""Start the aiPHeed thesis-demo system: API (thesis mode, strict) + the approved frontend.

    cd backend
    venv\Scripts\python.exe scripts\start_thesis_demo.py            (API on 8000, dashboard on 8080)
    venv\Scripts\python.exe scripts\start_thesis_demo.py --api-only

Uses backend/config/thesis_demo.env. If DATABASE_URL is not set (in the environment or backend/.env) a local scratch
SQLite database is created in the system temp folder; if SECRET_KEY is not set a random one is generated for this run.
Nothing is deployed. FINAL_THESIS_SYSTEM_REPORT.md section 10 documents the configuration and the rollback.
"""
from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"


def read_env(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-port", type=int, default=8000)
    ap.add_argument("--ui-port", type=int, default=8080)
    ap.add_argument("--api-only", action="store_true")
    a = ap.parse_args()
    env = dict(os.environ)
    dotenv = read_env(BACKEND / ".env")
    env.update(read_env(BACKEND / "config" / "thesis_demo.env"))
    if "DATABASE_URL" not in env and "DATABASE_URL" not in dotenv:
        db = Path(tempfile.gettempdir()) / "aipheed_thesis_demo.db"
        env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db.as_posix()}"
    if "SECRET_KEY" not in env and "SECRET_KEY" not in dotenv:
        env["SECRET_KEY"] = secrets.token_hex(32)
    env.setdefault("CORS_ORIGINS", f"http://localhost:{a.ui_port},http://127.0.0.1:{a.ui_port}")
    env.pop("AIPHEED_NOW", None)                    # the dashboard target follows the real clock
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True)
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(a.api_port)], cwd=BACKEND, env=env)
    if a.api_only:
        return api.wait()
    npm = "npm.cmd" if os.name == "nt" else "npm"
    fe = dict(os.environ, VITE_API_BASE_URL=f"http://localhost:{a.api_port}")
    try:
        return subprocess.call([npm, "run", "dev", "--", "--port", str(a.ui_port), "--strictPort"], cwd=FRONTEND, env=fe)
    finally:
        api.terminate()


if __name__ == "__main__":
    sys.exit(main())
