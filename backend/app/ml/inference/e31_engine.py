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
import math
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

# E36: the served record is the E36 LightGBM record (scripts/build_record_e36.py); the E31 PCF21 record stays in
# data/e31/ as history and can be served again with AIPHEED_E31_RECORD=data/e31/e31_record.json.
# AIPHEED_RECORD names the served record (default "e53" -> data/e53/e53_record.json, E53-A1: the E48-A1 inputs plus
# the measured driver conditions, shrinkage-calibrated). "e49" (E48-A1 + E49-C2 calibration, the default until the
# final integration), "e36" (the E36 record) and "e48" (E48-A1 uncalibrated) stay selectable. AIPHEED_E31_RECORD, a
# full path, still overrides it.
DEFAULT_RECORD = "e53"
RECORD_NAME = os.getenv("AIPHEED_RECORD", DEFAULT_RECORD)
RECORD_PATH = Path(os.getenv("AIPHEED_E31_RECORD", f"data/{RECORD_NAME}/{RECORD_NAME}_record.json"))
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


def served_rows() -> list[dict]:
    """The record's quarter rows the system serves: lead <= AIPHEED_MAX_LEAD (default 1, so the E38 lead-2 row stays in
    the record but is not shown; app/quarterly/target.py)."""
    from app.quarterly.target import max_lead

    return [q for q in record()["quarters"] if q.get("lead", 1) <= max_lead()]


def quarter_row(quarter: str, horizon: str = "forecast") -> dict | None:
    """horizon 'nowcast' prefers the NOWCAST row and falls back to the lead-1 row; 'forecast' never uses a nowcast."""
    order = (NOWCAST_MODES + FORECAST_MODES) if horizon == "nowcast" else FORECAST_MODES
    rows = [q for q in served_rows() if q["quarter"] == quarter and q["mode"] in order]
    rows.sort(key=lambda q: order.index(q["mode"]))
    return rows[0] if rows else None


def current_quarter() -> str | None:
    """The quarter under way at the information cutoff (the NOWCAST target)."""
    return next((q["quarter"] for q in served_rows() if q["mode"] in NOWCAST_MODES), None)


def _confidence(q: dict, v: dict) -> str:
    """The row's mode, origin and signal; the S1 interval only for an engine that produces one (PCF21). A row produced
    by a different model than the served engine (the E53 record's E55 lead-2 row) names its own model and carries its
    own accuracy note (row fields model_name / accuracy_note)."""
    from app.quarterly import self_description as SD

    model = q.get("model_name") or SD.served_engine(record(), SD.active_record_key()).get("name", "served engine")
    iv = f"; S1 80% interval {v['S1_80pct_interval']}" if v.get("S1_80pct_interval") else ""
    from app.quarterly import preview as PV

    if PV.lead2_preview() and q.get("lead", 1) >= 2:      # lead-2 preview on (the default): the preview says so plainly
        # the lead-2 row comes from the record's next-quarter model, not the served lead-1 engine
        model = q.get("model_name") or (record().get("next_quarter_model") or {}).get("name") or model
        return (f"{MODE_LABEL[q['mode']]}. {model}, issued at {q['origin']} with information published before it. "
                f"Signal {v['signal']}{iv}. {PV.compose_note(record())[0]}")
    note = f"; {q['accuracy_note']}" if q.get("accuracy_note") else ""
    return (f"{MODE_LABEL[q['mode']]}. {model}, issued at {q['origin']} with information published before it. "
            f"Signal {v['signal']}{iv}{note}. Indicative only.")


