"""
E138 WHERE candidates. All produce P(elevated) = P(true relative logit > 0) and are fitted on identical rows.

    NAT        national base rate (training mean of the soft label q)
    REG        regional base rate: training mean q of the same region, shrunk to NAT with kappa = 5 rows
    PERS       previous survey position (E137 Persistence; ENNS rows only)
    LR-<set>   L2 logistic regression on soft labels; C chosen by inner grouped CV from C_GRID
    RR-<set>   continuous relative-risk ridge on y (weights 1/(se^2 + tau^2)); P = Phi(yhat / sigma)
    HIER-<set> LR plus a region random intercept (empirical Bayes, shrinkage n / (n + kappa))
    GB-<set>   LightGBM, strongly regularised and fixed (stumps, 60 trees, min 20 rows per leaf, L2 20, monotone)
Feature sets are named in FEATURE_SETS. The anchor enters linear models as (value or 0, has_anchor flag).
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e137.features import GROUPS, MONOTONE

warnings.filterwarnings("ignore")
P1 = ["p_subsistence"]
P = GROUPS["poverty"][:3]
D = ["p_density"]
MK = GROUPS["market"]
CL = GROUPS["climate"]
A = ["a_prev_y"]
FEATURE_SETS = {"P1": P1, "P": P, "PD": P + D, "PA": P + A, "PM": P + D + MK, "PC": P + D + CL, "PMC": P + D + MK + CL,
                "ALL": P + D + MK + CL + A}
# simplest first: the order used by the one-SE selection rule
COMPLEXITY = ["NAT", "LR-P1", "LR-P", "LR-PA", "LR-PD", "RR-P", "LR-PM", "LR-PC", "LR-PMC", "RR-PMC", "LR-ALL", "RR-ALL",
              "GB-PMC", "GB-ALL"]
C_GRID = [0.03, 0.1, 0.3, 1.0, 3.0]
KAPPA = 5.0
SEED = 20261104


def design(X: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    Z = X[[c for c in cols if c != "a_prev_y"]].copy()
    if "a_prev_y" in cols:
        Z["has_anchor"] = X["a_prev_y"].notna().astype(float)
        Z["a_prev_y"] = X["a_prev_y"].fillna(0.0)
    return Z


class _Std:
    def fit(self, Z):
        self.med_ = Z.median()
        F = Z.fillna(self.med_)
        self.mu_, self.sd_ = F.mean(), F.std(ddof=0).replace(0, 1.0)
        return self

    def __call__(self, Z):
        return ((Z.fillna(self.med_) - self.mu_) / self.sd_).values


def _soft_lr(Zs, q, C):
    return LogisticRegression(C=C, max_iter=5000).fit(np.vstack([Zs, Zs]), np.r_[np.ones(len(q)), np.zeros(len(q))],
                                                      sample_weight=np.r_[q, 1 - q])


class LR:
    def __init__(self, cols, C=None):
        self.cols, self.C = list(cols), C

    def _fit(self, tr, C):
        Z = design(tr, self.cols)
        std = _Std().fit(Z)
        return std, _soft_lr(std(Z), tr["q"].values, C)

    def fit(self, tr):
        C = self.C
        if C is None:
            g = tr["region"].values
            k = min(5, len(np.unique(g)))
            best = None
            for c in C_GRID:
                p = np.full(len(tr), np.nan)
                for a, b in GroupKFold(k).split(tr, groups=g):
                    std, m = self._fit(tr.iloc[a], c)
                    p[b] = m.predict_proba(std(design(tr.iloc[b], self.cols)))[:, 1]
                s = M137.expected_brier(p, tr["q"])
                if best is None or s < best[0] - 1e-12:
                    best = (s, c)
            C = best[1]
        self.C_ = C
        self.std_, self.m_ = self._fit(tr, C)
        return self

    def logit(self, X):
        return self.m_.decision_function(self.std_(design(X, self.cols)))

    def predict_proba(self, X):
        return 1 / (1 + np.exp(-self.logit(X)))

    def coefficients(self) -> dict:
        names = list(design(pd.DataFrame(columns=self.cols), self.cols).columns)
        return dict(zip(names, self.m_.coef_[0].round(4)))


class RR:
    """Continuous relative-risk ridge. alpha by inner CV; sigma = model error with survey error removed."""

    ALPHAS = [0.3, 1.0, 3.0, 10.0, 30.0]

    def __init__(self, cols):
        self.cols = list(cols)

    def _fit(self, tr, a):
        Z = design(tr, self.cols)
        std = _Std().fit(Z)
        w = 1.0 / (tr["se_y"] ** 2 + M137.tau2(tr))
        return std, Ridge(alpha=a).fit(std(Z), tr["y"], sample_weight=w)

    def fit(self, tr):
        g = tr["region"].values
        k = min(5, len(np.unique(g)))
        best = None
        for a in self.ALPHAS:
            pred = np.full(len(tr), np.nan)
            for i, j in GroupKFold(k).split(tr, groups=g):
                std, m = self._fit(tr.iloc[i], a)
                pred[j] = m.predict(std(design(tr.iloc[j], self.cols)))
            s2 = max(M137.SIGMA_FLOOR ** 2, float(np.mean((tr["y"] - pred) ** 2 - tr["se_y"] ** 2)))
            s = M137.expected_brier(norm.cdf(pred / np.sqrt(s2)), tr["q"])
            if best is None or s < best[0] - 1e-12:
                best = (s, a, np.sqrt(s2))
        _, self.alpha_, self.sigma_ = best
        self.std_, self.m_ = self._fit(tr, self.alpha_)
        return self

    def predict_y(self, X):
        return self.m_.predict(self.std_(design(X, self.cols)))

    def predict_proba(self, X):
        return norm.cdf(self.predict_y(X) / self.sigma_)


class HIER(LR):
    """LR plus an empirical-Bayes region intercept: the weighted mean logit residual of the region's training rows,
    shrunk by n / (n + KAPPA). A region with no training rows gets 0 (then HIER = LR)."""

    def fit(self, tr):
        super().fit(tr)
        q = tr["q"].clip(0.02, 0.98)
        resid = np.log(q / (1 - q)) - self.logit(tr)
        g = pd.DataFrame({"r": tr["region"].values, "e": resid})
        st = g.groupby("r")["e"].agg(["mean", "count"])
        self.off_ = (st["mean"] * st["count"] / (st["count"] + KAPPA)).to_dict()
        return self

    def predict_proba(self, X):
        z = self.logit(X) + X["region"].map(self.off_).fillna(0.0).values
        return 1 / (1 + np.exp(-z))


class GB:
    PARAMS = dict(objective="cross_entropy", num_leaves=2, max_depth=1, n_estimators=60, learning_rate=0.05,
                  min_child_samples=20, reg_lambda=20.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                  random_state=SEED, n_jobs=1, verbose=-1)

    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, tr):
        self.m_ = lgb.LGBMRegressor(monotone_constraints=[MONOTONE[c] for c in self.cols], **self.PARAMS)
        self.m_.fit(tr[self.cols], tr["q"].clip(1e-4, 1 - 1e-4))
        return self

    def predict_proba(self, X):
        return np.clip(self.m_.predict(X[self.cols]), 1e-4, 1 - 1e-4)

    def contributions(self, X):
        c = self.m_.booster_.predict(X[self.cols], pred_contrib=True)
        return pd.DataFrame(c, columns=self.cols + ["bias"], index=X.index)


class REG:
    def fit(self, tr):
        self.nat_ = float(tr["q"].mean())
        st = tr.groupby("region")["q"].agg(["mean", "count"])
        self.r_ = ((st["mean"] * st["count"] + self.nat_ * KAPPA) / (st["count"] + KAPPA)).to_dict()
        return self

    def predict_proba(self, X):
        return X["region"].map(self.r_).fillna(self.nat_).values


def make(name: str):
    if name == "NAT":
        return M137.BaseRate()
    if name == "REG":
        return REG()
    if name == "PERS":
        return M137.Persistence()
    kind, fs = name.split("-")
    cols = FEATURE_SETS[fs]
    return {"LR": LR, "RR": RR, "HIER": HIER, "GB": GB}[kind](cols)


CANDIDATES = ["NAT", "REG", "PERS", "LR-P1", "LR-P", "LR-PD", "LR-PA", "LR-PM", "LR-PC", "LR-PMC", "LR-ALL",
              "RR-P", "RR-PMC", "RR-ALL", "HIER-P", "HIER-PMC", "GB-PMC", "GB-ALL"]
