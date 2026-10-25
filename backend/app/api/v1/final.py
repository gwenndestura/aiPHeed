"""
app/api/v1/final.py
-------------------
Read-only routes for the final forecasting engine (app.services.final_engine). They add to, and do not change, the
existing dashboard routes or the served FIRI v2 priority score.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services import dashboard as D
from app.services import final_engine as FE

router = APIRouter()


def _guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except FE.EngineMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/final/overview")
def final_overview() -> dict:
    """Latest SWS hunger observation (dates, age), latest-reading outlook, LightGBM research forecast, CPI, freshness."""
    return _guard(FE.overview)


@router.get("/final/evaluation")
def final_evaluation() -> dict:
    """Walk-forward metrics of the LightGBM by lead against baselines, the 75% verdict and the reliable-lead result."""
    return _guard(FE.evaluation)


@router.get("/final/families")
def final_families() -> dict:
    """The 12 indicator families, each model column, its missingness and the five driver groups."""
    return _guard(FE.families)


@router.get("/final/contributions")
def final_contributions() -> dict:
    """SHAP share of each driver group in the LightGBM hunger forecasts."""
    return _guard(FE.contributions)


@router.get("/final/archive")
def final_archive(kind: str | None = Query(None, pattern="^(retrospective|prospective)$"),
                  area: str | None = Query(None, pattern="^(NCR|BL|VIS|MIN)$")) -> dict:
    """Retrospective predictions with outcomes and sealed prospective forecasts (never overwritten)."""
    return _guard(FE.archive, kind, area)


@router.get("/final/news")
def final_news(limit: int = Query(100, ge=1, le=1000), category: str | None = None,
               kind: str | None = Query(None, pattern="^(future|reported)$"),
               before: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    """De-duplicated food-event headlines; `before` keeps only articles published before that date."""
    return _guard(FE.news, limit, category, kind, before)


@router.get("/final/cpi")
def final_cpi() -> dict:
    """Province food-price squeeze (food CPI YoY minus all-items YoY): economic access, not hunger."""
    return _guard(FE.cpi)


@router.get("/final/lgus")
def final_lgus() -> dict:
    """All 142 cities and municipalities with their indicator-based priority score and local-evidence status."""
    q = D.latest_quarter()
    return _guard(FE.lgus, D.municipality_summary(q))
