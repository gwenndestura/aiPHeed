"""
app/api/v1/e113.py
------------------
Read-only routes for E113 (final hunger forecast model; branch
aiPHeed/e113-final-model). They serve the files exported by
aipheed-backend-aligned/experiments/E113_Final_Model/runner/run_e113.py (phase `export`) unchanged.
They do not change any existing route, the served FIRI v2 score or the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "e113"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been exported (run run_e113.py export)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/e113/evaluation")
def e113_evaluation() -> dict:
    """Adopted forecast, selection tier, per-lead MASE and 80% coverage of every model (4-area panel)."""
    return _read("evaluation_summary.json")


@router.get("/e113/forecast")
def e113_forecast() -> dict:
    """Sealed hunger forecasts from origin 2026-Q3: seal A (issue 2026-10-01) and seal B (2026-10-25), with hashes."""
    return _read("forecast.json")
