"""
The one base directory for backend files (AUDIT D4). Relative data/, models/ and config/ paths in app/ are resolved
against the backend directory, not the process working directory, so the API behaves the same when started from the
repository root, from backend/, or from Docker's WORKDIR /app. Absolute paths (e.g. from environment variables) are
returned unchanged.
"""
from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def backend_path(p: str | Path) -> Path:
    q = Path(p)
    return q if q.is_absolute() else BACKEND_DIR / q
