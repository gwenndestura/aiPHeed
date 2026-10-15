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

RECORD_PATH = Path(os.getenv("AIPHEED_E31_RECORD", "data/e31/e31_record.json"))
FORECAST_MODES = ("BACKTEST", "RETROSPECTIVE_BLIND", "FORECAST")
NOWCAST_MODES = ("NOWCAST",)
MODE_LABEL = {
    "BACKTEST": "Backtest (development evidence; the outcome was examined before the model froze)",
    "RETROSPECTIVE_BLIND": "Frozen forecast scored on an unseen outcome",
    "FORECAST": "Forecast (lead 1; reliability not established)",
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
                "confidence_statement": f"{MODE_LABEL[q['mode']]}. Signal {v['signal']}; S1 80% interval "
                                        f"{v.get('S1_80pct_interval')}. Indicative only.",
                "verification_date": q["information_cutoff"], "mode": q["mode"], "origin": q["origin"],
                "information_cutoff": q["information_cutoff"], "provenance": q.get("provenance"),
            })
        out.sort(key=lambda r: r["risk_probability"], reverse=True)
        return out


class E31Explainer:
    """Driver decomposition of the served engine for one province-quarter (forecast horizon first, then nowcast)."""

    GROUPS = {"regional_hunger": "Regional hunger (SWS, shared)", "price_pressure": "Provincial food-price pressure"}

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
                 "disaggregation_label": rk["meaning"], "data_sufficiency_flag": suff.get(r["province_code"])}
                for r in rk["rows"]]
        return pd.DataFrame(rows)
