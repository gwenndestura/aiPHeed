"""
app/api/v1/fi10.py
------------------
Read-only routes for FI10 (app.fi10, docs/fi10): provincial food-price pressure outlooks for Cavite, Laguna, Batangas,
Rizal and Quezon (Leads 1-2, provisional), with provincial poverty, priority and the regional hunger reference.
Files are written by `python -m app.fi10.serve issue`; nothing is trained on a request. A forecast issued in an earlier
quarter is never returned as current (503 stale).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.fi9 import quarters as Q
from app.fi10 import OUT
from app.fi10.serve import today

router = APIRouter(prefix="/fi10")
REISSUE = "python -m app.fi10.serve issue"


@lru_cache(maxsize=8)
def _read(path: str, mtime: float):
    return json.loads(Path(path).read_text())


def _load(name: str):
    p = OUT / name
    if not p.exists():
        raise HTTPException(status_code=503, detail=f"{name} not generated yet (see docs/fi10)")
    return _read(str(p), p.stat().st_mtime)


@router.get("/provinces")
def provinces():
    f = _load("forecast.json")
    now = Q.lead1(today())
    if f["issue_quarter"] != now["issue_quarter"]:
        raise HTTPException(status_code=503, detail={"status": "stale", "reason": f"issued in {f['issue_quarter']}; current quarter is "
                                                                                   f"{now['current_quarter']}", "reissue": REISSUE})
    return f


@router.get("/evaluation")
def evaluation():
    e = _load("evaluation.json")
    keep = lambda lead: {c: {"test": v["test"], "dev_balanced_accuracy": v["dev"]["balanced_accuracy"],
                             "test_by_province": {p: {k: m[k] for k in ("balanced_accuracy", "tp", "n_high", "fp", "n_low")} for p, m in v["test_by_province"].items()}}
                         for c, v in e["by_lead"][lead].items() if not c.startswith("Ablation")}
    return {"selection": e["selection"], "max_reliable_lead": e["max_reliable_lead"], "best_lead": e["best_lead_by_test_balanced_accuracy"],
            "by_lead": {lead: keep(lead) for lead in e["by_lead"]}}
