"""aiPHeed FI11: one unified five-trigger food-insecurity model, trigger-combination study A-H, Leads 1-4.

The outcome is the only repeatedly measured food-insecurity series: SWS involuntary hunger, Balance Luzon (regional).
No provincial food-insecurity label exists, so FI11 is regional; provincial outputs remain FI10 (measured price
pressure, labelled as such). Writes data/fi11 and docs/fi11; production FI9 changes only on an 'adopt' decision.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi11-1.0"
FI11 = BACKEND_DIR / "data" / "fi11"
OUT = FI11 / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi11"
for _d in (FI11, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
