"""
app.e146
--------
E146: quarterly survey-anchored forecast of provincial food insecurity (docs/e146/PROTOCOL.md). Area movement from SWS,
lasting provincial position from E143 C4, province shocks learned on real survey rows. E137-E145 are imported, not modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e146-1.0"
PROTOCOL_VERSION = "E146-P1"
DATA = BACKEND_DIR / "data" / "e146"
RAW = DATA / "raw"
OUT = DATA / "out"
