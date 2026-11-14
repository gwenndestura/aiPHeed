"""
Real-time forecasting period, forecast history and forecast-versus-actual (served model: FINAL). Public reads; the scheduled run
and outcome entry are protected.

  GET  /api/v1/forecast-period       the Philippine quarter now, the served issue, its forecast quarters (validated leads only),
                                     generation time, latest data update, freshness (stale + reason), next issue date
  GET  /api/v1/final/forecast-history every issued forecast, never overwritten, with its status (historical / current issue) and
                                     validation status (validated / awaiting outcome); filters: province, issue, target
  GET  /api/v1/forecast-evaluation   forecast versus observed outcome, overall / by lead / by province / by target quarter
  GET  /api/v1/data-sources          each official source, its real publication rhythm and the last update
  POST /api/v1/internal/forecast-cycle   scheduled run (Authorization: Bearer $AIPHEED_CRON_TOKEN); does nothing unless due
  POST /api/v1/admin/forecast-outcomes   record an observed FNRI provincial result (admin login; source file hash required)
"""
from __future__ import annotations

import hmac
import os
import threading

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app.final import cycle as CY
from app.final import history as HI
from app.final import period as PD
from app.final import sources as SR
from app.services.security import forbid_demo_writes, require_admin

router = APIRouter()
_RUNNING = threading.Lock()


def _latest_data_update() -> str | None:
    t = [s["last_success_utc"] for s in SR.status() if s.get("last_success_utc")]
    return max(t) if t else None


@router.get("/forecast-period")
def forecast_period() -> dict:
    try:
        from app.final import serving as SVG
        SVG.refresh()
    except Exception:                                            # noqa: BLE001 - the period itself never depends on serving
        pass
    st = CY.status()
    served = st["served_issue_quarter"]
    served_targets = []
    if served:
        for x in PD.targets(served):
            served_targets.append({**x, "status": PD.status_of(x["quarter"], st["current_quarter"])})
    return {**st, "served_targets": served_targets, "latest_data_update_utc": _latest_data_update(),
            "model": {"id": st["model_id"], "name": PD.serving().get("model_name"), "approved_on": PD.serving().get("approved_on"),
                      "lead_basis": PD.serving().get("lead_basis"), "caveat": PD.serving().get("caveat")}}


@router.get("/final/forecast-history")
def forecast_history(province: str | None = Query(None), issue: str | None = Query(None), target: str | None = Query(None)) -> dict:
    per = PD.period()
    served = HI.latest_issue(per["model_id"])
    rows = HI.with_outcomes(per["model_id"])
    out = []
    risks: dict = {}
    for r in rows:
        if province and r["province"].lower() != province.lower():
            continue
        if issue and r["issue_quarter"] != issue:
            continue
        if target and r["target_quarter"] != target:
            continue
        out.append({**r, "risk_pct": _risk_pct(r, risks), "issue_status": ("current issue" if r["issue_quarter"] == served else
                                          "superseded" if r.get("record_status") == "superseded" else "historical"),
                    "issue_label": PD.issue_label(r["issue_quarter"]), "issue_date": PD.issue_datetime(r["issue_quarter"]).isoformat(),
                    "target_status": PD.status_of(r["target_quarter"], per["current_quarter"])})
    # newest issue first by its issue DATE (as text "2026-Q4" would sort after the later "2026-11"), then target and province
    out.sort(key=lambda r: r["province"])                                      # stable: provinces A-Z within an issue and target
    out.sort(key=lambda r: (r["issue_date"], r["target_quarter"]), reverse=True)
    ids = HI.issues(per["model_id"])
    sup = HI.supersessions(per["model_id"])
    return {"current_quarter": per["current_quarter"], "served_issue_quarter": served, "issues": ids,
            "issues_newest_first": list(reversed(ids)),
            "count": len(out), "forecasts": out, "ledger": HI.verify(),
            # recorded disclosures per issue (e.g. figures published after the cut-off), never a rewrite of the issue itself
            "issue_notes": {q: {"note": PD.issue_note(q), "published_by": PD.published_by(q)}
                            for q in ids if PD.issue_note(q)},
            "superseded": {q: {"superseded_by": r["superseded_by"], "superseded_by_label": PD.issue_label(r["superseded_by"]),
                               "reason": r["reason"], "by": r["by"], "evidence": r["evidence"], "recorded_utc": r["recorded_utc"]}
                           for q, r in sup.items()}}


