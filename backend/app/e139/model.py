"""
E139 data and models.

Features (all public before the issue date; E137 builders plus one measured-history feature):
    poverty     p_poverty, p_subsistence, p_poverty_gap, p_density
    market      m_food_cpi_yoy, m_rice_cpi_yoy, m_food_threshold_rel
    climate     c_rain_anom_6m, c_tc_4q, c_tc_clim, c_agri_pc, c_agri_yoy, c_fish_yoy
    history     a_prev_y (the province's previous measured relative position),
                a_region_prev (mean measured relative position of the region's provinces in the previous survey)
    employment, news: no nationally comparable provincial series for the training years (context only)

Models (all return P(elevated) and use identical rows):
    LGBM      linear-prior LightGBM (primary)                 NAT      national base rate
    RR-F      weighted ridge, all features                    REG      regional base rate (same-survey neighbours)
    LR-F      soft-label logistic, all features               REGPREV  region's previous measured level
    RR-P      ridge, poverty only                             PERS     province's previous measured level
    LR-P      logistic, poverty only                          HIER-P   E138 poverty + region intercept
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import GroupKFold

from app.e137 import evaluate as E137
from app.e137 import model as M137
from app.e138 import models as M138

warnings.filterwarnings("ignore")
SEED = 20261105
POV = ["p_poverty", "p_subsistence", "p_poverty_gap"]
DENS = ["p_density"]
MKT = ["m_food_cpi_yoy", "m_rice_cpi_yoy", "m_food_threshold_rel"]
CLI = ["c_rain_anom_6m", "c_tc_4q", "c_tc_clim", "c_agri_pc", "c_agri_yoy", "c_fish_yoy"]
HIST = ["a_prev_y", "a_region_prev"]
GROUPS = {"poverty": POV + DENS, "market": MKT, "climate": CLI, "history": HIST}
ALL = POV + DENS + MKT + CLI + HIST
BASE = POV + HIST                       # linear prior: poverty and measured history only
ALPHAS = [1.0, 3.0, 10.0, 30.0]
TREES = [0, 30, 100]                    # compact, frozen grid: inner CV may choose no trees
LGB_PARAMS = dict(objective="regression", num_leaves=3, max_depth=2, min_child_samples=15, reg_lambda=10.0,
                  learning_rate=0.05, subsample=0.8, subsample_freq=1, colsample_bytree=0.7, random_state=SEED,
                  n_jobs=1, verbose=-1)


def data(outcome="mod_sev", reference="pooled", lead=0) -> pd.DataFrame:
    X = E137._data(outcome, reference, lead)
    prev = X[X["survey"] == "FNRI2015"].groupby("region")["y"].mean()
    X["a_region_prev"] = np.where(X["survey"] != "FNRI2015", X["region"].map(prev), np.nan)
    return X


def lin_design(X: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """History features enter linear models as value-or-0 plus a has_ flag (missing means 'no earlier survey')."""
    Z = X[[c for c in cols if c not in HIST]].copy()
    for h in [c for c in cols if c in HIST]:
        Z[f"has_{h}"] = X[h].notna().astype(float)
        Z[h] = X[h].fillna(0.0)
    return Z


class _Std:
    def fit(self, Z):
        self.med_ = Z.median()
        F = Z.fillna(self.med_)
        self.mu_, self.sd_ = F.mean(), F.std(ddof=0).replace(0, 1.0)
        return self

    def __call__(self, Z):
        return ((Z.fillna(self.med_) - self.mu_) / self.sd_).values


def _w(tr):
    return 1.0 / (tr["se_y"] ** 2 + M137.tau2(tr))


def _sigma(y, pred, se):
    return float(np.sqrt(max(M137.SIGMA_FLOOR ** 2, np.mean((y - pred) ** 2 - se ** 2))))


def _inner(tr, k=5):
    g = tr["region"].values
    return list(GroupKFold(min(k, len(np.unique(g)))).split(tr, groups=g))


class Ridge_:
    """Weighted ridge on the relative logit; alpha by inner CV; P = Phi(yhat / sigma)."""

    def __init__(self, cols, alpha=None):
        self.cols, self.alpha = list(cols), alpha

    def _fit(self, tr, a):
        Z = lin_design(tr, self.cols)
        s = _Std().fit(Z)
        return s, Ridge(alpha=a).fit(s(Z), tr["y"], sample_weight=_w(tr))

    def fit(self, tr):
        best = None
        for a in ([self.alpha] if self.alpha is not None else ALPHAS):
            pred = np.full(len(tr), np.nan)
            for i, j in _inner(tr):
                s, m = self._fit(tr.iloc[i], a)
                pred[j] = m.predict(s(lin_design(tr.iloc[j], self.cols)))
            sig = _sigma(tr["y"].values, pred, tr["se_y"].values)
            eb = M137.expected_brier(norm.cdf(pred / sig), tr["q"])
            if best is None or eb < best[0] - 1e-12:
                best = (eb, a, sig)
        _, self.alpha_, self.sigma_ = best
        self.std_, self.m_ = self._fit(tr, self.alpha_)
        return self

    def predict_y(self, X):
        return self.m_.predict(self.std_(lin_design(X, self.cols)))

    def predict_proba(self, X):
        return norm.cdf(self.predict_y(X) / self.sigma_)

    def contributions(self, X) -> pd.DataFrame:
        Z = lin_design(X, self.cols)
        return pd.DataFrame(self.std_(Z) * self.m_.coef_, columns=Z.columns, index=X.index)


class Logit_:
    def __init__(self, cols):
        self.cols = list(cols)

    def fit(self, tr):
        Z = lin_design(tr, self.cols)
        self.std_ = _Std().fit(Z)
        Zs, q = self.std_(Z), tr["q"].values
        self.m_ = LogisticRegression(C=1.0, max_iter=5000).fit(np.vstack([Zs, Zs]), np.r_[np.ones(len(q)), np.zeros(len(q))],
                                                               sample_weight=np.r_[q, 1 - q])
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(self.std_(lin_design(X, self.cols)))[:, 1]


class LGBM:
    """Linear-prior LightGBM. Base = Ridge_(BASE) fitted on the training rows; trees fitted on all features with
    init_score = base prediction. Number of trees from TREES by inner grouped CV (0 allowed). sigma from inner CV."""

    def __init__(self, cols=None, base_cols=None):
        self.cols = list(cols or ALL)
        self.base_cols = [c for c in (base_cols or BASE) if c in self.cols]

    def _fit(self, tr, n):
        base = Ridge_(self.base_cols, self.alpha_).fit(tr) if self.base_cols else None
        b = base.predict_y(tr) if base else np.zeros(len(tr))
        booster = None
        if n:
            booster = lgb.LGBMRegressor(n_estimators=n, **LGB_PARAMS)
            booster.fit(tr[self.cols], tr["y"], sample_weight=_w(tr), init_score=b)
        return base, booster

    @staticmethod
    def _pred(base, booster, X, cols):
        b = base.predict_y(X) if base else np.zeros(len(X))
        return b + (booster.predict(X[cols]) if booster is not None else 0.0)

    def fit(self, tr):
        # base alpha chosen once on the training rows (inner CV inside Ridge_), then held fixed while trees are chosen
        self.alpha_ = Ridge_(self.base_cols).fit(tr).alpha_ if self.base_cols else None
        best = None
        for n in TREES:
            pred = np.full(len(tr), np.nan)
            for i, j in _inner(tr):
                base, bst = self._fit(tr.iloc[i], n)
                pred[j] = self._pred(base, bst, tr.iloc[j], self.cols)
            sig = _sigma(tr["y"].values, pred, tr["se_y"].values)
            eb = M137.expected_brier(norm.cdf(pred / sig), tr["q"])
            if best is None or eb < best[0] - 1e-12:
                best = (eb, n, sig)
        _, self.n_trees_, self.sigma_ = best
        self.base_, self.booster_ = self._fit(tr, self.n_trees_)
        return self

    def predict_y(self, X):
        return self._pred(self.base_, self.booster_, X, self.cols)

    def predict_proba(self, X):
        return norm.cdf(self.predict_y(X) / self.sigma_)

    def contributions(self, X) -> pd.DataFrame:
        """Additive contributions to the predicted relative logit, by feature: exact linear terms of the base plus
        TreeSHAP of the trees (has_ flags are attributed to their history feature)."""
        out = pd.DataFrame(0.0, index=X.index, columns=self.cols)
        if self.base_:
            c = self.base_.contributions(X)
            for col in c.columns:
                out[col.replace("has_", "")] += c[col]
        if self.booster_ is not None:
            s = self.booster_.booster_.predict(X[self.cols], pred_contrib=True)
            out += pd.DataFrame(s[:, :-1], columns=self.cols, index=X.index)
        return out

    def group_contributions(self, X) -> pd.DataFrame:
        c = self.contributions(X)
        return pd.DataFrame({g: c[[f for f in fs if f in c]].sum(axis=1) for g, fs in GROUPS.items()})


class RegPrev:
    """P from the region's previous measured level: Phi(a_region_prev / s); s from training rows that have it.
    Rows without a previous survey get the training base rate."""

    def fit(self, tr):
        t = tr[tr["a_region_prev"].notna()]
        self.base_ = float(tr["q"].mean())
        self.s_ = _sigma(t["y"].values, t["a_region_prev"].values, t["se_y"].values) if len(t) >= 8 else None
        return self

    def predict_proba(self, X):
        p = np.full(len(X), self.base_)
        if self.s_:
            m = X["a_region_prev"].notna().values
            p[m] = norm.cdf(X["a_region_prev"].values[m] / self.s_)
        return p


def make(name: str, cols: list[str] | None = None):
    return {"LGBM": lambda: LGBM(cols), "RR-F": lambda: Ridge_(ALL), "LR-F": lambda: Logit_(ALL),
            "RR-P": lambda: Ridge_(POV), "LR-P": lambda: Logit_(POV), "NAT": M137.BaseRate, "REG": M138.REG,
            "REGPREV": RegPrev, "PERS": M137.Persistence, "HIER-P": lambda: M138.HIER(M138.P)}[name]()


CANDIDATES = ["LGBM", "RR-F", "LR-F", "RR-P", "LR-P", "HIER-P", "NAT", "REG", "REGPREV", "PERS"]
