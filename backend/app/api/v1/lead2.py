"""
app/api/v1/lead2.py
-------------------
E41 Lead-2 two-layer candidate, served only when AIPHEED_LEAD2_MODEL=e41. Responses keep observed evidence, the
forecast probability (price pressure, not food insecurity) and the operational band apart. A record whose target is not
the dashboard's current forecast target is refused (409) instead of being shown as current.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.ml.inference import e41_lead2 as E41
from app.services import reference as ref

router = APIRouter()


def _record() -> dict:
    if not E41.active():
        raise HTTPException(status_code=404, detail="The E41 Lead-2 candidate is not enabled. The served model is "
                                                    "E38; set AIPHEED_LEAD2_MODEL=e41 to serve the candidate.")
    try:
        rec = E41.record()
    except E41.RecordError as e:
        raise HTTPException(status_code=503, detail=str(e))
    from app.quarterly.target import forecast_target

    target = forecast_target()["target_quarter"]
    if rec["targetQuarter"] != target:
        raise HTTPException(status_code=409, detail=f"The E41 forecast is for {rec['targetQuarter']}, but the current "
                                                    f"forecast target is {target}. No forecast exists for {target} yet; "
                                                    f"the older forecast is not shown as current.")
    return rec


@router.get("/lead2/summary")
def lead2_summary():
    rec = _record()
    return {k: rec[k] for k in ("name", "status", "origin", "targetQuarter", "lead", "information", "scoreTypes",
                                "operationalRules", "evaluation", "limitations", "content_sha256")} | {
        "provinces": [{"id": ref.province_slug(c), "provinceCode": c, "name": v["name"],
                       "probabilityAbove4pct": v["forecast"]["probabilityAbove4pct"], "band": v["forecast"]["band"],
                       "foodInflationPoint": v["forecast"]["foodInflationPoint"],
                       "interval80": v["forecast"]["interval80"], "alertCandidate": v["operational"]["alertCandidate"],
                       "e40Probability": v["exploratory"]["e40Probability"]}
                      for c, v in sorted(rec["provinces"].items(),
                                         key=lambda kv: -kv[1]["forecast"]["probabilityAbove4pct"])]}


@router.get("/lead2/provinces/{province_id}")
def lead2_province(province_id: str):
    rec = _record()
    code = ref.province_code(province_id) or province_id
    if code not in rec["provinces"]:
        raise HTTPException(status_code=404, detail=f"unknown province '{province_id}'")
    return {"targetQuarter": rec["targetQuarter"], "origin": rec["origin"], "scoreTypes": rec["scoreTypes"],
            "operationalRules": rec["operationalRules"], **rec["provinces"][code]}
