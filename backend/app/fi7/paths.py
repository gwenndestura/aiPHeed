"""FI7 outputs live in data/fi7 (FI7 reads FI5 raw data, FI6-N news caches and its own extra raw files)."""
from __future__ import annotations

from app.paths import BACKEND_DIR

FI7 = BACKEND_DIR / "data" / "fi7"
OUT = FI7 / "out"
MODELS = FI7 / "models"

for _d in (FI7, OUT, MODELS):
    _d.mkdir(parents=True, exist_ok=True)
