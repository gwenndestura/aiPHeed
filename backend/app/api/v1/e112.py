"""
app/api/v1/e112.py
------------------
Read-only routes for E112 (food-insecurity forecasting with issue-date news indicators; branch
aiPHeed/e112-food-insecurity-forecasting). They serve the files exported by
aipheed-backend-aligned/experiments/E112_Food_Insecurity_Forecasting/runner/run_e112.py (phase `export`) unchanged.
They do not change any existing route, the served FIRI v2 score or the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "e112"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been exported (run run_e112.py export)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/e112/evaluation")
def e112_evaluation() -> dict:
    """The final method, per-lead reliability status, news tests and Balance Luzon MAE of every candidate."""
    return _read("evaluation_summary.json")


@router.get("/e112/forecast")
def e112_forecast() -> dict:
    """The sealed regional hunger forecasts from origin 2026-Q3 (issue 2026-10-01), with their seal hash."""
    return _read("forecast.json")


@router.get("/e112/news-indicators")
def e112_news_indicators() -> dict:
    """Quarterly news volume, category shares and year-over-year changes (de-duplicated project corpus)."""
    return _read("news_indicators.json")
