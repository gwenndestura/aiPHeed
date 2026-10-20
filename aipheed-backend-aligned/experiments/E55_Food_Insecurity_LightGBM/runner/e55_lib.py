"""E55 library (PROTOCOL.md): the food-insecurity target T43 (Chapter I section 1.7: SWS hunger AND PSA food prices),
the LightGBM food-insecurity model E55-LGBM, its poverty / trigger variants, the LightGBM factor diagnostics, and exact
TreeSHAP attribution.

E55-LGBM at origin O(t) for target quarter t+2 (the quarter after the issue quarter, "one quarter ahead"):

    P(T43 HIGH) = P(regional SWS hunger > 11.3 at t+2)  x  P(provincial food-price signal at t+2)
                  [I7 regional hunger component, unchanged]   [LightGBM, below]

LightGBM price-signal classifier (trained on the as-of PS labels of training targets <= t-1, vintage d.cut(t)):
  * offset (init_score) = logit of the structural probability from the base-effect CPI projections of food YoY and
    food-minus-headline YoY (drift multiplier m), with the projection RMSE of the fitting rows as the error scale;
  * boosted depth-1 trees on the five trigger groups, news and the rice-policy block, with an INTERCEPT-FREE logistic
    objective (gradients centred to sum zero at every iteration), so the trees can redistribute risk across
    province-quarters but cannot carry a level shift learned in an earlier price regime (the I7 D3 lesson, for trees);
  * configuration (m, trees, feature set, recency half-life) chosen by embargoed forward-chaining log-loss on training
    targets only (I7.folds); decision p >= 0.5, fixed.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E55 = Path(__file__).resolve().parents[1]
EXP = E55.parent
sys.path.insert(0, str(EXP / "E53_LightGBM_Calibration" / "runner"))
import e53_lib as E  # noqa: E402

I7, M, K, L, P2, np, pd = E.I7, E.M, E.K, E.L, E.P2, E.np, E.pd
FIVE = E.FIVE
LGB_BASE = dict(learning_rate=0.05, min_child_samples=10, reg_lambda=10.0, colsample_bytree=1.0, subsample=1.0,
                deterministic=True, force_row_wise=True, random_state=55, n_jobs=1, verbose=-1, feature_pre_filter=False)
ZCLIP = 6.0
SAE = E55 / "data" / "sae2021_calabarzon_municipal.csv"
POV_KNOWN_FROM = pd.Timestamp("2025-01-01")          # E54 PROTOCOL section 1 (conservative SAE 2021 release date)


# ================================================================================================ labels
def t43_labels(d) -> pd.DataFrame:
    """T43 for every quarter with an SWS round in the production file (all rounds, quarter mean) and complete CPI:
    HIGH iff H_q > 11.3 AND (food YoY_q > province P60 OR food-minus-headline YoY_q > province P60), 2021-2022 frozen
    thresholds (E40 label_spec.json). Also returns the approved-rounds-only variant and PS."""
    th = L.e40_spec()
    r = pd.read_csv(L.SWS_FILE)
    r["q"] = r["quarter"].map(L.qi)
    L._assert_window("SWS", q=r["q"])
    h_all = r.groupby("q")["H"].mean()
    h_app = r[r["definition_A"].astype(str) == "True"].groupby("q")["H"].mean()
    F, HL = L.quarter_F(d), L.quarter_F(d, "all_items").rename(columns={"F": "HL"})
    Y = F.merge(HL, on=["province_code", "q"])
    Y["PS"] = ((Y["F"] > Y["province_code"].map(th["food"])) | ((Y["F"] - Y["HL"]) > Y["province_code"].map(th["gap"]))).astype(int)
    Y["H_all"], Y["H_app"] = Y["q"].map(h_all), Y["q"].map(h_app)
    Y["T43"] = np.where(Y["H_all"].notna(), ((Y["H_all"] > th["H"]) & (Y["PS"] == 1)).astype(float), np.nan)
    Y["T43_approved"] = np.where(Y["H_app"].notna(), ((Y["H_app"] > th["H"]) & (Y["PS"] == 1)).astype(float), np.nan)
    Y["quarter"] = Y["q"].map(L.qs)
    return Y


def t43_last(d, t: int) -> dict:
    """Persistence: the latest T43 label (all rounds) whose SWS rounds were all posted and CPI quarter complete
    before O(t), per province."""
    r = pd.read_csv(L.SWS_FILE)
    r["q"] = r["quarter"].map(L.qi)
    r["published"] = pd.to_datetime(r["published"])
    O = L.origin(t)
    complete = {q for q, g in r.groupby("q") if (g["published"] < O).all()}
    Y = t43_labels(d.cut(t))
    Y = Y[Y["q"].isin(complete) & (Y["q"] <= t - 1) & Y["T43"].notna()]
    out = {}
    for p in L.PROVS:
        g = Y[Y["province_code"] == p].sort_values("q")
        out[p] = (float(g["T43"].iloc[-1]), int(g["q"].iloc[-1])) if len(g) else (np.nan, None)
    return out


# ================================================================================================ poverty (E54 POV)
def pov_values() -> dict:
    """Unweighted province mean of the PSA 2021 municipal SAE poverty incidence (E54 POV), 141 LGUs."""
    s = pd.read_csv(SAE, dtype={"lgu_code": str})
    col = "poverty_incidence_2021"
    s = s[s[col].notna()].assign(province_code=lambda f: f["province"].map(L.BY_NAME))
    assert s["province_code"].notna().all() and len(s) == 141
    return s.groupby("province_code")[col].mean().to_dict()


def add_poverty(XB: pd.DataFrame, mode: str) -> pd.DataFrame:
    """POV-AS: known only at origins O(t) >= 2025-01-01, else NaN (LightGBM missing). POV-LA: known at every origin
    (look-ahead sensitivity). FE: province indicator columns (diagnostic). Centred across provinces (E54 encoding)."""
    XB = XB.copy()
    if mode == "FE":
        for p in L.PROVS:
            XB[f"fe_{p}"] = (XB["province_code"] == p).astype(float)
        return XB
    pv = pov_values()
    mu = float(np.mean([pv[p] for p in L.PROVS]))
    XB["pov"] = XB["province_code"].map(lambda p: pv[p] - mu)
    if mode == "AS":
        XB.loc[XB["t"].map(L.origin) < POV_KNOWN_FROM, "pov"] = np.nan
    return XB


def pov_cols(mode: str | None) -> list[str]:
    return [] if mode is None else ([f"fe_{p}" for p in L.PROVS] if mode == "FE" else ["pov"])


# ================================================================================================ structural offset
def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    return np.clip(np.log(p / (1 - p)), -ZCLIP, ZCLIP)


def _sig(z):
    return 1 / (1 + np.exp(-np.asarray(z, float)))


def struct_scale(fit: pd.DataFrame, m: float) -> tuple[float, float, float]:
    """RMSE of the food and gap base-effect projections on the fitting rows, and their error correlation."""
    eF = (fit["F_true"] - fit[f"base_{m}"]).to_numpy(float)
    eG = (fit["G_true"] - fit[f"gbase_{m}"]).to_numpy(float)
    ok = np.isfinite(eF) & np.isfinite(eG)
    eF, eG = eF[ok], eG[ok]
    sF, sG = float(np.sqrt(np.mean(eF ** 2))), float(np.sqrt(np.mean(eG ** 2)))
    rho = float(np.corrcoef(eF, eG)[0, 1]) if len(eF) > 2 else 0.0
    return max(sF, 1e-3), max(sG, 1e-3), (0.0 if not np.isfinite(rho) else rho)


def struct_logit(rows: pd.DataFrame, m: float, scale) -> np.ndarray:
    sF, sG, rho = scale
    p = P2.p_price_biv(rows[f"base_{m}"].to_numpy(float), rows[f"gbase_{m}"].to_numpy(float), sF, sG, rho,
                       rows["province_code"])
    return _logit(p)


# ================================================================================================ LightGBM pieces
def _objective(centred: bool):
    def fobj(y_true, y_pred, weight):
        p = _sig(y_pred)
        w = np.ones_like(p) if weight is None else np.asarray(weight, float)
        g = w * (p - y_true)
        if centred:
            g = g - w * (g.sum() / w.sum())
        h = np.maximum(w * p * (1 - p), 1e-12)
        return g, h
    return fobj


def recency_weights(q: pd.Series, hl) -> np.ndarray | None:
    if hl is None:
        return None
    q = np.asarray(q, float)
    return 0.5 ** ((q.max() - q) / float(hl))


class PriceLGB:
    """One LightGBM price-signal classifier with a structural offset (or none) and its TreeSHAP."""

    def __init__(self, cols, m=1.0, trees=40, leaves=2, offset=True, centred=True, hl=None, unbalance=False,
                 min_child=10, struct_features=False):
        self.cols, self.m, self.trees, self.leaves = list(cols), m, trees, leaves
        self.offset, self.centred, self.hl, self.unbalance = offset, centred, hl, unbalance
        self.min_child, self.struct_features = min_child, struct_features

    def _X(self, rows):
        cols = self.cols + ([f"base_{self.m}", f"gbase_{self.m}", f"dfood_{self.m}", f"dgap_{self.m}"]
                            if self.struct_features else [])
        self.feat = cols
        return rows[cols].astype(float)

    def fit(self, fit: pd.DataFrame):
        import lightgbm as lgb
        y = fit["PS"].to_numpy(float)
        self.scale = struct_scale(fit, self.m)
        init = struct_logit(fit, self.m, self.scale) if self.offset else None
        w = recency_weights(fit["q"], self.hl)
        if self.unbalance and y.sum() > 0:
            cw = np.where(y == 1, (len(y) - y.sum()) / y.sum(), 1.0)
            w = cw if w is None else w * cw
        self.const = None
        if len(set(y)) < 2:
            self.const = float(y.mean())
            return self
        kw = dict(LGB_BASE, num_leaves=self.leaves, n_estimators=self.trees, min_child_samples=self.min_child)
        if self.offset:
            kw["objective"] = _objective(self.centred)
        else:
            kw["objective"] = "binary"
        self.model = lgb.LGBMRegressor(**kw) if self.offset else lgb.LGBMClassifier(**kw)
        self.model.fit(self._X(fit), y, sample_weight=w, init_score=init)
        self.c = 0.0
        if self.offset and self.centred:          # exact no-level-shift constraint: trees average 0 on the fitting rows
            tf = self.model.booster_.predict(self._X(fit), raw_score=True)
            self.c = float(np.average(tf, weights=w))
        return self

    def raw(self, rows) -> np.ndarray:
        """Log-odds of P(price signal): offset + trees."""
        if self.const is not None:
            return _logit(np.full(len(rows), self.const))
        t = self.model.booster_.predict(self._X(rows), raw_score=True) - self.c
        return (struct_logit(rows, self.m, self.scale) if self.offset else 0.0) + t

    def predict(self, rows) -> np.ndarray:
        return _sig(self.raw(rows))

    def contributions(self, rows) -> pd.DataFrame:
        """Exact TreeSHAP (LightGBM pred_contrib) of the trees, one column per feature + 'tree_bias' (expected tree
        output minus the no-level-shift constant); together with the offset they sum to raw()."""
        c = self.model.booster_.predict(self._X(rows), pred_contrib=True)
        c[:, -1] -= self.c
        return pd.DataFrame(c, columns=self.feat + ["tree_bias"], index=rows.index)


def frame(d, X, B, t, pov=None):
    tr, te = E.frame(d, X, B, t)
    if pov is not None:
        tr, te = add_poverty(tr, pov), add_poverty(te, pov)
    return tr, te


def feature_cols(feat: str, pov=None, drop: tuple = ()) -> list[str]:
    groups = ["market"] if feat == "market" else P2.ALL_GROUPS
    cols = [c for g in groups if g not in drop for c in P2.PRICE_GROUPS[g]]
    if "policy" not in drop:
        cols += M.POLICY
    return cols + pov_cols(pov)


# ================================================================================================ E55-LGBM (nested)
MULTS = [1.0, 0.5, 0.0]


def grid():
    return [{"m": m, "trees": n, "feat": f, "hl": h} for m in MULTS for n in (10, 40) for f in ("market", "all")
            for h in (None, 6)]


def simplicity(c):
    return (c["trees"], 0 if c["feat"] == "market" else 1, 0 if c["hl"] is None else 1, MULTS.index(c["m"]))


def _inner(args):
    tr, c, pov, drop = args
    cols = feature_cols(c["feat"], pov, drop)
    ll, n = 0.0, 0
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = np.clip(PriceLGB(cols, c["m"], c["trees"], hl=c["hl"]).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
        y = hold["PS"].to_numpy(float)
        ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        n += len(y)
    return ll / n if n else float("inf")


def hunger(d, X, t):
    """I7's regional hunger component, unchanged: P(H(t+2) > 11.3) from approved rounds posted before O(t)."""
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    if len(htr) < P2.MIN_H_PAIRS or not len(hte):
        return None
    return P2.hunger_component(htr, hte, hcols)


