"""PROTOCOL_FINAL.md arms on top of study I's engine (engine_opt.fit_predict, unchanged).
  rate   'none' | 'lin' | 'sqrt' : LightGBM learns change per unit g since the anchor survey; forecast = anchor + g x predicted rate
  miss   'native' | 'median' | 'rimp' | 'mind' | 'dropgap'
  comp   add anchor-survey HFIAS composition inputs
With rate='none', miss='native', comp=False this is H_cw exactly."""
from __future__ import annotations

import re

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm

import engine_opt as EO
from app.e151 import prov as Pv
from app.hcw import engine as H
from app.paths import BACKEND_DIR

COMP_COLS = ["hc_sev", "hc_mild", "hc_disp_ms", "hc_disp_any"]
norm_key = lambda s: re.sub(r"[^a-z]", "", str(s).lower().replace("province", "").replace("city of ", ""))


def _g(gap, mode, g0):
    r = np.asarray(gap, float) / g0
    return r if mode == "lin" else np.sqrt(r)


class M4(EO.M2):
    RATE = "none"

    def fit(self, d):
        if self.RATE == "none":
            return super().fit(d)
        gen = (d["syn"].values != 1) if "syn" in d else np.ones(len(d), bool)
        self.g0_ = float(d["gap_q"].values[gen].astype(float).mean())
        g = _g(d["gap_q"].values, self.RATE, self.g0_)
        d = d.assign(e=d["e"].values / g)
        self.use_ = self._select(d)
        p = EO.hp_dict(self.hp)
        par = dict(objective="regression", num_leaves=p["num_leaves"], max_depth=p["max_depth"], min_child_samples=p["min_child_samples"], reg_lambda=p["lambda_l2"],
                   reg_alpha=p["lambda_l1"], min_split_gain=p["min_split_gain"], n_estimators=p["n_estimators"], learning_rate=p["learning_rate"],
                   colsample_bytree=p["feature_fraction"], subsample=p["bagging_fraction"], subsample_freq=p["bagging_freq"],
                   monotone_constraints=[H.NEW_SIGN.get(c, Pv.SIGN.get(c, 0)) if c in H.NEW_SIGN else Pv.SIGN.get(c, 0) for c in self.use_],
                   monotone_constraints_method="basic", random_state=self.seed, n_jobs=1, verbose=-1)
        X = d[self.use_]
        if self.impute:
            self.med_ = X.median()
            X = X.fillna(self.med_)
        self.m_ = lgb.LGBMRegressor(**par).fit(X, d["e"].values, sample_weight=EO.weights(d, self.cw) * g ** 2)
        return self

    def predict(self, X):
        r = super().predict(X)
        return r if self.RATE == "none" else _g(X["gap_q"].values, self.RATE, self.g0_) * r


# ------------------------------------------------------------------ input preparation (no outcome is read)
def _comp_table():
    B = BACKEND_DIR / "data"
    a = pd.read_csv(B / "hfias" / "clean" / "fnri2015_hfias.csv")
    a = a[a["level"].astype(str).str.lower().eq("province")].rename(columns={"name": "province"}).assign(ref="2015-Q3")
    b = pd.read_csv(B / "e141" / "clean" / "nns2013_hfias.csv").assign(ref="2013-Q3")
    t = pd.concat([a, b], ignore_index=True)[["province", "ref", "mild_pct", "moderate_pct", "severe_pct"]]
    cl = lambda v: np.clip(np.asarray(v, float) / 100.0, 0.005, 0.995)
    sev, ms, anyi = cl(t["severe_pct"]), cl(t["moderate_pct"] + t["severe_pct"]), cl(t["mild_pct"] + t["moderate_pct"] + t["severe_pct"])
    mild = cl(t["mild_pct"])
    t["hc_sev"], t["hc_mild"] = np.log(sev / (1 - sev)), np.log(mild / (1 - mild))
    t["hc_disp_ms"], t["hc_disp_any"] = norm.ppf(ms) - norm.ppf(sev), norm.ppf(anyi) - norm.ppf(ms)
    t["k"] = t["province"].map(norm_key)
    return t.drop_duplicates(["k", "ref"]).set_index(["k", "ref"])[COMP_COLS]


