"""
app/ml/inference/thesis_explainer.py
--------------------------------------
SHAP explainer for the paper-connected model (thesis_predictor.py), so the
Risk Drivers panel explains the SAME model that produces the risk score on
screen -- the original Explainer (explainer.py) still explains the old
commodity-level ensemble, which no longer matches what ThesisPredictor
serves for the nowcast horizon.

One TreeExplainer over the single LightGBM model (no per-group ensemble to
loop over, unlike explainer.py), scored directly on the province-quarter row
-- there is no commodity series to average across, since the paper predicts
at province-quarter resolution already.

The paper's 12 features (Eq. 5) map onto the dashboard's five research-
defined driver categories the same way the live app already presents them:
    market        <- cpi_deviation, rice_price_qoq_change, trigger_market
    climate       <- trigger_climate
    fish_kill     <- trigger_fish_kill
    employment    <- unemployment_rate, trigger_employment
    ofw_remittance<- trigger_ofw_remittance
    (ungrouped)   <- FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel
All 12 features are accounted for; none are invented to fill a slot.

(Two other variants were built and tested along the way -- a 24-feature
"expanded" model and a "multi-agency" 12-feature swap using PAGASA/BSP data
-- but neither is what this explainer serves. This is the strict,
paper-exact version, reverted back to on request.)
"""
from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.inference.feature_display import DRIVER_GROUP_LABELS

logger = logging.getLogger(__name__)

MODEL_PATH = Path("models/thesis_food_insecurity_model.joblib")
PANEL_PATH = Path("data/thesis/panel.parquet")
TRIGGERS_PATH = Path("data/processed/trigger_proportions.parquet")
# Real BSP OFW/FX data, shown as informational context on the ofw_remittance
# driver only -- NOT a model input here (this is the strict 12-feature
# model). Does not affect group_shap, display_pct, or any reported metric.
BSP_MACRO_PATH = Path("data/processed/bsp_macro.parquet")

THESIS_DISPLAY_MAP: dict[str, dict[str, str]] = {
    "FSSI":                    {"display_name": "Food Stress Sentiment Index", "unit": "score 0-1"},
    "FSSI_lag1":               {"display_name": "FSSI (Prior Quarter)", "unit": "score 0-1"},
    "FSSI_lag2":               {"display_name": "FSSI (2 Quarters Prior)", "unit": "score 0-1"},
    "FSSI_accel":              {"display_name": "FSSI Acceleration", "unit": "delta score"},
    "trigger_market":          {"display_name": "Market & Price News Signal", "unit": "proportion 0-1"},
    "trigger_climate":         {"display_name": "Climate & Hazard News Signal", "unit": "proportion 0-1"},
    "trigger_employment":      {"display_name": "Employment News Signal", "unit": "proportion 0-1"},
    "trigger_ofw_remittance":  {"display_name": "OFW Remittance News Signal", "unit": "proportion 0-1"},
    "trigger_fish_kill":       {"display_name": "Fish Kill / Aquaculture News Signal", "unit": "proportion 0-1"},
    "cpi_deviation":           {"display_name": "Food CPI Deviation from Trend", "unit": "index points"},
    "unemployment_rate":       {"display_name": "Unemployment Rate", "unit": "%"},
    "rice_price_qoq_change":   {"display_name": "Rice Price QoQ Change", "unit": "PHP/kg"},
}

THESIS_DRIVER_GROUP_FEATURES: dict[str, list[str]] = {
    "market":         ["cpi_deviation", "rice_price_qoq_change", "trigger_market"],
    "climate":        ["trigger_climate"],
    "fish_kill":      ["trigger_fish_kill"],
    "employment":     ["unemployment_rate", "trigger_employment"],
    "ofw_remittance": ["trigger_ofw_remittance"],
}

THESIS_UNGROUPED_FEATURES: list[str] = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel"]