def lgbm_forecast(d, X, B, t, pov=None, drop: tuple = (), feats: tuple = ("market", "all"), n_jobs=8,
                  fixed: dict | None = None):
    """E55-LGBM (or a variant) at origin t. Returns None when the I7 frame is not eligible (same rule as I7).
    pov: None | "AS" | "LA" | "FE"; drop: groups removed ("climate", ..., "news", "policy"); feats: allowed feature sets."""
    from joblib import Parallel, delayed
    tr, te = frame(d, X, B, t, pov)
    if not E.ok(tr, te):
        return None
    hc = hunger(d, X, t)
    if hc is None:
        return None
    g = [fixed] if fixed else [c for c in grid() if c["feat"] in feats]
    if fixed:
        scores = [float("nan")]
        best = 0
    else:
        scores = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner)((tr, c, pov, drop)) for c in g)
        best = min(range(len(g)), key=lambda i: (round(scores[i], 10), simplicity(g[i])))
    c = g[best]
    cols = feature_cols(c["feat"], pov, drop)
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = PriceLGB(cols, c["m"], c["trees"], hl=c["hl"]).fit(fit)
    pp = mdl.predict(te)
    return {"t": t, "p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "H_hat": hc["H_hat"], "cfg": c,
            "inner_logloss": scores[best], "grid_logloss": {str(i): s for i, s in enumerate(scores)}, "model": mdl,
            "te": te, "tr": fit, "cols": cols, "n_train_rows": int(len(fit)), "n_train_q": int(fit["q"].nunique()),
            "n_train_HIGH": int(fit["PS"].sum())}


