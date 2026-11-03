"""aiPHeed FI12: provincial outcome validation against the owner-supplied workbook (2026-11-03).

Outcomes: FNRI 2015 HFIAS (direct, provincial), ENNS 2018/2019/2021 (direct, secondary source, one year per province),
PSA subsistence incidence 2018/2021/2023 (food poverty). SWS Balance Luzon stays regional (FI9) and is never copied to
provinces; food-price pressure (FI10) is a predictor or a separate target. Read-only with respect to production:
writes data/fi12 and docs/fi12 only.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi12-1.0"
FI12 = BACKEND_DIR / "data" / "fi12"
OUT = FI12 / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi12"
PROVINCES = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
CODE = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal", "PH040500000": "Batangas"}
for _d in (FI12, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
