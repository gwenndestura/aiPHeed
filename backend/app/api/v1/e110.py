"""
app/api/v1/e110.py
------------------
Read-only routes for E110 (SWS hunger forecasts for Balance Luzon and the 4-area generalization panel; branch
aiPHeed/e110-hunger-generalization). They serve the files exported by
aipheed-backend-aligned/experiments/E110_Hunger_Generalization/runner/run_e110.py (phase `export`) unchanged.
They do not change any existing route, the served FIRI v2 score or the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "e110"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been exported (run run_e110.py export)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/e110/evaluation")
def e110_evaluation() -> dict:
    """Per lead: the reliability status and MAE of every method (Balance Luzon and the 4-area panel)."""
    return _read("evaluation_summary.json")


@router.get("/e110/forecast")
def e110_forecast() -> dict:
    """The sealed regional hunger forecasts from origin 2026-Q3 (issue 2026-10-01), with their seal hash."""
    return _read("forecast.json")