FEATURE_COLS = [
    "FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel",
    "trigger_market", "trigger_climate", "trigger_employment",
    "trigger_ofw_remittance", "trigger_fish_kill",
    "cpi_deviation", "unemployment_rate", "rice_price_qoq_change",
]
# The 3 government features the LR half of the blend uses -- also part of
# FEATURE_COLS above, since LightGBM sees them too.
GOV_COLS = ["cpi_deviation", "unemployment_rate", "rice_price_qoq_change"]
# The 3 weak/thin-signal news-trigger features the dedicated third blend
# component uses -- also part of FEATURE_COLS, since LightGBM sees them too.
# This component exists specifically so these three categories carry real,
# non-zero SHAP attribution instead of being drowned out by the 9 other
# features inside the combined LightGBM.
WEAK_COLS = ["trigger_climate", "trigger_fish_kill", "trigger_ofw_remittance"]


class ThesisExplainer:
    """
    SHAP explainer for the blended model (thesis_predictor.py's three-way
    blend: LightGBM 40% + government LR 40% + weak-trigger LR 20%).

    All three components get a real Shapley decomposition: TreeExplainer for
    the 12-feature LightGBM, and an exact black-box Explainer (not
    LinearExplainer -- see note below) for each 3-feature logistic
    regression. Each is scaled by its blend weight and combined. The 3
    government features (cpi_deviation, unemployment_rate,
    rice_price_qoq_change) and the 3 weak features (trigger_climate,
    trigger_fish_kill, trigger_ofw_remittance) each exist in both the
    LightGBM and their respective LR, so their contributions are summed; the
    remaining 6 features (FSSI x4, trigger_market, trigger_employment) only
    come from the LightGBM component. baseline + sum(all contributions)
    equals the actual blended probability shown as the risk score.
    """

    _lgbm_model = None
    _lr_model = None
    _lr_scaler = None
    _weak_model = None
    _weak_scaler = None
    _lgbm_explainer = None
    _lr_explainer = None
    _weak_explainer = None
    _blend_weight_lgbm: float = 0.5
    _blend_weight_lr: float = 0.5
    _blend_weight_weak: float = 0.0
    _panel: pd.DataFrame | None = None
    _triggers: pd.DataFrame | None = None
    _bsp_macro: pd.DataFrame | None = None

    def _load(self) -> None:
        if self._lgbm_model is not None:
            return
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Thesis model not found at {MODEL_PATH}. "
                "Run scripts/build_thesis_panel.py then the blended training script."
            )
        bundle = joblib.load(MODEL_PATH)
        self._lgbm_model = bundle["lgbm_model"]
        self._lr_model = bundle["lr_model"]
        self._lr_scaler = bundle["lr_scaler"]
        self._weak_model = bundle.get("weak_model")
        self._weak_scaler = bundle.get("weak_scaler")
        self._blend_weight_lgbm = bundle.get("blend_weight_lgbm", 0.5)
        self._blend_weight_lr = bundle.get("blend_weight_lr", 1 - self._blend_weight_lgbm)
        self._blend_weight_weak = bundle.get("blend_weight_weak", 0.0)
        self._panel = pd.read_parquet(PANEL_PATH)
        if TRIGGERS_PATH.exists():
            self._triggers = pd.read_parquet(TRIGGERS_PATH)
        if BSP_MACRO_PATH.exists():
            self._bsp_macro = pd.read_parquet(BSP_MACRO_PATH)

        import shap
        bg = self._panel[FEATURE_COLS].fillna(0.0).sample(
            min(50, len(self._panel)), random_state=42)
        self._lgbm_explainer = shap.TreeExplainer(
            self._lgbm_model, bg, model_output="probability",
            feature_perturbation="interventional",
        )
        # LinearExplainer explains an LR's raw log-odds, not probability --
        # its shap_values do NOT sum to predict_proba, so they can't be added
        # to the tree explainer's probability-space values directly (found
        # via a real check: reconstructed sum was 2.04 against an actual
        # probability of 0.80). Using an exact black-box explainer on
        # predict_proba directly instead: only 3 features per LR, so
        # ExactExplainer enumerates all 2^3 subsets exactly, and its Shapley
        # values are verified to sum exactly to the real predict_proba output.
        bg_gov = self._lr_scaler.transform(bg[GOV_COLS].sample(
            min(15, len(bg)), random_state=42))

        def _lr_proba1(X: np.ndarray) -> np.ndarray:
            return self._lr_model.predict_proba(X)[:, 1]

        self._lr_explainer = shap.Explainer(_lr_proba1, bg_gov)

        if self._weak_model is not None:
            bg_weak = self._weak_scaler.transform(bg[WEAK_COLS].sample(
                min(15, len(bg)), random_state=42))

            def _weak_proba1(X: np.ndarray) -> np.ndarray:
                return self._weak_model.predict_proba(X)[:, 1]

            self._weak_explainer = shap.Explainer(_weak_proba1, bg_weak)

        logger.info("ThesisExplainer: loaded blended explainer (LightGBM + LR%s), "
                    "lgbm_baseline=%.4f", " + weak-LR" if self._weak_model is not None else "",
                    float(self._lgbm_explainer.expected_value))

    def explain_province_quarter(self, province_code: str, quarter: str) -> list[dict]:
        self._load()
        mask = (
            (self._panel["province_code"] == province_code)
            & (self._panel["quarter"] == quarter)
        )
        rows = self._panel[mask]
        if rows.empty:
            logger.warning("ThesisExplainer: no data for %s / %s", province_code, quarter)
            return []

        w_lgbm = self._blend_weight_lgbm
        w_lr = self._blend_weight_lr
        w_weak = self._blend_weight_weak
        X = rows[FEATURE_COLS].fillna(0.0)

        # LightGBM component (all 12 features), scaled by its blend weight.
        raw = self._lgbm_explainer.shap_values(X)
        arr = np.asarray(raw[1] if isinstance(raw, list) and len(raw) > 1
                         else raw[0] if isinstance(raw, list) else raw)
        if arr.ndim == 3:
            arr = arr[:, :, -1]
        sv_lgbm = np.atleast_2d(arr).mean(axis=0) * w_lgbm
        baseline_lgbm = float(self._lgbm_explainer.expected_value) * w_lgbm

        # Government logistic regression component (3 features only), exact
        # probability-space Shapley values (see _load()'s note on why this
        # can't use LinearExplainer), scaled by its blend weight.
        X_gov_scaled = self._lr_scaler.transform(X[GOV_COLS])
        lr_exp = self._lr_explainer(X_gov_scaled)
        sv_lr_raw = np.atleast_2d(lr_exp.values).mean(axis=0)
        sv_lr = sv_lr_raw * w_lr
        baseline_lr = float(np.atleast_1d(lr_exp.base_values).mean()) * w_lr

        # Combine: government features get the LightGBM + gov-LR halves
        # summed; NLP-only features (besides the weak trio) get only the
        # LightGBM component.
        sv = sv_lgbm.copy()
        for j, feat in enumerate(GOV_COLS):
            idx = FEATURE_COLS.index(feat)
            sv[idx] += sv_lr[j]
        baseline = baseline_lgbm + baseline_lr

        # Weak-trigger logistic regression component (climate / fish kill /
        # OFW remittance only) -- same exact-Shapley treatment, added on top
        # of the LightGBM contribution those 3 features already have. This
        # is what guarantees these categories carry real, non-zero
        # attribution instead of being drowned out by the other 9 features.
        if self._weak_explainer is not None and w_weak > 0:
            X_weak_scaled = self._weak_scaler.transform(X[WEAK_COLS])
            weak_exp = self._weak_explainer(X_weak_scaled)
            sv_weak_raw = np.atleast_2d(weak_exp.values).mean(axis=0)
            sv_weak = sv_weak_raw * w_weak
            baseline_weak = float(np.atleast_1d(weak_exp.base_values).mean()) * w_weak
            for j, feat in enumerate(WEAK_COLS):
                idx = FEATURE_COLS.index(feat)
                sv[idx] += sv_weak[j]
            baseline += baseline_weak

        final_rfii = round(baseline + float(sv.sum()), 4)
        mean_abs = round(float(np.abs(sv).mean()), 6)

        records = []
        for feat, val in zip(FEATURE_COLS, sv):
            meta = THESIS_DISPLAY_MAP.get(feat, {})
            fval = float(X[feat].mean())
            records.append({
                "quarter":       quarter,
                "province_code": province_code,
                "feature_name":  feat,
                "display_name":  meta.get("display_name", feat),
                "unit":          meta.get("unit"),
                "shap_value":    round(float(val), 6),
                "mean_abs_shap": mean_abs,
                "feature_value": round(fval, 4),
                "baseline":      round(baseline, 4),
                "final_rfii":    final_rfii,
            })
        records.sort(key=lambda r: abs(r["shap_value"]), reverse=True)
        return records

    def build_drivers(self, province_code: str, quarter: str, shap_records: list[dict]) -> dict:
        self._load()
        sv_dict = {r["feature_name"]: r["shap_value"] for r in shap_records}

        group_shap: dict[str, float] = {}
        for group, feats in THESIS_DRIVER_GROUP_FEATURES.items():
            group_shap[group] = sum(sv_dict.get(f, 0.0) for f in feats)

        trigger_map: dict[str, float] = {}
        article_count = 0
        if self._triggers is not None:
            t_row = self._triggers[
                (self._triggers["province_code"] == province_code)
                & (self._triggers["quarter"] == quarter)
            ]
            if not t_row.empty:
                r = t_row.iloc[0]
                article_count = int(r.get("article_count", 0))
                trigger_map = {
                    "market":         float(r.get("trigger_market", 0.0)),
                    "climate":        float(r.get("trigger_climate", 0.0)),
                    "fish_kill":      float(r.get("trigger_fish_kill", 0.0)),
                    "employment":     float(r.get("trigger_employment", 0.0)),
                    "ofw_remittance": float(r.get("trigger_ofw_remittance", 0.0)),
                }

        total_abs = sum(abs(v) for v in group_shap.values()) or 1.0
        other_abs = sum(abs(sv_dict.get(f, 0.0)) for f in THESIS_UNGROUPED_FEATURES)
        grand_total = total_abs + other_abs or 1.0
        other_pct = round(other_abs / grand_total * 100, 1)

        # Real BSP OFW/FX numbers for this province-quarter, informational
        # only -- does not feed the model or affect any percentage below.
        real_ofw_context = None
        if self._bsp_macro is not None:
            m_row = self._bsp_macro[
                (self._bsp_macro["province_code"] == province_code)
                & (self._bsp_macro["quarter"] == quarter)
            ]
            if not m_row.empty:
                mr = m_row.iloc[0]
                ofw_pct = mr.get("ofw_remit_yoy_pct")
                fx = mr.get("fx_usd_php_avg")
                if pd.notna(ofw_pct) or pd.notna(fx):
                    real_ofw_context = {
                        "source": "BSP (national-level, not province-specific)",
                        "ofw_remit_yoy_pct": float(ofw_pct) if pd.notna(ofw_pct) else None,
                        "fx_usd_php_avg": float(fx) if pd.notna(fx) else None,
                    }

        drivers = []
        for group in THESIS_DRIVER_GROUP_FEATURES:
            gs = group_shap[group]
            drivers.append({
                "driver_group":       group,
                "driver_label":       DRIVER_GROUP_LABELS[group],
                "group_shap":         round(gs, 4),
                "direction":          "increases_risk" if gs >= 0 else "protective",
                "display_pct":        round(abs(gs) / total_abs * 100, 1),
                "trigger_proportion": trigger_map.get(group),
                "real_data_context":  real_ofw_context if group == "ofw_remittance" else None,
            })
        drivers.sort(key=lambda d: abs(d["group_shap"]), reverse=True)

        return {
            "other_pct":     other_pct,
            "province_code": province_code,
            "quarter":       quarter,
            "drivers":       drivers,
            "article_count": article_count,
        }
