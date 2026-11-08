"""FI6 outputs live in data/fi6 (FI6 reads FI5's raw data and NLP caches from data/fi5)."""
from __future__ import annotations

from app.paths import BACKEND_DIR

FI6 = BACKEND_DIR / "data" / "fi6"
OUT = FI6 / "out"
MODELS = FI6 / "models"
VALIDATION = FI6 / "nlp_validation"

for _d in (OUT, MODELS, VALIDATION):
    _d.mkdir(parents=True, exist_ok=True)
