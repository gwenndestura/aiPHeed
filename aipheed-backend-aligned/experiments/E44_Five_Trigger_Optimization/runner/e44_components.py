"""E44 iterations I2/I3 (PROTOCOL.md section 3): five-trigger component model.

P(T43 at t+2) = P(H(t+2) > 11.3) x P(province price signal at t+2), with
  price:  F(t+2) = base-effect projection (drift multiplier m) + five-trigger residual model (ridge or LightGBM),
          selected by blocked leave-one-target-quarter-out RMSE on training pairs; predictive SD = that RMSE;
  hunger: H(t+2) = H_last + ridge on regional five-trigger signals, selected the same way.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e44_classifiers as C  # noqa: E402

K, L, np, pd = C.K, C.L, C.np, C.pd
from scipy.stats import norm  # noqa: E402

MULTS = [1.0, 0.5, 0.0]
PRICE_GROUPS = {"market": ["F_hat_M1", "F_now", "D_now", "gap_now", "rice_whsl_yoy"],
                "climate": ["tc_count", "tc_count_l1", "enso", "enso_l2", "palay_yoy", "corn_yoy", "enso_x_mom",
                            "tcl1_x_palay"],
                "fish_kill": ["fish_yoy", "aqua_yoy"],
                "employment": ["ur_yoy", "under_yoy"],
                "ofw_remittance": ["remit_usd_yoy", "remit_php_yoy", "fx_yoy"],
                "news": ["news_market", "news_climate", "news_fish_kill", "news_employment", "news_ofw_remittance",
                         "news_n"]}
HUNGER_GROUPS = {"market": ["F_now"], "climate": ["enso", "enso_l2", "tc_count", "tc_count_l1", "palay_yoy"],
                 "fish_kill": ["fish_yoy"], "employment": ["ur_yoy", "under_yoy"],
                 "ofw_remittance": ["remit_php_yoy", "fx_yoy"], "news": ["news_n"]}
ALL_GROUPS = ["market", "climate", "fish_kill", "employment", "ofw_remittance", "news"]
MIN_PRICE_Q, MIN_H_PAIRS = 6, 6


# ------------------------------------------------------------------------------------------------ features
def features(d, x, origins):
    X = C.features(d, x, origins)
    X["enso_x_mom"] = X["enso"] * X["mom3"]
    X["tcl1_x_palay"] = X["tc_count_l1"] * X["palay_yoy"]
    return X


def proj(d_cut, t, p, mult, commodity):
    """Base-effect projection of the quarter-mean YoY at t+2 (E41 M1 with drift x mult), for food or all items."""
    m0 = L.m0_of(t)
    I = L._series(d_cut, p, commodity)
    if m0 not in I.index:
        return np.nan
    lnI = np.log(I)
    g, _, n = L.drift_sigma(lnI, m0)
    ms = L.target_months(t, 2)
    if n < 6 or any((m - 12) not in I.index for m in ms):
        return np.nan
    return float(np.mean([100 * (math.exp(lnI[m0] + g * mult * (m - m0)) / I[m - 12] - 1) for m in ms]))


def bases(d, origins):
    rows = []
    for t in origins:
        c = d.cut(t)
        for p in L.PROVS:
            r = {"t": t, "province_code": p}
            for m in MULTS:
                r[f"base_{m}"] = proj(c, t, p, m, "food")
                r[f"hl_{m}"] = proj(c, t, p, m, "all_items")
            rows.append(r)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ models
class Ridge:
    def __init__(self, cols, alpha):
        self.cols, self.alpha = cols, alpha

    def fit(self, X, y):
        from sklearn.linear_model import Ridge as R
        Z = X[self.cols].astype(float)
        self.med = Z.median()
        self.miss = [c for c in self.cols if Z[c].isna().any()]
        D = self._design(Z)
        self.mu, self.sd = D.mean(), D.std(ddof=0).replace(0, 1)
        self.keep = [c for c in D if D[c].std(ddof=0) > 0]
        self.m = R(alpha=self.alpha).fit(((D - self.mu) / self.sd)[self.keep] if self.keep else np.zeros((len(D), 1)), y)
        return self

    def _design(self, Z):
        D = Z.fillna(self.med).fillna(0.0)
        for c in self.miss:
            D[f"{c}__missing"] = Z[c].isna().astype(float)
        return D

    def _z(self, X):
        D = self._design(X[self.cols].astype(float))
        return ((D - self.mu) / self.sd)[self.keep] if self.keep else np.zeros((len(D), 1))

    def predict(self, X):
        return self.m.predict(self._z(X))

    def contributions(self, X) -> pd.DataFrame:
        if not self.keep:
            return pd.DataFrame(0.0, index=X.index, columns=self.cols)
        c = self._z(X) * self.m.coef_
        c.columns = [k.replace("__missing", "") for k in c.columns]
        return c.T.groupby(level=0).sum().T


class GBR:
    def __init__(self, cols, leaves, n_est):
        self.cols, self.leaves, self.n_est = cols, leaves, n_est

    def fit(self, X, y):
        from lightgbm import LGBMRegressor
        self.m = LGBMRegressor(num_leaves=self.leaves, n_estimators=self.n_est, learning_rate=0.05, reg_lambda=10.0,
                               min_child_samples=5, random_state=42, deterministic=True, n_jobs=1,
                               force_row_wise=True, verbosity=-1).fit(X[self.cols].astype(float), y)
        return self

    def predict(self, X):
        return self.m.predict(X[self.cols].astype(float))

    def contributions(self, X) -> pd.DataFrame:
        c = self.m.booster_.predict(X[self.cols].astype(float), pred_contrib=True)[:, :-1]
        return pd.DataFrame(c, columns=self.cols, index=X.index)


def price_grid():
    g = [{"mult": m, "model": "ridge", "alpha": a} for m in MULTS for a in (1.0, 10.0, 100.0)]
    g += [{"mult": m, "model": "lgbm", "leaves": nl, "n_est": ne} for m in MULTS for nl in (2, 4) for ne in (50, 150)]
    return g


def make_price(cfg, cols):
    return Ridge(cols, cfg["alpha"]) if cfg["model"] == "ridge" else GBR(cols, cfg["leaves"], cfg["n_est"])


def price_simplicity(cfg):
    return (cfg["model"] != "ridge", -cfg.get("alpha", 0), cfg.get("leaves", 0), cfg.get("n_est", 0), -cfg["mult"])


def _price_oof(args):
    tr, cfg, cols = args
    b = f"base_{cfg['mult']}"
    tr = tr.dropna(subset=[b])
    out = []
    for q in sorted(tr["q"].unique()):
        fit, hold = tr[tr["q"] != q], tr[tr["q"] == q]
        m = make_price(cfg, cols).fit(fit, fit["F_true"] - fit[b])
        out.append(hold[["q", "province_code", "F_true"]].assign(F_hat=hold[b].to_numpy() + m.predict(hold)))
    o = pd.concat(out, ignore_index=True)
    return float(np.sqrt(np.mean((o["F_hat"] - o["F_true"]) ** 2))), o


def price_component(tr, te, cols, n_jobs=8):
    """Select (mult, model) by blocked LOQO RMSE; return F_hat, HL_hat, s, OOF, the fitted model and its config."""
    from joblib import Parallel, delayed
    grid = price_grid()
    res = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_price_oof)((tr, g, cols)) for g in grid)
    best = min(range(len(grid)), key=lambda i: (round(res[i][0], 10), price_simplicity(grid[i])))
    cfg, (rmse, o) = grid[best], res[best]
    b = f"base_{cfg['mult']}"
    trb = tr.dropna(subset=[b])
    model = make_price(cfg, cols).fit(trb, trb["F_true"] - trb[b])
    return {"cfg": cfg, "rmse": rmse, "oof": o, "model": model, "F_hat": te[b].to_numpy() + model.predict(te),
            "HL_hat": te[f"hl_{cfg['mult']}"].to_numpy(), "base": te[b].to_numpy()}


def p_price(F_hat, HL_hat, s, provs):
    th = L.e40_spec()
    cut = np.array([min(th["food"][p], th["gap"][p] + hl) for p, hl in zip(provs, HL_hat)])
    return 1 - norm.cdf((cut - np.asarray(F_hat)) / s)


def _h_oof(tr, alpha, cols):
    out = []
    for q in tr["q"].unique():
        fit, hold = tr[tr["q"] != q], tr[tr["q"] == q]
        if cols:
            m = Ridge(cols, alpha).fit(fit, fit["H_true"] - fit["H_base"])
            pr = hold["H_base"].to_numpy() + m.predict(hold)
        else:
            pr = hold["H_base"].to_numpy()
        out.append(hold[["q"]].assign(H_hat=pr, H_true=hold["H_true"].to_numpy()))
    o = pd.concat(out, ignore_index=True)
    return float(np.sqrt(np.mean((o["H_hat"] - o["H_true"]) ** 2))), o


def hunger_component(htr, hte, cols):
    """Ridge on regional signals (alpha by LOQO RMSE); cols empty = random walk."""
    alphas = (1.0, 10.0, 100.0) if cols else (None,)
    res = {a: _h_oof(htr, a, cols) for a in alphas}
    a = min(alphas, key=lambda z: (round(res[z][0], 10), -(z or 0)))
    rmse, o = res[a]
    if cols:
        m = Ridge(cols, a).fit(htr, htr["H_true"] - htr["H_base"])
        H_hat = float(hte["H_base"].iloc[0] + m.predict(hte)[0])
    else:
        m, H_hat = None, float(hte["H_base"].iloc[0])
    return {"alpha": a, "rmse": rmse, "oof": o, "model": m, "H_hat": H_hat,
            "p": float(1 - norm.cdf((L.e40_spec()["H"] - H_hat) / max(rmse, 1e-6)))}


# ------------------------------------------------------------------------------------------------ hunger series
def h_series(d_full, t: int, supplementary: bool) -> pd.Series:
    """Quarter-mean H of rounds posted before O(t): approved rounds, plus the supplementary ones for I3."""
    c = d_full.cut(t)
    s = c.sws.groupby("q")["H"].mean()
    if supplementary:
        r = pd.read_csv(L.SWS_FILE)
        r = r[r["definition_A"].astype(str) != "True"].copy()
        r["q"] = r["quarter"].map(L.qi)
        r = r[pd.to_datetime(r["published"]) < L.origin(t)]
        sup = r.groupby("q")["H"].mean()
        s = pd.concat([s, sup[~sup.index.isin(s.index)]]).sort_index()
    return s


def hunger_frame(X: pd.DataFrame, hs: pd.Series, t: int, cols: list[str]):
    """Regional training pairs (origins t' with H(t'+2) posted before O(t)) and the test row at t. The base of a
    training pair is H_last as of its own origin t' (from X); the test base is the latest H posted before O(t)."""
    hc = sorted(set(c for g in HUNGER_GROUPS.values() for c in g))
    reg = X.groupby("t")[hc + ["H_last"]].mean().reset_index().rename(columns={"H_last": "H_base"})
    reg["H_true"] = reg["t"].map(lambda tp: hs.get(tp + 2, np.nan))
    htr = reg[(reg["t"] + 2 <= t - 1) & reg["H_true"].notna() & reg["H_base"].notna()].assign(q=lambda f: f["t"] + 2)
    hte = reg[reg["t"] == t].copy()
    if len(hte):
        latest = hs[hs.index <= t]
        hte["H_base"] = float(latest.iloc[-1]) if len(latest) else np.nan
    return htr, hte


