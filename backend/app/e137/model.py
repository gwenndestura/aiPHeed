"""
E137 Layer S models. Two LightGBM formulations (compared under the frozen rule in PROTOCOL.md section 6) and the
baselines, all fitted on identical training rows.

    REL   LightGBM regression on the relative logit y, weights 1 / (se_y^2 + tau^2); P(elevated) = Phi(yhat / sigma),
          sigma = model error estimated in inner cross-validation (survey error removed).
    SOFT  LightGBM cross-entropy on the soft label q = P(true relative logit > 0 | survey).
    B0    base rate (training mean of q).
    B1    persistence: the province's previous measured relative position (ENNS rows only).
    B2    PSA-only: soft-label logistic regression on the poverty indicators.
    B3    logistic regression (soft labels) on all features.
Hyper-parameters are chosen inside the training rows only (grouped inner folds by region).
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from app.e137.features import FEATURES, GROUPS, MONOTONE

warnings.filterwarnings("ignore", category=UserWarning)
SEED = 20261103
GRID = {
    "A": dict(num_leaves=4, max_depth=2, min_child_samples=10, n_estimators=150, learning_rate=0.05, reg_lambda=5.0),
    "B": dict(num_leaves=4, max_depth=2, min_child_samples=15, n_estimators=300, learning_rate=0.03, reg_lambda=10.0),
    "C": dict(num_leaves=8, max_depth=3, min_child_samples=10, n_estimators=150, learning_rate=0.05, reg_lambda=5.0),
    "D": dict(num_leaves=2, max_depth=1, min_child_samples=10, n_estimators=300, learning_rate=0.05, reg_lambda=5.0),
}
COMMON = dict(subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=SEED, n_jobs=1, verbose=-1)
PSA_ONLY = GROUPS["poverty"][:3]
SIGMA_FLOOR = 0.05


def _lgb(cfg: str, cols: list[str], objective: str):
    mono = [MONOTONE[c] for c in cols]
    return lgb.LGBMRegressor(objective=objective, monotone_constraints=mono, monotone_constraints_method="advanced",
                             **GRID[cfg], **COMMON)


def tau2(tr: pd.DataFrame) -> float:
    return max(0.01, float(np.var(tr["y"]) - np.mean(tr["se_y"] ** 2)))


def expected_brier(p, q) -> float:
    p, q = np.asarray(p, float), np.asarray(q, float)
    return float(np.mean((p - q) ** 2 + q * (1 - q)))


class LGBRisk:
    """kind = 'REL' or 'SOFT'."""

    def __init__(self, kind: str, cols: list[str] | None = None, cfg: str | None = None):
        self.kind, self.cols, self.cfg = kind, list(cols or FEATURES), cfg

    def _fit_one(self, cfg, tr):
        X = tr[self.cols]
        if self.kind == "REL":
            m = _lgb(cfg, self.cols, "regression")
            m.fit(X, tr["y"], sample_weight=1.0 / (tr["se_y"] ** 2 + tau2(tr)))
        else:
            m = _lgb(cfg, self.cols, "cross_entropy")
            m.fit(X, tr["q"].clip(1e-4, 1 - 1e-4))
        return m

    def _inner(self, tr: pd.DataFrame):
        """Inner grouped CV: choose cfg; estimate sigma for REL. Returns (cfg, sigma)."""
        groups = tr["region"].values
        k = min(5, len(np.unique(groups)))
        scores, sig = {}, {}
        for cfg in GRID:
            pred = np.full(len(tr), np.nan)
            for a, b in GroupKFold(k).split(tr, groups=groups):
                m = self._fit_one(cfg, tr.iloc[a])
                pred[b] = m.predict(tr.iloc[b][self.cols])
            if self.kind == "REL":
                s2 = max(SIGMA_FLOOR ** 2, float(np.mean((tr["y"] - pred) ** 2 - tr["se_y"] ** 2)))
                sig[cfg] = np.sqrt(s2)
                scores[cfg] = expected_brier(norm.cdf(pred / sig[cfg]), tr["q"])
            else:
                scores[cfg] = expected_brier(np.clip(pred, 0, 1), tr["q"])
        best = min(scores, key=lambda c: (scores[c], list(GRID).index(c)))
        return best, sig.get(best)

    def fit(self, tr: pd.DataFrame):
        self.cfg_, self.sigma_ = self._inner(tr) if self.cfg is None else (self.cfg, None)
        self.m_ = self._fit_one(self.cfg_, tr)
        if self.kind == "REL" and self.sigma_ is None:
            self.sigma_ = SIGMA_FLOOR
        return self

    def predict_y(self, X):
        return self.m_.predict(X[self.cols]) if self.kind == "REL" else np.log(self.predict_proba(X) / (1 - self.predict_proba(X)))

    def predict_proba(self, X):
        if self.kind == "REL":
            return norm.cdf(self.m_.predict(X[self.cols]) / self.sigma_)
        return np.clip(self.m_.predict(X[self.cols]), 1e-4, 1 - 1e-4)

    def contributions(self, X) -> pd.DataFrame:
        """TreeSHAP (raw-score scale) per feature, plus 'bias'."""
        c = self.m_.booster_.predict(X[self.cols], pred_contrib=True)
        return pd.DataFrame(c, columns=self.cols + ["bias"], index=X.index)


class SoftLogit:
    """Logistic regression on soft labels: each row enters as y=1 with weight q and y=0 with weight 1-q."""

    def __init__(self, cols: list[str]):
        self.cols = list(cols)

    def fit(self, tr: pd.DataFrame):
        X = tr[self.cols]
        self.med_ = X.median()
        Xf = X.fillna(self.med_)
        self.mu_, self.sd_ = Xf.mean(), Xf.std(ddof=0).replace(0, 1.0)
        Z = ((Xf - self.mu_) / self.sd_).values
        q = tr["q"].values
        self.m_ = LogisticRegression(C=1.0, max_iter=2000).fit(np.vstack([Z, Z]), np.r_[np.ones(len(q)), np.zeros(len(q))],
                                                               sample_weight=np.r_[q, 1 - q])
        return self

    def predict_proba(self, X):
        Z = ((X[self.cols].fillna(self.med_) - self.mu_) / self.sd_).values
        return self.m_.predict_proba(Z)[:, 1]


class BaseRate:
    def fit(self, tr):
        self.p_ = float(tr["q"].mean())
        return self

    def predict_proba(self, X):
        return np.full(len(X), self.p_)


class Persistence:
    """P = Phi(prev_y / sqrt(prev_se^2 + change_var)); change_var from training rows that have a previous value, else
    the training between-province variance (stated in the protocol)."""

    def fit(self, tr):
        t = tr[tr["prev_y"].notna()]
        if len(t) >= 8:
            self.v_ = max(0.01, float(np.var(t["y"] - t["prev_y"]) - np.mean(t["se_y"] ** 2 + t["prev_se_y"] ** 2)))
        else:
            self.v_ = tau2(tr)
        return self

    def predict_proba(self, X):
        return np.asarray(norm.cdf(X["prev_y"] / np.sqrt(X["prev_se_y"] ** 2 + self.v_)), float)


def candidates(kind: str) -> dict:
    return {"LGBM": LGBRisk(kind), "B0_base_rate": BaseRate(), "B1_persistence": Persistence(),
            "B2_psa_only": SoftLogit(PSA_ONLY), "B3_logistic": SoftLogit(FEATURES)}
