"""FI7 models: the FI6 LightGBM change model plus simple statistical competitors and a training-only threshold.

    delta_lgbm   FI6 DeltaModel (monotone LightGBM on the change from the latest reading; sigma from inner folds)
    delta_ridge  ridge regression on the same change target (median imputation + scaling fitted on training only;
                 alpha and sigma from the same expanding inner folds)
    damped       damped persistence: level = normal + phi**age * (latest - normal); phi fitted by least squares on
                 training pairs; sigma = training residual SD. No other inputs.
    + threshold  wrapper: decision threshold chosen on inner out-of-fold probabilities (maximum balanced accuracy)
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.fi6 import models as M6

INNER_FOLDS, MIN_INNER_TRAIN = 4, 20
M6.EXTRA_MONOTONE.update({
    "world_rice_yoy": 1, "world_rice_3m": 1, "world_urea_yoy": 1, "tc_max_wind_q": 1, "typhoon_passages_4q": 1,
    "underemp_rate": 1, "underemp_yoy": 1, "fish_yoy": -1,
    **{f"w_{d}": 1 for d in ["market", "climate", "employment", "remittance", "poverty", "climate_damage", "displaced"]},
    **{f"ew_esc_{d}": 1 for d in ["market", "climate", "employment", "remittance", "poverty"]},
    **{f"ew_per_{d}": 1 for d in ["market", "climate", "employment", "remittance", "poverty"]},
})


def _folds(n: int):
    start = max(MIN_INNER_TRAIN, int(n * 0.6))
    e = np.linspace(start, n, INNER_FOLDS + 1).astype(int)
    return [(a, b) for a, b in zip(e[:-1], e[1:]) if b > a]


def _prob(level, thr, sigma):
    return 1 - norm.cdf((np.asarray(thr, float) - np.asarray(level, float)) / sigma)


class RidgeDelta:
    ALPHAS = [1.0, 10.0, 100.0]

    def __init__(self, features):
        self.features, self.cols = features, []

    def _make(self, a):
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=a))

    def fit(self, X, delta):
        delta = np.asarray(delta, float)
        self.cols = [c for c in self.features if X[c].notna().sum() >= 5 and X[c].nunique() > 1]
        best = None
        for a in self.ALPHAS:
            res = []
            for lo, hi in _folds(len(delta)):
                m = self._make(a).fit(X.iloc[:lo][self.cols], delta[:lo])
                res.append(delta[lo:hi] - m.predict(X.iloc[lo:hi][self.cols]))
            r = np.concatenate(res)
            if best is None or np.mean(np.abs(r)) < best[1]:
                best = (a, np.mean(np.abs(r)), np.sqrt(np.mean(r ** 2)))
        self.choice, self.sigma = best[0], max(best[2], M6.SIGMA_FLOOR)
        self.est = self._make(self.choice).fit(X[self.cols], delta)
        return self

    def predict_delta(self, X):
        return self.est.predict(X[self.cols])

    def predict_proba(self, X):
        return _prob(X["hunger_last"].to_numpy(float) + self.predict_delta(X), X["threshold_known"], self.sigma)


class Damped:
    choice = "phi"

    def fit(self, X, delta):
        dev0 = (X["hunger_last"] - X["baseline_known"]).to_numpy(float)
        dev1 = (X["hunger_target"] - X["baseline_known"]).to_numpy(float)
        age = X["hunger_age_q"].to_numpy(float)
        ok = ~(np.isnan(dev0) | np.isnan(dev1) | np.isnan(age))
        grid = np.linspace(0, 1, 101)
        sse = [np.sum((dev1[ok] - (p ** age[ok]) * dev0[ok]) ** 2) for p in grid]
        self.phi = float(grid[int(np.argmin(sse))])
        resid = dev1[ok] - (self.phi ** age[ok]) * dev0[ok]
        self.sigma = max(float(np.std(resid, ddof=1)), M6.SIGMA_FLOOR)
        return self

    def predict_level(self, X):
        return X["baseline_known"].to_numpy(float) + (self.phi ** X["hunger_age_q"].to_numpy(float)) * \
            (X["hunger_last"] - X["baseline_known"]).to_numpy(float)

    def predict_delta(self, X):
        return self.predict_level(X) - X["hunger_last"].to_numpy(float)

    def predict_proba(self, X):
        return _prob(self.predict_level(X), X["threshold_known"], self.sigma)


class Thresholded:
    """Any probabilistic model + a decision threshold chosen on inner out-of-fold predictions (training only)."""

    def __init__(self, make):
        self.make = make

    def fit(self, X, delta):
        y = X["y"].to_numpy(int)
        oof_p, oof_y = [], []
        for lo, hi in _folds(len(y)):
            m = self.make().fit(X.iloc[:lo], np.asarray(delta)[:lo])
            oof_p.append(m.predict_proba(X.iloc[lo:hi]))
            oof_y.append(y[lo:hi])
        p, yy = np.concatenate(oof_p), np.concatenate(oof_y)
        best, self.tau = -1, 0.5
        if len(set(yy)) == 2:
            for t in np.linspace(0.1, 0.9, 33):
                yh = p >= t
                ba = (np.mean(yh[yy == 1]) + np.mean(~yh[yy == 0])) / 2
                if ba > best + 1e-9:
                    best, self.tau = ba, float(t)
        self.inner = self.make().fit(X, delta)
        self.sigma, self.choice = self.inner.sigma, f"tau={self.tau:.2f}"
        return self

    def predict_delta(self, X):
        return self.inner.predict_delta(X)

    def predict_proba(self, X):
        return self.inner.predict_proba(X)            # probabilities untouched (Brier/AUC/calibration unaffected)

    def predict_class(self, X):
        return (self.predict_proba(X) >= self.tau).astype(int)


class Anchored:
    """Damped-persistence anchor + LightGBM on what the anchor misses (E12; registered after E09 showed the anchor
    alone beats the change model). level = anchor + residual_hat; sigma from the residual model's inner folds."""

    def __init__(self, features):
        self.features = features

    def fit(self, X, delta):
        self.anchor = Damped().fit(X, delta)
        resid = (X["hunger_target"].to_numpy(float) - self.anchor.predict_level(X))
        self.res = M6.DeltaModel(self.features).fit(X, resid)
        self.sigma, self.choice = self.res.sigma, f"phi={self.anchor.phi:.2f}/{self.res.choice}"
        return self

    def predict_level(self, X):
        return self.anchor.predict_level(X) + self.res.predict_delta(X)

    def predict_delta(self, X):
        return self.predict_level(X) - X["hunger_last"].to_numpy(float)

    def predict_proba(self, X):
        return _prob(self.predict_level(X), X["threshold_known"], self.sigma)


def make(kind: str, features):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if kind == "delta_lgbm":
            return M6.DeltaModel(features)
        if kind == "delta_ridge":
            return RidgeDelta(features)
        if kind == "damped":
            return Damped()
        if kind == "delta_lgbm_tau":
            return Thresholded(lambda: M6.DeltaModel(features))
        if kind == "anchored_lgbm":
            return Anchored(features)
        if kind == "anchored_lgbm_tau":
            return Thresholded(lambda: Anchored(features))
        if kind == "damped_tau":
            return Thresholded(lambda: Damped())
        return M6.make({"persist": "persist", "clf_lgbm": "clf_lgbm", "logit": "logit", "clim": "clim"}[kind], features)


def fit(model, kind: str, tr: pd.DataFrame):
    if kind in ("delta_lgbm", "delta_ridge", "damped", "delta_lgbm_tau", "persist", "anchored_lgbm", "anchored_lgbm_tau", "damped_tau"):
        return model.fit(tr, tr["delta_target"].to_numpy(float))
    return model.fit(tr, tr["y"].to_numpy(int))
