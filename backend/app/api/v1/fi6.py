"""
app/api/v1/fi6.py
-----------------
Read-only routes for FI6 (app.fi6, docs/fi6): the uncertainty-aware food insecurity target, LightGBM change model,
baselines, LGU priority and the NLP validation kit. They serve files written by `python -m app.fi6.pipeline all`
and never compute or retrain. FI6 is not wired to the approved dashboard map. Errors: 503 when a file has not been
generated, 404 for an unknown province.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.fi6 import VERSION
from app.fi6.paths import OUT, VALIDATION

router = APIRouter(prefix="/fi6")
STATUS = (f"{VERSION}: probability that SWS Balance Luzon hunger is significantly above its five-year normal (beyond the "
          "survey margin of error); province and LGU figures are vulnerability-adjusted priorities, not measurements; "
          "development evidence, not connected to the dashboard map")
SHOWN = ["LightGBM (proposed)", "Naive persistence", "PSA-only (government indicators)", "NLP-only (news composites)",
         "Logistic regression", "Climatology (base rate)", "LightGBM without news (government + latest reading)"]


@lru_cache(maxsize=32)
def _read(path: str, mtime: float):
    p = Path(path)
    return json.loads(p.read_text()) if p.suffix == ".json" else pd.read_csv(p, dtype={"lgu_psgc": str, "province_code": str})


def _load(p: Path):
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"{p.name} not generated yet (run python -m app.fi6.pipeline all)")
    return _read(str(p), p.stat().st_mtime)


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))


@router.get("/status")
def status():
    ev, lock = _load(OUT / "evaluation.json"), _load(OUT / "METHOD_LOCK.json")
    ver = _load(OUT / "verification.json") if (OUT / "verification.json").exists() else None
    return {"status": STATUS, "version": VERSION, "lock_sha256": lock["lock_sha256"],
            "code_matches_lock": ev.get("lock", {}).get("code_matches_lock"), "max_reliable_lead": ev["max_reliable_lead"],
            "verification": ver}


@router.get("/target")
def target():
    lock = _load(OUT / "METHOD_LOCK.json")
    return {"status": STATUS, "definition": lock["target"], "candidates_compared": lock["target_choice_basis"]}


@router.get("/forecast")
def forecast():
    return {"status": STATUS, **_load(OUT / "forecast.json")}


@router.get("/evaluation")
def evaluation(lead: int | None = Query(None, ge=1, le=4)):
    ev = _load(OUT / "evaluation.json")
    s = ev["summary"] if lead is None else {str(lead): ev["summary"][str(lead)]}
    return {"status": STATUS, "max_reliable_lead": ev["max_reliable_lead"], "protocol": ev["protocol"], "audit": ev["audit"], "summary": s}


@router.get("/baselines")
def baselines():
    ev = _load(OUT / "evaluation.json")
    rows = []
    for lead, s in ev["summary"].items():
        for name in SHOWN:
            m = s["models"][name]
            rows.append({"lead": int(lead), "model": name, **{k: m.get(k) for k in [
                "n", "n_high", "accuracy", "balanced_accuracy", "precision", "recall", "f1", "auc", "brier", "brier_skill", "fpr", "fnr"]},
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


@router.get("/nlp/validation")
def nlp_validation():
    res = VALIDATION / "validation_result.json"
    return {"status": STATUS, "result": _load(res) if res.exists() else {"status": "kit generated; not yet annotated"},
            "kit": [p.name for p in sorted(VALIDATION.glob("*"))]}


# ---- FI6-N: source-consistent news archive (app.fi6.news_archive / news_events / news_model) -------------------------
NEWS_OUT = OUT.parent / "out_news"
NEWS_DIR = OUT.parent / "news_archive"


@router.get("/news/evaluation")
def news_evaluation():
    """Controlled comparisons: government only vs news only vs government + news vs minus each news domain."""
    return {"status": STATUS, **_load(NEWS_OUT / "news_evaluation.json")}


@router.get("/news/forecast")
def news_forecast():
    return {"status": STATUS, **_load(NEWS_OUT / "forecast_news.json")}


@router.get("/news/audit")
def news_audit():
    """Archive coverage, date, geography and label audit, plus the quarterly news features."""
    return {"status": STATUS, "audit": _load(NEWS_DIR / "audit.json"),
            "quarterly_features": _records(_load(NEWS_DIR / "news_features_quarterly.csv"))}


@router.get("/news/provinces")
def news_provinces(province: str | None = None):
    """Objective 1: per province-quarter risk-event share (bias-corrected by shrinkage toward the region)."""
    t = _load(NEWS_DIR / "fssi_archive_province_quarter.csv")
    if province:
        t = t[t["province"].str.lower() == province.lower()]
    return {"status": STATUS, "rows": _records(t)}
