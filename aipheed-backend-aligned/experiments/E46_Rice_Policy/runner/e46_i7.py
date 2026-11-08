"""E46 iteration I7 (ADDENDUM_I7.md): the defect-corrected five-trigger component model.

Changes against I2/I6, each fixing a defect diagnosed in ADDENDUM_I7.md section 1:
  D1  the price signal is built from two consistently projected quantities, food YoY F and the food-headline gap G
      (each = base-effect projection + residual), instead of a corrected F compared with an uncorrected headline;
  D2  the decision is p >= 0.5 with p = P(H > 11.3) x P(price signal): no per-origin Platt or threshold refit on
      a handful of out-of-fold labels;
  D3  residual models are ridge regressions WITHOUT an intercept (they explain variation across province-quarters,
      they cannot carry a level shift learned in an earlier regime), selected by embargoed forward-chaining RMSE
      (an inner fold at target q is fitted only on targets <= q-3, whose outcomes were published before its origin).
The hunger component is E44 I2's, unchanged. Five trigger groups + news + the as-of policy block are the residual
inputs; the grid always includes "no residual", so the data decide each input's weight.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_lib as M  # noqa: E402

C, K, L, P2, np, pd = M.C, M.K, M.L, M.P2, M.np, M.pd
from scipy.stats import norm  # noqa: E402

ALPHAS = [None, 1.0, 10.0, 100.0, 1000.0]          # None = base-effect projection only (no residual)
N_FORWARD, MIN_EARLIER, EMBARGO = 6, 4, 3           # I5 conventions; embargo = targets <= q-3 at inner origin q-2
DECISION = 0.5


class RidgeNI(P2.Ridge):
    """E44 Ridge with optional intercept (standardised inputs, median imputation + missing flags)."""

    def __init__(self, cols, alpha, intercept=False):
        super().__init__(cols, alpha)
        self.intercept = intercept

    def fit(self, X, y):
        from sklearn.linear_model import Ridge as R
        Z = X[self.cols].astype(float)
        self.med = Z.median()
        self.miss = [c for c in self.cols if Z[c].isna().any()]
        D = self._design(Z)
        self.mu, self.sd = D.mean(), D.std(ddof=0).replace(0, 1)
        self.keep = [c for c in D if D[c].std(ddof=0) > 0]
        self.m = R(alpha=self.alpha, fit_intercept=self.intercept).fit(
            ((D - self.mu) / self.sd)[self.keep] if self.keep else np.zeros((len(D), 1)), y)
        return self


def grid(force_base=False):
    return [{"mult": m, "alpha": a} for m in P2.MULTS for a in ([None] if force_base else ALPHAS)]


def simplicity(cfg):
    # base-only first, then stronger shrinkage, then the E41 M1 default drift (1.0), 0.5, 0.0
    return (cfg["alpha"] is not None, -(cfg["alpha"] or 0), [1.0, 0.5, 0.0].index(cfg["mult"]))


def folds(qs, selection):
    qs = sorted(qs)
    if selection == "loqo":
        return [(q, [x for x in qs if x != q]) for q in qs]
    out = []
    for q in qs:
        fit = [x for x in qs if x <= q - EMBARGO]
        if len(fit) >= MIN_EARLIER:
            out.append((q, fit))
    return out[-N_FORWARD:]


def _fit(cfg, cols, fit, ycol, b, intercept):
    return RidgeNI(cols, cfg["alpha"], intercept).fit(fit, fit[ycol] - fit[b])


def _oof(args):
    tr, cfg, cols, ycol, bfmt, intercept, selection = args
    b = bfmt.format(cfg["mult"])
    tr = tr.dropna(subset=[b, ycol])
    out = []
    for q, fq in folds(tr["q"].unique(), selection):
        fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
        res = 0.0 if cfg["alpha"] is None else _fit(cfg, cols, fit, ycol, b, intercept).predict(hold)
        out.append(hold[["q", "province_code"]].assign(y_true=hold[ycol].to_numpy(), y_hat=hold[b].to_numpy() + res))
    if not out:
        return float("inf"), pd.DataFrame(columns=["q", "province_code", "y_true", "y_hat"])
    o = pd.concat(out, ignore_index=True)
    return float(np.sqrt(np.mean((o["y_hat"] - o["y_true"]) ** 2))), o


def component(tr, te, cols, ycol, bfmt, intercept, selection, force_base, n_jobs):
    from joblib import Parallel, delayed
    g = grid(force_base)
    res = Parallel(n_jobs=n_jobs, backend="loky")(
        delayed(_oof)((tr, c, cols, ycol, bfmt, intercept, selection)) for c in g)
    best = min(range(len(g)), key=lambda i: (round(res[i][0], 10), simplicity(g[i])))
    cfg, (rmse, o) = g[best], res[best]
    b = bfmt.format(cfg["mult"])
    trb = tr.dropna(subset=[b, ycol])
    model = None if cfg["alpha"] is None else _fit(cfg, cols, trb, ycol, b, intercept)
    hat = te[b].to_numpy() + (0.0 if model is None else model.predict(te))
    return {"cfg": cfg, "rmse": rmse, "oof": o, "model": model, "hat": hat, "base": te[b].to_numpy(),
            "grid_rmse": {f"m{c['mult']}_a{c['alpha']}": r[0] for c, r in zip(g, res)}}


def forecast(d, X, B, t, groups=P2.ALL_GROUPS, policy=True, intercept=False, selection="forward",
             force_base=False, n_jobs=8):
    pcols = [c for g in groups for c in P2.PRICE_GROUPS[g]] + (M.POLICY if policy else [])
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    c = d.cut(t)
    F = L.quarter_F(c).rename(columns={"F": "F_true"})
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL_true"})
    FG = F.merge(HL, on=["province_code", "q"]).assign(G_true=lambda f: f["F_true"] - f["HL_true"])
    XB = X.merge(B, on=["t", "province_code"])
    for m in P2.MULTS:
        XB[f"gbase_{m}"] = XB[f"base_{m}"] - XB[f"hl_{m}"]
    tr = XB[XB["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(FG, on=["province_code", "q"])
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    htr, hte = P2.hunger_frame(X, P2.h_series(d, t, False), t, hcols)
    if (tr["q"].nunique() < P2.MIN_PRICE_Q or len(htr) < P2.MIN_H_PAIRS or not len(hte)
            or te[[f"base_{m}" for m in P2.MULTS]].isna().all().all()):
        return None
    fc = component(tr, te, pcols, "F_true", "base_{}", intercept, selection, force_base, n_jobs)
    gc = component(tr, te, pcols, "G_true", "gbase_{}", intercept, selection, force_base, n_jobs)
    if not (np.isfinite(fc["rmse"]) and np.isfinite(gc["rmse"])):
        return None
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    hc = P2.hunger_component(htr, hte, hcols)
    ps = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    p = hc["p"] * ps
    return {"t": t, "p": np.asarray(p), "threshold": DECISION, "p_hunger": hc["p"], "p_price": ps,
            "F_hat": fc["hat"], "G_hat": gc["hat"], "F_base": fc["base"], "G_base": gc["base"], "rho": rho,
            "H_hat": hc["H_hat"], "food_cfg": fc["cfg"], "gap_cfg": gc["cfg"], "food_rmse": fc["rmse"],
            "gap_rmse": gc["rmse"], "food_grid": fc["grid_rmse"], "gap_grid": gc["grid_rmse"],
            "hunger_alpha": hc["alpha"], "hunger_rmse": hc["rmse"], "food_model": fc["model"],
            "gap_model": gc["model"], "hunger_model": hc["model"], "te": te, "hte": hte, "pcols": pcols,
            "hcols": hcols, "n_price_train_q": int(tr["q"].nunique())}
