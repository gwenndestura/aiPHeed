"""
app/ml/inference/explainer.py
------------------------------
Equation 7 — SHAP Forecast Attribution.

The SHAP TreeExplainer decomposes each LightGBM forecast into an additive sum
of exact per-feature contributions:

    f(X_t) = phi_0 + SUM_{j=1..M} phi_j

where phi_0 is the baseline expected forecast — the mean prediction across all
training instances, with no feature information — and each phi_j quantifies how
far feature j shifted the prediction above or below that baseline. M is the
number of features in the final selected matrix (Section 3.3.2.7).

Explaining the served model directly means the attribution reproduces the
forecast exactly rather than approximating it: the same LightGBM that produced
the probability produces the Shapley values.

Every published forecast carries its explanation by default (Section 3.6, the
«include» relationship from viewing province forecasts), so a non-technical
reviewer at the partner agencies can see which indicators moved a prediction
before acting on it.

Outputs two record types:

1. shap_records  (stored in DB, served as SHAPResponse)
   One row per feature per province-quarter. Includes display_name,
   feature_group, feature_value, unit, baseline, and final_rfii.

2. driver_records  (derived on-the-fly from shap_records, served as DriversResponse)
   One row per driver group per province-quarter.

Usage:
    from app.ml.inference.explainer import Explainer
    explainer = Explainer()
    shap_records   = explainer.explain_quarter("2025-Q4")
    driver_records = explainer.build_drivers("PH040300000", "2025-Q4", shap_records)
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.inference.feature_display import (
    DRIVER_GROUP_FEATURES,
    DRIVER_GROUP_LABELS,
    FEATURE_DISPLAY_MAP,
)

logger = logging.getLogger(__name__)

MODEL_PATH    = Path("models/lgbm_best.pkl")
FEATURES_PATH = Path("data/processed/features_fused.parquet")
TRIGGERS_PATH = Path("data/processed/trigger_proportions.parquet")

# The feature list travels inside the model bundle so serving, explaining and
# training cannot drift apart.

PROVINCE_NAMES: dict[str, str] = {
    "PH040100000": "Cavite",
    "PH040200000": "Laguna",
    "PH040300000": "Quezon",
    "PH040400000": "Rizal",
    "PH040500000": "Batangas",
}


class Explainer:
    """
    Lazy-loading SHAP TreeExplainer over the served LightGBM model.

    Uses interventional perturbation with model_output='probability' so the
    Shapley values are directly interpretable as probability contributions:

        phi_0 + sum(phi_j) = predicted risk_probability     (Equation 7)

    phi_0 is the baseline expected forecast across the training instances.
    """

    _model = None
    _explainer = None
    _features: pd.DataFrame | None = None
    _triggers: pd.DataFrame | None = None
    _baseline: float | None = None
    _feature_cols: list[str] | None = None

    def _load(self) -> None:
        if self._model is not None:
            return

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. Run "
                "app.ml.training.trainer.train_model() first (Algorithm 4)."
            )
        bundle = joblib.load(MODEL_PATH)
        if isinstance(bundle, dict):
            self._model = bundle["model"]
            self._feature_cols = list(bundle["feature_cols"])
        else:
            from app.ml.features.feature_selector import load_selected

            self._model = bundle
            self._feature_cols = load_selected()
        logger.info(
            "Explainer: model loaded from %s (%d features)",
            MODEL_PATH, len(self._feature_cols),
        )

        # The same fused matrix the predictor scores, so the two cannot diverge.
        if not FEATURES_PATH.exists():
            raise FileNotFoundError(
                f"{FEATURES_PATH} not found. Run feature_matrix.build_feature_matrix()."
            )
        self._features = pd.read_parquet(FEATURES_PATH)
        logger.info("Explainer: feature matrix loaded (%d province-quarters)",
                    len(self._features))

        if TRIGGERS_PATH.exists():
            self._triggers = pd.read_parquet(TRIGGERS_PATH)

        # Background sample drawn from the matrix the model was trained on, so
        # phi_0 is the mean prediction across training instances as Equation 7
        # defines it.
        import shap

        bg = self._features[self._feature_cols].fillna(0.0)
        bg = bg.sample(min(100, len(bg)), random_state=42)
        self._explainer = shap.TreeExplainer(
            self._model, bg,
            model_output="probability",
            feature_perturbation="interventional",
        )
        self._baseline = float(np.atleast_1d(self._explainer.expected_value)[-1])
        logger.info("Explainer ready: baseline phi_0 = %.4f", self._baseline)

    # -- Province-quarter SHAP --------------------------------------------

    def explain_province_quarter(
        self,
        province_code: str,
        quarter: str,
    ) -> list[dict]:
        """
        Compute exact per-feature Shapley values for one province-quarter
        (Equation 7).

        Returns
        -------
        list[dict]  — one dict per feature, sorted by |shap_value|.
        Each dict contains:
            quarter, province_code,
            feature_name, display_name, feature_group, unit,
            shap_value, mean_abs_shap, feature_value,
            baseline, final_rfii

        baseline is phi_0; final_rfii is phi_0 + sum(phi_j), which reproduces
        the served risk probability for that province-quarter.
        """
        self._load()

        if self._features is None:
            return []

        mask = (
            (self._features["province_code"] == province_code)
            & (self._features["quarter"] == quarter)
        )
        rows = self._features[mask]
        if rows.empty:
            logger.warning(
                "explain_province_quarter: no data for %s / %s",
                province_code, quarter,
            )
            return []

        cols = self._feature_cols
        X = rows[cols].fillna(0.0)

        raw = self._explainer.shap_values(X)
        arr = np.asarray(raw[-1] if isinstance(raw, list) else raw)
        if arr.ndim == 3:                 # (rows, features, classes)
            arr = arr[:, :, -1]
        sv = np.atleast_2d(arr)[0]        # one province-quarter, one row

        baseline   = float(self._baseline)
        final_rfii = round(baseline + float(sv.sum()), 4)
        mean_abs   = round(float(np.abs(sv).mean()), 6)

        records = []
        for feat, val in zip(cols, sv):
            meta = FEATURE_DISPLAY_MAP.get(feat, {})
            fval = float(X[feat].iloc[0]) if feat in X.columns else None
            records.append({
                "quarter":         quarter,
                "province_code":   province_code,
                "feature_name":    feat,
                "display_name":    meta.get("display_name", feat),
                "feature_group":   meta.get("feature_group", "other"),
                "unit":            meta.get("unit"),
                "shap_value":      round(float(val), 6),
                "mean_abs_shap":   mean_abs,
                "feature_value":   round(float(fval), 4) if fval is not None else None,
                "baseline":        round(baseline, 4),
                "final_rfii":      final_rfii,
            })

        records.sort(key=lambda r: abs(r["shap_value"]), reverse=True)
        return records

    def explain_quarter(self, quarter: str) -> list[dict]:
        """Explain all 5 provinces for a given quarter."""
        all_records = []
        for province_code in PROVINCE_NAMES:
            all_records.extend(
                self.explain_province_quarter(province_code, quarter)
            )
        return all_records

    # ── Driver group aggregation ──────────────────────────────────────────

    def build_drivers(
        self,
        province_code: str,
        quarter: str,
        shap_records: list[dict],
    ) -> dict:
        """
        Aggregate SHAP records into the driver groups for the Risk Drivers panel.

        Parameters
        ----------
        province_code  : str
        quarter        : str
        shap_records   : output of explain_province_quarter().

        Returns
        -------
        dict  matching DriversResponse schema:
            province_code, quarter,
            drivers: list[DriverRecord dicts],
            article_count: int
        """
        self._load()

        sv_dict = {r["feature_name"]: r["shap_value"] for r in shap_records}

        # ── Group SHAP ────────────────────────────────────────────────────
        group_shap: dict[str, float] = {}
        for group, feats in DRIVER_GROUP_FEATURES.items():
            group_shap[group] = sum(sv_dict.get(f, 0.0) for f in feats)

        # ── Trigger proportions from NLP corpus ───────────────────────────
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
                    "market":        float(r.get("trigger_market", 0.0)),
                    "climate":       float(r.get("trigger_climate", 0.0)),
                    "employment":    float(r.get("trigger_employment", 0.0)),
                    "macro_ofw":     float(r.get("trigger_ofw_remittance", 0.0)),
                    "nlp_sentiment": float(r.get("trigger_fish_kill", 0.0)),
                }

        # ── Build driver records ───────────────────────────────────────────
        total_abs = sum(abs(v) for v in group_shap.values()) or 1.0

        drivers = []
        for group in DRIVER_GROUP_FEATURES:
            gs = group_shap[group]
            drivers.append({
                "driver_group":       group,
                "driver_label":       DRIVER_GROUP_LABELS[group],
                "group_shap":         round(gs, 4),
                "direction":          "increases_risk" if gs >= 0 else "protective",
                "display_pct":        round(abs(gs) / total_abs * 100, 1),
                "trigger_proportion": trigger_map.get(group),
            })

        # Sort by abs(group_shap) descending
        drivers.sort(key=lambda d: abs(d["group_shap"]), reverse=True)

        return {
            "province_code": province_code,
            "quarter":       quarter,
            "drivers":       drivers,
            "article_count": article_count,
        }
