"""aiPHeed FI9-X: government + news fusion study, Philippine label integration and method review (isolated).

Writes only data/fi9x and docs/fi9x (branch fi9x/gov-news-fusion). Production FI9 (data/fi9/model, data/fi9/out,
PRODUCTION_PIN.json) changes only after an 'adopt' decision under the locked protocol (app.fi9x.study).
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi9x-1.0"
FI9X = BACKEND_DIR / "data" / "fi9x"
OUT = FI9X / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi9x"
for _d in (FI9X, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
