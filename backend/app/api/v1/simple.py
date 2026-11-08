"""
app/api/v1/simple.py
--------------------
Read-only routes for the simple methodology (branch aipheed/simple-methodology). They serve the files written by
scripts/run_simple_method.py unchanged, so what an API client sees is exactly what the pipeline produced. They do not
change any existing route or the served dashboard score.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
DATA = Path(__file__).resolve().parents[3] / "data" / "simple_method"


def _read(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} has not been generated (run scripts/run_simple_method.py)")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/simple/forecast")
def simple_forecast() -> dict:
    """The current forecast record: Lead 1 and Lead 2 per province, the recommended arm, explanations and LGU ranks."""
    return _read("record.json")


@router.get("/simple/evaluation")
def simple_evaluation() -> dict:
    """The rolling-origin evaluation of every arm at Leads 1-3 on identical rows."""
    return _read("evaluation.json")
