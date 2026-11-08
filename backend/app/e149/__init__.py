"""
app.e149
--------
E149: E148's quarterly survey-anchored system with HIGH at 50 % (docs/e149/PROTOCOL.md). E148 is imported and never modified;
outputs go to data/e149 only.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e149-1.0"
PROTOCOL_VERSION = "E149-P1"
DATA = BACKEND_DIR / "data" / "e149"
OUT = DATA / "out"
