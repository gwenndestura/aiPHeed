"""
app/api/v1/report.py
---------------------
GET /api/v1/report?scope=region|province&id=&quarter=
GET /api/v1/report/data?type=trend|shap&scope=&id=&from=&to=&municipality=

/report returns a rendered PDF assessment for CALABARZON or for one province.
/report/data returns the structured content the Visualization page lays out
as its PDF (see app/services/report_data.py).

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

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services import dashboard as svc
from app.services import report as rpt
from app.services import plain_report
from app.services import report_data as rdata
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
    if svc.is_forecast_quarter(q):
        # The report's wording describes the nowcast indicator; the E20
        # forecast is a different target, so it is not rendered under it.
        raise svc.QuarterNotAvailable(
            f"Reports cover nowcast quarters only. The {q} forecast is a different "
            "target and model; see the Forecast Period banner on the dashboard."
        )
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


@router.get("/report/data", dependencies=[Depends(report_guard)])
async def get_report_data(
    type: str = Query(..., pattern="^(trend|shap)$"),
    scope: str = Query("region", pattern="^(region|province)$"),
    id: str | None = Query(None, description="Province id for scope=province"),
    from_: str | None = Query(None, alias="from", description="First quarter (trend)"),
    to: str | None = Query(None, description="Last quarter (trend), or the quarter (shap)"),
    municipality: str | None = Query(None, description="Optional LGU id inside the province"),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Structured content for the Visualization page's PDF reports.

    Returns the plain-language report for DA Region IV-A staff
    (app/services/plain_report.py). Every finding, number and sentence is
    produced here from model output and backend data; the frontend only lays
    it out. The technical payload (report_data.build_report) is kept for other
    uses but no longer feeds these PDFs. Costs a SHAP pass per
    province-quarter, hence the report rate limit. Withheld province-quarters
    are blanked before any text is composed, and the response is never cached
    for the same reason as /report.
    """
    end = to or svc.latest_quarter()
    start = from_ or end
    rejected = await rv.rejected_pairs(db)
    try:
        body = await run_in_threadpool(
            plain_report.build_plain_report, type, scope, id, start, end, rejected, municipality)
    except rdata.ReportRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(body, headers={"Cache-Control": "no-store"})