# ================================================================================================ factor diagnostics
DIAG = {
    "F0_naive": dict(offset=False, struct_features=False, leaves=4, trees=100, centred=False),
    "F1_struct_features": dict(offset=False, struct_features=True, leaves=4, trees=100, centred=False),
    "F2_offset": dict(offset=True, centred=False, leaves=2, trees=40),
    "F3_offset_centred": dict(offset=True, centred=True, leaves=2, trees=40),
    "F4_recency": dict(offset=True, centred=True, leaves=2, trees=40, hl=6),
    "F5_complex": dict(offset=True, centred=True, leaves=8, trees=300, min_child=5),
    "F6_class_weight": dict(offset=True, centred=True, leaves=2, trees=40, unbalance=True),
    "F7_tuned_threshold": dict(offset=True, centred=True, leaves=2, trees=40),
    "F8_platt": dict(offset=True, centred=True, leaves=2, trees=40),
    "F9_no_remittance": dict(offset=True, centred=True, leaves=2, trees=40),
    "F10_last8q": dict(offset=True, centred=True, leaves=2, trees=40),
}


def diag_forecast(d, X, B, t, name: str):
    """One fixed configuration (no selection): m = 1.0, all groups + policy. Gate = I7 hunger component."""
    tr, te = frame(d, X, B, t)
    if not E.ok(tr, te):
        return None
    hc = hunger(d, X, t)
    if hc is None:
        return None
    kw = dict(DIAG[name])
    drop = ("ofw_remittance",) if name == "F9_no_remittance" else ()
    cols = feature_cols("all", None, drop)
    if name == "F9_no_remittance":
        cols = [c for c in cols if c != "news_ofw_remittance"]
    fit = tr.dropna(subset=["base_1.0", "gbase_1.0", "F_true", "G_true"])
    if name == "F10_last8q":
        fit = fit[fit["q"] > fit["q"].max() - 8]
    mdl = PriceLGB(cols, 1.0, **kw).fit(fit)
    pp = mdl.predict(te)
    thr = 0.5
    if name in ("F7_tuned_threshold", "F8_platt"):
        oof = []
        for q, fq in I7.folds(fit["q"].unique(), "forward"):
            f_, h_ = fit[fit["q"].isin(fq)], fit[fit["q"] == q]
            if len(f_) and len(h_):
                oof.append(h_.assign(p_oof=PriceLGB(cols, 1.0, **kw).fit(f_).predict(h_)))
        if oof:
            o = pd.concat(oof)
            if name == "F8_platt" and o["PS"].nunique() == 2 and len(o) >= 10:
                cal = E.fit_calibrator(o["p_oof"], o["PS"], "C2")
                pp = E.apply_calibrator(cal, pp)
            if name == "F7_tuned_threshold" and o["PS"].nunique() == 2:
                ph = hc["p"]
                cand = np.round(np.arange(0.2, 0.81, 0.05), 2)
                ys = o["PS"].to_numpy()

                def bal(th_):
                    yh = (ph * o["p_oof"].to_numpy() >= th_).astype(int)
                    rh = ((yh == 1) & (ys == 1)).sum() / max(ys.sum(), 1)
                    rl = ((yh == 0) & (ys == 0)).sum() / max((ys == 0).sum(), 1)
                    return (rh + rl) / 2
                thr = float(max(cand, key=lambda th_: (round(bal(th_), 10), th_ == 0.5, -abs(th_ - 0.5))))
    return {"t": t, "p": hc["p"] * pp, "p_price": pp, "threshold": thr}


