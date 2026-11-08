"""
E144 Stage A0 (real-time nowcast), Stage A (pooled-area LightGBM, h = 1..4) and baselines B1-B6 (PROTOCOL.md s.3).
"""
from __future__ import annotations

from functools import lru_cache

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

from app.e144 import data as D
from app.fi5.target import qindex

PARAMS = dict(n_estimators=200, learning_rate=0.03, num_leaves=7, max_depth=3, min_child_samples=20, subsample=0.8,
              subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=144, verbose=-1)
HORIZONS = (1, 2, 3, 4)
FIRST_ISSUE = qindex("2010-Q1")
NOW_COLS = ["nowcast", "nowcast_anom"]
SETS = {
    "A LightGBM (full)": D.HIST_COLS + NOW_COLS + D.NEWS_COLS + D.NAT_COLS + ["h"],
    "B5 LightGBM, no news": D.HIST_COLS + D.NAT_COLS + ["h"],
    "B6 LightGBM, news only": D.NEWS_COLS + ["h"],
}
LOGIT_SETS = {
    "B2 Logistic, combined": D.HIST_COLS + NOW_COLS + D.NEWS_COLS + D.NAT_COLS + ["h"],
    "B3 Logistic, government + history (PSA-only)": D.HIST_COLS + D.NAT_COLS + ["h"],
    "B4 Logistic, news only (NLP-only)": D.NEWS_COLS + ["h"],
}


def _logit(p):
    p = np.clip(np.asarray(p, float) / 100.0, 1e-3, 1 - 1e-3)
    return np.log(p / (1 - p))


# -------------------------------------------------------------------------------------------------- Stage A0
def _a0_row(area: str, q: int) -> dict:
    d = D.q_end(q)
    r = {"area": area, "qi": q}
    r.update({k: v for k, v in D.history(area, d, q).items() if k in D.HIST_COLS})
    r.update(D.news(area, q, d))
    r.update(D.national(d))
    return r


A0_COLS = D.HIST_COLS + D.NEWS_COLS + D.NAT_COLS


@lru_cache(maxsize=None)
def nowcast_series() -> pd.DataFrame:
    """Real-time A0 nowcast of every area-quarter: the model for quarter q is fitted only on area-quarters whose reading
    was published on or before q_end(q) (labels from 2010-Q1)."""
    s = D.sws_quarterly()
    rows = pd.DataFrame([_a0_row(a, q) for a in D.AREAS for q in range(FIRST_ISSUE, qindex("2026-Q3") + 1)])
    rows = rows.merge(s[["area", "qi", "hunger", "published"]], on=["area", "qi"], how="left")
    for c in A0_COLS:
        if c not in rows:
            rows[c] = np.nan
    out = []
    for q in sorted(rows["qi"].unique()):
        d = D.q_end(q)
        tr = rows[(rows["published"] <= d) & rows["hunger"].notna()]
        te = rows[rows["qi"] == q]
        if len(tr) < 30:
            pred = np.full(len(te), np.nan)
        else:
            m = lgb.LGBMRegressor(**PARAMS).fit(tr[A0_COLS], _logit(tr["hunger"]))
            z = m.predict(te[A0_COLS])
            pred = 100 / (1 + np.exp(-z))
        out.append(pd.DataFrame({"area": te["area"].values, "qi": q, "nowcast": pred}))
    return pd.concat(out, ignore_index=True)


# -------------------------------------------------------------------------------------------------- Stage A rows
@lru_cache(maxsize=None)
def panel(last_issue: int = qindex("2026-Q3")) -> pd.DataFrame:
    """One row per area x issue quarter i x horizon h: features as of d = q_end(i); label of T = i+1+h."""
    nc = nowcast_series().set_index(["area", "qi"])["nowcast"]
    rows = []
    for i in range(FIRST_ISSUE, last_issue + 1):
        d = D.q_end(i)
        nat = D.national(d)
        for a in D.AREAS:
            nw = D.news(a, i, d)
            for h in HORIZONS:
                T = i + 1 + h
                r = {"area": a, "issue_qi": i, "issue_date": d, "h": h, "target_qi": T}
                hist = D.history(a, d, T)
                r.update({k: hist.get(k) for k in D.HIST_COLS})
                base = hist.get("baseline_asof", np.nan)
                n = nc.get((a, i), np.nan)
                r["nowcast"], r["nowcast_anom"] = n, n - base if pd.notna(n) else np.nan
                r.update(nw)
                r.update(nat)
                lab = D.label(a, T)
                if lab:
                    r.update(y=lab["high"], hunger_target=lab["hunger"], label_published=lab["published"])
                rows.append(r)
    X = pd.DataFrame(rows)
    for c in set(sum(SETS.values(), []) + sum(LOGIT_SETS.values(), [])):
        if c not in X:
            X[c] = np.nan
    X["last_high"] = (X["hunger_last_anom"] > 0).astype(float)
    return X


