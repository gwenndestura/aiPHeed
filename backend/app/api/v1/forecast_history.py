"""
app/api/v1/forecast_history.py
------------------------------
Read-only audit routes for the SWS-release re-issue (app.ml.inference.sws_reissue): every recorded issue of a
province-quarter forecast (quarter-start and re-issues, never edited), the forecast the dashboard shows, and the
re-issue store's status. Nothing here writes, and nothing changes what is served when AIPHEED_SWS_REISSUE is off.
"""
from __future__ import annotations

import json
import math

from fastapi import APIRouter, Query

from app.ml.inference import ch1_system as CH1
from app.ml.inference import sws_reissue as RI

router = APIRouter()


def _clean(rec: dict) -> dict:
    return {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in rec.items()}


@router.get("/forecast-history")
def forecast_history(province: str | None = Query(None, pattern=r"^PH\d{9}$"),
                     quarter: str | None = Query(None, pattern=r"^\d{4}-Q[1-4]$")) -> dict:
    """All recorded issues (oldest first) and the forecast in force on the dashboard for the same filter."""
    h = RI.history_for(province, quarter)
    shown = [{"province_code": c, "quarter": q, "issue_date": r["issue_date"],
              "data_cutoff": r.get("data_cutoff") or r["issue_date"], "issue_trigger": r.get("issue_trigger") or "quarter_start",
              "sws_reading_used": r.get("sws_newest_q"), "probability": float(r["probability"]), "lead": int(r["lead"])}
             for (c, q), r in CH1.rows().items()
             if (province is None or c == province) and (quarter is None or q == quarter)]
    return {"reissueEnabled": RI.enabled(), "asOf": RI.today().isoformat(), "count": int(len(h)),
            "issues": [_clean(x) for x in h.to_dict("records")], "shownOnDashboard": shown}


@router.get("/forecast-history/status")
def forecast_history_status() -> dict:
    """Whether the re-issue is enabled, the store files, the last run and any history rows the overlay refused."""
    last = None
    lp = RI.log_path()
    if lp.exists():
        lines = [ln for ln in lp.read_text(encoding="utf-8").splitlines() if ln.strip()]
        last = json.loads(lines[-1]) if lines else None
    return {"reissueEnabled": RI.enabled(), "asOf": RI.today().isoformat(), "storeDir": str(RI.store_dir()),
            "swsStoreExists": RI.sws_path().exists(), "historyExists": RI.history_path().exists(),
            "historyRows": int(len(RI.load_history())), "lastRun": last, "overlayRefused": CH1.overlay_report(),
            "enableWith": ["AIPHEED_SWS_REISSUE=1", "AIPHEED_ENABLE_SCHEDULER=1 (daily 05:00 job)",
                           "enter each SWS release: python scripts/sws_reissue.py enter ..."]}