# ================================================================================================ TreeSHAP grouping
def group_of(col: str) -> str:
    if col == "pov" or col.startswith("fe_"):
        return "poverty"
    return E.group_of(col)


def attribution(fx: dict, i: int, train_offset_mean: float | None = None) -> dict:
    """Additive log-odds decomposition of the price-signal component of province row i:
        logit P_price = baseline + market_projection + sum_g TreeSHAP_g
    baseline = mean training offset + tree expected value; market_projection = offset_i - mean training offset (the
    base-effect CPI projection, part of Market / Prices). Exact: the reconstruction error is returned."""
    mdl, te = fx["model"], fx["te"]
    row = te.iloc[[i]]
    raw = float(mdl.raw(row)[0])
    if mdl.const is not None:
        return {"raw": raw, "baseline": raw, "groups": {}, "error": 0.0, "constant": True}
    off = float(struct_logit(row, mdl.m, mdl.scale)[0])
    mo = float(np.mean(struct_logit(fx["tr"], mdl.m, mdl.scale))) if train_offset_mean is None else train_offset_mean
    c = mdl.contributions(row).iloc[0]
    groups = {g: 0.0 for g in FIVE + ["poverty", "other"]}
    per_feature = {}
    for k, v in c.items():
        if k == "tree_bias":
            continue
        groups[group_of(k)] += float(v)
        per_feature[k] = float(v)
    groups["market"] += off - mo
    baseline = mo + float(c["tree_bias"])
    err = abs(baseline + sum(groups.values()) - raw)
    return {"raw": raw, "baseline": baseline, "offset": off, "offset_train_mean": mo, "groups": groups,
            "per_feature": per_feature, "error": err, "constant": False}
