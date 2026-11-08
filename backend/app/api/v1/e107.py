"""
app/api/v1/e107.py
------------------
Read-only routes for E107 (one LightGBM on the 12 aiPHeed indicators, rolling-origin Leads 1-4; branch
aipheed/e107-twelve-indicator-lightgbm). They serve the files exported by
aipheed-backend-aligned/experiments/E107_Twelve_Indicator_LightGBM/runner/run_e107.py (phase `export`) unchanged.
They do not change any existing route, the served FIRI v2 score or the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "e107"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been exported (run run_e107.py export)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/e107/evaluation")
def e107_evaluation() -> dict:
    """Per target and lead: the reliability decision, the 75% check and the main metrics of every arm."""
    return _read("evaluation_summary.json")


@router.get("/e107/forecast")
def e107_forecast() -> dict:
    """The sealed Lead 1-4 forecasts from origin 2026-Q3 (issue 2026-10-01), with their seal hash and status."""
    return _read("forecast.json")


@router.get("/e107/indicators")
def e107_indicators() -> dict:
    """The 12 indicator families, their sources, availability, transformation, missing-data rule and model columns."""
    return _read("indicators.json")