# -------------------------------------------------------------------------------------------------- learners
class LogitM:
    def __init__(self, cols):
        self.cols = cols

    def _prep(self, X, fit=False):
        Z = X[self.cols].astype(float).copy()
        miss = Z.isna().astype(float).add_suffix("_miss")
        if fit:
            self.med_ = Z.median()
            self.keep_ = [c for c in miss.columns if miss[c].std() > 0]
        Z = Z.fillna(self.med_).fillna(0.0)
        Z = pd.concat([Z, miss[self.keep_]], axis=1)
        if fit:
            self.sc_ = StandardScaler().fit(Z)
        return self.sc_.transform(Z)

    def fit(self, X, y):
        self.m_ = LogisticRegression(C=1.0, max_iter=2000).fit(self._prep(X, True), y)
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(self._prep(X))[:, 1]


class LGBC:
    def __init__(self, cols):
        self.cols = cols

    def fit(self, X, y):
        self.m_ = lgb.LGBMClassifier(**PARAMS).fit(X[self.cols], y)
        return self

    def predict_proba(self, X):
        return self.m_.predict_proba(X[self.cols])[:, 1]


class LGBLevel:
    """Regressor of logit(area hunger) with per-horizon predictive SD from grouped 5-fold out-of-fold residuals."""

    def __init__(self, cols):
        self.cols = cols

    def fit(self, X):
        X = X[X["hunger_target"].notna()]
        y = _logit(X["hunger_target"])
        g = X["issue_qi"].values
        oof = np.full(len(X), np.nan)
        for a, b in GroupKFold(min(5, len(np.unique(g)))).split(X, groups=g):
            oof[b] = lgb.LGBMRegressor(**PARAMS).fit(X.iloc[a][self.cols], y[a]).predict(X.iloc[b][self.cols])
        res = pd.Series(y - oof).groupby(X["h"].values).std()
        self.sd_ = {int(k): float(v) for k, v in res.items()}
        self.m_ = lgb.LGBMRegressor(**PARAMS).fit(X[self.cols], y)
        return self

    def predict(self, X):
        return self.m_.predict(X[self.cols]), np.array([self.sd_.get(int(h), max(self.sd_.values())) for h in X["h"]])


def persistence(tr, te):
    rate = tr.groupby("last_high")["y"].mean()
    base = float(tr["y"].mean())
    return te["last_high"].map(rate).fillna(base).values


def walk_forward(X: pd.DataFrame, first_eval: int, last_eval: int, cutoff: pd.Timestamp) -> pd.DataFrame:
    """At each issue i: train on rows whose target label was published on or before q_end(i); predict issue i's rows
    whose label was published on or before `cutoff` (the evaluation data cutoff)."""
    out = []
    for i in range(first_eval, last_eval + 1):
        d = D.q_end(i)
        tr = X[X["y"].notna() & (X["label_published"] <= d)]
        te = X[(X["issue_qi"] == i) & X["y"].notna() & (X["label_published"] <= cutoff)].copy()
        if te.empty or tr["y"].nunique() < 2:
            continue
        ytr = tr["y"].astype(int)
        for n, cols in SETS.items():
            te[n] = LGBC(cols).fit(tr, ytr).predict_proba(te)
        for n, cols in LOGIT_SETS.items():
            te[n] = LogitM(cols).fit(tr, ytr).predict_proba(te)
        te["B1 Persistence"] = persistence(tr, te)
        te["Climatology"] = float(ytr.mean())
        lv = LGBLevel(SETS["A LightGBM (full)"]).fit(tr)
        te["level_logit"], te["level_sd"] = lv.predict(te)
        out.append(te)
    return pd.concat(out, ignore_index=True)
