"""
app/api/v1/forecast.py
-----------------------
The score behind the gauge, the HIGH/LOW pill, the map colouring and the
trend chart.

GET /api/v1/forecast?scope=&id=&quarter=
GET /api/v1/forecast/timeseries?scope=&id=&from=&to=

Asking for a quarter the model cannot score returns 404 forecast_not_found
rather than a zero. A grey province reads as "no forecast published"; a 0.00
reads as "no risk", and those are opposite claims.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.public import ForecastResponse, TimeseriesResponse
from app.services import dashboard as svc
from app.services import reference as ref
from app.services import review as rv

router = APIRouter()

SCOPES = ("region", "province", "municipality")


async def _withheld_for(db: AsyncSession, quarter: str) -> frozenset[str]:
    """Province slugs an admin has withheld for this quarter."""
    return frozenset(pid for pid, q in await rv.rejected_pairs(db, quarter))


async def _confirmed_alert(db: AsyncSession, scope: str, subject_id: str, quarter: str, body: dict) -> bool:
    """True when a DA administrator has confirmed an alert for this area and quarter (E34, D3). The region view uses
    the regional alert; a province its own; a municipality its province's."""
    from app.db.repository.alert_repo import AlertRepository
    from app.quarterly.alerts_e31 import REGION_CODE

    if scope == "region":
        code = REGION_CODE
    elif scope == "province":
        code = ref.province_code(subject_id.lower())
    else:
        code = ref.province_code(body.get("provinceId") or "")
    if code is None:
        return False
    return any(a.quarter == quarter and a.province_code == code and not a.dismissed
               for a in await AlertRepository(db).get_confirmed())


def _quarter_label(quarter: str) -> str:
    year, qn = ref.quarter_parts(quarter)
    return f"Q{qn} {year} ({ref.QUARTER_MONTHS[qn]})"


def _subject_name(scope: str, subject_id: str) -> str:
    if scope == "region":
        return ref.REGION_NAME
    if scope == "province":
        name = ref.province_name(subject_id)
        if name is None:
            raise svc.SubjectNotFound(f"Unknown province id '{subject_id}'.")
        return name
    row = ref.municipality_row(subject_id)
    if row is None:
        raise svc.SubjectNotFound(f"Unknown municipality id '{subject_id}'.")
    return row["lgu_name"]


def _score_for(
    scope: str,
    subject_id: str,
    quarter: str,
    withheld: frozenset[str] = frozenset(),
    horizon: str = svc.DEFAULT_HORIZON,
) -> dict:
    """
    One subject's score for one quarter, in the shape the gauge needs.

    A withheld province -- or a municipality inside one -- raises rather than
    returning a number, so the score cannot reach the client through a caller
    that forgot to cross-check the rejection list.
    """
    if scope == "region":
        region = svc.region_forecast(quarter, withheld, horizon)
        return {
            "riskScore": region["riskScore"],
            "riskLevel": region["riskLevel"],
            "qoqChange": region["qoqChange"],
            "limitedSignal": region["limitedSignal"],
            "provinceCounts": region["provinceCounts"],
            "provincesIncluded": region["provincesIncluded"],
            "horizon": horizon,
            "derivation": region["derivation"],
        }

    if scope == "province":
        slug = subject_id.lower()
        if slug in withheld:
            raise svc.ForecastWithheld(
                f"The {quarter} forecast for this province has been withheld from "
                "publication by a reviewer."
            )
        match = [p for p in svc.province_summary(quarter, horizon=horizon) if p["id"] == slug]
        if not match:
            raise svc.SubjectNotFound(f"Unknown province id '{subject_id}'.")
        p = match[0]
        return {
            "riskScore": p["riskScore"],
            "riskLevel": p["riskLevel"],
            "qoqChange": p["qoqChange"],
            "limitedSignal": p["limitedSignal"],
            "riskLabel": p["riskLabel"],
            "forecastHorizonQuarters": p["forecastHorizonQuarters"],
            "horizonLabel": p["horizonLabel"],
            "confidenceStatement": p["confidenceStatement"],
            "verificationDate": p["verificationDate"],
            "horizon": horizon,
        }

    m = svc.municipality_forecast(subject_id, quarter)
    if m["provinceId"] in withheld:
        raise svc.ForecastWithheld(
            f"The {quarter} forecast for {m['name']} is derived from its province, "
            "which a reviewer has withheld from publication."
        )
    return {
        "riskScore": m["riskIndex"],
        "riskLevel": m["riskLevel"],
        "qoqChange": None,
        "limitedSignal": m["limitedSignal"],
        "provinceId": m["provinceId"],
        "disaggregationLabel": m["disaggregationLabel"],
    }


