"""
Setup H + class weights (registry hcw-lgbm-1.0): the procedure, ported line for line from the research engine that produced
the validated results (research_notes/aiPHeed_study_20261110/evidence/scripts: opt_run.py spec `rp_H_sel` + h_run.py group
`HCW`, option `cw=True`). `tests/unit/test_hcw_engine.py` checks that this port reproduces the saved research predictions.

Procedure (all choices on TRAINING rows only):
  * target: province HFIAS moderate+severe (logit) minus a survey anchor (H, OH or RSS; app.e164.auto.anchors)
  * inputs: the E168 feature sets (GOV, FULL, GOV+cons, FULL+cons) without the fisheries-production and OFW-remittance
    groups, plus four groups: agricultural production (palay/corn), agricultural vulnerability (rainfall/typhoon),
    household economics (regional GRDP) and the provincial food-market prices already in the panel (l_*)
  * per training fold: the 25 inputs with the largest |rank correlation| with the residual, near-duplicates (rho > 0.95)
    pruned; LightGBM regressor with fixed monotone signs; row weight 1/(se^2 + 0.05) x balanced HIGH/LOW class weight
  * inner GroupKFold by region chooses anchor x feature set x 16 hyper-parameter settings (lowest weighted squared error)
  * probability: normal CDF of the forecast logit over the residual scale, or linear / Platt calibration, whichever has the
    lowest inner Brier; HIGH = P >= 0.5
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
from app.e168 import lgbm_only as L

MODEL_ID = "hcw-lgbm-1.0"
ANC = ("H", "OH", "RSS")
SEEDS = (168, 1, 2, 3, 4)
SEL, PRUNE = 25, (True,)
FS_KEYS = list(L.FS)                                   # GOV, FULL, GOV+cons, FULL+cons
HPO = [(a, b, c, d, 0.02, 0.8, 0.8, -1) for a, b, c, d in L.HPO]
NEW_GROUPS = {"rp_agprod": ["ag_palay_yoy", "ag_corn_yoy", "ag_dev3y", "ag_pc"],
              "rp_agvuln": ["vu_dry6", "vu_rain12", "vu_tc_wind", "vu_tc_strong", "vu_tc_clim"],
              "rp_hhecon": ["hh_grdp_g", "hh_grdp_rel"],
              "rp_foodmkt": ["l_fg_yoy", "l_rice_yoy", "l_fish_yoy", "l_rice_rel", "l_fg_rel", "l_terms"]}
ADD = [c for g in NEW_GROUPS.values() for c in g]
FOODMKT = set(NEW_GROUPS["rp_foodmkt"])
NEW_SIGN = {"ag_palay_yoy": -1, "ag_corn_yoy": -1, "ag_dev3y": -1, "ag_pc": -1, "vu_dry6": 1, "vu_rain12": 0, "vu_tc_wind": 1, "vu_tc_strong": 1, "vu_tc_clim": 1, "hh_grdp_g": -1, "hh_grdp_rel": -1,
            "l_fg_yoy": 0, "l_rice_yoy": 1, "l_fish_yoy": 1, "l_rice_rel": 1, "l_fg_rel": 0, "l_terms": 0}
DROP = ("fish", "remittance")


def group_of(c: str) -> str:
    from app.e163 import model as E163
    if c == "c_fish_yoy":
        return "fish"
    for pre, g in (("ag_", "rp_agprod"), ("vu_", "rp_agvuln"), ("hh_", "rp_hhecon")):
        if c.startswith(pre):
            return g
    if c in FOODMKT:
        return "rp_foodmkt"
    if c.startswith("x_"):
        return "engineered"
    return E163.gmap(c) or "none"


def feature_sets() -> dict[str, list[str]]:
    FS = {k: list(v) + [c for c in ADD if c not in v] for k, v in L.FS.items()}
    return {k: [c for c in v if group_of(c) not in DROP] for k, v in FS.items()}


def _weights(d: pd.DataFrame) -> np.ndarray:
    w = (1.0 / (d["se_true"] ** 2 + 0.05)).values.astype(float)
    h = d["y_true"].values >= 0
    n, nh = len(h), max(1, int(h.sum()))
    return w * np.where(h, n / (2.0 * nh), n / (2.0 * max(1, n - nh)))


class Model:
    def __init__(self, cols, hp, prune, seed, cache, ckey, anchor_tag):
        self.cols, self.hp, self.prune, self.seed, self.cache, self.ckey, self.tag = list(cols), hp, prune, seed, cache, ckey, anchor_tag

    def _select(self, d):
        k = self.ckey + (self.prune, self.tag)
        if k in self.cache:
            return self.cache[k]
        use = [c for c in self.cols if c in d and d[c].notna().any() and d[c].nunique() > 1]
        r = d[use].rank()
        c = r.corrwith(d["e"].rank()).abs().fillna(0.0).sort_values(ascending=False)
        use = list(c.index[:SEL])
        if self.prune and len(use) > 1:
            R = d[use].rank().corr().abs()
            keep = []
            for col in use:
                if all(not (R.at[col, k_] > 0.95) for k_ in keep):
                    keep.append(col)
            use = keep
        self.cache[k] = use
        return use

    def fit(self, d):
        self.use_ = self._select(d)
        nl, mcs, lam, ne, lr, cs, ss, depth = self.hp
        par = dict(objective="regression", num_leaves=nl, max_depth=depth, min_child_samples=mcs, reg_lambda=lam, reg_alpha=0.0, min_split_gain=0.0, n_estimators=ne, learning_rate=lr,
                   colsample_bytree=cs, subsample=ss, subsample_freq=1,
                   monotone_constraints=[NEW_SIGN.get(c, Pv.SIGN.get(c, 0)) if c in NEW_SIGN else Pv.SIGN.get(c, 0) for c in self.use_],
                   monotone_constraints_method="basic", random_state=self.seed, n_jobs=1, verbose=-1)
        self.m_ = lgb.LGBMRegressor(**par).fit(d[self.use_], d["e"].values, sample_weight=_weights(d))
        return self

    def predict(self, X):
        return self.m_.predict(X[self.use_])

    def contributions(self, X) -> tuple[np.ndarray, list[str]]:
        """Exact additive LightGBM contributions (logit scale) per input, plus the bias as the last column."""
        return self.m_.predict(X[self.use_], pred_contrib=True), list(self.use_)


def _with_e(d: pd.DataFrame, tag: str) -> pd.DataFrame:
    return d.assign(e=d["y_true"].values - d[tag].values)


def fit_predict(tr: pd.DataFrame, te: pd.DataFrame, AN: dict, seed: int, FS: dict | None = None) -> dict:
    """One seed of the procedure. tr/te carry y_true, se_true, q_true, gap_q, region (tr) and the inputs; AN = anchors
    {name: (train array, test array)}. Returns mu (logit), p (P(HIGH)), half (90 % half-width, logit), calibration,
    configuration and the final model (for contributions)."""
    FS = FS or feature_sets()
    tr = tr.reset_index(drop=True).copy()
    te = te.reset_index(drop=True).copy()
    for a in ANC:
        tr[f"a_{a}"], te[f"a_{a}"] = AN[a][0], AN[a][1]
    y, q, w0 = tr["y_true"].values, tr["q_true"].values, (1.0 / (tr["se_true"] ** 2 + 0.05)).values
    gap = tr["gap_q"].values.astype(float)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    cache, best = {}, None
    for a, f, pr, h in product(ANC, FS_KEYS, PRUNE, HPO):
        tag = f"a_{a}"
        oof = np.full(len(tr), np.nan)
        for j, (i_tr, i_te) in enumerate(folds):
            d = _with_e(tr.iloc[i_tr].reset_index(drop=True), tag)
            oof[i_te] = AN[a][0][i_te] + Model(FS[f], h, pr, seed, cache, (j, f, 0), tag).fit(d).predict(tr.iloc[i_te])
        cov = ~np.isnan(oof)
        sse = float(np.sum(w0[cov] * (y[cov] - oof[cov]) ** 2) / cov.sum())
        if best is None or sse < best["sse"]:
            best = {"sse": sse, "cfg": (a, f, pr, h), "oof": oof, "cov": cov}
    a, f, pr, h = best["cfg"]
    tag, ate = f"a_{a}", AN[a][1]
    m = Model(FS[f], h, pr, seed, cache, ("final", f, 0, 0), tag).fit(_with_e(tr, tag))
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
    cfg = f"{a}|{f}|prune={pr}|leaves={nl},minchild={mcs},lambda={lam},trees={ne}|cal={chosen}|cw=balanced|sel={SEL}"
    return {"mu": mu, "p": P[chosen], "half": 1.645 * np.asarray(sd_te, float), "cal": chosen, "cfg": cfg, "model": m, "te": te, "anchor": a}
