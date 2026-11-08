"""
app.e144
--------
E144: label-borrowing, news-fed LightGBM forecasting of provincial food-insecurity risk (protocol E144-P1,
docs/e144/PROTOCOL.md; methodology docs/research/AIPHEED_METHODOLOGY_LABEL_SCARCE_FORECASTING.md).

Stage A0/A learn from SWS involuntary hunger in the four SWS areas (quarterly, 2010+, owner approval 2026-11-04) with
area-specific GDELT news; Stage B is E143 C4 (provincial HFIAS relative risk); Stage C links area hunger to provincial
HFIAS on the measured survey rounds. E137-E143 are imported, never modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e144-1.0"
PROTOCOL_VERSION = "E144-P2"
DATA = BACKEND_DIR / "data" / "e144"
OUT = DATA / "out"
RAW = DATA / "raw"
