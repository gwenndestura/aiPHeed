"""aiPHeed FI9-Z: class-specific (HIGH and LOW) audit, class-sensitive candidates under a locked rule, objective
assessment. Isolated: writes data/fi9z and docs/fi9z; production changes only after an 'adopt' decision.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi9z-1.0"
FI9Z = BACKEND_DIR / "data" / "fi9z"
OUT = FI9Z / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi9z"
for _d in (FI9Z, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
