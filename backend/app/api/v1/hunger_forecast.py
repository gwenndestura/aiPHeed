"""
app/api/v1/hunger_forecast.py
-----------------------------
Read-only routes for the numerical SWS hunger forecast (app.forecasting; backend completion 2026-11). They serve the
write-once stored forecasts (data/forecasting/forecasts) and never compute or retrain. /hunger-forecast/v2/* is the
approved v2 path (docs/aipheed/v2, data/forecasting/forecasts_v2); the routes without /v2 keep serving the legacy
SEAS-LLM candidate. Neither is the number on the dashboard map (P0H4 price-pressure risk index,
app.ml.inference.ch1_system); every response says so. Errors: 404 when no forecast is stored for the requested
issue, 422 for an invalid request, 503 when no forecast or artifact is available at all.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.forecasting import explain as X
from app.forecasting import geography as G
from app.forecasting import store as S
from app.forecasting.evidence import AREAS
from app.forecasting.v2 import explain as X2
from app.forecasting.v2 import store as V2S

router = APIRouter()
CONTEXT = Path(__file__).resolve().parents[3] / "data" / "forecasting" / "context"
STATUS = ("legacy prospective candidate (E134 Addendum 2 SEAS-LLM), superseded by the approved v2 path "
          "/api/v1/hunger-forecast/v2; not the dashboard's served model; no lead has passed the frozen reliability rules N1-N7")
V2_STATUS = ("approved v2 forecasting path (docs/aipheed/v2): pre-registered nested selection chose persistence; every "
             "number is an SWS area value; development evidence only, no lead has passed the frozen rules N1-N7")


def _body(issue: date | None) -> dict:
    if not S.STORE.exists() or not any(S.STORE.glob("*.json")):
        raise HTTPException(status_code=503, detail="no hunger forecast has been generated (run app.forecasting.store)")
    b = S.latest(issue)
    if b is None:
        raise HTTPException(status_code=404, detail=f"no stored hunger forecast for issue date {issue}")
    return b


def _issue(issue_date: str | None) -> date | None:
    if issue_date is None:
        return None
    try:
        d = date.fromisoformat(issue_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="issue_date must be YYYY-MM-DD")
    if d.day != 1 or d.month not in (1, 4, 7, 10):
        raise HTTPException(status_code=422, detail="issue_date must be the first day of a quarter")
    return d


@router.get("/hunger-forecast")
def hunger_forecast(issue_date: str | None = Query(None, description="quarter-start issue date; default latest")) -> dict:
    """Numerical SWS hunger forecasts (Leads 1-4, 4 SWS areas) with interval, provenance and status."""
    b = _body(_issue(issue_date))
    return {"status": STATUS, "key": b["key"], "records": b["records"]}


@router.get("/hunger-forecast/explanation")
def hunger_forecast_explanation(lead: int = Query(2, ge=1, le=4),
                                area: Literal["metro_manila", "balance_luzon", "visayas", "mindanao"] = "balance_luzon",
                                issue_date: str | None = None) -> dict:
    """Exact additive explanation of one forecast; trigger groups listed as context, not contributions."""
    b = _body(_issue(issue_date))
    rec = [r for r in b["records"] if r["lead"] == lead and r["area"] == area]
    if len(rec) != 1:
        raise HTTPException(status_code=404, detail=f"no record for lead {lead}, area {area}")
    return {"status": STATUS, "record": rec[0], "explanation": X.explain(rec[0])}


@router.get("/hunger-forecast/geography")
def hunger_forecast_geography(lead: int = Query(2, ge=1, le=4), issue_date: str | None = None) -> dict:
    """All 5 provinces and 142 LGUs with explicit evidence status (Balance Luzon value as a broader-area reference)."""
    b = _body(_issue(issue_date))
    return {"status": STATUS, **G.geography_view(b["records"], lead)}


# ------------------------------------------------------------------ v2 (approved path, docs/aipheed/v2)
def _v2_body(issue: date | None) -> dict:
    if not V2S.STORE.exists() or not any(V2S.STORE.glob("*.json")):
        raise HTTPException(status_code=503, detail="no v2 hunger forecast has been generated (run app.forecasting.v2.store)")
    b = V2S.latest(issue)
    if b is None:
        raise HTTPException(status_code=404, detail=f"no stored v2 hunger forecast for issue date {issue}")
    return b


def _context(issue: str, area: str) -> dict | None:
    p = CONTEXT / f"context_{issue}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))["areas"].get(area)


@router.get("/hunger-forecast/v2")
def hunger_forecast_v2(issue_date: str | None = Query(None, description="quarter-start issue date; default latest")) -> dict:
    """v2 numerical SWS hunger forecasts (Leads 1-4, 4 SWS areas) with conformal interval, provenance and status."""
    b = _v2_body(_issue(issue_date))
    return {"status": V2_STATUS, "key": b["key"], "records": b["records"]}


@router.get("/hunger-forecast/v2/explanation")
def hunger_forecast_v2_explanation(lead: int = Query(2, ge=1, le=4),
                                   area: Literal["metro_manila", "balance_luzon", "visayas", "mindanao"] = "balance_luzon",
                                   issue_date: str | None = None) -> dict:
    """Exact additive decomposition of one v2 forecast; the five trigger groups as point-in-time context."""
    b = _v2_body(_issue(issue_date))
    rec = [r for r in b["records"] if r["lead"] == lead and r["area"] == area]
    if len(rec) != 1:
        raise HTTPException(status_code=404, detail=f"no record for lead {lead}, area {area}")
    return {"status": V2_STATUS, "record": rec[0], "explanation": X2.explain(rec[0], _context(rec[0]["issue_date"], area))}


@router.get("/hunger-forecast/v2/geography")
def hunger_forecast_v2_geography(lead: int = Query(2, ge=1, le=4), issue_date: str | None = None) -> dict:
    """All 5 provinces and 142 LGUs with explicit status (Balance Luzon value as a broader-area reference)."""
    b = _v2_body(_issue(issue_date))
    return {"status": V2_STATUS, **G.geography_view(b["records"], lead)}


assert set(AREAS) == {"metro_manila", "balance_luzon", "visayas", "mindanao"}
