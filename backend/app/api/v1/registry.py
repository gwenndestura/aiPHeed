"""
app/api/v1/registry.py
----------------------
Release-gated routes.

public_router (no auth, /api/v1/final/...)
    GET /final/model-registry          statuses of registered models and the production pointer (no forecasts)
    GET /final/food-insecurity/outlook only the registry's approved production model; status validation_pending otherwise

admin_router (admin auth, /api/v1/admin/candidates/...)
    Candidate outputs for review. They never appear on public routes or the dashboard.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from app import registry as R
from app.services.security import require_admin

public_router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])

# Serving functions per approved model id; a model without an entry here cannot be served even if approved.
PRODUCTION_SERVERS = {"pfi-1.0": ("app.pfi.serve", "outlook"), "e139-lgbm-1.0": ("app.e139.serve", "outlook")}
CANDIDATES = {"pfi-1.0": "app.pfi.serve", "e139-lgbm-1.0": "app.e139.serve"}


@public_router.get("/final/model-registry")
def model_registry() -> dict:
    return R.summary()


@public_router.get("/final/food-insecurity/outlook")
def approved_outlook() -> dict:
    """The official food-insecurity forecast. Only the registry's approved production model is served; until one exists
    the answer is `validation_pending` with no forecast values (never a candidate's numbers)."""
    try:
        p = R.production()
    except R.NoApprovedModel as exc:
        return _pending(str(exc))
    if p["model_id"] not in PRODUCTION_SERVERS:
        return _pending(f"no server registered for the approved model {p['model_id']}")
    import importlib
    mod, fn = PRODUCTION_SERVERS[p["model_id"]]
    out = getattr(importlib.import_module(mod), fn)()
    return {"status": "approved", **out, "production": p}


def _pending(reason: str) -> dict:
    reg = R.summary()
    return {"status": "validation_pending", "forecast": None, "reason": reason,
            "message": ("No food-insecurity forecasting model has passed all acceptance tests yet, so no official "
                        "food-insecurity forecast is shown. Indicators on this dashboard are context, not forecasts."),
            "candidates": [{k: m[k] for k in ("model_id", "status", "failed_checks")} for m in reg["models"]
                           if m["status"] != "legacy_incumbent"],
            "acceptance_checks_total": 16}


def _candidate(model_id: str):
    if model_id not in CANDIDATES:
        raise HTTPException(status_code=404, detail=f"unknown candidate {model_id}")
    import importlib
    return importlib.import_module(CANDIDATES[model_id])


@admin_router.get("/candidates/{model_id}/gate")
def candidate_gate(model_id: str) -> dict:
    p = R.DIR / "gate_results" / f"{model_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="gate not evaluated")
    return json.loads(p.read_text())


@admin_router.get("/candidates/{model_id}/{view}")
def candidate_view(model_id: str, view: str) -> dict:
    """Candidate output for internal review only (outlook, evaluation, model, lgus, register). Labelled as unapproved."""
    m = _candidate(model_id)
    fns = {"outlook": "outlook", "evaluation": "evaluation", "model": "model_card", "lgus": "lgus", "register": "register"}
    if view not in fns:
        raise HTTPException(status_code=404, detail=f"unknown view {view}")
    from app.e139 import serve as E139S
    from app.pfi import engine as PE
    try:
        out = getattr(m, fns[view])()
    except (PE.ArtifactMissing, E139S.ArtifactMissing) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    status = (R.load()["models"].get(model_id) or {}).get("status", "unregistered")
    return {"CANDIDATE_NOT_APPROVED": status != "approved", "registry_status": status, **out}
