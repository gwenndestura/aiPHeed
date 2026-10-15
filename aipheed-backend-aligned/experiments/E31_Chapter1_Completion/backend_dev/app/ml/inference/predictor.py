"""
app/ml/inference/predictor.py
------------------------------
Province-level food insecurity forecast predictor.

Serves the approved model: the LightGBM binary classifier of Equation 5,

    y_hat(p, t+h) = F[ FSSI(t), FSSI(t-1), FSSI(t-2), dFSSI(t),
                       trigger(t), CPI_dev(t), unemp(t), rice_change(t) ]

which outputs the probability that province p is at HIGH food insecurity risk
h quarters ahead, where h is the Maximum Reliable Lead Time discovered by
Algorithm 3 and carried inside the model bundle. One model, one horizon
(Rule 2, Single Forecast Horizon).

Every forecast carries, per Rules 5 and 6:
  * an explicit horizon label (forecast_horizon_quarters)
  * a data sufficiency flag — LIMITED_SIGNAL when the province-quarter holds
    fewer than five geocoded articles, propagated to all municipal outputs
  * a verification date

Rule 7, Early Warning Trigger: an alert fires when a province's forecast
exceeds that province's rolling historical threshold. Human confirmation is
required before the partner agencies are notified, so detect_alerts() only
stages records — it never publishes.

Loads models/lgbm_best.pkl, written by app/ml/training/trainer.py. The bundle
carries the model, the Section 3.3.2.7 feature list and the discovered lead
time, so serving cannot drift from training.

Usage:
    from app.ml.inference.predictor import Predictor
    predictor = Predictor()
    forecasts = predictor.forecast_quarter("2025-Q4")
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_PATH        = Path("models/lgbm_best.pkl")
FEATURES_PATH     = Path("data/processed/features_fused.parquet")
BIAS_WEIGHTS_PATH = Path("data/processed/bias_weights.parquet")

PROVINCE_NAMES: dict[str, str] = {
    "PH040100000": "Cavite",
    "PH040200000": "Laguna",
    "PH040300000": "Quezon",
    "PH040400000": "Rizal",
    "PH040500000": "Batangas",
}

# Section 3.3.2.3 / Rule 5: province-quarters with fewer than five geocoded
# articles are flagged LIMITED_SIGNAL, propagated to all 142 municipal outputs.
DATA_SUFFICIENCY_MIN_ARTICLES = 5

# A province is classified HIGH when its risk probability is at or above this
# value — the natural cut for a binary classifier trained on a median-split
# label (Equation 3 guarantees a balanced class split).
RISK_CUTOFF = 0.50

# ---------------------------------------------------------------------------
# Rule 7 — Early Warning Trigger
# ---------------------------------------------------------------------------
# "An alert will fire when a province's forecast exceeds the rolling historical
# threshold." The threshold is that province's own rolling history of published
# risk probabilities: mean + 1 standard deviation over the trailing window. A
# province is compared against its own past, not against the other provinces,
# so a structurally higher-risk province does not alert every quarter.
ALERT_ROLLING_WINDOW = 8   # trailing quarters forming the rolling history
ALERT_ROLLING_MIN    = 4   # minimum history before a threshold can be computed
ALERT_SIGMA          = 1.0 # standard deviations above the rolling mean


VALIDATION_STATEMENT = (
    "EXPERIMENTAL relative risk estimate, not validated: no model has beaten the persistence, calibrated-"
    "persistence, always-HIGH and climatology baselines on unseen quarters, and accuracy above 75% is not evidence "
    "of skill here because a rule that always says HIGH scores higher. Not an official food insecurity "
    "classification."
)

class Predictor:
    """Singleton: the model bundle and feature matrix are loaded once."""

    _instance: Predictor | None = None

    def __new__(cls) -> Predictor:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
            cls._instance._feature_cols = None
            cls._instance._lead_time = None
            cls._instance._features = None
            cls._instance._bias = None
        return cls._instance

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load the model bundle, the fused feature matrix and the bias weights."""
        if self._model is not None:
            return

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"{MODEL_PATH} not found. Run app.ml.training.trainer.train_model() "
                "to produce the production model (Algorithm 4)."
            )

        bundle = joblib.load(MODEL_PATH)
        if isinstance(bundle, dict):
            self._model = bundle["model"]
            self._feature_cols = list(bundle["feature_cols"])
            self._lead_time = int(bundle.get("max_reliable_lead_time", 0))
        else:
            # A bare estimator from an older run: fall back to the selected set.
            from app.ml.features.feature_selector import load_selected

            self._model = bundle
            self._feature_cols = load_selected()
            self._lead_time = 0
            logger.warning(
                "lgbm_best.pkl holds a bare estimator with no feature list; "
                "falling back to selected_features.json. Re-run training to "
                "regenerate a self-describing bundle."
            )

        if not FEATURES_PATH.exists():
            raise FileNotFoundError(
                f"{FEATURES_PATH} not found. Run feature_matrix.build_feature_matrix() first."
            )
        self._features = pd.read_parquet(FEATURES_PATH)

        self._bias = (
            pd.read_parquet(BIAS_WEIGHTS_PATH)
            if BIAS_WEIGHTS_PATH.exists() else None
        )
        if self._bias is None:
            logger.warning(
                "%s not found — data sufficiency flags cannot be computed and "
                "will be reported as None.", BIAS_WEIGHTS_PATH,
            )

        logger.info(
            "Predictor ready: %d features, Maximum Reliable Lead Time = %d quarter(s)",
            len(self._feature_cols), self._lead_time,
        )

    # ------------------------------------------------------------------
    # Horizon and provenance labelling (Rule 6)
    # ------------------------------------------------------------------

    @property
    def lead_time(self) -> int:
        """The Maximum Reliable Lead Time, in quarters, from Algorithm 3."""
        self.load()
        return int(self._lead_time)

    def horizon_label(self) -> str:
        """The explicit horizon label Rule 6 requires on every forecast."""
        k = self.lead_time
        if k == 0:
            return ("Same-quarter estimate (lead 0): not a forecast. No forward lead time has been validated "
                    "against the baselines.")
        return f"{k} quarter(s) ahead (not validated)"

    def confidence_statement(self) -> str:
        """The confidence statement Rule 6 requires on every forecast."""
        # E27 fix: accuracy above 75% is not evidence of skill on these quarters (always-HIGH scores 0.925 at
        # lead 1, persistence 0.875), so it is never quoted as validation.
        return VALIDATION_STATEMENT + (" Reported as a same-quarter estimate, not a forecast."
                                       if self.lead_time == 0 else "")

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _rows_for(self, quarter: str) -> pd.DataFrame:
        """The feature rows for one quarter, over the selected feature set."""
        rows = self._features[self._features["quarter"] == quarter]
        if rows.empty:
            return rows
        missing = [c for c in self._feature_cols if c not in rows.columns]
        if missing:
            raise ValueError(
                f"Feature matrix is missing model columns {missing}. Rebuild it "
                "with feature_matrix.build_feature_matrix()."
            )
        return rows

    def forecast_quarter(self, quarter: str) -> list[dict]:
        """
        Province-level forecasts for one quarter (Equation 5).

        Returns one dict per CALABARZON province, sorted by risk_probability
        descending, each carrying:
            province_code, province_name, quarter, risk_probability, risk_label,
            data_sufficiency_flag, forecast_horizon_quarters, horizon_label,
            confidence_statement, verification_date
        """
        self.load()

        rows = self._rows_for(quarter)
        if rows.empty:
            logger.warning("forecast_quarter: no feature rows for %s.", quarter)
            return []

        X = rows[self._feature_cols]
        probs = self._model.predict_proba(X)[:, 1]

        verified = datetime.now(timezone.utc).date().isoformat()
        results: list[dict] = []
        for (_, row), prob in zip(rows.iterrows(), probs):
            province_code = row["province_code"]
            results.append({
                "province_code":  province_code,
                "province_name":  PROVINCE_NAMES.get(province_code, province_code),
                "quarter":        quarter,
                "risk_probability": round(float(prob), 4),
                "risk_label":     "HIGH" if prob >= RISK_CUTOFF else "LOW",
                "data_sufficiency_flag": self._data_sufficiency(province_code, quarter),
                "forecast_horizon_quarters": self.lead_time,
                "horizon_label":       self.horizon_label(),
                "confidence_statement": self.confidence_statement(),
                "verification_date":   verified,
            })

        results.sort(key=lambda r: r["risk_probability"], reverse=True)
        logger.info("forecast_quarter(%s): %d provinces forecast", quarter, len(results))
        return results

    def forecast_all_quarters(self) -> list[dict]:
        """Province forecasts for every scoreable quarter, oldest first."""
        out: list[dict] = []
        for q in self.available_quarters():
            out.extend(self.forecast_quarter(q))
        return out

    def available_quarters(self) -> list[str]:
        """Quarters the feature matrix can score, oldest first."""
        self.load()
        return sorted(self._features["quarter"].unique().tolist())

    # ------------------------------------------------------------------
    # Rule 7 — Early Warning Trigger
    # ------------------------------------------------------------------

    def rolling_threshold(self, history: list[float]) -> float | None:
        """
        A province's rolling historical alert threshold: the mean plus one
        standard deviation of its trailing published risk probabilities.

        Returns None when the province has fewer than ALERT_ROLLING_MIN prior
        quarters — no threshold can be formed, so no alert can fire.
        """
        window = [float(v) for v in history][-ALERT_ROLLING_WINDOW:]
        if len(window) < ALERT_ROLLING_MIN:
            return None
        mean = float(np.mean(window))
        sd = float(np.std(window, ddof=1)) if len(window) > 1 else 0.0
        return mean + ALERT_SIGMA * sd

    def detect_alerts(
        self,
        current_forecasts: list[dict],
        history: dict[str, list[float]] | None = None,
        prev_forecasts: list[dict] | None = None,
    ) -> list[dict]:
        """
        Stage early warning alerts for provinces whose forecast exceeds their
        own rolling historical threshold (Rule 7).

        Parameters
        ----------
        current_forecasts : output of forecast_quarter() for the current cycle.
        history           : {province_code: [risk_probability, ...]} in
                            chronological order, oldest first, EXCLUDING the
                            current quarter. Reconstructed from the feature
                            matrix when not supplied.
        prev_forecasts    : the previous quarter's forecasts, used only to
                            record prev_risk_probability and risk_delta on the
                            staged row for the reviewer's context.

        Every returned record is STAGED. Nothing is published and no partner
        agency is notified until an administrator confirms it.
        """
        self.load()

        if history is None:
            history = self._history_from_matrix(
                exclude_quarter=current_forecasts[0]["quarter"] if current_forecasts else None
            )

        prev_by_province = {
            f["province_code"]: f["risk_probability"] for f in (prev_forecasts or [])
        }

        alerts: list[dict] = []
        for f in current_forecasts:
            province_code = f["province_code"]
            threshold = self.rolling_threshold(history.get(province_code, []))
            if threshold is None:
                logger.info(
                    "%s / %s: fewer than %d prior quarters — no rolling threshold, "
                    "no alert.", province_code, f["quarter"], ALERT_ROLLING_MIN,
                )
                continue

            current_prob = float(f["risk_probability"])
            if current_prob < threshold:
                continue

            prev_prob = prev_by_province.get(province_code)
            alerts.append({
                "quarter":               f["quarter"],
                "province_code":         province_code,
                "province_name":         f["province_name"],
                "threshold_exceeded":    True,
                "risk_probability":      round(current_prob, 4),
                "rolling_threshold":     round(threshold, 4),
                "prev_risk_probability": (
                    round(float(prev_prob), 4) if prev_prob is not None else None
                ),
                "risk_delta": (
                    round(current_prob - float(prev_prob), 4)
                    if prev_prob is not None else None
                ),
                "alert_reason": "ROLLING_THRESHOLD_EXCEEDED",
                "confirmed": False,
                "dismissed": False,
            })
            logger.info(
                "ALERT staged — %s | %s | probability %.3f >= rolling threshold %.3f",
                f["province_name"], f["quarter"], current_prob, threshold,
            )

        if not alerts:
            logger.info(
                "No province exceeded its rolling threshold — the cycle concludes "
                "with no public-facing alert."
            )
        return alerts

    def _history_from_matrix(self, exclude_quarter: str | None) -> dict[str, list[float]]:
        """Score every earlier quarter to reconstruct each province's history."""
        history: dict[str, list[float]] = {}
        for q in self.available_quarters():
            if exclude_quarter is not None and q >= exclude_quarter:
                continue
            for f in self.forecast_quarter(q):
                history.setdefault(f["province_code"], []).append(f["risk_probability"])
        return history

    # ------------------------------------------------------------------
    # Rule 5 — Data Sufficiency Flag
    # ------------------------------------------------------------------

    def _data_sufficiency(self, province_code: str, quarter: str) -> str | None:
        """
        'LIMITED_SIGNAL' when the province-quarter holds fewer than five
        geocoded articles, else 'OK'. None when the bias weights are absent.
        """
        if self._bias is None:
            return None
        row = self._bias[
            (self._bias["province_code"] == province_code)
            & (self._bias["quarter"] == quarter)
        ]
        if row.empty:
            return "LIMITED_SIGNAL"
        count = int(row.iloc[0]["article_count"])
        return "OK" if count >= DATA_SUFFICIENCY_MIN_ARTICLES else "LIMITED_SIGNAL"
