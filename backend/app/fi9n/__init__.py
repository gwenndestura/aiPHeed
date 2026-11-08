"""aiPHeed FI9-N: reassessment of the value of news/NLP by forecasting horizon (isolated; reads FI6-N, FI7, FI9).

Writes only data/fi9n and docs/fi9n. FI6-N outputs (data/fi6/out_news) and production FI9 are only read.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi9n-1.0"
FI9N = BACKEND_DIR / "data" / "fi9n"
OUT = FI9N / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi9n"
for _d in (FI9N, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
