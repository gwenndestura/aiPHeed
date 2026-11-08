"""
app/api/v1/dashboard.py
------------------------
Catalog endpoints: display config, the timeline, and the geography the map
draws attribute data onto.

GET /api/v1/config
GET /api/v1/quarters
GET /api/v1/provinces
GET /api/v1/ranking
GET /api/v1/provinces/{province_id}/municipalities
GET /api/v1/search
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.public import (
    ConfigResponse,
    MunicipalitiesResponse,
    ProvincesResponse,
    RankingResponse,
    QuartersResponse,
    SearchResponse,
)
from app.services import dashboard as svc
from app.services import reference as ref
from app.services import review as rv
from app.services import search as search_svc

router = APIRouter()

PST = timezone(timedelta(hours=8))

# The frontend type declares four risk bands; the model produces two. Both are
# reported so the unused pair reads as a deliberate gap, not an oversight.
RISK_LEVELS_DEFINED = ["low", "moderate", "high", "severe"]


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """
    Thresholds, active risk bands, what the score means, and both models.

    `horizons` describes the single operational horizon (Rule 2) side by
    side -- what each answers, the quarters it reaches, and its metrics with
    their baselines -- so the UI can offer the choice without hardcoding either.
    """
    # SYSTEM_FIXES item 4: with the Chapter I forecast served, the range is that forecast's own quarters
    quarters = svc.ch1_quarters() if svc._ch1_mode() else svc.available_quarters()
    horizons = {}
    for h in svc.HORIZONS:
        hq = svc.available_quarters(h)
        horizons[h] = {
            **(svc.E31_HORIZON_INFO if svc.e31_active() else svc.HORIZON_INFO)[h],
            "earliest": hq[0] if hq else None,
            "latest": hq[-1] if hq else None,
            "count": len(hq),
            "performance": svc.model_performance(h),
        }
    return ConfigResponse(
        horizons=horizons,
        region=ref.REGION_ID,
        thresholds={
            "riskDisplayCutoff": ref.RISK_DISPLAY_CUTOFF,
            "alertThreshold": ref.ALERT_THRESHOLD,
            "triggerRedCutoff": ref.TRIGGER_RED_CUTOFF,
            "limitedSignalMinArticles": ref.LIMITED_SIGNAL_MIN_ARTICLES,
        },
        riskLevelsActive=ref.ACTIVE_RISK_LEVELS,
        riskLevelsDefined=RISK_LEVELS_DEFINED,
        # E44: the definition of the score served for the dashboard's default (target) quarter
        indicator=svc.indicator_for(svc.forecast_target()["target_quarter"]),
        quarterRange={
            "earliest": quarters[0] if quarters else None,
            "latest": quarters[-1] if quarters else None,
            "count": len(quarters),
            "forecastQuarters": ([q for q in quarters if svc.is_estimate_quarter(q)] if svc._ch1_mode() else
                                 [q for q in svc.available_quarters(svc.NOWCAST)
                                  if svc.E31.quarter_row(q, svc.NOWCAST)["mode"] in ("FORECAST", "NOWCAST")]
                                 if svc.e31_active() else []),
            "forecastTarget": svc.forecast_target(),
            "note": (
                "Backtests are observed quarters. The current quarter and the next calendar quarter (the dashboard's "
                "target) are forecasts issued at the start of the current quarter with information published before "
                "it; neither outcome is known yet."
                if svc.e31_active() else
                "Every scorable quarter is an observed one. The model scores "
                "quarters PSA has already published production volumes for, so "
                "there are no forward forecast quarters to display."
            ),
        },
        modelPerformance=svc.model_performance(),
        servingModel=svc.serving_model(),
    )


@router.get("/quarters", response_model=QuartersResponse)
async def get_quarters(
    horizon: str = Query(svc.DEFAULT_HORIZON, pattern="^(nowcast|forecast)$"),
) -> QuartersResponse:
    """
    The timeline the slider should render.

    `current` is the newest scorable quarter, which trails the calendar by the
    PSA publication lag. `lagQuarters` reports that gap so the UI can say why
    the slider stops where it does instead of looking broken.
    """
    h = svc.check_horizon(horizon)
    target = svc.forecast_target()                    # app/quarterly/target.py: the only clock (Asia/Manila)
    now = datetime.fromisoformat(target["now_ph"])
    calendar_quarter = target["calendar_quarter"]
    current = svc.latest_quarter(h)
    lag = ref.quarter_index(calendar_quarter) - ref.quarter_index(current)
    return QuartersResponse(
        current=current,
        horizon=h,
        serverTime=now.isoformat(),
        calendarQuarter=calendar_quarter,
        lagQuarters=max(lag, 0),
        # the target quarter's forecast exists even when the default view opens on the reliable Lead-1 quarter
        forecastTarget={**target, "available": (target["target_quarter"] in svc.ch1_quarters() if svc._ch1_mode()
                                                else current == target["target_quarter"])},
        quarters=svc.timeline(h),
    )


@router.get("/provinces", response_model=ProvincesResponse)
async def get_provinces(
    quarter: str | None = Query(None, description="Defaults to the latest scorable quarter"),
    horizon: str = Query(svc.DEFAULT_HORIZON, pattern="^(nowcast|forecast)$"),
    db: AsyncSession = Depends(get_db),
) -> ProvincesResponse:
    """
    The five provinces with headline stats, ranked by risk descending.

    A province a reviewer has withheld still appears -- the map needs its
    geography -- but with `withheld: true` and no score.
    """
    h = svc.check_horizon(horizon)
    q = svc.resolve_quarter(quarter, h)
    withheld = frozenset(pid for pid, rq in await rv.rejected_pairs(db, q))
    return ProvincesResponse(
        quarter=q,
        horizon=h,
        indicator=svc.indicator_for(q),
        data=svc.province_summary(q, withheld, h),
    )


@router.get("/ranking", response_model=RankingResponse)
async def get_ranking(
    quarter: str | None = Query(None, description="Defaults to the latest scorable quarter"),
    horizon: str = Query(svc.DEFAULT_HORIZON, pattern="^(nowcast|forecast)$"),
    db: AsyncSession = Depends(get_db),
) -> RankingResponse:
    """
    The published provinces ranked by risk probability, with the SHAP features
    that separate each from the next one down. Withheld provinces are left out.
    """
    h = svc.check_horizon(horizon)
    q = svc.resolve_quarter(quarter, h)
    withheld = frozenset(pid for pid, rq in await rv.rejected_pairs(db, q))
    return RankingResponse(**svc.ranking(q, withheld, h))


@router.get(
    "/provinces/{province_id}/municipalities",
    response_model=MunicipalitiesResponse,
)
async def get_municipalities(
    province_id: str,
    quarter: str | None = Query(None),
) -> MunicipalitiesResponse:
    """
    The province's cities and municipalities, ranked by risk index.

    Each row is the province score reweighted by poverty (60%) and population
    density (40%), not a model run of its own.
    """
    slug = province_id.lower()
    if slug not in ref.PROVINCES:
        raise svc.SubjectNotFound(f"Unknown province id '{province_id}'.")
    q = svc.resolve_quarter(quarter)
    return MunicipalitiesResponse(
        provinceId=slug,
        quarter=q,
        indicator=svc.indicator_for(q),
        data=svc.municipality_summary(q, province_id=slug),
    )


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=100, description="Name of a province, city or municipality"),
    limit: int = Query(search_svc.DEFAULT_LIMIT, ge=1, le=50),
) -> SearchResponse:
    """
    The five provinces and 142 LGUs, ranked: exact, starts with, a word
    starts with, contains, close spelling (accents, "city", "sta"/"sto" and
    punctuation ignored). When nothing matches, the nearest names come back
    flagged `suggestion` (app/services/search.py).
    """
    return SearchResponse(data=search_svc.search(q, limit))
