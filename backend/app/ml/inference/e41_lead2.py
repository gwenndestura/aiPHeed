"""
app/ml/inference/e41_lead2.py
-----------------------------
E41 Lead-2 two-layer candidate (aipheed-backend-aligned/experiments/E41_Lead2_Audit). Served only when
AIPHEED_LEAD2_MODEL=e41 or e42 (E42: same forecast plus the E42 evidence); the default (e38) leaves the dashboard
exactly as it is.

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
# E42: same E41 forecast, enriched with the E42 evidence (variants, signal count, trigger status, backtest)
RECORD_E42 = Path(os.getenv("AIPHEED_E42_RECORD", "data/e42/e42_lead2_record.json"))
# E43: five-trigger food-stress risk forecast (Chapter I section 1.7 target); own score type, drivers and statuses
RECORD_E43 = Path(os.getenv("AIPHEED_E43_RECORD", "data/e43/e43_record.json"))
# E44: final five-trigger candidate (I2, forecasting acceptance not met)
RECORD_E44 = Path(os.getenv("AIPHEED_E44_RECORD", "data/e44/e44_record.json"))
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                "employment": "Employment", "ofw_remittance": "OFW Remittance"}


class RecordError(RuntimeError):
    pass


def mode() -> str:
    return os.getenv("AIPHEED_LEAD2_MODEL", "e38").lower()


def active() -> bool:
    return mode() in ("e41", "e42", "e43", "e44")


def record() -> dict:
    path = {"e42": RECORD_E42, "e43": RECORD_E43, "e44": RECORD_E44}.get(mode(), RECORD)
    if not path.exists():
        raise RecordError(f"no {mode().upper()} record has been generated (scripts/build_record_{mode()}.py)")
    rec = json.loads(path.read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != rec.get("content_sha256"):
        raise RecordError(f"{mode().upper()} record failed its integrity check")
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
        prob = probability(v)
        out.append({
            "province_code": code, "province_name": v["name"], "quarter": quarter,
            "risk_probability": prob, "risk_label": None, "observed_label": None,
            "observed_S1": None,
            "data_sufficiency_flag": "SUFFICIENT" if v["observed"]["news"]["sufficient"] else "LIMITED_SIGNAL",
            "forecast_horizon_quarters": 2, "horizon_label": f"Lead 2 ({quarter}), issued {rec['origin']}",
            "confidence_statement": f["explanation"], "verification_date": rec["origin"],
            "mode": f"{mode().upper()}_LEAD2",
            "origin": rec["origin"], "information_cutoff": rec["origin"], "provenance": rec["sources"],
            "score_type": f["scoreType"], "score_definition": rec["scoreTypes"][f["scoreType"]], "band": f["band"],
        })
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


def probability(v: dict) -> float:
    """The served probability of a province entry (E43: food-stress risk; E41/E42: price pressure)."""
    f = v["forecast"]
    return f["probability"] if "probability" in f else f["probabilityAbove4pct"]


STATUS_ORDER = ["contributes", "no_effect", "stale", "data_not_in_model", "no_model_input", "no_data"]


def trigger_statuses(quarter: str, code: str | None = None) -> dict[str, str] | None:
    """E43 records carry their own per-province trigger status; for the region a group takes its strongest status
    across provinces. None for records without statuses (E41/E42 use the dashboard's model-input rule)."""
    if not serves(quarter):
        return None
    provs = record()["provinces"]
    if not all(isinstance(next(iter(v.get("triggerStatus", {}).values()), None), dict)
               and "status" in next(iter(v["triggerStatus"].values())) for v in provs.values()):
        return None
    if code:
        return {g: s["status"] for g, s in provs[code]["triggerStatus"].items()}
    out: dict[str, str] = {}
    for v in provs.values():
        for g, s in v["triggerStatus"].items():
            out[g] = min(out.get(g, s["status"]), s["status"], key=STATUS_ORDER.index)
    return out


def backtest_series(code: str | None) -> dict[str, float]:
    """E46: the served candidate's own development backtest (same model procedure, information available at each past
    origin), quarter -> probability; region = mean of the five provinces where all five exist. Empty if the record has
    no backtest. Used so a trend line never joins the old v1 label scores to the candidate's probabilities."""
    if not active():
        return {}
    provs = record()["provinces"]
    by_q: dict[str, list[float]] = {}
    for c, v in provs.items():
        if code and c != code:
            continue
        for x in v.get("pastForecasts", []):
            p = x.get("probability", x.get("probabilityAbove4pct"))
            if p is not None:
                by_q.setdefault(x["targetQuarter"], []).append(float(p))
    need = 1 if code else len(provs)
    return {q: sum(ps) / len(ps) for q, ps in by_q.items() if len(ps) == need}


def trigger_evidence(quarter: str, code: str | None) -> dict[str, str]:
    """E44: the observed evidence sentence per trigger (province scope only; empty otherwise)."""
    if not code or not serves(quarter):
        return {}
    ts = record()["provinces"].get(code, {}).get("triggerStatus", {})
    return {g: v["evidenceNote"] for g, v in ts.items() if isinstance(v, dict) and v.get("evidenceNote")}


def drivers(code: str, quarter: str) -> dict:
    """Five-trigger structure for the dashboard. E43 records carry the served model's own grouped contributions;
    for E41/E42 every model input is a price input (Market / Prices) and the other four groups have no input (0)."""
    v = record()["provinces"][code]
    if "drivers" in v:
        return v["drivers"]
    p = min(max(probability(v), 1e-6), 1 - 1e-6)
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
