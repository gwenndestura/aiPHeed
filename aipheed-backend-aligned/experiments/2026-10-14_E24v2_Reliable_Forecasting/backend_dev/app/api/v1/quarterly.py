"""
app/api/v1/quarterly.py
-----------------------
Read-only endpoint for the current forecast period and its status. It serves the SAME forecast record the
dashboard and the PDF report read (app.quarterly.update.load_latest), so the target quarter, supporting-news
window and cutoff are identical everywhere. No database access.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.quarterly.update import load_latest

RECORDS_DIR = Path(os.getenv("AIPHEED_QUARTERLY_RECORDS", "data/quarterly_runs"))
router = APIRouter(prefix="/quarterly", tags=["quarterly"])


@router.get("/forecast-period")
def forecast_period():
    rec = load_latest(RECORDS_DIR)
    if rec is None:
        raise HTTPException(status_code=404, detail="no quarterly forecast record has been generated")
    return {k: rec[k] for k in ("period", "status", "missing", "labels", "supporting_news", "forecast",
                                "content_sha256", "generated_at", "cutoff_reached") if k in rec}
