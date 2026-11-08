"""
app.e145
--------
E145: first test of province-level news against measured provincial food insecurity (HFIAS), for every province the
FNRI rounds measured, not only CALABARZON. Protocol docs/e145/PROTOCOL.md. E137-E144 are imported, never modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e145-1.0"
PROTOCOL_VERSION = "E145-P1"
DATA = BACKEND_DIR / "data" / "e145"
RAW = DATA / "raw"
OUT = DATA / "out"
