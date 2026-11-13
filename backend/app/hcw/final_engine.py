"""
FINAL (RATE + MIND): the experimental successor of Setup H + class weights. NOT SERVED, NOT REGISTERED.

Research record: research_notes/aiPHeed_hcw_final_optimization_20261112 (PROTOCOL_FINAL.md, sha256 263a9dd7...). FINAL failed
two of the seven acceptance rules on the forward folds (Rule 3 Brier interval, Rule 4 HIGH recall at Lead 1), so nothing in the
application imports this module. It exists so the candidate can be reproduced, sealed and scored on a future survey round.

FINAL is app.hcw.engine.fit_predict with two changes and nothing else:
  RATE  LightGBM learns the change per unit g since the anchor survey, g = quarters since the anchor / mean training value:
        target (y - anchor) / g, row weight x g^2, forecast = anchor + g x predicted rate.
  MIND  inputs with gaps are filled with the training median and get a 0/1 "was missing" companion input.
Inputs, per-fold selection of 25 inputs, correlation pruning, monotone constraints, three anchors, four input sets, 16-setting
grid, survey-precision x balanced class weights, raw-first calibration, 0.5 cut-off: unchanged. No synthetic rows.
The original engine (app.hcw.engine) is not modified.
"""
from __future__ import annotations

from itertools import product

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import GroupKFold

from app.e151 import prov as Pv
from app.e164 import auto as A4
from app.e165 import final as F5
from app.hcw import engine as H

VERSION = "final-rate-mind-1.0-experimental"
STATUS = "experimental: fails acceptance rules 3 and 4 (forward folds); not approved for serving"
MI = "mi_"


def add_missing_flags(tr: pd.DataFrame, te: pd.DataFrame, FS: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict, list[str]]:
    """MIND: a 0/1 companion for every candidate input that has gaps in the training rows. Reads inputs only."""
    tr, te = tr.copy(), te.copy()
    allc = sorted({c for v in FS.values() for c in v if c in tr.columns})
    gappy = [c for c in allc if tr[c].isna().any() and tr[c].notna().any()]
    for c in gappy:
        tr[MI + c], te[MI + c] = tr[c].isna().astype(float), te[c].isna().astype(float)
    return tr, te, {k: list(v) + [MI + c for c in gappy if c in v] for k, v in FS.items()}, gappy


class FinalModel(H.Model):
    """H.Model on the per-quarter target, with training-median fill."""

    def fit(self, d):
        self.g0_ = float(d["gap_q"].values.astype(float).mean())
        g = d["gap_q"].values.astype(float) / self.g0_
        d = d.assign(e=d["e"].values / g)
        self.use_ = self._select(d)
        nl, mcs, lam, ne, lr, cs, ss, depth = self.hp
        par = dict(objective="regression", num_leaves=nl, max_depth=depth, min_child_samples=mcs, reg_lambda=lam, reg_alpha=0.0, min_split_gain=0.0, n_estimators=ne, learning_rate=lr,
                   colsample_bytree=cs, subsample=ss, subsample_freq=1,
                   monotone_constraints=[H.NEW_SIGN.get(c, Pv.SIGN.get(c, 0)) if c in H.NEW_SIGN else Pv.SIGN.get(c, 0) for c in self.use_],
                   monotone_constraints_method="basic", random_state=self.seed, n_jobs=1, verbose=-1)
        X = d[self.use_]
        self.med_ = X.median()
        self.m_ = lgb.LGBMRegressor(**par).fit(X.fillna(self.med_), d["e"].values, sample_weight=H._weights(d) * g ** 2)
        return self

    def _g(self, X):
        return X["gap_q"].values.astype(float) / self.g0_

    def predict(self, X):
        return self._g(X) * self.m_.predict(X[self.use_].fillna(self.med_))

    def contributions(self, X) -> tuple[np.ndarray, list[str]]:
        """Additive contributions on the forecast (logit) scale: LightGBM's exact rate contributions x g."""
        return self._g(X)[:, None] * self.m_.predict(X[self.use_].fillna(self.med_), pred_contrib=True), list(self.use_)


