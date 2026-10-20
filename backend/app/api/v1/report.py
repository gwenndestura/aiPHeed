"""
app/api/v1/report.py
---------------------
GET /api/v1/report?scope=region|province&id=&quarter=

Returns a rendered PDF assessment for CALABARZON or for one province.

Public, like the dashboard it summarises -- and subject to the same review
gate: a province a reviewer has withheld returns 404 forecast_withheld rather
than a document, and a withheld province is excluded from the regional
assessment's average.

There is no municipality scope. Municipal values reweight the province figure
rather than resolving independently, so a per-LGU document would restate its
province's findings under a heading implying separate evidence. LGUs appear as
a ranked table inside the province report.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services import dashboard as svc
from app.services import report as rpt
from app.services import reference as ref
from app.services import review as rv
from app.services.ratelimit import report_guard

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/report",
    responses={200: {"content": {"application/pdf": {}},
                     "description": "The rendered assessment"}},
    response_class=Response,
    dependencies=[Depends(report_guard)],
)
async def get_report(
    scope: str = Query("region", pattern="^(region|province)$"),
    id: str = Query("calabarzon", description="calabarzon | quezon | batangas | ..."),
    quarter: str | None = Query(None, description="Defaults to the latest scorable quarter"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Render the assessment as a PDF download.

    Generation costs a SHAP pass per province, so the regional report is the
    slower of the two. It is not cached: the review state it reflects can
    change between requests, and serving a stale copy could republish a figure
    an admin has just withheld.
    """
    q = svc.resolve_quarter(quarter)
    withheld = frozenset(pid for pid, rq in await rv.rejected_pairs(db, q))

    if scope == "region":
        pdf = rpt.build_region_report(q, withheld)
    else:
        pdf = rpt.build_province_report(id, q, withheld)

    name = rpt.filename(scope, id, q)
    logger.info("report: %s %s %s -> %d bytes", scope, id, q, len(pdf))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            # The review state behind it can change at any time.
            "Cache-Control": "no-store",
        },
    )


@router.get("/report/data")
async def get_report_data(
    type: str = Query("trend", pattern="^(trend|shap)$"),
    scope: str = Query("region", pattern="^(region|province)$"),
    id: str | None = Query(None),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
    municipality: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """E31: the Visualization page's report payload, built from the E31 record (same numbers as the map)."""
    from fastapi import HTTPException

    from app.ml.inference import thesis_system as THESIS
    from app.quarterly import preview as PV
    from app.services import report_data_e31 as R

    if not svc.e31_active():
        raise HTTPException(status_code=404, detail="report data is served from the E31 record only")
    # Thesis p. 60: a report never shows a withheld (rejected) forecast
    slugs = [id.lower()] if scope == "province" and id else list(ref.PROVINCES)
    quarters = [to] if type == "shap" and to else R._window(from_, to)
    held = await rv.rejected_pairs(db)
    if any((s, q) in held for s in slugs for q in quarters if R._row(q) is not None):
        raise svc.ForecastWithheld("This report includes a forecast that is withheld from publication "
                                   "(rejected by a DA administrator).")
    try:
        if type == "trend":
            out = R.trend(scope, id, from_, to)
        else:
            if not id or not to:
                raise HTTPException(status_code=422, detail="a driver report needs a province id and a quarter (to)")
            out = R.drivers(id, to)
        # lead-2 preview on (the default): a report that ends on the preview quarter says so (optional fields). In
        # thesis mode the quarter carries FIRI v2, not the record's lead-2 model, so the record's note does not apply.
        last = (out.get("metadata") and dict(out["metadata"]).get("Data", "")[:7].replace(" ", "-")) or None
        return {**out, **({} if THESIS.active() else PV.fields(last))}
    except KeyError as ex:
        raise HTTPException(status_code=404, detail=str(ex))