# ------------------------------------------------------------------------------------------------ one origin
def forecast(d, X, B, t, groups=ALL_GROUPS, supplementary=False, hunger_rw=False, n_jobs=8):
    pcols = [c for g in groups for c in PRICE_GROUPS[g]]
    hcols = [] if hunger_rw else [c for g in groups if g in HUNGER_GROUPS for c in HUNGER_GROUPS[g]]
    F = L.quarter_F(d.cut(t)).rename(columns={"q": "qF", "F": "F_true"})
    XB = X.merge(B, on=["t", "province_code"])
    tr = XB[XB["t"] + 2 <= t - 1].assign(qF=lambda f: f["t"] + 2).merge(F, on=["province_code", "qF"])
    tr = tr.rename(columns={"qF": "q"})
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    hs = h_series(d, t, supplementary)
    htr, hte = hunger_frame(X, hs, t, hcols)
    if tr["q"].nunique() < MIN_PRICE_Q or len(htr) < MIN_H_PAIRS or not len(hte) or te[[f"base_{m}" for m in MULTS]].isna().all().all():
        return None
    pc = price_component(tr, te, pcols, n_jobs)
    hc = hunger_component(htr, hte, hcols)
    pp = p_price(pc["F_hat"], pc["HL_hat"], pc["rmse"], te["province_code"])
    p_joint = hc["p"] * pp
    # out-of-fold joint p on labelled training targets -> threshold (+ Platt if >= 3 HIGH)
    lab = K.available_labels(d, t)
    o = pc["oof"].merge(hc["oof"].groupby("q")["H_hat"].first().rename("H_hat").reset_index(), on="q")
    o = o.merge(tr[["province_code", "q", f"hl_{pc['cfg']['mult']}"]], on=["province_code", "q"])
    o = o.merge(lab[["province_code", "q", "y"]], on=["province_code", "q"])
    thr, platt, p_cal = 0.5, None, p_joint
    if len(o) and o["y"].nunique() == 2:
        ph = 1 - norm.cdf((L.e40_spec()["H"] - o["H_hat"]) / max(hc["rmse"], 1e-6))
        po = ph * p_price(o["F_hat"], o[f"hl_{pc['cfg']['mult']}"], pc["rmse"], o["province_code"])
        if o["y"].sum() >= 3:
            platt = C.platt_fit(po, o["y"])
            po = C.platt_apply(platt, po)
            p_cal = C.platt_apply(platt, p_joint)
        thr = max(C.THRESHOLDS, key=lambda th: (round(C.balanced(o["y"], po >= th), 10), th == 0.5, th))
    return {"t": t, "p": np.asarray(p_cal), "p_raw": p_joint, "p_hunger": hc["p"], "p_price": pp, "threshold": thr,
            "F_hat": pc["F_hat"], "H_hat": hc["H_hat"], "price_cfg": pc["cfg"], "price_rmse": pc["rmse"],
            "hunger_alpha": hc["alpha"], "hunger_rmse": hc["rmse"], "platt": platt is not None,
            "price_model": pc["model"], "hunger_model": hc["model"], "te": te, "hte": hte, "pcols": pcols, "hcols": hcols,
            "n_price_train_q": int(tr["q"].nunique()), "n_hunger_pairs": int(len(htr))}


