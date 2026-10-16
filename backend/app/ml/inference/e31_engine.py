"""
app/ml/inference/e31_engine.py
------------------------------
The E31 data layer for the main dashboard. It serves the ONE E31 record (data/e31/e31_record.json, the same bytes as
/api/v1/quarterly/e31/record and the PDF) through the interfaces the dashboard service already uses:

  E31Engine        Predictor interface (available_quarters, forecast_quarter, lead_time), one per horizon:
                     horizon "forecast"  -> lead-1 estimates only: development BACKTESTS (2023-Q4..2026-Q2), the
                                            RETROSPECTIVE_BLIND 2026-Q3 forecast, the 2027-Q1 FORECAST;
                     horizon "nowcast"   -> the dashboard's default timeline: the best available estimate of each
                                            quarter, i.e. the same-quarter NOWCAST where the quarter is under way
                                            (2026-Q4, cutoff 2026-10-14) and the lead-1 estimate elsewhere. Every
                                            row carries its mode, so forecasts and nowcasts stay distinguishable.
  E31Explainer     Explainer interface: the exact driver decomposition of the served engine (S1 - tau =
                   (H - tau) + 2D), not SHAP of a different model.
  E31Disaggregator Disaggregator interface: the Objective 3 LGU ranking (app.quarterly.lgu_audit), recomputed for the
                   province probabilities of the requested quarter.

Nothing here fits a model: the record is the single source, so the map, ranking, explanation, news and PDF agree.
"""
from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

# E36: the served record is the E36 LightGBM record (scripts/build_record_e36.py); the E31 PCF21 record stays in
# data/e31/ as history and can be served again with AIPHEED_E31_RECORD=data/e31/e31_record.json.
RECORD_PATH = Path(os.getenv("AIPHEED_E31_RECORD", "data/e36/e36_record.json"))
FORECAST_MODES = ("BACKTEST", "RETROSPECTIVE_BLIND", "FORECAST")
NOWCAST_MODES = ("NOWCAST",)
MODE_LABEL = {
    "BACKTEST": "Backtest (development evidence; refitted at its origin with earlier data only, but the outcome had "
                "been examined in earlier experiments)",
    "RETROSPECTIVE_BLIND": "Frozen forecast scored on an unseen outcome",
    "FORECAST": "Forecast (frozen before the outcome exists; reliability not established)",
    "NOWCAST": "Same-quarter nowcast (lead 0; never evaluated)",
}


class RecordUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=2)
def _load(path: str, mtime: float) -> dict:
    rec = json.loads(Path(path).read_text(encoding="utf-8"))
    body = {k: v for k, v in rec.items() if k != "content_sha256"}
    if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode("utf-8")).hexdigest() != rec.get("content_sha256"):
        raise RecordUnavailable("E31 record failed its integrity check")
    return rec


def record() -> dict:
    if not RECORD_PATH.exists():
        raise RecordUnavailable(f"E31 record not found at {RECORD_PATH}")
    return _load(str(RECORD_PATH), RECORD_PATH.stat().st_mtime)


def available() -> bool:
    try:
        record()
        return True
    except RecordUnavailable:
        return False


def quarter_row(quarter: str, horizon: str = "forecast") -> dict | None:
    """horizon 'nowcast' prefers the NOWCAST row and falls back to the lead-1 row; 'forecast' never uses a nowcast."""
    order = (NOWCAST_MODES + FORECAST_MODES) if horizon == "nowcast" else FORECAST_MODES
    rows = [q for q in record()["quarters"] if q["quarter"] == quarter and q["mode"] in order]
    rows.sort(key=lambda q: order.index(q["mode"]))
    return rows[0] if rows else None


def current_quarter() -> str | None:
    """The quarter under way at the information cutoff (the NOWCAST target)."""
    return next((q["quarter"] for q in record()["quarters"] if q["mode"] in NOWCAST_MODES), None)


def _confidence(q: dict, v: dict) -> str:
    """The row's mode, origin and signal; the S1 interval only for an engine that produces one (PCF21)."""
    model = record().get("served_engine", {}).get("name", "served engine")
    iv = f"; S1 80% interval {v['S1_80pct_interval']}" if v.get("S1_80pct_interval") else ""
    return (f"{MODE_LABEL[q['mode']]}. {model}, issued at {q['origin']} with information published before it. "
            f"Signal {v['signal']}{iv}. Indicative only.")