def fit_predict(tr: pd.DataFrame, te: pd.DataFrame, AN: dict, seed: int, FS: dict | None = None) -> dict:
    """One seed of FINAL. Same arguments and return keys as app.hcw.engine.fit_predict, plus 'version' and 'missing_flags'."""
    FS = {k: list(v) for k, v in (FS or H.feature_sets()).items()}
    tr = tr.reset_index(drop=True).copy()
    te = te.reset_index(drop=True).copy()
    tr, te, FS, gappy = add_missing_flags(tr, te, FS)
    for a in H.ANC:
        tr[f"a_{a}"], te[f"a_{a}"] = AN[a][0], AN[a][1]
    y, q, w0 = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cache, best = {}, None
    for a, f, pr, h in product(H.ANC, H.FS_KEYS, H.PRUNE, H.HPO):
        tag = f"a_{a}"
        oof = np.full(len(tr), np.nan)
        for j, (i_tr, i_te) in enumerate(folds):
            d = H._with_e(tr.iloc[i_tr].reset_index(drop=True), tag)
            oof[i_te] = AN[a][0][i_te] + FinalModel(FS[f], h, pr, seed, cache, (j, f, 0), tag).fit(d).predict(tr.iloc[i_te])
        cov = ~np.isnan(oof)
        sse = float(np.sum(w0[cov] * (y[cov] - oof[cov]) ** 2) / cov.sum())
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof, "cov": cov}
    a, f, pr, h = best["cfg"]
    tag, ate = f"a_{a}", AN[a][1]
    m = FinalModel(FS[f], h, pr, seed, cache, ("final", f, 0, 0), tag).fit(H._with_e(tr, tag))
    mu = ate + m.predict(te)
    oof, cov = best["oof"], best["cov"]
    yc, qc, gc, oc = y[cov], q[cov], gap[cov], oof[cov]
    sd_, _ = A4.scale(yc - oc, gc, gc)
    inner = {"raw": float(np.mean((norm.cdf(oc / sd_) - qc) ** 2))}
    sd_te, _ = A4.scale(yc - oc, gc, te["gap_q"].values)
    P = {"raw": norm.cdf(mu / sd_te)}
    if cov.all():
        lin, pl = np.zeros(len(tr)), np.zeros(len(tr))
        for i_tr, i_te in folds:
            Z = np.column_stack([np.ones(len(i_tr)), oof[i_tr]]) * np.sqrt(w0[i_tr])[:, None]
            ab = np.linalg.lstsq(Z, y[i_tr] * np.sqrt(w0[i_tr]), rcond=None)[0]
            lin[i_te] = ab[0] + ab[1] * oof[i_te]
            pl[i_te] = F5.soft_platt(oof[i_tr], q[i_tr]).predict_proba(oof[i_te].reshape(-1, 1))[:, 1]
        sdl, _ = A4.scale(y - lin, gap, gap)
        inner["linear"], inner["platt"] = float(np.mean((norm.cdf(lin / sdl) - q) ** 2)), float(np.mean((pl - q) ** 2))
        Z = np.column_stack([np.ones(len(tr)), oof]) * np.sqrt(w0)[:, None]
        ab = np.linalg.lstsq(Z, y * np.sqrt(w0), rcond=None)[0]
        sd_lin, _ = A4.scale(y - lin, gap, te["gap_q"].values)
        P["linear"] = norm.cdf((ab[0] + ab[1] * mu) / sd_lin)
        P["platt"] = F5.soft_platt(oof, q).predict_proba(mu.reshape(-1, 1))[:, 1]
    chosen = min(inner, key=inner.get)
    nl, mcs, lam, ne = h[:4]
    cfg = f"{a}|{f}|prune={pr}|leaves={nl},minchild={mcs},lambda={lam},trees={ne}|cal={chosen}|cw=balanced|sel={H.SEL}|rate=lin|miss=mind"
    return {"mu": mu, "p": P[chosen], "half": 1.645 * np.asarray(sd_te, float), "cal": chosen, "cfg": cfg, "model": m, "te": te, "anchor": a, "sse": best["sse"],
            "version": VERSION, "status": STATUS, "missing_flags": gappy}
