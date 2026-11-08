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
        raise HTTPException(status_code=404, detail="The Lead-2 candidate is not enabled. The served model is E38; set "
                                                    "AIPHEED_LEAD2_MODEL=e41, e42 or e43 to serve the candidate.")
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


def _timing() -> dict:
    """E44: the temporal convention, stated on every Lead-2 response (dashboard rule = Lead 2 from the latest
    completed quarter; app/quarterly/target.py)."""
    from app.quarterly.target import forecast_target

    ft = forecast_target()
    return {"originQuarter": ft["latest_complete_data_quarter"], "currentQuarter": ft["calendar_quarter"],
            "targetQuarter": ft["target_quarter"], "leadFromOrigin": ft["lead_from_latest_data_quarter"],
            "issuedAt": ft["origin"],
            "convention": "Nowcast = current quarter; Lead 1 = one quarter after the latest completed quarter; "
                          "Lead 2 = two quarters after it. The dashboard shows the quarter after the current calendar "
                          "quarter, which is Lead 2 from the latest completed quarter."}


@router.get("/lead2/summary")
def lead2_summary():
    rec = _record()
    return {"timing": _timing()} | {k: rec[k] for k in ("name", "status", "origin", "targetQuarter", "lead", "information", "scoreTypes",
                                "operationalRules", "limitations", "content_sha256")} | {
        k: rec[k] for k in ("evaluation", "assessment", "indicator", "dataFreshness", "modelFamily", "modelVersion",
                            "finalModelArtifacts") if k in rec} | {
        "provinces": [{"id": ref.province_slug(c), "provinceCode": c, "name": v["name"],
                       "probability": E41.probability(v), "scoreType": v["forecast"]["scoreType"],
                       "probabilityAbove4pct": v["forecast"].get("probabilityAbove4pct"), "band": v["forecast"]["band"],
                       "foodInflationPoint": v["forecast"].get("foodInflationPoint"),
                       "interval80": v["forecast"].get("interval80"), "alertCandidate": v["operational"]["alertCandidate"],
                       "e40Probability": (v.get("exploratory") or {}).get("e40Probability"),
                       # E42 record only (absent for E41)
                       "variantRange": v["forecast"].get("variantRange"),
                       "signalCount": (v.get("signalCount") or {}).get("value")}
                      for c, v in sorted(rec["provinces"].items(),
                                         key=lambda kv: -E41.probability(kv[1]))]}


@router.get("/lead2/provinces/{province_id}")
def lead2_province(province_id: str):
    rec = _record()
    code = ref.province_code(province_id) or province_id
    if code not in rec["provinces"]:
        raise HTTPException(status_code=404, detail=f"unknown province '{province_id}'")
    return {"timing": _timing(), "targetQuarter": rec["targetQuarter"], "origin": rec["origin"],
            "scoreTypes": rec["scoreTypes"],
            "operationalRules": rec["operationalRules"], **rec["provinces"][code]}
