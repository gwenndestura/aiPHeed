"""
app/api/v1/demo.py
------------------
E178 Part A scenario / demo mode (docs/e178/PROTOCOL.md). Read-only; administrator login required (the view-only demo
account included), mounted with the research-only dependency in app/api/router.py.

It serves ONLY the synthetic scenario files in data/e178/synthetic/ (python -m app.e178.scenarios run). It never reads or
changes the approved E168 forecast, and no real endpoint reads these files. Every response is labelled
SYNTHETIC – FOR DEMONSTRATION and carries "synthetic": true.

    GET /api/v1/demo/scenarios                  index: label, scenario list, the production issue it starts from
    GET /api/v1/demo/scenarios/{scenario_id}    one scenario (S0, S1, S2, S3, S4, S5)
"""
from __future__ import annotations

import functools
import json

from fastapi import APIRouter, HTTPException

from app.e178.common import LABEL, SYN

router = APIRouter(prefix="/demo")
SUMMARY = SYN / "scenarios_summary.json"
ORDER = ["S0", "S1", "S2", "S3", "S4", "S5"]
NOTICE = ("Synthetic scenario inputs run through the frozen E168 procedure to show how the system responds. These are "
          "not forecasts, not validation evidence and not part of the public outlook.")


@functools.lru_cache(maxsize=2)
def _load(mtime: int) -> dict:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def _summary() -> dict:
    if not SUMMARY.exists():
        raise HTTPException(status_code=404, detail="Scenario data has not been generated (python -m app.e178.scenarios run).")
    return _load(SUMMARY.stat().st_mtime_ns)


@router.get("/scenarios")
def scenarios() -> dict:
    d = _summary()
    titles = d["titles"]
    return {"synthetic": True, "label": LABEL, "notice": NOTICE,
            "production": d["meta"]["production"], "firstHigh": d["meta"]["s3_first_high"], "s3bUsed": d["meta"]["s3b_used"],
            "scenarios": [{"id": s, "title": titles[s]} for s in ORDER if s in d["scenarios"]]}


@router.get("/scenarios/{scenario_id}")
def scenario(scenario_id: str) -> dict:
    d = _summary()
    sid = scenario_id.upper()
    if sid not in d["scenarios"] or sid not in ORDER:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario_id}'. Use one of {ORDER}.")
    meta = {k: d["meta"][k] for k in ("groups", "shocks", "unsigned_columns", "s3_first_high", "s3b_used", "production")}
    return {"synthetic": True, "label": LABEL, "notice": NOTICE, "id": sid, "title": d["titles"][sid], "meta": meta,
            "data": d["scenarios"][sid]}