class E31Engine:
    def __init__(self, horizon: str = "forecast"):
        self.horizon = "nowcast" if horizon == "nowcast" else "forecast"

    @property
    def lead_time(self) -> int:
        return 0 if self.horizon == "nowcast" else 1

    def available_quarters(self) -> list[str]:
        modes = (NOWCAST_MODES + FORECAST_MODES) if self.horizon == "nowcast" else FORECAST_MODES
        return sorted({q["quarter"] for q in record()["quarters"] if q["mode"] in modes})

    def horizon_label(self, q: dict | None = None) -> str:
        if q is not None and q["mode"] == "NOWCAST":
            return "Same-quarter estimate (nowcast), lead 0"
        if q is not None and q["mode"] == "BACKTEST":
            return "Backtest: one-quarter-ahead estimate made on development data"
        if q is not None and q["mode"] == "RETROSPECTIVE_BLIND":
            return "One quarter ahead (frozen 1 July 2026), scored on the released outcome"
        if q is not None and q.get("role") == "next_quarter":
            return (f"Next quarter (forecast issued {q['origin'][:10]}, two quarters after the latest complete "
                    "data quarter)")
        if q is not None and q.get("role") == "current_quarter":
            return f"Current quarter (forecast issued {q['origin'][:10]}), lead 1"
        if q is not None and q["mode"] == "FORECAST":
            return f"One quarter ahead (forecast issued {q['origin'][:10]}), lead 1"
        return "One quarter ahead (forecast), lead 1"

    def forecast_quarter(self, quarter: str) -> list[dict]:
        q = quarter_row(quarter, self.horizon)
        if q is None:
            return []
        news = {(r["province_code"], r["quarter"]): r for r in record()["news"]["by_province_quarter"]}
        ev_q = (q.get("provenance") or {}).get("news_evidence_window", {}).get("evidence_quarter") or quarter
        out = []
        for code, v in q["provinces"].items():
            n = news.get((code, ev_q))
            out.append({
                "province_code": code, "province_name": v["province"], "quarter": quarter,
                "risk_probability": v["p_high"],
                # no HIGH/LOW for an estimate whose lead is not validated (E27 rule); the observed label is shown
                # separately where the outcome has been released
                "risk_label": None, "observed_label": v.get("observed_label"), "observed_S1": v.get("observed_S1"),
                "data_sufficiency_flag": (n or {}).get("evidence_status_v2", "NO_USABLE_EVIDENCE"),
                "forecast_horizon_quarters": q["lead"], "horizon_label": self.horizon_label(q),
                "confidence_statement": _confidence(q, v),
                "verification_date": q["information_cutoff"], "mode": q["mode"], "origin": q["origin"],
                "information_cutoff": q["information_cutoff"], "provenance": q.get("provenance"),
            })
        out.sort(key=lambda r: r["risk_probability"], reverse=True)
        return out


class E31Explainer:
    """Driver decomposition of the served engine for one province-quarter (forecast horizon first, then nowcast)."""

    GROUPS = {"regional_hunger": "Regional hunger (SWS, shared)", "price_pressure": "Provincial food-price pressure"}
    # E36: the drivers are the exact TreeSHAP values of the served LightGBM (log-odds), one per input feature.

    def _prov(self, code: str, quarter: str) -> dict | None:
        q = quarter_row(quarter, "forecast") or quarter_row(quarter, "nowcast")
        return None if q is None else q["provinces"].get(code)

    def explain_province_quarter(self, code: str, quarter: str) -> list[dict]:
        v = self._prov(code, quarter)
        if not v:
            return []
        return [{"feature_name": d["key"], "display_name": d["factor"], "shap_value": d["contribution"],
                 "feature_value": d["value"]} for d in v.get("drivers", [])]

    def build_drivers(self, code: str, quarter: str, records: list[dict]) -> dict:
        if record().get("schema") == "e36/1":
            return five_trigger_drivers(code, quarter, records)
        drivers = [{"driver_group": r["feature_name"], "driver_label": self.GROUPS.get(r["feature_name"], r["display_name"]),
                    "group_shap": r["shap_value"],
                    "direction": "increases_risk" if (r["shap_value"] or 0) >= 0 else "protective",
                    "trigger_proportion": None} for r in records]
        return {"drivers": drivers, "article_count": 0}


