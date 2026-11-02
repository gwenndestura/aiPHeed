"""aiPHeed FI9-R: reliability reassessment of the FI9 Lead-1 outlook (isolated from production).

Writes only to data/fi9r and docs/fi9r. It never writes data/fi9/model or data/fi9/out (production FI9). Production
changes are possible only through data/fi9/PRODUCTION_PIN.json after an 'adopt' decision (app.fi9r.evaluate).
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi9r-1.0"
FI9R = BACKEND_DIR / "data" / "fi9r"
OUT = FI9R / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi9r"
for _d in (FI9R, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
