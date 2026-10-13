"""
app/ml/inference/e20_forecast.py
---------------------------------
Serves the E20 2027-Q1 forecast next to the nowcast timeline.

Reads data/e20/serving.json, exported by the E19/E20 experiments
(aipheed-backend-aligned/experiments/2026-10-13_E20_2027Q1_Forecast/). Only
the PUBLISHED forecast leads are served -- today that is lead 5, 2027-Q1 from
the 2025-Q4 information cutoff. The unpublished 2026 leads are not.

What the score is: the probability that the province's food-CPI inflation is
above the CALABARZON five-province average in the target quarter (relative
food-price pressure). It is a different target and a different model from the
nowcast, so the dashboard labels every 2027-Q1 surface as a forecast and never
computes a quarter-on-quarter change against a nowcast quarter.

Optional context files:
    data/e21/forecast_uncertainty_2027Q1.json  -- refit parameter uncertainty
    data/e22/nns_fies_verified.json            -- NNS FIES context figure
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SERVING_PATH = Path("data/e20/serving.json")
UNCERTAINTY_PATH = Path("data/e21/forecast_uncertainty_2027Q1.json")
NNS_VERIFIED_PATH = Path("data/e22/nns_fies_verified.json")

DRIVER_GROUP_FEATURES: dict[str, list[str]] = {
    "market": ["F_t", "F_tm1", "D_t", "D_tm1", "dF_t", "rice_qoq_t", "trigger_market"],
    "climate": ["trigger_climate"],
    "fish_kill": ["trigger_fish_kill"],
    "employment": ["unemp_tm1", "trigger_employment"],
    "ofw_remittance": ["trigger_ofw_remittance"],
}
# The FSSI block is real model input but none of the five driver categories;
# it is reported as `other_pct`, the same way the nowcast reports its extras.
UNGROUPED = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"]
DRIVER_GROUP_LABELS = {
    "market": "Market / Prices",
    "climate": "Climate Stress",
    "fish_kill": "Fish Kill",
    "employment": "Employment",
    "ofw_remittance": "OFW Remittance",
}
TRIGGER_COLUMN = {g: f"trigger_{g}" for g in DRIVER_GROUP_FEATURES}


def news_coverage(article_count: int | None) -> str | None:
    """'none' (0 articles), 'limited' (1-4) or 'ok' (5+) in the origin quarter."""
    if article_count is None:
        return None
    if article_count <= 0:
        return "none"
    return "ok" if article_count >= 5 else "limited"


def nns_context() -> dict | None:
    """The latest verified CALABARZON FIES figure, as context -- not validation."""
    if not NNS_VERIFIED_PATH.exists():
        return None
    data = json.loads(NNS_VERIFIED_PATH.read_text(encoding="utf-8"))
    region = [f for f in data["figures"] if f["level"] == "region" and "CALABARZON" in f["area"]]
    if not region:
        return None
    national = {f["year"]: f for f in data["figures"] if f["level"] == "national"}
    r = max(region, key=lambda f: f["year"])
    nat = national.get(r["year"])
    text = (f"Context, not validation: in {r['year']}, {r['value_pct']}% of CALABARZON households were "
            f"moderately or severely food insecure (FIES; {r['ci_level']} CI {r['ci'][0]}-{r['ci'][1]}), "
            "the lowest of all regions"
            + (f", against {nat['value_pct']}% nationally" if nat else "")
            + ". The forecast ranks provinces within the region on relative food-price pressure; "
              "it says nothing about absolute food insecurity.")
    return {"text": text, "source": r["source"], "url": r["url"], "year": r["year"],
            "valuePct": r["value_pct"]}


class E20Forecast:
    """Singleton over the serving file; it is read once."""

    _instance: "E20Forecast | None" = None
    _serving: dict | None = None

    def __new__(cls) -> "E20Forecast":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self) -> dict | None:
        """The serving payload, or None when it has not been exported."""
        if self._serving is None and SERVING_PATH.exists():
            self._serving = json.loads(SERVING_PATH.read_text(encoding="utf-8"))
            logger.info("E20Forecast: serving loaded (forecast %s, cutoff %s)",
                        self._serving["meta"].get("forecast_period"),
                        self._serving["meta"].get("information_cutoff"))
        return self._serving

    @property
    def meta(self) -> dict:
        return (self.load() or {}).get("meta", {})

    def _published_leads(self) -> list[dict]:
        s = self.load()
        if s is None:
            return []
        return [v for v in s["leads"].values() if v.get("published", True)
                and v.get("experiment") == "E20"]

    def forecast_quarters(self) -> dict[str, dict]:
        """Target quarter -> its published lead."""
        return {v["target_quarter"]: v for v in self._published_leads()}

    def is_forecast_quarter(self, quarter: str) -> bool:
        return quarter in self.forecast_quarters()

    def origin_quarter(self, quarter: str) -> str | None:
        """The information-cutoff quarter a forecast quarter was made from."""
        lead = self.forecast_quarters().get(quarter)
        if lead is None or not lead["forecasts"]:
            return None
        return lead["forecasts"][0]["origin_quarter"]

    # ------------------------------------------------------------- records

    def _uncertainty(self, province_code: str, lead: dict) -> dict | None:
        if not UNCERTAINTY_PATH.exists():
            return None
        u = json.loads(UNCERTAINTY_PATH.read_text(encoding="utf-8"))
        # Only when it describes the model actually served for this quarter.
        if u.get("target_quarter") != lead["target_quarter"] or u.get("model") != lead["selected_model"]:
            return None
        p = u["provinces"].get(province_code)
        return None if p is None else {**p, "n_refits": u["n_refits"], "note": u["note"]}

    def _status_note(self, lead: dict) -> str:
        m = lead["metrics_primary"].get(lead["selected_model"], {})
        auc = m.get("roc_auc")
        ci = m.get("roc_auc_ci95") or [None, None]
        auc_txt = (f"walk-forward ROC-AUC {auc:.2f}, 95% CI {ci[0]:.2f}-{ci[1]:.2f}"
                   if isinstance(auc, (int, float)) and None not in ci else "no AUC")
        return (f"{lead['lead']}-quarter-ahead forecast from the {self.meta.get('information_cutoff')} "
                f"information cutoff by {lead['selected_model_name']} (lowest Brier score of all "
                f"candidates in a {lead.get('evaluation_quarters')}-quarter back-test; {auc_txt}). "
                f"Status: {lead.get('status_label', lead['status'])}. Not validated.")

    def forecast_quarter(self, quarter: str) -> list[dict]:
        """Province records in the shape the dashboard's nowcast engine returns."""
        lead = self.forecast_quarters().get(quarter)
        if lead is None:
            return []
        thr = self.meta.get("threshold", 0.5)
        note = self._status_note(lead)
        out = []
        for f in lead["forecasts"]:
            prob = float(f["probability"])
            out.append({
                "province_code": f["province_code"],
                "province_name": f["province_name"],
                "quarter": quarter,
                "risk_probability": round(prob, 4),
                "risk_label": "HIGH" if prob >= thr else "LOW",
                "data_sufficiency_flag": ("LIMITED_SIGNAL"
                                          if f["data_sufficiency"] == "LIMITED_SIGNAL" else None),
                "series_monitored": None,
                "series_at_risk": None,
                "series_needing_review": None,
                "top_at_risk_commodities": [],
                "is_forecast": True,
                "lead": lead["lead"],
                "origin_quarter": f["origin_quarter"],
                "model_id": lead["selected_model"],
                "model_status": lead["status"],
                "confidence_note": note,
                "article_count": f.get("article_count"),
                "news_coverage": news_coverage(f.get("article_count")),
                "uncertainty": self._uncertainty(f["province_code"], lead),
            })
        out.sort(key=lambda x: x["risk_probability"], reverse=True)
        return out

    # ------------------------------------------------------------- drivers

    def build_drivers(self, province_code: str, quarter: str) -> dict:
        """
        Grouped SHAP for a forecast quarter, in ThesisExplainer.build_drivers()'s
        shape. Values are the served model's own SHAP (exact linear SHAP for a
        logistic regression), stored at export time.
        """
        lead = self.forecast_quarters().get(quarter)
        row = None
        if lead is not None:
            row = next((f for f in lead["forecasts"] if f["province_code"] == province_code), None)
        values = (row or {}).get("shap", {}).get("values", {})
        feats = (row or {}).get("features", {})

        group = {g: sum(values.get(f, 0.0) for f in fs) for g, fs in DRIVER_GROUP_FEATURES.items()}
        total_abs = sum(abs(v) for v in group.values())
        other_abs = sum(abs(values.get(f, 0.0)) for f in UNGROUPED)
        grand = total_abs + other_abs
        drivers = [{
            "driver_group": g,
            "driver_label": DRIVER_GROUP_LABELS[g],
            "group_shap": round(v, 4),
            "direction": "increases_risk" if v >= 0 else "protective",
            "display_pct": round(abs(v) / total_abs * 100, 1) if total_abs else 0.0,
            "trigger_proportion": feats.get(TRIGGER_COLUMN[g]),
            "real_data_context": None,
        } for g, v in group.items()]
        drivers.sort(key=lambda d: abs(d["group_shap"]), reverse=True)
        return {
            "province_code": province_code,
            "quarter": quarter,
            "available": bool(values),
            "other_pct": round(other_abs / grand * 100, 1) if grand else 0.0,
            "drivers": drivers,
            "article_count": int((row or {}).get("article_count") or 0),
        }

    # ------------------------------------------------------------- banner

    def forecast_meta(self, shown_quarters: frozenset[str] = frozenset()) -> dict | None:
        """
        Everything the dashboard's forecast banner needs about the headline forecast.

        `shown_quarters` are quarters the dashboard already scores another way
        (the nowcast); an unpublished E20 lead for one of them is not listed
        as missing.
        """
        leads = self._published_leads()
        if not leads:
            return None
        lead = max(leads, key=lambda v: v["lead"])
        m = self.meta
        sel = lead["metrics_primary"][lead["selected_model"]]
        s = self.load() or {}
        not_displayed = []
        for h, v in sorted(s.get("leads", {}).items(), key=lambda kv: int(kv[0])):
            if v.get("published", True) or v["target_quarter"] in shown_quarters:
                continue
            # The reason is stated from the lead's own back-test, not the stored
            # superseded_reason, which calls a quarter "elapsed" by export date.
            vm = v["metrics_primary"][v["selected_model"]]
            ci = vm.get("roc_auc_ci95") or [0.0, 0.0]
            not_displayed.append({
                "lead": int(h), "targetQuarter": v["target_quarter"],
                "reason": (f"Not published: no demonstrated ranking skill {h} quarters ahead "
                           f"(back-test ROC-AUC {vm['roc_auc']:.2f}, 95% CI {ci[0]:.2f}-{ci[1]:.2f})."),
            })
        probs = [f["probability"] for f in lead["forecasts"]]
        return {
            "period": lead["target_quarter"],
            "periodLabel": m.get("forecast_period_label") or lead["target_quarter"],
            "generatedAt": m.get("generated_at"),
            "informationCutoff": m.get("information_cutoff", m.get("trained_through")),
            "informationCutoffReason": m.get("information_cutoff_reason"),
            "latestEligibleObservations": m.get("latest_eligible_observations"),
            "horizonQuarters": lead["lead"],
            "horizonCalculation": m.get("horizon_calculation"),
            "model": lead["selected_model"],
            "modelName": lead["selected_model_name"],
            "selectionRule": m.get("selection_rule"),
            "status": lead["status"],
            "statusLabel": lead.get("status_label", lead["status"]),
            "backtest": {k: sel.get(k) for k in ("accuracy", "precision", "recall", "f1",
                                                  "roc_auc", "roc_auc_ci95", "brier", "n")},
            "evaluationQuarters": lead.get("evaluation_quarters"),
            "differentiatesProvinces": lead.get("differentiates_provinces", True),
            "probabilityRange": [round(min(probs), 4), round(max(probs), 4)],
            "limitations": m.get("limitations", []),
            "regressionForecasts": m.get("regression_forecasts"),
            "target": m.get("target"),
            "notDisplayed": not_displayed,
            "experiment": "E20",
            "context": nns_context(),
        }
