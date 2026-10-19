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

import functools
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
# E46: defect-corrected five-trigger component model (I7, forecasting acceptance not met)
RECORD_E46 = Path(os.getenv("AIPHEED_E46_RECORD", "data/e46/e46_record.json"))
# E52: provincial food-price pressure (target PS) from the E46 I7 price component; development criteria met, not
# independently validated
RECORD_E52 = Path(os.getenv("AIPHEED_E52_RECORD", "data/e52/e52_record.json"))
# E53: E52 price model with the arm adopted in E53 (calibration audit) and the corrected D-1 attribution
RECORD_E53 = Path(os.getenv("AIPHEED_E53_RECORD", "data/e53/e53_record.json"))
# E55: food-insecurity risk (target T43: regional SWS hunger > 11.3 AND provincial food-price pressure) from the E55
# LightGBM model, exact TreeSHAP explanations
RECORD_E55 = Path(os.getenv("AIPHEED_E55_RECORD", "data/e55/e55_record.json"))
# E56: final model of the E56 LightGBM optimization cycle (two-quarter food-insecurity risk, T43), saved artifacts in
# data/e56/model/, data-freshness disclosure
RECORD_E56 = Path(os.getenv("AIPHEED_E56_RECORD", "data/e56/e56_record.json"))
# E58: E56 record + two-signal early warning (ALERT / EMERGING / NONE, direction) per province and quarter
RECORD_E58 = Path(os.getenv("AIPHEED_E58_RECORD", "data/e58/e58_record.json"))
# E64: Objectives 1-3 completion candidate (improved news pipeline v3 + E56 procedure family, same Lead-2 target T43)
RECORD_E64 = Path(os.getenv("AIPHEED_E64_RECORD", "data/e64/e64_record.json"))
GROUP_LABELS = {"market": "Market / Prices", "climate": "Climate Stress", "fish_kill": "Fish Kill",
                "employment": "Employment", "ofw_remittance": "OFW Remittance"}


class RecordError(RuntimeError):
    pass


def mode() -> str:
    return os.getenv("AIPHEED_LEAD2_MODEL", "e38").lower()


def active() -> bool:
    return mode() in ("e41", "e42", "e43", "e44", "e46", "e52", "e53", "e55", "e56", "e58", "e64")


def record() -> dict:
    path = {"e42": RECORD_E42, "e43": RECORD_E43, "e44": RECORD_E44, "e46": RECORD_E46, "e52": RECORD_E52, "e53": RECORD_E53,
            "e55": RECORD_E55, "e56": RECORD_E56, "e58": RECORD_E58,
            "e64": RECORD_E64}.get(mode(), RECORD)
    if not path.exists():
        raise RecordError(f"no {mode().upper()} record has been generated (scripts/build_record_{mode()}.py)")
    st = path.stat()
    return _load(str(path), st.st_mtime_ns, st.st_size, mode().upper())


@functools.lru_cache(maxsize=4)
def _load(path: str, mtime_ns: int, size: int, name: str) -> dict:
    """Parsed and integrity-checked record, cached per file version (path, mtime, size), as E31 caches its record.
    A dashboard request used to re-read and re-hash the record up to ~400 times; a changed file is re-read and
    re-checked on the next call. Callers treat the record as read-only."""
    rec = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != rec.get("content_sha256"):
        raise RecordError(f"{name} record failed its integrity check")
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
            "estimate_kind": "forecast",
        })
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


def probability(v: dict) -> float:
    """The served probability of a province entry (E43: food-stress risk; E41/E42: price pressure)."""
    f = v["forecast"]
    return f["probability"] if "probability" in f else f["probabilityAbove4pct"]


STATUS_ORDER = ["contributes", "no_effect", "stale", "data_not_in_model", "no_model_input", "insufficient_data", "no_data"]


def has_past_drivers(quarter: str) -> bool:
    """E47: the governing record carries as-of five-trigger attributions for this past quarter, for every province."""
    if not governs():
        return False
    provs = record()["provinces"]
    return all(quarter in v.get("pastDrivers", {}) for v in provs.values())


def _status_block(v: dict, quarter: str) -> dict:
    """Trigger statuses of one province entry for this quarter: the issued forecast's, or the past quarter's own."""
    if quarter == record()["targetQuarter"]:
        return v.get("triggerStatus", {})
    return v.get("pastDrivers", {}).get(quarter, {}).get("triggerStatus", {})


def trigger_statuses(quarter: str, code: str | None = None) -> dict[str, str] | None:
    """E43 records carry their own per-province trigger status; for the region a group takes its strongest status
    across provinces. None for records without statuses (E41/E42 use the dashboard's model-input rule). E47: past
    quarters of a governing record use their own as-of statuses."""
    if not (serves(quarter) or has_past_drivers(quarter)):
        return None
    provs = record()["provinces"]
    blocks = {c: _status_block(v, quarter) for c, v in provs.items()}
    if not all(isinstance(next(iter(b.values()), None), dict) and "status" in next(iter(b.values()))
               for b in blocks.values()):
        return None
    if code:
        return {g: s["status"] for g, s in blocks[code].items()}
    out: dict[str, str] = {}
    for b in blocks.values():
        for g, s in b.items():
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


def governs() -> bool:
    """E46: True when a candidate is enabled AND its record is for the dashboard's current target quarter. Every quarter
    the dashboard shows then carries the candidate's own score of its own target event (as-of backtest, an earlier
    Lead-2 forecast, or the issued forecast), or nothing: never the v1 label probability of another model next to it
    (the "observed about 0.98, forecast about 0.2" discrepancy)."""
    if not active():
        return False
    from app.quarterly.target import forecast_target

    try:
        return record()["targetQuarter"] == forecast_target()["target_quarter"]
    except RecordError:
        return False


