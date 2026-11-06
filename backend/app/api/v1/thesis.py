"""
app/api/v1/thesis.py
--------------------
Public, read-only routes for the thesis model E166 (survey-anchored automatic model selection with temperature-shrunk
scores). They only read E166's exported files (backend/data/e166/out); no model runs at request time.

Status served with every response: retrospectively validated (C1-C6 pass at Leads 1-2; 75 % accuracy rule to Lead 4),
adoption pending the adviser's decision. The 2027-Q1 forecast is the prospective test.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.paths import BACKEND_DIR

router = APIRouter()
OUT = BACKEND_DIR / "data" / "e166" / "out"
OBJ = OUT / "objectives"
STATUS = {
    "model": "E166: survey anchor + automatic model selection + temperature-shrunk scores",
    "validation": "retrospective, rolling origin over FNRI ENNS 2018, 2019 and 2021 (72 province rows per lead)",
    "reliability": "passes all six criteria (C1-C6) at Leads 1-2; at or above 75 % accuracy at Leads 1-4",
    "adoption": "pending adviser decision; the sealed 2027-Q1 forecast is the prospective test",
    "disclaimer": "Risk indicator only. Not an official food-insecurity classification and not a replacement for DOST-FNRI or PSA statistics.",
}


def _json(p: Path) -> dict:
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"thesis model output missing: {p.name}")
    return json.loads(p.read_text())


@lru_cache(maxsize=1)
def _lgus() -> list[dict]:
    p = OBJ / "lgu_rankings_2027-Q1.csv"
    if not p.exists():
        raise HTTPException(status_code=503, detail="thesis model output missing: lgu_rankings_2027-Q1.csv")
    d = pd.read_csv(p, dtype={"lgu_code": str})
    return d.round(4).to_dict("records")


@router.get("/thesis/overview")
def overview() -> dict:
    """Status, the reliability table by lead (official E156 criteria) and the maximum reliable lead under both rules."""
    r = _json(OUT / "results.json")
    leads = []
    for x in r["reliability"]["TS"]["leads"]:
        c = x["confusion"]
        leads.append({"lead": x["lead"], "rows": x["rows"], "correct": c["tp"] + c["tn"], "accuracy": x["accuracy"], "precision": x["precision"],
                      "highRecall": x["high_recall"], "lowRecall": x["low_recall"], "f1": x["f1"], "auc": x["auc"], "brier": x["brier_soft"],
                      "calibrationSlope95": x["calibration_slope_ci95"], "criteria": x["criteria"], "reliable": x["reliable"],
                      "meetsPaperRule75": x["accuracy"] >= 0.75})
    paper = 0
    for x in sorted(leads, key=lambda z: z["lead"]):
        if not x["meetsPaperRule75"]:
            break
        paper = x["lead"]
    return {"status": STATUS, "maxReliableLeadStrict": r["reliability"]["TS"]["maximum_reliable_lead"], "maxReliableLeadPaperRule": paper,
            "adoptionRule": r["decision"]["rule"], "leads": leads}


@router.get("/thesis/forecast")
def forecast() -> dict:
    """2027-Q1 province forecasts (Lead 1) with each province's survey-anchor part and top SHAP drivers."""
    f, s = _json(OBJ / "forecast_2027-Q1.json"), _json(OBJ / "shap_results.json")
    drivers = {p["province"]: p for p in s["province_2027Q1"]}
    rows = [{**r, "surveyAnchorPart": drivers.get(r["province"], {}).get("survey_anchor_part"),
             "adjustmentPart": drivers.get(r["province"], {}).get("adjustment_part"),
             "topDrivers": drivers.get(r["province"], {}).get("top_drivers", [])} for r in f["forecasts"]]
    return {"status": STATUS, "issue": f["issue"], "targetQuarter": f["target_quarter"], "lead": f["lead"], "config": f["config"],
            "lambda": f["lam"], "highLine": 50, "provinces": rows}


@router.get("/thesis/lgus")
def lgus(province: str | None = Query(None), limit: int = Query(142, ge=1, le=142)) -> dict:
    """142 LGU priority rankings for 2027-Q1 (paper Algorithm 5: within-province min-max, 0.6 poverty + 0.4 density)."""
    rows = [r for r in _lgus() if province is None or r["province_name"].lower() == province.lower()]
    return {"status": STATUS, "formula": "risk = province P(HIGH) x (0.6 x poverty_norm + 0.4 x density_norm), normalised within province",
            "count": len(rows), "rows": rows[:limit]}


@router.get("/thesis/baselines")
def baselines(lead: int = Query(1, ge=1, le=8)) -> dict:
    """E166 against the six RQ3 baselines (and PSA-only, E158, AUTO), with Brier differences and 95 % intervals."""
    b = _json(OBJ / "baseline_results.json")
    x = b["leads"].get(str(lead))
    if x is None:
        raise HTTPException(status_code=404, detail=f"no baseline results for lead {lead}")
    return {"status": STATUS, "lead": lead, "metrics": x["metrics"], "e166MinusBrier": x["E166_minus_brier"], "beatsRq3": x["E166_beats_rq3"]}


@router.get("/thesis/drivers")
def drivers() -> dict:
    """SHAP drivers of the live model (RQ1) and the H1 result."""
    s = _json(OBJ / "shap_results.json")
    return {"status": STATUS, "groupShare": s["group_share"], "sourceShare": s["source_share"], "top15": s["top15"], "h1": s["H1"],
            "note": s["anchor_note"] + " Importance is not added accuracy: removing news did not change accuracy (E164)."}


@router.get("/thesis/face-validity")
def face_validity() -> dict:
    """Face-validity anchor against DOST-FNRI published figures (SO5)."""
    return {"status": STATUS, **_json(OBJ / "face_validity.json")}
