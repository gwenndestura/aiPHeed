"""
app.e150
--------
E150: fundamental redesign of risk scoring and quarterly forecasting (docs/e150). E137-E149 are imported, never modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e150-1.0"
PROTOCOL_VERSION = "E150-P1"
DATA = BACKEND_DIR / "data" / "e150"
RAW = DATA / "raw"
OUT = DATA / "out"