def _origin_for_target(quarter: str) -> str:
    """Lead-2 origin of a target quarter (E41 convention): first day of the quarter before it."""
    y, q = int(quarter[:4]), int(quarter[-1])
    i = y * 4 + q - 1 - 1
    return f"{i // 4}-{(i % 4) * 3 + 1:02d}-01"


def _entries(v: dict) -> dict[str, dict]:
    out = {}
    for kind, key in (("backtest", "pastForecasts"), ("earlier_forecast", "earlierForecasts")):
        for x in v.get(key, []):
            p = x.get("probability", x.get("probabilityAbove4pct"))
            if p is not None:
                out[x["targetQuarter"]] = {"probability": float(p), "kind": kind, "observedHigh": x.get("observedHigh"),
                                           "origin": x.get("origin") or _origin_for_target(x["targetQuarter"])}
    return out


def candidate_quarters() -> list[str]:
    """Quarters for which the governing candidate has a value for every province (its target included)."""
    rec = record()
    provs = rec["provinces"]
    per = [set(_entries(v)) for v in provs.values()]
    qs = set.intersection(*per) if per else set()
    return sorted(qs | {rec["targetQuarter"]}, key=lambda q: (int(q[:4]), int(q[-1])))


def rows_for(quarter: str) -> list[dict]:
    """Engine-shaped rows of the governing candidate for any quarter it covers; [] otherwise."""
    rec = record()
    if quarter == rec["targetQuarter"]:
        return forecast_rows(quarter)
    if quarter not in candidate_quarters():
        return []
    st = next(iter(rec["scoreTypes"]))
    name = mode().upper()
    out = []
    for code, v in rec["provinces"].items():
        e = _entries(v)[quarter]
        if e["kind"] == "backtest":
            obs = None if e["observedHigh"] is None else ("HIGH" if e["observedHigh"] else "LOW")
            label = (f"Backtest of the {name} candidate: Lead-2 estimate for {quarter} made as of {e['origin']} with "
                     f"information published before it (development evidence, not a forecast issued live). "
                     f"Observed outcome of the same event: {obs or 'not available'}.")
        else:
            obs = None
            label = (f"Lead-2 forecast for {quarter} issued {e['origin']} by the {name} candidate procedure with "
                     "information published before it; the outcome is not yet published.")
        out.append({
            "province_code": code, "province_name": v["name"], "quarter": quarter,
            "risk_probability": e["probability"], "risk_label": None, "observed_label": obs,
            "observed_S1": None, "data_sufficiency_flag": "SUFFICIENT",
            "forecast_horizon_quarters": 2, "horizon_label": label, "confidence_statement": label,
            "verification_date": e["origin"], "mode": f"{name}_LEAD2_{e['kind'].upper()}", "origin": e["origin"],
            "information_cutoff": e["origin"], "provenance": rec.get("sources"),
            "score_type": st, "score_definition": rec["scoreTypes"][st],
            "band": "High" if e["probability"] >= 2 / 3 else ("Watch" if e["probability"] >= 1 / 3 else "Low"),
            "estimate_kind": e["kind"],
        })
    out.sort(key=lambda r: r["risk_probability"], reverse=True)
    return out


def early_warning(quarter: str, code: str | None) -> list[dict]:
    """E58: early-warning blocks of the governing record for this quarter (one province, or every province for the
    region), each with the province name; [] for records without warnings or quarters they do not cover."""
    if not (serves(quarter) or has_past_drivers(quarter)):
        return []
    rec = record()
    out = []
    for c, v in rec["provinces"].items():
        if code and c != code:
            continue
        w = v.get("earlyWarning") if quarter == rec["targetQuarter"] else v.get("pastDrivers", {}).get(quarter, {}).get("earlyWarning")
        if w:
            out.append({"provinceCode": c, "province": v["name"], **w})
    return out


def partial_inputs(quarter: str, code: str | None) -> list[str]:
    """E53: trigger groups some of whose observed inputs had no value at the issue date (inputsPresent < 1), for one
    province or, for the region, in any province. Empty for records without coverage data."""
    if not (serves(quarter) or has_past_drivers(quarter)):
        return []
    provs = record()["provinces"]
    out: list[str] = []
    for c, v in provs.items():
        if code and c != code:
            continue
        for g, s in _status_block(v, quarter).items():
            if isinstance(s, dict) and s.get("inputsPresent", 1) < 1 and g not in out:
                out.append(g)
    return out


def trigger_evidence(quarter: str, code: str | None) -> dict[str, str]:
    """E44: the observed evidence sentence per trigger (province scope only; empty otherwise)."""
    if not code or not (serves(quarter) or has_past_drivers(quarter)):
        return {}
    ts = _status_block(record()["provinces"].get(code, {}), quarter)
    return {g: v["evidenceNote"] for g, v in ts.items() if isinstance(v, dict) and v.get("evidenceNote")}


def drivers(code: str, quarter: str) -> dict:
    """Five-trigger structure for the dashboard. E43 records carry the served model's own grouped contributions;
    for E41/E42 every model input is a price input (Market / Prices) and the other four groups have no input (0)."""
    v = record()["provinces"][code]
    if quarter != record()["targetQuarter"] and quarter in v.get("pastDrivers", {}):
        return v["pastDrivers"][quarter]["drivers"]               # E47: the past quarter's own as-of attribution
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
