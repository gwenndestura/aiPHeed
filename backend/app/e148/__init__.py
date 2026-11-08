"""
app.e148
--------
E148: mixed-frequency, survey-anchored quarterly forecast of provincial food insecurity (docs/e148/PROTOCOL.md).
Measured surveys train and anchor it; quarterly inputs drive it every quarter. E147 and its seal are preserved.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e148-1.0"
PROTOCOL_VERSION = "E148-P1"
DATA = BACKEND_DIR / "data" / "e148"
OUT = DATA / "out"
