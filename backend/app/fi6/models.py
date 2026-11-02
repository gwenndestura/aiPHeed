"""FI6 models.

Proposed: LightGBM regression of the change in hunger from the latest published reading, with monotone
constraints. Configuration (stumps / small) and the forecast error spread sigma are both estimated by expanding
inner folds inside the training window only. P(HIGH) = 1 - Phi((threshold_known - (hunger_last + delta_hat)) / sigma).

Baselines: persistence (delta_hat = 0, sigma = SD of past changes); PSA-only and NLP-only = LightGBM classifiers on
their feature subsets without any SWS information; logistic regression (FI5 implementation) on all features;
climatology = training base rate.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.fi5.models import LGBM_CONFIGS, Model as ClfModel
from app.fi6.features import MONOTONE

REG_CONFIGS = ["stumps", "small"]
INNER_FOLDS = 4
MIN_INNER_TRAIN = 20
SIGMA_FLOOR = 1.0       # pp; never claim more certainty than one percentage point
EXTRA_MONOTONE: dict[str, int] = {}   # directions registered by extensions (FI6-N archive news features)


def _usable(X: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if X[c].notna().sum() >= 5 and X[c].nunique(dropna=True) > 1]


def _reg(cfg: str, cols: list[str]):
    import lightgbm as lgb
    p = dict(LGBM_CONFIGS[cfg])
    return lgb.LGBMRegressor(**p, reg_lambda=1.0, colsample_bytree=0.8, subsample=0.8, subsample_freq=1,
                             monotone_constraints=[{**MONOTONE, **EXTRA_MONOTONE}.get(c, 0) for c in cols], monotone_constraints_method="advanced",
                             random_state=42, deterministic=True, force_col_wise=True, n_jobs=1, verbose=-1)


def _inner(cfg: str, X: pd.DataFrame, y: np.ndarray, cols: list[str]) -> np.ndarray:
    """Out-of-fold residuals from expanding inner folds over the last 40 % of the training rows."""
    n = len(y)
    start = max(MIN_INNER_TRAIN, int(n * 0.6))
    edges = np.linspace(start, n, INNER_FOLDS + 1).astype(int)
    res = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        m = _reg(cfg, cols).fit(X.iloc[:a][cols], y[:a])
        res.append(y[a:b] - m.predict(X.iloc[a:b][cols]))
    return np.concatenate(res) if res else np.array([])


class DeltaModel:
    def __init__(self, features: list[str]):
        self.features, self.cols, self.est, self.choice, self.sigma = features, [], None, None, np.nan

    def fit(self, X: pd.DataFrame, delta: np.ndarray):
        delta = np.asarray(delta, float)
        self.cols = _usable(X, self.features)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            best = None
            for cfg in REG_CONFIGS:
                r = _inner(cfg, X, delta, self.cols)
                if len(r) == 0:
                    continue
                mae = float(np.mean(np.abs(r)))
                if best is None or mae < best[1] - 1e-9:
                    best = (cfg, mae, float(np.sqrt(np.mean(r ** 2))))
            self.choice = best[0] if best else "stumps"
            self.sigma = max(best[2] if best else float(np.std(delta, ddof=1)), SIGMA_FLOOR)
            self.est = _reg(self.choice, self.cols).fit(X[self.cols], delta)
        return self

    def predict_delta(self, X: pd.DataFrame) -> np.ndarray:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return self.est.predict(X[self.cols])

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        level = X["hunger_last"].to_numpy(float) + self.predict_delta(X)
        return 1 - norm.cdf((X["threshold_known"].to_numpy(float) - level) / self.sigma)


class Persistence:
    def fit(self, X, delta):
        self.sigma = max(float(np.std(np.asarray(delta, float), ddof=1)), SIGMA_FLOOR)
        return self

    def predict_proba(self, X):
        return 1 - norm.cdf((X["threshold_known"].to_numpy(float) - X["hunger_last"].to_numpy(float)) / self.sigma)


def make(kind: str, features: list[str] | None):
    if kind == "reg":
        return DeltaModel(features)
    if kind == "persist":
        return Persistence()
    if kind == "clf_lgbm":
        return ClfModel("lgbm", features)
    if kind == "logit":
        return ClfModel("logit", features)
    if kind == "clim":
        return ClfModel("climatology")
    raise ValueError(kind)


def fit(model, kind: str, tr: pd.DataFrame):
    if kind in ("reg", "persist"):
        return model.fit(tr, tr["delta_target"].to_numpy(float))
    return model.fit(tr, tr["y"].to_numpy(int))
