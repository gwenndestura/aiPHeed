"""aiPHeed FI10: province-level forecasting for Cavite, Laguna, Batangas, Rizal and Quezon.

No repeated provincial food-insecurity outcome exists (docs/fi9z/CALABARZON_FORECASTING_FEASIBILITY_REPORT.md), so FI10
forecasts what IS measured per province every quarter, and labels it for what it is:
  * DIRECT provincial forecast: provincial food-price pressure (PSA provincial food CPI, monthly, 1994+), Leads 1-4;
  * PROXY provincial outlook: that forecast shown beside the provincial vulnerability (validated against FNRI 2015)
    and the regional hunger outlook (Balance Luzon), never merged into an invented food-insecurity score.
Writes data/fi10 and docs/fi10; production FI9 is not modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi10-1.0"
FI10 = BACKEND_DIR / "data" / "fi10"
RAW = FI10 / "raw"
OUT = FI10 / "out"
DOCS = BACKEND_DIR.parent / "docs" / "fi10"
PROVINCES = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
for _d in (FI10, RAW, OUT, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
