"""Run the approved frontend (unchanged files) on port 8082 against the E41 preview backend on 8001."""
import os
import subprocess
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[4] / "frontend"
env = dict(os.environ, VITE_API_BASE_URL=os.environ.get("E41_API_URL", "http://localhost:8001"))
npm = "npm.cmd" if os.name == "nt" else "npm"
sys.exit(subprocess.call([npm, "run", "dev", "--", "--port", "8082", "--strictPort"], cwd=FRONTEND, env=env))
