"""Run the approved frontend (unchanged files) on port 8083 against the E55 preview backend on 8003."""
import os
import subprocess
import sys
from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[4] / "frontend"
env = dict(os.environ, VITE_API_BASE_URL="http://localhost:8003")
npm = "npm.cmd" if os.name == "nt" else "npm"
sys.exit(subprocess.call([npm, "run", "dev", "--", "--port", "8083", "--strictPort"], cwd=FRONTEND, env=env))