class E31Engine:
    def __init__(self, horizon: str = "forecast"):
        self.horizon = "nowcast" if horizon == "nowcast" else "forecast"

    @property
    def lead_time(self) -> int:
        return 0 if self.horizon == "nowcast" else 1

    def available_quarters(self) -> list[str]:
        modes = (NOWCAST_MODES + FORECAST_MODES) if self.horizon == "nowcast" else FORECAST_MODES
        return sorted({q["quarter"] for q in served_rows() if q["mode"] in modes})

    def horizon_label(self, q: dict | None = None) -> str:
        from app.quarterly import preview as PV

        if q is not None and PV.lead2_preview() and q.get("lead", 1) >= 2:
            below = PV.compose_note(record())[1]
            return (f"Two quarters ahead (forecast issued {q['origin'][:10]}): experimental preview"
                    + (", below the 75% accuracy target" if below else "") + "; not a validated forecast")
        if q is not None and q.get("horizon_label"):          # a row that states its own horizon (E53 record, E55 row)
            return q["horizon_label"]
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
        # Review-branch port (D-E66-3, Angel's E66): rank on the unrounded index, so 4-dp display rounding creates no
        # artificial ties (e.g. Pila and San Pablo, 2026-Q4). The displayed index and every score are unchanged.
        # AIPHEED_LGU_EXACT_RANKS=0 restores the ranks on the rounded index.
        exact = os.getenv("AIPHEED_LGU_EXACT_RANKS", "1").strip() != "0"
        rk = build_ranking(vul, ros, prob, {"source": f"E31 record, {quarter}"}, exact_ranks=exact)
        suff = {f["province_code"]: f.get("data_sufficiency_flag") for f in forecasts}
        # E64 (Objective 3 traceability, review-branch port): what each relative index is built from
        src = {f["province_code"]: {"mode": f.get("mode"), "origin": f.get("origin"), "quarter": f.get("quarter"),
                                    "score_type": f.get("score_type")} for f in forecasts}
        rows = [{"lgu_code": r["lgu_code"], "risk_index": r["risk_index"], "rank_region": r["rank_region"],
                 "rank_in_province": r["rank_in_province"], "tied": r["tied"],
                 "disaggregation_label": rk["meaning"], "data_sufficiency_flag": suff.get(r["province_code"]),
                 "province_probability": r["province_probability"], "vulnerability_index": r["vulnerability_index"],
                 "estimate_source": src.get(r["province_code"]), "ranking_method": rk["method"],
                 "rows_sha256": rk["rows_sha256"]}
                for r in rk["rows"]]
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------- the five triggers
# The approved dashboard (branch 10-15-updated-flexible-ui) explains every estimate with the thesis's five trigger
# groups. The served E36/E38 LightGBM is grouped exactly as the E20 forecaster did (app/ml/inference/e20_forecast.py):
# a group's contribution is the sum of the exact TreeSHAP of the model inputs that belong to it, the five shares are
# rescaled among themselves, and every other input (regional hunger, the last published label, news volume, FSSI) is
# reported as `other_pct`, not folded into a group. The served model's direct trigger-group inputs are the provincial
# food and rice price features (Market / Prices). Its news inputs (NEWS_FEATURES) are assigned to the five groups by
# topic: their total |SHAP| is split in proportion to the share of the validated (R1.1) news titles behind them, in
# the forecast's evidence quarter, that the existing classifier (app/ml/nlp/trigger_classifier.py) puts in each group
# (a title with k topics counts 1/k for each; a title with no topic stays unassigned). news_n and news_direct_share
# are built from the province's titles, news_reg from the five provinces' titles. fssi_v2 is a zero-shot intensity
# score (XLM-R), not a weighted sum of driver components, so it stays unassigned, as do hunger and the last label.
# `trigger_proportion` is the measured share of the province's attributed news titles in the evidence quarter that
# the classifier assigns to the group.
# A served model that has the thesis's trigger-proportion inputs (Eq. 5, e.g. the E48-A1 record) attributes each to
# its driver; the E36 record has no trig_* input, so for it these entries contribute nothing.
TRIGGER_GROUP_FEATURES = {"market": ["D_last", "Dnow", "rice_rel", "trig_market"], "climate": ["trig_climate"],
                          "fish_kill": ["trig_fish_kill"], "employment": ["trig_employment"],
                          "ofw_remittance": ["trig_ofw_remittance"]}
# A served record whose model also has the measured driver-condition inputs (E53: cond_*, each the rank of a measured
# indicator against earlier quarters; read with the other inputs from the record's per-row drivers) adds each of them
# to its driver. Records without cond_* (E49, E48, E36) keep TRIGGER_GROUP_FEATURES unchanged.
COND_GROUP_FEATURES = {"market": ["cond_market"], "climate": ["cond_climate"], "fish_kill": ["cond_fish"],
                       "employment": ["cond_employment"], "ofw_remittance": ["cond_ofw"]}
NEWS_FEATURES = {"province": ["news_n", "news_direct_share"], "region": ["news_reg"]}
# Inputs outside the five drivers, named for the explainability note: the regional hunger survey (SWS) inputs and the
# latest published label (built from SWS and CPI), and the news-tone score.
SURVEY_FEATURES = ["H_last", "H_gap", "H_trend", "H_margin", "y_last"]
NEWS_TONE_FEATURES = ["fssi_v2", "fssi_missing"]


