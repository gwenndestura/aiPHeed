"""
app/api/v1/e108.py
------------------
Read-only routes for E108 (factored forecast: regional hunger outlook x a provincial price-pressure LightGBM on the 12
aiPHeed indicators; branch aiPHeed/e108-best-defensible-forecasting). They serve the files exported by
aipheed-backend-aligned/experiments/E108_Best_Defensible_Forecasting/runner/run_e108.py (phase `export`) unchanged.
They do not change any existing route, the served FIRI v2 score or the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "e108"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been exported (run run_e108.py export)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/e108/evaluation")
def e108_evaluation() -> dict:
    """Per target and lead: the reliability decision, the 75% check and the main metrics of every arm."""
    return _read("evaluation_summary.json")


@router.get("/e108/forecast")
def e108_forecast() -> dict:
    """The sealed Lead 1-4 forecasts from origin 2026-Q3 (issue 2026-10-01), with their seal hash and status."""
    return _read("forecast.json")


@router.get("/e108/indicators")
def e108_indicators() -> dict:
    """The 12 indicator families, their sources, availability, transformation, missing-data rule and model columns."""
    return _read("indicators.json")
