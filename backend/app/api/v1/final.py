"""
app/api/v1/final.py
-------------------
Read-only routes for the final forecasting engine (app.services.final_engine). They add to, and do not change, the
existing dashboard routes or the served FIRI v2 priority score.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services import dashboard as D
from app.services import final_engine as FE
from app.services.security import require_admin

router = APIRouter()
# Release gate: hunger forecasts of the research engine (LightGBM and latest-reading outlooks, their evaluation, SHAP
# shares and archive) have not passed app.registry's gate, so they need an admin login; measured data stay public.
ADMIN = [Depends(require_admin)]
UNAPPROVED_OVERVIEW_KEYS = ("outlook",)


def _guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except FE.EngineMissing as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/final/overview")
def final_overview() -> dict:
    """Latest measured SWS hunger observation (dates, age), CPI and data freshness. The research engine's hunger
    forecasts are not public (release gate): they are in /api/v1/admin/... and /final/evaluation (admin)."""
    out = {k: v for k, v in _guard(FE.overview).items() if k not in UNAPPROVED_OVERVIEW_KEYS}
    from app import registry as R
    try:
        p = R.production()
        fi = (f"food-insecurity forecast: {p['model_id']} approved by the owner-defined acceptance "
              f"(/api/v1/final/food-insecurity/outlook); ")
    except R.NoApprovedModel:
        fi = "food-insecurity forecast: validation pending; "
    out["forecastStatus"] = fi + ("SWS hunger forecast: validation pending, not public "
                                  "(see /api/v1/final/model-registry)")
    return out


@router.get("/final/evaluation", dependencies=ADMIN)
def final_evaluation() -> dict:
    """Walk-forward metrics of the LightGBM by lead against baselines, the 75% verdict and the reliable-lead result."""
    return _guard(FE.evaluation)


@router.get("/final/families")
def final_families() -> dict:
    """The 12 indicator families, each model column, its missingness and the five driver groups."""
    return _guard(FE.families)


@router.get("/final/contributions", dependencies=ADMIN)
def final_contributions() -> dict:
    """SHAP share of each driver group in the LightGBM hunger forecasts."""
    return _guard(FE.contributions)


@router.get("/final/archive", dependencies=ADMIN)
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


# ------------------------------------------------------------------------------------------------ Chapter I risk
@router.get("/final/risk/evaluation")
def final_risk_evaluation() -> dict:
    """Walk-forward evaluation of the Chapter I province risk forecast (UNI-FINAL, one LightGBM across leads): per-lead metrics, baselines,
    reliability verdicts, Objective-4 comparisons, news tests and calibration."""
    from app.ml.inference import ch1_system as CH1
    if not CH1.active():
        raise HTTPException(status_code=503, detail="Chapter I risk engine not exported (run export_ch1.py)")
    return CH1.evaluation()


@router.get("/final/risk/rows")
def final_risk_rows(kind: str | None = Query(None, pattern="^(forecast|retrospective)$"),
                    quarter: str | None = Query(None, pattern=r"^\d{4}-Q[1-4]$")) -> dict:
    """Province rows: walk-forward Lead-1 forecasts with observed outcomes, and the forecasts issued 2026-10-01."""
    from app.ml.inference import ch1_system as CH1
    if not CH1.active():
        raise HTTPException(status_code=503, detail="Chapter I risk engine not exported (run export_ch1.py)")
    rows = [dict(r, kind=CH1.kind(r), reliable_horizon=CH1.status(r) == "reliable", status=CH1.status(r))
            for r in CH1.rows().values()
            if (kind is None or CH1.kind(r) == kind) and (quarter is None or r["quarter"] == quarter)]
    return {"count": len(rows), "maxReliableLead": CH1.reliable_lead(), "horizon": CH1.horizon(), "rows": rows,
            "definition": CH1.indicator()["definition"], "caveat": CH1.INDICATOR["caveat"]}
