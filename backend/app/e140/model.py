"""
E140 LightGBM-native candidates (one controlled improvement; PROTOCOL.md). Same target, rows, folds and release rules
as E139 (app.e139.model.data); E139 is imported unchanged.

Diagnosis (diagnostics.json) behind the design:
    * E139's trees could only fit residuals of a linear prior that already holds the features' linear signal; at every
      tree count the trees made out-of-fold Brier worse. Trees without the prior kept improving with more trees
      (0.257 -> 0.206 at 300) but stayed above the prior (0.192): step functions approximate a near-linear signal
      poorly at n = 125.
    * 31 % of the prior's residual variance is between regions, 9 % between island groups (Luzon/Visayas/Mindanao),
      and E138 found the poverty-food-insecurity relation differs by island group.

Candidates:
    LT    LightGBM with LINEAR TREES (piecewise-linear leaves), no separate prior: the trees themselves carry the linear
          poverty/history signal and may split by island group or other features where slopes differ.
    GBC   LightGBM, constant leaves, no prior, compact features (poverty, history, island, food CPI, cyclones), small
          learning rate and more trees.
The number of trees is chosen by inner grouped CV from a frozen grid that does NOT contain 0. Both candidates are
evaluated; the reported LightGBM candidate is the one with the lower inner-CV error inside each training fold (nested).
"""
from __future__ import annotations

import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e137 import model as M137
from app.e139 import model as M9

warnings.filterwarnings("ignore")
SEED = 20261104
ISLAND = {"Luzon": 0, "Visayas": 1, "Mindanao": 2}
LT_FEATURES = M9.ALL + ["island_code"]
GBC_FEATURES = M9.POV + M9.HIST + ["island_code", "m_food_cpi_yoy", "c_tc_4q", "c_tc_clim"]
LT_GRID = [10, 30, 100]
GBC_GRID = [100, 300, 600]
LT_PARAMS = dict(objective="regression", linear_tree=True, linear_lambda=1.0, num_leaves=2, max_depth=1,
                 min_child_samples=20, learning_rate=0.1, reg_lambda=5.0, subsample=0.8, subsample_freq=1,
                 colsample_bytree=0.8, random_state=SEED, n_jobs=1, verbose=-1)
GBC_PARAMS = dict(objective="regression", num_leaves=4, max_depth=2, min_child_samples=10, learning_rate=0.02,
                  reg_lambda=5.0, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=SEED,
                  n_jobs=1, verbose=-1)


def data(*a, **k) -> pd.DataFrame:
    X = M9.data(*a, **k)
    X["island_code"] = X["island"].map(ISLAND).astype(float)
    return X


def _sigma(y, p, se):
    return float(np.sqrt(max(M137.SIGMA_FLOOR ** 2, np.mean((y - p) ** 2 - se ** 2))))


class LGBNative:
    """kind 'LT' (linear trees) or 'GBC' (constant-leaf trees). No linear prior; init score = weighted training mean."""

    def __init__(self, kind: str, cols: list[str] | None = None, n_trees: int | None = None):
        self.kind = kind
        self.cols = list(cols or (LT_FEATURES if kind == "LT" else GBC_FEATURES))
        self.grid = LT_GRID if kind == "LT" else GBC_GRID
        self.params = LT_PARAMS if kind == "LT" else GBC_PARAMS
        self.n_fixed = n_trees

    def _fit(self, tr, n):
        w = M9._w(tr)
        mu = float(np.average(tr["y"], weights=w))
        m = lgb.LGBMRegressor(n_estimators=n, **self.params)
        m.fit(tr[self.cols], tr["y"] - mu, sample_weight=w)
        return mu, m

    def inner(self, tr):
        g = tr["region"].values
        folds = list(GroupKFold(min(5, len(np.unique(g)))).split(tr, groups=g))
        best = None
        for n in ([self.n_fixed] if self.n_fixed else self.grid):
            pred = np.full(len(tr), np.nan)
            for i, j in folds:
                mu, m = self._fit(tr.iloc[i], n)
                pred[j] = mu + m.predict(tr.iloc[j][self.cols])
            sig = _sigma(tr["y"].values, pred, tr["se_y"].values)
            eb = M137.expected_brier(norm.cdf(pred / sig), tr["q"])
            if best is None or eb < best[0] - 1e-12:
                best = (eb, n, sig)
        return best

    def fit(self, tr):
        self.inner_eb_, self.n_trees_, self.sigma_ = self.inner(tr)
        self.mu_, self.m_ = self._fit(tr, self.n_trees_)
        return self

    def predict_y(self, X):
        return self.mu_ + self.m_.predict(X[self.cols])

    def predict_proba(self, X):
        return norm.cdf(self.predict_y(X) / self.sigma_)

    def group_effects(self, X, ref: pd.DataFrame) -> pd.DataFrame:
        """Local group effect on the relative logit: prediction minus prediction with that group's features set to
        the training median (used for explanations; additive only approximately)."""
        base = self.predict_y(X)
        out = {}
        for g, fs in M9.GROUPS.items():
            Z = X.copy()
            for f in [f for f in fs if f in self.cols]:
                Z[f] = ref[f].median()
            out[g] = base - self.predict_y(Z)
        return pd.DataFrame(out, index=X.index)


QUARTERLY = ["m_food_cpi_yoy", "m_rice_cpi_yoy", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy"]


class LGBAuto:
    """Nested choice between LT and GBC by inner-CV error inside each training set (part of the learner).
    `drop`: features removed from both (used for the quarterly-indicator test)."""

    def __init__(self, drop=None):
        self.drop = list(drop or [])

    def fit(self, tr):
        a = LGBNative("LT", [c for c in LT_FEATURES if c not in self.drop]).fit(tr)
        b = LGBNative("GBC", [c for c in GBC_FEATURES if c not in self.drop]).fit(tr)
        self.chosen_ = a if a.inner_eb_ <= b.inner_eb_ else b
        self.kind_, self.n_trees_ = self.chosen_.kind, self.chosen_.n_trees_
        return self

    def predict_y(self, X):
        return self.chosen_.predict_y(X)

    def predict_proba(self, X):
        return self.chosen_.predict_proba(X)


class PriorPlusTrees(M9.LGBM):
    """E139's linear-prior LightGBM with trees FORCED (30), for comparison 3 in the directive."""

    def fit(self, tr):
        self.alpha_ = M9.Ridge_(self.base_cols).fit(tr).alpha_
        self.base_, self.booster_ = self._fit(tr, 30)
        self.n_trees_ = 30
        p = self._pred(self.base_, self.booster_, tr, self.cols)
        self.sigma_ = _sigma(tr["y"].values, p, tr["se_y"].values)
        return self


def make(name: str):
    return {"LGBM-AUTO": LGBAuto, "LGBM-LT": lambda: LGBNative("LT"), "LGBM-GBC": lambda: LGBNative("GBC"),
            "PRIOR": lambda: M9.Ridge_(M9.BASE), "PRIOR+TREES30": PriorPlusTrees, "E139": M9.LGBM,
            "RR-F": lambda: M9.Ridge_(M9.ALL), "NAT": M137.BaseRate, "REGPREV": M9.RegPrev, "PERS": M137.Persistence,
            "LGBM-AUTO-noQ": lambda: LGBAuto(QUARTERLY)}[name]()


CANDIDATES = ["LGBM-AUTO", "LGBM-LT", "LGBM-GBC", "PRIOR", "PRIOR+TREES30", "E139", "RR-F", "NAT", "REGPREV", "PERS"]