_ALIAS = {"cotabato": "northcotabato", "northcotabato": "cotabato", "compostelavalley": "davaodeoro", "davaodeoro": "compostelavalley", "samar": "westernsamar", "westernsamar": "samar",
          "mountainprovince": "mtprovince", "mtprovince": "mountainprovince"}


def add_comp(d, T):
    out = {c: [] for c in COMP_COLS}
    for prov, key, ref in zip(d["province"], d["key"], d["ref_anchor"]):
        hit = None
        for k in (norm_key(prov), norm_key(key), _ALIAS.get(norm_key(prov)), _ALIAS.get(norm_key(key))):
            if k is not None and (k, ref) in T.index:
                hit = T.loc[(k, ref)]
                break
        for c in COMP_COLS:
            out[c].append(float(hit[c]) if hit is not None else np.nan)
    return d.assign(**out)


def rimp(tr, te, cols):
    """Hierarchical fill using inputs only: region's published series, then region x origin mean over all rows, (median later)."""
    A = pd.concat([tr.assign(_s=0), te.assign(_s=1)], ignore_index=True)
    for loc, reg in (("l_fg_yoy", "r_fg_yoy"), ("l_rice_yoy", "r_rice_yoy"), ("l_rain3", "r_rain3")):
        if loc in A and reg in A:
            A[loc] = A[loc].fillna(A[reg])
    u = A.drop_duplicates(["key", "i"])
    for c in cols:
        if c in A and A[c].isna().any() and pd.api.types.is_numeric_dtype(A[c]):
            m = u.groupby(["region", "i"])[c].mean()
            fill = pd.Series(list(zip(A["region"], A["i"]))).map(m)
            A[c] = A[c].fillna(pd.Series(fill.values, index=A.index))
    n = len(tr)
    return A.iloc[:n].drop(columns="_s").reset_index(drop=True), A.iloc[n:].drop(columns="_s").reset_index(drop=True)


def fit_predict(tr, te, AN, seed, rate="none", miss="native", comp=False, **kw):
    FS = {k: list(v) for k, v in H.feature_sets().items()}
    tr, te = tr.reset_index(drop=True).copy(), te.reset_index(drop=True).copy()
    info = {}
    if comp:
        T = _comp_table()
        tr, te = add_comp(tr, T), add_comp(te, T)
        info["comp_missing_train"], info["comp_missing_test"] = float(tr["hc_sev"].isna().mean()), float(te["hc_sev"].isna().mean())
        FS = {k: v + COMP_COLS for k, v in FS.items()}
    allc = sorted({c for v in FS.values() for c in v if c in tr.columns})
    if miss == "rimp":
        tr, te = rimp(tr, te, allc)
        kw["impute"] = True
    elif miss == "median":
        kw["impute"] = True
    elif miss == "mind":
        gappy = [c for c in allc if tr[c].isna().any() and tr[c].notna().any()]
        for c in gappy:
            tr["mi_" + c], te["mi_" + c] = tr[c].isna().astype(float), te[c].isna().astype(float)
        FS = {k: v + ["mi_" + c for c in gappy if c in v] for k, v in FS.items()}
        kw["impute"] = True
    elif miss == "dropgap":
        drop = {c for c in allc if tr[c].isna().mean() > 0.15}
        FS = {k: [c for c in v if c not in drop] for k, v in FS.items()}
        info["dropped"] = sorted(drop)
    cls = type("M4b", (M4,), {"RATE": rate})
    old = EO.M2
    EO.M2 = cls
    try:
        r = EO.fit_predict(tr, te, AN, seed, FS=FS, **kw)
    finally:
        EO.M2 = old
    r["info"] = info
    return r