@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    scope: str = Query("region", pattern="^(region|province|municipality)$"),
    id: str = Query("calabarzon", description="calabarzon | quezon | quezon-infanta"),
    quarter: str | None = Query(None, description="Defaults to the latest scorable quarter"),
    horizon: str = Query(svc.DEFAULT_HORIZON, pattern="^(nowcast|forecast)$",
                         description=("One operational horizon (Rule 2). Both ids "
                                      "resolve to the same model; no forward lead "
                                      "time has been validated (E27), so the output "
                                      "is an experimental same-quarter estimate.")),
    db: AsyncSession = Depends(get_db),
) -> ForecastResponse:
    """
    The single most-used endpoint: one subject's score for one quarter.

    Rule 2 fixes a single operational horizon, so `nowcast` is an accepted
    alias of `forecast` and both resolve to the same model, published at the
    Maximum Reliable Lead Time discovered by Algorithm 3.
    """
    h = svc.check_horizon(horizon)
    q = svc.resolve_quarter(quarter, h)
    body = _score_for(scope, id, q, await _withheld_for(db, q), h)
    return ForecastResponse(
        scope=scope,
        id=id.lower(),
        name=_subject_name(scope, id),
        quarter=q,
        quarterLabel=_quarter_label(q),
        indicator=svc.indicator_for(q),
        # E34: true for a quarter whose outcome is not yet known (E31 nowcast/forecast); backtests are false.
        isForecast=svc.is_estimate_quarter(q),
        isCurrent=(q == svc.latest_quarter(h)),
        # E34 (D3): only an alert a DA administrator has CONFIRMED is public; never a score threshold alone.
        alert=await _confirmed_alert(db, scope, id, q, body),
        **body,
    )


@router.get("/forecast/timeseries", response_model=TimeseriesResponse)
async def get_timeseries(
    scope: str = Query("province", pattern="^(region|province|municipality)$"),
    id: str = Query(..., description="calabarzon | quezon | quezon-infanta"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    horizon: str = Query(svc.DEFAULT_HORIZON, pattern="^(nowcast|forecast)$"),
    db: AsyncSession = Depends(get_db),
) -> TimeseriesResponse:
    """
    A score per quarter over a range, for the trend chart.

    A municipality series is the parent province's series under a fixed
    poverty/density weight, so its shape matches the province exactly. It is
    served because the chart offers the choice, not because the model resolves
    municipalities independently.
    """
    h = svc.check_horizon(horizon)
    quarters = svc.available_quarters(h)
    start = from_ or (quarters[0] if quarters else None)
    end = to or (quarters[-1] if quarters else None)
    lo, hi = ref.quarter_index(start), ref.quarter_index(end)
    window = [q for q in quarters if lo <= ref.quarter_index(q) <= hi]

    # Withheld quarters drop out of the line rather than plotting a gap at
    # zero, which would read as a real fall to no risk.
    rejected = await rv.rejected_pairs(db)

    series = []
    for q in window:
        withheld = frozenset(pid for pid, rq in rejected if rq == q)
        try:
            body = _score_for(scope, id, q, withheld, h)
        except svc.SubjectNotFound:
            raise  # bad id: every quarter would fail, so say so once
        except svc.ForecastWithheld:
            continue
        except Exception:  # a quarter the subject has no rows for
            continue
        if body["riskScore"] is None:
            continue
        series.append({
            "quarter": q,
            "riskScore": body["riskScore"],
            "riskLevel": body["riskLevel"],
            "isForecast": svc.is_estimate_quarter(q),
            # E42: a series can mix score types when the Lead-2 candidate is enabled; each point says which it is
            "scoreType": svc.indicator_for(q)["id"],
        })

    # E46: with a Lead-2 candidate enabled, a line must not join two different scores (the v1 label probability of
    # past quarters, about 0.9, and the candidate's probability of its own target event, about 0.2). Past quarters
    # then come from the candidate's own as-of backtest, and points of any other score type are left out.
    target = svc.forecast_target()["target_quarter"]
    if svc.E41L2.serves(target):
        cand = svc.indicator_for(target)["id"]
        code = None if scope == "region" else ref.province_code(id.lower().split("-")[0])
        bt = svc.E41L2.backtest_series(code)
        series = [p for p in series if p["scoreType"] == cand] + [
            {"quarter": q, "riskScore": round(v, 4), "riskLevel": ref.risk_level(v), "isForecast": False,
             "scoreType": cand}
            for q, v in bt.items() if lo <= ref.quarter_index(q) <= hi]
        series.sort(key=lambda p: ref.quarter_index(p["quarter"]))
        indicator = svc.indicator_for(target)
    else:
        indicator = svc.INDICATOR

    return TimeseriesResponse(
        scope=scope,
        id=id.lower(),
        name=_subject_name(scope, id),
        indicator=indicator,
        series=series,
    )
