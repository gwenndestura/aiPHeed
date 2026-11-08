"""
E142 survey-anchored risk-state model.

    mu(x)          structural level from indicators only (no measured history): E140 LGBM-AUTO without the history group
                   (primary, LightGBM) or the E139 ridge without history (reference)
    d = s - mu     deviation of the province from its structural level; stationary variance tau^2
    transition     d(t+1) = phi d(t) + eta   (AR(1), quarterly), so over h quarters E[d] shrinks by phi^h
    observation    y(round) = s + e,  e ~ N(0, se_y^2)

Estimation inside a training set (method of moments, all from measured rows):
    mu_oof         out-of-fold mu for every training row (grouped 5-fold by region), so deviations are not in-sample
    tau^2          mean over training rows of (y - mu_oof)^2 - se_y^2           (floor 0.01)
    phi            least squares of the per-transition products dev(t) x dev(prev) on tau^2 x phi^h over phi in [0, 1]
                   (independent survey errors do not bias the cross-product); with no transition in training, phi is
                   NOT identified and is set to 0 (the model is then structural only)
Prediction for a target with a previous round h quarters earlier:
    m0 = tau^2 / (tau^2 + se_prev^2) x (y_prev - mu(x_prev));  P0 = tau^2 se_prev^2 / (tau^2 + se_prev^2)
    y_hat = mu(x) + phi^h m0;  V = phi^(2h) P0 + tau^2 (1 - phi^(2h));  P(elevated) = Phi(y_hat / sqrt(V))
Without a previous round: y_hat = mu(x), V = tau^2.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e139 import model as M9
from app.e140 import model as M140

PHI_GRID = np.round(np.arange(0.0, 1.0001, 0.001), 3)
ROUND_QUARTER = {"NNS2013": 2013 * 4 + 2, "FNRI2015": 2015 * 4 + 2, "ENNS2018": 2018 * 4 + 2, "ENNS2019": 2019 * 4 + 2}


def gap_quarters(X: pd.DataFrame) -> pd.Series:
    """Quarters between the previous round's reference quarter and this row's (Q3 of each survey year)."""
    return X["survey"].map(ROUND_QUARTER) - X["prev_survey"].map(ROUND_QUARTER)


class _Mu:
    def __init__(self, kind: str):
        self.kind = kind

    def make(self):
        if self.kind == "lgbm":
            return M140.LGBAuto(drop=M9.HIST)
        return M9.Ridge_([c for c in M9.ALL if c not in M9.HIST])


class StateModel:
    def __init__(self, mu: str = "lgbm"):
        self.mu = _Mu(mu)

    def fit(self, tr: pd.DataFrame):
        tr = tr.reset_index(drop=True)
        g = tr["region"].values
        mu_oof = np.full(len(tr), np.nan)
        for a, b in GroupKFold(min(5, len(np.unique(g)))).split(tr, groups=g):
            mu_oof[b] = self.mu.make().fit(tr.iloc[a]).predict_y(tr.iloc[b])
        dev = tr["y"].values - mu_oof
        self.tau2_ = float(max(0.01, np.mean(dev ** 2 - tr["se_y"].values ** 2)))
        # transitions: pair each training row with its previous round in training
        key_dev = {(k, s): d for k, s, d in zip(tr["key"], tr["survey"], dev)}
        prods, hs = [], []
        for k, ps, d, h in zip(tr["key"], tr["prev_survey"], dev, gap_quarters(tr)):
            if isinstance(ps, str) and (k, ps) in key_dev:
                prods.append(d * key_dev[(k, ps)])
                hs.append(h)
        self.n_transitions_ = len(prods)
        if prods:
            prods, hs = np.asarray(prods), np.asarray(hs, float)
            loss = [np.sum((prods - self.tau2_ * p ** hs) ** 2) for p in PHI_GRID]
            self.phi_ = float(PHI_GRID[int(np.argmin(loss))])
        else:
            self.phi_ = 0.0                                   # not identified without a measured transition
        self.mu_model_ = self.mu.make().fit(tr)
        self._prev_mu = {}
        return self

    def _mu(self, X):
        return self.mu_model_.predict_y(X)

    def predict(self, X: pd.DataFrame, prev_rows: pd.DataFrame | None = None, h=None):
        """prev_rows: the previous-round rows (features as of that round) aligned to X, used for mu(x_prev);
        when None, mu at the current features is used as mu_prev (structural level assumed unchanged)."""
        mu = self._mu(X)
        mu_prev = self._mu(prev_rows) if prev_rows is not None else mu
        has = X["prev_y"].notna().values
        se_p = X["prev_se_y"].fillna(0).values
        k = self.tau2_ / (self.tau2_ + se_p ** 2)
        m0 = np.where(has, k * (X["prev_y"].fillna(0).values - mu_prev), 0.0)
        p0 = np.where(has, self.tau2_ * se_p ** 2 / (self.tau2_ + se_p ** 2), self.tau2_)
        hh = np.where(has, np.asarray(gap_quarters(X) if h is None else h, float), 0.0)
        w = np.where(has, self.phi_ ** np.nan_to_num(hh), 0.0)
        yhat = mu + w * m0
        V = w ** 2 * p0 + self.tau2_ * (1 - w ** 2)
        return yhat, V

    def predict_proba(self, X, prev_rows=None, h=None):
        yhat, V = self.predict(X, prev_rows, h)
        return norm.cdf(yhat / np.sqrt(V))
