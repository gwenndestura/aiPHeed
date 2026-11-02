"""
app/api/v1/fi7.py
-----------------
Read-only routes for FI7 (app.fi7, docs/fi7): release-aware next-quarter food insecurity outlook, the experiment
registry, the final comparison against all baselines, and the 142-LGU priority. They serve files written by
`python -m app.fi7.experiments run|final` and `python -m app.fi7.serve issue`; nothing is computed or retrained on a
request. Not wired to the approved dashboard map (that needs the owner's approval). 503 when a file is missing.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.fi7 import VERSION
from app.fi7.paths import OUT

router = APIRouter(prefix="/fi7")
STATUS = (f"{VERSION}: probability that SWS Balance Luzon hunger is significantly above its five-year normal; issued "
          "inside the current quarter after the latest SWS release; h=1 is the next quarter. Province and LGU figures are "
          "vulnerability-adjusted priorities, not measurements. Development evidence; not the dashboard's served model.")


@lru_cache(maxsize=32)
def _read(path: str, mtime: float):
    p = Path(path)
    return json.loads(p.read_text()) if p.suffix == ".json" else pd.read_csv(p, dtype={"lgu_psgc": str, "province_code": str})


def _load(name: str):
    p = OUT / name
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"{name} not generated yet (see docs/fi7/FINAL_REPORT.md)")
    return _read(str(p), p.stat().st_mtime)


def _records(df):
    return json.loads(df.to_json(orient="records"))


@router.get("/forecast")
def forecast():
    return {"status": STATUS, **_load("forecast.json")}


@router.get("/evaluation")
def evaluation(h: int | None = Query(None, ge=0, le=3)):
    ev = _load("final_evaluation.json")
    by = ev["by_lead"] if h is None else {str(h): ev["by_lead"][str(h)]}
    return {"status": STATUS, "furthest_reliable_lead": ev["furthest_reliable_lead"], "by_lead": by}


@router.get("/experiments")
def experiments():
    return {"status": STATUS, "registry": _records(_load("experiment_registry.csv")), "lock": _load("EXPERIMENT_LOCK.json")["lock_sha256"]}


@router.get("/lgus")
def lgus(province: str | None = None, limit: int = Query(142, ge=1, le=142)):
    t = _load("lgu_rankings.csv")
    if province:
        t = t[t["province_name"].str.lower() == province.lower()]
        if t.empty:
            raise HTTPException(status_code=404, detail=f"unknown province {province}")
    return {"status": STATUS, "n": int(len(t)), "rows": _records(t.head(limit)), "sensitivity": _records(_load("lgu_weight_sensitivity.csv"))}


@router.get("/provinces")
def provinces():
    return {"status": STATUS, "rows": _records(_load("province_priority.csv"))}
