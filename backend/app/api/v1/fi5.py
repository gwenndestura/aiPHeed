"""
app/api/v1/fi5.py
-----------------
Read-only routes for the FI5 five-domain food insecurity system (app.fi5, docs/fi5). They serve the files written
by `python -m app.fi5.pipeline all` under data/fi5 and never compute or retrain. FI5 is independent of FIRI v2 and
is not the number painted on the approved dashboard map; every response carries `status` saying what it is.
Errors: 503 when the pipeline has not produced the requested file, 404 for an unknown province.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.fi5 import VERSION
from app.fi5.paths import NLP, OUT
from app.fi5.sources import REGISTRY

router = APIRouter(prefix="/fi5")
STATUS = (f"{VERSION}: SWS Balance Luzon hunger above its five-year average, forecast by LightGBM on five domains "
          "(market, climate, employment, remittances, poverty; news inside each domain); province and LGU figures "
          "are vulnerability-adjusted priorities, not province or municipal measurements")


@lru_cache(maxsize=32)
def _read(path: str, mtime: float):
    p = Path(path)
    return json.loads(p.read_text()) if p.suffix == ".json" else pd.read_csv(p, dtype={"lgu_psgc": str, "province_code": str})


def _load(p: Path):
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"{p.name} not generated yet (run python -m app.fi5.pipeline all)")
    return _read(str(p), p.stat().st_mtime)


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


@router.get("/status")
def status():
    lock = _load(OUT / "METHOD_LOCK.json")
    ver = _load(OUT / "verification.json") if (OUT / "verification.json").exists() else None
    ev = _load(OUT / "evaluation.json")
    return {"status": STATUS, "version": VERSION, "lock_sha256": lock.get("lock_sha256"),
            "code_matches_lock": ev.get("lock", {}).get("code_matches_lock"),
            "max_reliable_lead": ev.get("max_reliable_lead"), "verification": ver}


@router.get("/forecast")
def forecast():
    return {"status": STATUS, **_load(OUT / "forecast.json")}


@router.get("/evaluation")
def evaluation(lead: int | None = Query(None, ge=1, le=4)):
    ev = _load(OUT / "evaluation.json")
    summ = ev["summary"] if lead is None else {str(lead): ev["summary"][str(lead)]}
    return {"status": STATUS, "max_reliable_lead": ev["max_reliable_lead"], "protocol": ev["protocol"],
            "audit": ev["audit"], "summary": summ}


@router.get("/baselines")
def baselines():
    """Consolidated comparison: LightGBM vs the four baselines, every lead, same walk-forward rows."""
    ev = _load(OUT / "evaluation.json")
    keep = ["LightGBM (proposed)", "Naive persistence", "PSA-only (government indicators)",
            "NLP-only (news features)", "Logistic regression", "Climatology (base rate)"]
    rows = []
    for lead, s in ev["summary"].items():
        for name in keep:
            m = s["models"][name]
            rows.append({"lead": int(lead), "model": name, **{k: m.get(k) for k in
                         ["n", "n_high", "n_low", "accuracy", "precision", "recall", "f1", "auc", "brier", "brier_skill", "fpr"]},
                         "vs_proposed": s["vs_proposed"].get(name)})
    return {"status": STATUS, "rows": rows}


@router.get("/provinces")
def provinces():
    return {"status": STATUS, "rows": _records(_load(OUT / "province_priority.csv"))}


@router.get("/lgus")
def lgus(province: str | None = None, limit: int = Query(142, ge=1, le=142)):
    t = _load(OUT / "lgu_rankings.csv")
    if province:
        t = t[t["province_name"].str.lower() == province.lower()]
        if t.empty:
            raise HTTPException(status_code=404, detail=f"unknown province {province}")
    return {"status": STATUS, "n": int(len(t)), "rows": _records(t.head(limit)),
            "sensitivity": _records(_load(OUT / "lgu_weight_sensitivity.csv"))}


@router.get("/nlp/fssi")
def fssi(geo: str | None = None):
    f = _load(NLP / "fssi_province_quarter.csv")
    if geo:
        f = f[f["geo"].str.lower() == geo.lower()]
    return {"status": STATUS, "summary": _load(NLP / "nlp_summary.json"), "rows": _records(f)}


@router.get("/nlp/topics")
def topics():
    return {"status": STATUS, "rows": _records(_load(NLP / "bertopic_topics.csv"))}


@router.get("/features")
def features():
    imp = _load(OUT / "shap_importance_by_block.csv") if (OUT / "shap_importance_by_block.csv").exists() else None
    return {"status": STATUS, "features": [s.__dict__ for s in REGISTRY],
            "shap_by_block": None if imp is None else _records(imp)}
