"""
tests/unit/test_v2_paths.py
---------------------------
AUDIT D4: data/, models/ and config/ paths resolve against the backend directory (app.paths), so the API returns the
same responses whether the process starts in backend/ or in the repository root. Each run is a fresh subprocess.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.paths import BACKEND_DIR, backend_path

BACKEND = Path(__file__).resolve().parents[2]
ROUTES = ["/api/v1/config", "/api/v1/provinces", "/api/v1/ranking", "/api/v1/hunger-forecast/v2",
          "/api/v1/hunger-forecast/v2/geography", "/api/v1/hunger-forecast"]
PROBE = f"""
import hashlib, json, sys
sys.path.insert(0, {str(BACKEND)!r})
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
out = {{}}
for u in {ROUTES!r}:
    r = c.get(u)
    out[u] = [r.status_code, hashlib.sha256(r.content).hexdigest()]
print(json.dumps(out))
"""


def _run(cwd: Path) -> dict:
    env = {**os.environ, "AIPHEED_NOW": "2026-11-01T10:00"}      # fixed clock: /config echoes the current time
    r = subprocess.run([sys.executable, "-c", PROBE], cwd=cwd, capture_output=True, text=True, timeout=600, env=env)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_backend_path_resolution():
    assert BACKEND_DIR == BACKEND
    assert backend_path("data/x.csv") == BACKEND / "data" / "x.csv"
    assert backend_path(BACKEND / "y") == BACKEND / "y"


def test_api_identical_from_two_working_directories():
    a, b = _run(BACKEND), _run(BACKEND.parent)
    assert all(v[0] == 200 for v in a.values()), a
    assert a == b