# ================================================================================================ I4 (ADDENDUM_I4.md)
def _oof_generic(args):
    tr, cfg, cols, ycol, bfmt = args
    b = bfmt.format(cfg["mult"])
    tr = tr.dropna(subset=[b, ycol])
    out = []
    for q in sorted(tr["q"].unique()):
        fit, hold = tr[tr["q"] != q], tr[tr["q"] == q]
        m = make_price(cfg, cols).fit(fit, fit[ycol] - fit[b])
        out.append(hold[["q", "province_code"]].assign(y_true=hold[ycol].to_numpy(), y_hat=hold[b].to_numpy() + m.predict(hold)))
    o = pd.concat(out, ignore_index=True)
    return float(np.sqrt(np.mean((o["y_hat"] - o["y_true"]) ** 2))), o


def component_generic(tr, te, cols, ycol, bfmt, n_jobs=8):
    from joblib import Parallel, delayed
    grid = price_grid()
    res = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_oof_generic)((tr, g, cols, ycol, bfmt)) for g in grid)
    best = min(range(len(grid)), key=lambda i: (round(res[i][0], 10), price_simplicity(grid[i])))
    cfg, (rmse, o) = grid[best], res[best]
    b = bfmt.format(cfg["mult"])
    trb = tr.dropna(subset=[b, ycol])
    model = make_price(cfg, cols).fit(trb, trb[ycol] - trb[b])
    return {"cfg": cfg, "rmse": rmse, "oof": o, "model": model, "hat": te[b].to_numpy() + model.predict(te)}


