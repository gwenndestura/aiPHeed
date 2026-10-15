"""
app/ml/inference/e41_lead2.py
-----------------------------
E41 Lead-2 two-layer candidate (aipheed-backend-aligned/experiments/E41_Lead2_Audit). Served only when
AIPHEED_LEAD2_MODEL=e41; the default (e38) leaves the dashboard exactly as it is.

The record keeps three things apart: observed evidence (what PSA/SWS reported, with level and age), the forecast
probability (P(provincial food inflation > 4%) in the target quarter: price pressure, not food insecurity), and the
operational band and alert candidate derived from a documented rule.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

RECORD = Path(os.getenv("AIPHEED_E41_RECORD", "data/e41/e41_lead2_record.json"))
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                "employment": "Employment", "ofw_remittance": "OFW Remittance"}


class RecordError(RuntimeError):
    pass


def mode() -> str:
    return os.getenv("AIPHEED_LEAD2_MODEL", "e38").lower()


def active() -> bool:
    return mode() == "e41"


def record() -> dict:
    if not RECORD.exists():
        raise RecordError("no E41 record has been generated (scripts/build_record_e41.py)")
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != rec.get("content_sha256"):
        raise RecordError("E41 record failed its integrity check")
    return rec


def serves(quarter: str) -> bool:
    """True only when E41 is enabled and its frozen forecast is for exactly this quarter (no stale fallback)."""
    if not active():
        return False
    try:
        return record()["targetQuarter"] == quarter
    except RecordError:
        return False


def forecast_rows(quarter: str) -> list[dict]:
    """Engine-shaped rows (as E31Engine.forecast_quarter) with the price-pressure probability as risk_probability."""
    rec = record()
    if rec["targetQuarter"] != quarter:
        return []
    out = []
    for code, v in rec["provinces"].items():
        f = v["forecast"]
        out.append({
            "province_code": code, "province_name": v["name"], "quarter": quarter,
            "risk_probability": f["probabilityAbove4pct"], "risk_label": None, "observed_label": None,
            "observed_S1": None,
            "data_sufficiency_flag": "SUFFICIENT" if v["observed"]["news"]["sufficient"] else "LIMITED_SIGNAL",
            "forecast_horizon_quarters": 2, "horizon_label": f"Lead 2 ({quarter}), issued {rec['origin']}",
            "confidence_statement": f["explanation"], "verification_date": rec["origin"], "mode": "E41_LEAD2",
            "origin": rec["origin"], "information_cutoff": rec["origin"], "provenance": rec["sources"],
            "score_type": f["scoreType"], "score_definition": rec["scoreTypes"][f["scoreType"]], "band": f["band"],
        })
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


def drivers(code: str, quarter: str) -> dict:
    """Five-trigger structure for the dashboard: every model input of E41 is a price input (Market / Prices); the
    other four groups have no model input (0), and their measured news shares are reported as they are."""
    v = record()["provinces"][code]
    p = min(max(v["forecast"]["probabilityAbove4pct"], 1e-6), 1 - 1e-6)
    logit = math.log(p / (1 - p))
    shares = v["observed"]["news"]["triggerShares"]
    rows = []
    for g, label in GROUP_LABELS.items():
        val = round(logit, 4) if g == "market" else 0.0
        rows.append({"driver_group": g, "driver_label": label, "group_shap": val,
                     "direction": "increases_risk" if val >= 0 else "protective",
                     "trigger_proportion": shares.get(g)})
    rows.sort(key=lambda d: abs(d["group_shap"]), reverse=True)
    return {"drivers": rows, "article_count": v["observed"]["news"]["articles"], "other_pct": 0.0,
            "evidence_quarter": v["observed"]["news"]["quarter"]}
