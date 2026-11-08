"""
app.e147
--------
E147: food-insecure households on FNRI's published public-health scale, tested on the 2021 ENNS HFIAS round that no earlier
model has seen. Labels come from DOST-FNRI's public Hunger and Malnutrition Heat Map. Protocol docs/e147/PROTOCOL.md.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e147-1.0"
PROTOCOL_VERSION = "E147-P1"
DATA = BACKEND_DIR / "data" / "e147"
RAW = DATA / "raw"
OUT = DATA / "out"
