"""
app/api/v1/e109.py
------------------
Read-only routes for E109 (forecasting SWS Balance Luzon experienced hunger, a regional outcome; branch
aiPHeed/e109-hunger-forecasting). They serve the files exported by
aipheed-backend-aligned/experiments/E109_Hunger_Forecasting/runner/run_e109.py (phase `export`) unchanged.
They do not change any existing route, the served FIRI v2 score or the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "e109"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been exported (run run_e109.py export)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/e109/evaluation")
def e109_evaluation() -> dict:
    """Per lead: the reliability status and MAE of every method for SWS Balance Luzon hunger."""
    return _read("evaluation_summary.json")


@router.get("/e109/forecast")
def e109_forecast() -> dict:
    """The sealed Lead 1-4 regional hunger forecasts from origin 2026-Q3 (issue 2026-10-01), with their seal hash."""
    return _read("forecast.json")


@router.get("/e109/lgu-status")
def e109_lgu_status() -> dict:
    """Every one of the 142 LGUs with its status (insufficient local evidence) and PSA SAE poverty context."""
    return _read("lgu_status.json")