def _risk_pct(r: dict, cache: dict) -> float | None:
    """Food insecurity risk (%) of a ledger record (app.final.risk): exact from its issue's mu and sd when the issue folder is
    present, else from the stored level and 90% range (same value to rounding)."""
    from app.final import risk as RK
    from app.final import serving as SVG
    from app.paths import BACKEND_DIR
    d = BACKEND_DIR / str(r.get("issue_dir") or "")
    if r.get("issue_dir") and (d / "shap_live_summary.csv").exists():
        if d not in cache:
            cache[d] = SVG.issue_risks(d)
        v = cache[d].get((r["province"], r["target_quarter"]))
        if v is not None:
            return round(100 * v, 1)
    rng = r.get("range90_pct") or [None, None]
    if r.get("share_pct") is None or None in rng:
        return None
    return round(100 * RK.risk_from_record(float(r["share_pct"]), float(rng[0]), float(rng[1])), 1)


@router.get("/forecast-evaluation")
def forecast_evaluation() -> dict:
    return HI.evaluation(PD.serving()["model_id"])


@router.get("/data-sources")
def data_sources() -> dict:
    return {"sources": SR.status(), "latest_update_utc": _latest_data_update()}


def _check_token(authorization: str | None) -> None:
    want = os.getenv("AIPHEED_CRON_TOKEN", "")
    got = (authorization or "").removeprefix("Bearer ").strip()
    if len(want) < 24 or not hmac.compare_digest(want, got):
        raise HTTPException(status_code=401, detail="invalid or missing scheduler token")


def _run_once():
    if not _RUNNING.acquire(blocking=False):
        return
    try:
        out = CY.run()
        from app.final import serving as SVG
        if out.get("status") == "issued" and SVG.is_production():
            SVG.activate()
        try:
            from app.final import dbsync
            dbsync.sync()
        except Exception:                                        # noqa: BLE001 - the files stay the record of truth
            pass
    finally:
        _RUNNING.release()


@router.post("/internal/forecast-cycle", status_code=202)
def trigger_cycle(background: BackgroundTasks, authorization: str | None = Header(None)) -> dict:
    _check_token(authorization)
    background.add_task(_run_once)
    return {"accepted": True, "period": PD.period(), "note": "the run does nothing unless an issue or a source update is due; see /forecast-period"}


class OutcomeIn(BaseModel):
    province: str
    reference_quarter: str = Field(pattern=r"^\d{4}-Q[1-4]$")
    observed_share_pct: float = Field(ge=0, le=100)
    source: str = Field(min_length=3)
    source_sha256: str = Field(min_length=64, max_length=64)


# the admin router's guards (app/api/v1/admin.py): an admin login, and the demo account is read-only. Audit 2026-11-14: this route
# lived outside that router, so the demo account got 422 (its body was validated) instead of 403.
@router.post("/admin/forecast-outcomes", dependencies=[Depends(require_admin), Depends(forbid_demo_writes)])
async def record_outcome(body: OutcomeIn, user=Depends(require_admin)) -> dict:
    try:
        return HI.record_outcome(body.province, body.reference_quarter, body.observed_share_pct, body.source, body.source_sha256,
                                 authorized_by=getattr(user, "email", None) or str(getattr(user, "id", "admin")))
    except HI.HistoryError as e:
        raise HTTPException(status_code=409, detail=str(e))