def p_price_biv(F_hat, G_hat, sF, sG, rho, provs):
    from scipy.stats import multivariate_normal
    th = L.e40_spec()
    rho = float(np.clip(rho, -0.95, 0.95))
    cov = [[1.0, rho], [rho, 1.0]]
    out = []
    for f, g, p in zip(F_hat, G_hat, provs):
        zf, zg = (th["food"][p] - f) / sF, (th["gap"][p] - g) / sG
        out.append(1 - float(multivariate_normal(mean=[0, 0], cov=cov).cdf([zf, zg])))
    return np.array(out)


def forecast_i4(d, X, B, t, groups=ALL_GROUPS, hunger_rw=False, n_jobs=8):
    pcols = [c for g in groups for c in PRICE_GROUPS[g]]
    hcols = [] if hunger_rw else [c for g in groups if g in HUNGER_GROUPS for c in HUNGER_GROUPS[g]]
    c = d.cut(t)
    F = L.quarter_F(c).rename(columns={"F": "F_true"})
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL_true"})
    FG = F.merge(HL, on=["province_code", "q"]).assign(G_true=lambda f: f["F_true"] - f["HL_true"])
    XB = X.merge(B, on=["t", "province_code"])
    for m in MULTS:
        XB[f"gbase_{m}"] = XB[f"base_{m}"] - XB[f"hl_{m}"]
    tr = XB[XB["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(FG, on=["province_code", "q"])
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    hs = h_series(d, t, False)
    htr, hte = hunger_frame(X, hs, t, hcols)
    if tr["q"].nunique() < MIN_PRICE_Q or len(htr) < MIN_H_PAIRS or not len(hte) or te[[f"base_{m}" for m in MULTS]].isna().all().all():
        return None
    fc = component_generic(tr, te, pcols, "F_true", "base_{}", n_jobs)
    gc = component_generic(tr, te, pcols, "G_true", "gbase_{}", n_jobs)
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    hc = hunger_component(htr, hte, hcols)
    pp = p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    p_joint = hc["p"] * pp
    lab = K.available_labels(d, t)
    o = j.merge(hc["oof"].groupby("q")["H_hat"].first().rename("H_hat").reset_index(), on="q")
    o = o.merge(lab[["province_code", "q", "y"]], on=["province_code", "q"])
    thr, platt, p_cal = 0.5, None, p_joint
    if len(o) and o["y"].nunique() == 2:
        ph = 1 - norm.cdf((L.e40_spec()["H"] - o["H_hat"]) / max(hc["rmse"], 1e-6))
        po = ph * p_price_biv(o["y_hat_F"], o["y_hat_G"], fc["rmse"], gc["rmse"], rho, o["province_code"])
        if o["y"].sum() >= 3:
            platt = C.platt_fit(po, o["y"])
            po = C.platt_apply(platt, po)
            p_cal = C.platt_apply(platt, p_joint)
        thr = max(C.THRESHOLDS, key=lambda th: (round(C.balanced(o["y"], po >= th), 10), th == 0.5, th))
    return {"t": t, "p": np.asarray(p_cal), "p_raw": p_joint, "p_hunger": hc["p"], "p_price": pp, "threshold": thr,
            "F_hat": fc["hat"], "G_hat": gc["hat"], "rho": rho, "H_hat": hc["H_hat"], "food_cfg": fc["cfg"],
            "gap_cfg": gc["cfg"], "food_rmse": fc["rmse"], "gap_rmse": gc["rmse"], "hunger_alpha": hc["alpha"],
            "hunger_rmse": hc["rmse"], "platt": platt is not None, "food_model": fc["model"], "gap_model": gc["model"],
            "hunger_model": hc["model"], "te": te, "hte": hte, "pcols": pcols, "hcols": hcols}