class E31Disaggregator:
    def disaggregate(self, forecasts: list[dict], quarter: str | None = None) -> pd.DataFrame:
        from app.quarterly.lgu_audit import build_ranking

        vul = pd.read_csv(Path("data/inputs/lgu_vulnerability.csv"), dtype={"lgu_code": str})
        ros = pd.read_csv(Path("data/reference/calabarzon_lgus.csv"), dtype={"lgu_psgc": str})
        prob = {f["province_code"]: f["risk_probability"] for f in forecasts} or None
        rk = build_ranking(vul, ros, prob, {"source": f"E31 record, {quarter}"})
        suff = {f["province_code"]: f.get("data_sufficiency_flag") for f in forecasts}
        rows = [{"lgu_code": r["lgu_code"], "risk_index": r["risk_index"], "rank_region": r["rank_region"],
                 "rank_in_province": r["rank_in_province"], "tied": r["tied"],
                 "vulnerability_index": r["vulnerability_index"],
                 "disaggregation_label": rk["meaning"], "data_sufficiency_flag": suff.get(r["province_code"])}
                for r in rk["rows"]]
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- the five triggers
# The approved dashboard (branch 10-15-updated-flexible-ui) explains every estimate with the thesis's five trigger
# groups. The served E36/E38 LightGBM is grouped exactly as the E20 forecaster did (app/ml/inference/e20_forecast.py):
# a group's contribution is the sum of the exact TreeSHAP of the model inputs that belong to it, the five shares are
# rescaled among themselves, and every other input (regional hunger, the last published label, news volume, FSSI) is
# reported as `other_pct`, not folded into a group. The served model's only trigger-group inputs are the provincial
# food and rice price features (Market / Prices); climate, fish kill, employment and OFW have no input in it (E38:
# the five news trigger proportions carry almost no data in the title-only corpus and were not selected), so their
# contribution is exactly 0. `trigger_proportion` is the measured share of the province's attributed news titles in
# the forecast's evidence quarter that the existing classifier (app/ml/nlp/trigger_classifier.py) assigns to the group.
TRIGGER_GROUP_FEATURES = {"market": ["D_last", "Dnow", "rice_rel"], "climate": [], "fish_kill": [], "employment": [],
                          "ofw_remittance": []}
NEWS_STORE = Path(os.getenv("AIPHEED_E31_NEWS_STORE", "data/news_e31"))


@lru_cache(maxsize=1)
def _trigger_proportions() -> dict:
    from app.ml.nlp.trigger_classifier import classify_triggers

    out: dict = {}
    path = NEWS_STORE / "articles.jsonl"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        a = json.loads(line)
        code = a.get("geo_province_code")
        if not code:
            continue
        cell = out.setdefault((code, a["quarter"]), {"n": 0, **{g: 0 for g in TRIGGER_GROUP_FEATURES}})
        cell["n"] += 1
        for g in classify_triggers(a.get("title") or ""):
            cell[g] += 1
    return out


def five_trigger_drivers(code: str, quarter: str, records: list[dict]) -> dict:
    from app.ml.inference.e20_forecast import DRIVER_GROUP_LABELS

    shap = {r["feature_name"]: float(r["shap_value"] or 0.0) for r in records}
    q = quarter_row(quarter, "forecast") or quarter_row(quarter, "nowcast") or {}
    ev_q = (q.get("provenance") or {}).get("news_evidence_window", {}).get("evidence_quarter") or quarter
    cell = _trigger_proportions().get((code, ev_q))
    group = {g: sum(shap.get(f, 0.0) for f in fs) for g, fs in TRIGGER_GROUP_FEATURES.items()}
    grouped = {f for fs in TRIGGER_GROUP_FEATURES.values() for f in fs}
    other_abs = sum(abs(v) for f, v in shap.items() if f not in grouped)
    total_abs = sum(abs(v) for v in group.values())
    grand = total_abs + other_abs
    drivers = [{"driver_group": g, "driver_label": DRIVER_GROUP_LABELS[g], "group_shap": round(v, 4),
                "direction": "increases_risk" if v >= 0 else "protective",
                "trigger_proportion": (round(cell[g] / cell["n"], 4) if cell and cell["n"] else None)}
               for g, v in group.items()]
    drivers.sort(key=lambda d: abs(d["group_shap"]), reverse=True)
    return {"drivers": drivers, "article_count": int(sum(cell[g] for g in group) if cell else 0),
            "other_pct": round(other_abs / grand * 100, 1) if grand else 0.0, "evidence_quarter": ev_q}
