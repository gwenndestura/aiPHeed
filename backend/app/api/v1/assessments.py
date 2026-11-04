"""
Revised province assessments (isolated development backend).

    GET /api/v1/assessments/quarters      quarters available, with HIGH / LOW / INSUFFICIENT_DATA counts
    GET /api/v1/assessments?quarter=Q     province assessments for one quarter
    GET /api/v1/assessments/methodology   classification rule, target, model, limitations
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services import assessment as svc

router = APIRouter()


def _unavailable(exc: FileNotFoundError) -> HTTPException:
    """The revised-assessment files are not part of every build: say so instead of failing with a 500."""
    return HTTPException(status_code=503, detail=f"revised assessments are not available: {exc.filename} is missing")


@router.get("/assessments/quarters")
def assessment_quarters() -> list[dict]:
    try:
        return svc.quarters()
    except FileNotFoundError as exc:
        raise _unavailable(exc) from exc


@router.get("/assessments/methodology")
def assessment_methodology() -> dict:
    try:
        return svc.methodology()
    except FileNotFoundError as exc:
        raise _unavailable(exc) from exc


@router.get("/assessments")
def province_assessments(quarter: str = Query(..., pattern=r"^\d{4}-Q[1-4]$")) -> dict:
    try:
        return svc.assessments(quarter)
    except svc.AssessmentQuarterNotFound:
        raise HTTPException(status_code=404, detail=f"no revised assessment for {quarter}")
    except FileNotFoundError as exc:
        raise _unavailable(exc) from exc
