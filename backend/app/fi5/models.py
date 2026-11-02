"""LightGBM (proposed) and the four baselines, all behind one fit/predict interface.

LightGBM: three small, regularised configurations fixed in advance; at every walk-forward origin the
configuration is chosen on the last 8 training rows (time-ordered hold-out inside the training window, log loss),
then refitted on the whole training window. Class imbalance: class_weight="balanced". Logistic regression: L2,
median imputation and scaling fitted on the training window only, C chosen the same way. Persistence: the latest
published hunger reading is above (HIGH) or not above the target quarter's five-year average.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LGBM_CONFIGS = {
    "stumps": dict(num_leaves=2, max_depth=1, min_child_samples=10, n_estimators=120, learning_rate=0.05),
    "small": dict(num_leaves=4, max_depth=2, min_child_samples=8, n_estimators=150, learning_rate=0.03),
    "medium": dict(num_leaves=7, max_depth=3, min_child_samples=6, n_estimators=200, learning_rate=0.03),
}
LGBM_COMMON = dict(reg_lambda=1.0, colsample_bytree=0.8, subsample=0.8, subsample_freq=1, class_weight="balanced",
                   random_state=42, deterministic=True, force_col_wise=True, n_jobs=1, verbose=-1)
LOGIT_C = [0.03, 0.1, 0.3, 1.0]
INNER_HOLDOUT = 8
MIN_TRAIN_FOR_SELECTION = 30


def _usable(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if X[c].notna().sum() >= 5 and X[c].nunique(dropna=True) > 1]


def _lgbm(cfg: str):
    import lightgbm as lgb
    return lgb.LGBMClassifier(**LGBM_CONFIGS[cfg], **LGBM_COMMON)


def _logit(C: float):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(C=C, class_weight="balanced", max_iter=2000))


def _select(make, options, X: pd.DataFrame, y: np.ndarray):
    if len(y) < MIN_TRAIN_FOR_SELECTION:
        return options[len(options) // 2]
    Xa, ya, Xb, yb = X.iloc[:-INNER_HOLDOUT], y[:-INNER_HOLDOUT], X.iloc[-INNER_HOLDOUT:], y[-INNER_HOLDOUT:]
    if len(set(ya)) < 2:
        return options[len(options) // 2]
    best, best_loss = options[len(options) // 2], np.inf
    for o in options:
        m = make(o).fit(Xa, ya)
        loss = log_loss(yb, np.clip(m.predict_proba(Xb)[:, 1], 1e-4, 1 - 1e-4), labels=[0, 1])
        if loss < best_loss - 1e-9:
            best, best_loss = o, loss
    return best


class Model:
    """kind: lgbm | logit | persistence | climatology."""

    def __init__(self, kind: str, features: list[str] | None = None, select: bool = True, fixed: str | float | None = None):
        self.kind, self.features, self.select, self.fixed = kind, features or [], select, fixed
        self.est, self.choice, self.cols, self.base_rate = None, None, [], np.nan

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        y = np.asarray(y, int)
        self.base_rate = float(y.mean()) if len(y) else 0.5
        if self.kind in ("persistence", "climatology"):
            return self
        self.cols = _usable(X[self.features])
        if not self.cols or len(set(y)) < 2:
            self.kind_used = "climatology"
            return self
        Xf = X[self.cols]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if self.kind == "lgbm":
                self.choice = self.fixed or (_select(_lgbm, list(LGBM_CONFIGS), Xf, y) if self.select else "small")
                self.est = _lgbm(self.choice).fit(Xf, y)
            elif self.kind == "logit":
                self.choice = self.fixed or (_select(_logit, LOGIT_C, Xf, y) if self.select else 0.1)
                self.est = _logit(self.choice).fit(Xf, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.kind == "persistence":
            return (X["hunger_last_anom"].to_numpy(float) > 0).astype(float)
        if self.kind == "climatology" or self.est is None:
            return np.full(len(X), self.base_rate)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return self.est.predict_proba(X[self.cols])[:, 1]


def lgbm_regressor():
    import lightgbm as lgb
    return lgb.LGBMRegressor(**LGBM_CONFIGS["small"], reg_lambda=1.0, colsample_bytree=0.8, subsample=0.8,
                             subsample_freq=1, random_state=42, deterministic=True, force_col_wise=True, n_jobs=1,
                             verbose=-1)
