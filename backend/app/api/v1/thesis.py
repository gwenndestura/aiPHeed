"""
app/api/v1/thesis.py
--------------------
Public, read-only routes for the thesis model: E168 (E166 method, learner fixed to LightGBM) since the owner decision of
2026-11-06; E166 when AIPHEED_THESIS_MODEL=e166. They only read the model's exported files (backend/data/<model>/out);
no model runs at request time. Response shapes are unchanged from the E166 version of these routes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.paths import BACKEND_DIR
from app.services import e166_serving as SRV

router = APIRouter()
RQ3 = ("PERS", "LR", "LR_GOV", "LR_NEWS", "GOV", "NEWS")
HIGHER = ("accuracy", "precision", "f1", "auc")
E168 = SRV.MODEL != "e166"


def _out() -> Path:
    return BACKEND_DIR / "data" / SRV.MODEL / "out"


def _json(p: Path) -> dict:
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"thesis model output missing: {p.name}")
    return json.loads(p.read_text())


def _status() -> dict:
    return {"model": SRV.INDICATOR["name"], "method": SRV.METHOD,
            "validation": "retrospective, rolling origin over DOST-FNRI ENNS 2018, 2019 and 2021 (72 province rows per lead)",
            "reliability": SRV.STATUS,
            "adoption": "owner decision 2026-11-06 (E168); pending adviser decision; the sealed 2027-Q1 forecast is the prospective test",
            "disclaimer": "Risk indicator only. Not an official food-insecurity classification and not a replacement for DOST-FNRI or PSA statistics."}


def _results() -> dict:
    return _json(_out() / "results.json")


def _reliability() -> dict:
    r = _results()
    return r["reliability"] if E168 else r["reliability"]["TS"]


@router.get("/thesis/overview")
def overview() -> dict:
    """Status, the reliability table by lead (official E156 criteria) and the maximum reliable lead under both rules."""
    r, rel = _results(), _reliability()
    leads = []
    for x in rel["leads"]:
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
    return {"status": _status(), "maxReliableLeadStrict": rel["maximum_reliable_lead"], "maxReliableLeadPaperRule": paper,
            "adoptionRule": r["decision"].get("rule", r["decision"]), "leads": leads}


def _live() -> dict:
    return _json(SRV.HIST / f"{SRV.LIVE}.json")


@router.get("/thesis/forecast")
def forecast() -> dict:
    """2027-Q1 province forecasts (Lead 1) with each province's five risk-driver contributions."""
    f = _live()
    rows = []
    for r in f["forecasts"]:
        d = SRV.drivers(SRV.ref.province_code(r["province"].lower()), SRV.LIVE)
        top = sorted(d["drivers"], key=lambda x: -abs(x["group_shap"]))
        rows.append({**r, "topDrivers": [{"group": x["driver_label"], "contribution": x["group_shap"]} for x in top],
                     "otherSharePct": d["other_pct"]})
    return {"status": _status(), "issue": f["issue_date"], "targetQuarter": f["target_quarter"], "lead": f["lead"], "config": f["config"],
            "lambda": f["lam"], "highLine": 50, "provinces": rows}


@router.get("/thesis/lgus")
def lgus(province: str | None = Query(None), limit: int = Query(142, ge=1, le=142)) -> dict:
    """142 LGU priority rankings for 2027-Q1 (paper Algorithm 5: within-province min-max, 0.6 poverty + 0.4 density)."""
    d = pd.DataFrame(_live()["lgus"]).round(4)
    rows = [r for r in d.to_dict("records") if province is None or r["province_name"].lower() == province.lower()]
    return {"status": _status(), "formula": SRV.RANKING_METHOD, "count": len(rows), "rows": rows[:limit]}


@router.get("/thesis/baselines")
def baselines(lead: int = Query(1, ge=1, le=8)) -> dict:
    """The thesis model against the six RQ3 baselines (and PSA-only, earlier models), with Brier differences and 95 % intervals."""
    if not E168:
        x = _json(_out() / "objectives" / "baseline_results.json")["leads"].get(str(lead))
        if x is None:
            raise HTTPException(status_code=404, detail=f"no baseline results for lead {lead}")
        return {"status": _status(), "lead": lead, "metrics": x["metrics"], "e166MinusBrier": x["E166_minus_brier"], "beatsRq3": x["E166_beats_rq3"]}
    if lead != 1:
        raise HTTPException(status_code=404, detail="E168 baseline comparison is reported at Lead 1 (the reliable lead)")
    r = _results()
    me = next(x for x in r["reliability"]["leads"] if x["lead"] == 1)
    own = {"correct": me["confusion"]["tp"] + me["confusion"]["tn"], **{k: me[k] for k in ("accuracy", "precision", "high_recall", "low_recall", "f1", "auc")},
           "brier": me["brier_soft"]}
    metrics = {"E168": own, **{k: v["metrics"] for k, v in r["lead1_vs"].items()}}
    beats = {b: {**{k: own[k] > metrics[b][k] for k in HIGHER}, "brier": own["brier"] < metrics[b]["brier"]} for b in RQ3 if b in metrics}
    return {"status": _status(), "lead": 1, "metrics": metrics,
            "e168MinusBrier": {k: v["E168_minus_brier"] for k, v in r["lead1_vs"].items()}, "beatsRq3": beats}


@router.get("/thesis/drivers")
def drivers() -> dict:
    """SHAP drivers of the live model (RQ1) and the H1 result."""
    s = _json(_out() / "objectives" / "shap_results.json")
    if not E168:
        return {"status": _status(), "groupShare": s["group_share"], "sourceShare": s["source_share"], "top15": s["top15"], "h1": s["H1"],
                "note": s["anchor_note"] + " Importance is not added accuracy: removing news did not change accuracy (E164)."}
    return {"status": _status(), "groupShare": s["five_driver_share"], "otherShareOfTotal": s["other_share_of_total"],
            "sourceShare": s["source_share"], "top15": s["top15"], "h1": s["H1"], "note": s["note"]}


@router.get("/thesis/face-validity")
def face_validity() -> dict:
    """Face-validity anchor against DOST-FNRI published figures (SO5)."""
    return {"status": _status(), **_json(_out() / "objectives" / "face_validity.json")}
