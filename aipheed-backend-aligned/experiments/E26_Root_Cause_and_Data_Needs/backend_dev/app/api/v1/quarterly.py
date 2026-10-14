"""
app/api/v1/quarterly.py
-----------------------
Read-only endpoint for the current forecast period and its status. It serves the SAME forecast record the
dashboard and the PDF report read (app.quarterly.update.load_latest), so the target quarter, supporting-news
window and cutoff are identical everywhere. No database access.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.quarterly.update import load_latest

RECORDS_DIR = Path(os.getenv("AIPHEED_QUARTERLY_RECORDS", "data/quarterly_runs"))
E25_RECORD = Path(os.getenv("AIPHEED_E25_RECORD", "data/e25/e25_forecast_record.json"))
router = APIRouter(prefix="/quarterly", tags=["quarterly"])


@router.get("/e25-timeline")
def e25_timeline():
    """E25 timeline record (2025-Q1..2027-Q1): the SAME bytes the dashboard and the PDF read. The record's content
    SHA-256 is recomputed; a mismatch is an integrity failure (500), never served as data."""
    if not E25_RECORD.exists():
        raise HTTPException(status_code=404, detail="no E25 forecast record has been generated")
    rec = json.loads(E25_RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    got = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    if got != rec.get("content_sha256"):
        raise HTTPException(status_code=500, detail="E25 forecast record failed its integrity check")
    return rec


@router.get("/forecast-period")
def forecast_period():
    rec = load_latest(RECORDS_DIR)
    if rec is None:
        raise HTTPException(status_code=404, detail="no quarterly forecast record has been generated")
    return {k: rec[k] for k in ("period", "status", "missing", "labels", "supporting_news", "forecast",
                                "content_sha256", "generated_at", "cutoff_reached") if k in rec}
