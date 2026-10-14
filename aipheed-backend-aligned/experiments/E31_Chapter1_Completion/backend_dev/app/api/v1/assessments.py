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


@router.get("/assessments/quarters")
def assessment_quarters() -> list[dict]:
    return svc.quarters()


@router.get("/assessments/methodology")
def assessment_methodology() -> dict:
    return svc.methodology()


@router.get("/assessments")
def province_assessments(quarter: str = Query(..., pattern=r"^\d{4}-Q[1-4]$")) -> dict:
    try:
        return svc.assessments(quarter)
    except svc.AssessmentQuarterNotFound:
        raise HTTPException(status_code=404, detail=f"no revised assessment for {quarter}")