def uses_condition_inputs() -> bool:
    """True when the served model has the measured driver-condition inputs (cond_*)."""
    feats = set((((record().get("served_engine") or {}).get("config") or {}).get("features")) or [])
    return bool(feats & {f for fs in COND_GROUP_FEATURES.values() for f in fs})


def trigger_group_features() -> dict:
    """The served record's driver mapping: TRIGGER_GROUP_FEATURES, plus cond_* when the model has them."""
    if uses_condition_inputs():
        return {g: fs + COND_GROUP_FEATURES[g] for g, fs in TRIGGER_GROUP_FEATURES.items()}
    return TRIGGER_GROUP_FEATURES
NEWS_STORE = Path(os.getenv("AIPHEED_E31_NEWS_STORE", "data/news_e31"))


@lru_cache(maxsize=256)
def news_topic_shares(code: str | None, quarter: str) -> tuple[dict, dict]:
    """Share of the validated (R1.1) titles of a province (code) or of the region (code None) in a quarter that fall
    in each of the five groups, and the title counts per group. Shares sum to <= 1 (untagged titles are unassigned)."""
    from app.ml.nlp.trigger_classifier import classify_triggers

    titles = [a["title"] or "" for a in record()["news"]["articles"]
              if a["quarter"] == quarter and (code is None or a["province_code"] == code)]
    weight = {g: 0.0 for g in TRIGGER_GROUP_FEATURES}
    counts = {g: 0 for g in TRIGGER_GROUP_FEATURES} | {"no_topic": 0, "titles": len(titles)}
    for t in titles:
        topics = [g for g in classify_triggers(t) if g in weight]
        if not topics:
            counts["no_topic"] += 1
        for g in topics:
            weight[g] += 1 / len(topics)
            counts[g] += 1
    shares = {g: (w / len(titles) if titles else 0.0) for g, w in weight.items()}
    return shares, counts


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
    groups = trigger_group_features()
    group = {g: sum(shap.get(f, 0.0) for f in fs) for g, fs in groups.items()}
    magnitude = {g: abs(v) for g, v in group.items()}
    # news inputs: split their |SHAP| (and, for the direction, their signed SHAP) by the titles' topics
    assigned = 0.0
    for level, feats in NEWS_FEATURES.items():
        shares, _ = news_topic_shares(code if level == "province" else None, ev_q)
        a = sum(abs(shap.get(f, 0.0)) for f in feats)
        s = sum(shap.get(f, 0.0) for f in feats)
        for g, w in shares.items():
            magnitude[g] += w * a
            group[g] += w * s
            assigned += w * a
    grouped = {f for fs in groups.values() for f in fs}
    other_abs = sum(abs(v) for f, v in shap.items() if f not in grouped) - assigned
    total_abs = sum(magnitude.values())
    grand = total_abs + other_abs
    # the part outside the five drivers, by source (|SHAP|, the bars' basis): the regional hunger survey inputs and
    # the latest published label built from it; news tone (FSSI) and news volume whose titles match no driver
    news = {f for fs in NEWS_FEATURES.values() for f in fs}
    survey = sum(abs(shap.get(f, 0.0)) for f in SURVEY_FEATURES)
    outside = {"survey": survey, "news_other": sum(abs(v) for f, v in shap.items() if f in news) - assigned
               + sum(abs(shap.get(f, 0.0)) for f in NEWS_TONE_FEATURES)}
    outside["rest"] = max(other_abs - outside["survey"] - outside["news_other"], 0.0)
    # group_shap keeps its sign (direction) and carries the attributed magnitude, so the panel's |group_shap|
    # normalisation gives each group's share of the attributed |SHAP|
    drivers = [{"driver_group": g, "driver_label": DRIVER_GROUP_LABELS[g],
                "group_shap": round(math.copysign(magnitude[g], v), 4),
                "direction": "increases_risk" if v >= 0 else "protective",
                "trigger_proportion": (round(cell[g] / cell["n"], 4) if cell and cell["n"] else None)}
               for g, v in group.items()]
    drivers.sort(key=lambda d: abs(d["group_shap"]), reverse=True)
    return {"drivers": drivers, "article_count": int(sum(cell[g] for g in group) if cell else 0),
            "other_pct": round(other_abs / grand * 100, 1) if grand else 0.0, "evidence_quarter": ev_q,
            "outside_abs": outside, "five_abs": total_abs}
