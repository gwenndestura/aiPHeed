"""E53 library (PROTOCOL.md): the E52 price model (R0, exact I7 component), its calibrators (C1, C2), the LightGBM arms
(LGB-R, LGB-RL, LGB-C), and E51's metric code copied unchanged.

Every arm uses the I7 as-of frame: forecast at origin O(t) for target t+2, training targets <= t-1 with vintage d.cut(t).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
E53 = Path(__file__).resolve().parents[1]
EXP = E53.parent
sys.path.insert(0, str(EXP / "E46_Rice_Policy" / "runner"))
import e46_i7 as I7  # noqa: E402

M, K, L, P2, np, pd = I7.M, I7.K, I7.L, I7.P2, I7.np, I7.pd
FIVE = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
NEWS_TO_GROUP = {"news_market": "market", "news_climate": "climate", "news_fish_kill": "fish_kill",
                 "news_employment": "employment", "news_ofw_remittance": "ofw_remittance"}   # D-1; news_n -> other
LGB_FIXED = dict(learning_rate=0.05, min_child_samples=10, reg_lambda=10.0, colsample_bytree=0.8, subsample=1.0,
                 deterministic=True, force_row_wise=True, random_state=53, n_jobs=1, verbose=-1)


def group_of(col: str) -> str:
    """D-1 explanation mapping of every residual input to one of the five groups or 'other'."""
    for g in FIVE:
        if col in P2.PRICE_GROUPS[g]:
            return g
    if col in M.POLICY:
        return "market"
    return NEWS_TO_GROUP.get(col, "other")


# ---------------------------------------------------------------- frame (identical to I7.forecast)
def load():
    d, x, ev = L.load(), K.load_extra(), M.load_events()
    allo = list(range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1))
    return d, M.features(d, x, allo, ev), P2.bases(d, allo)


def frame(d, X, B, t):
    c = d.cut(t)
    F = L.quarter_F(c).rename(columns={"F": "F_true"})
    HL = L.quarter_F(c, "all_items").rename(columns={"F": "HL_true"})
    FG = F.merge(HL, on=["province_code", "q"]).assign(G_true=lambda f: f["F_true"] - f["HL_true"])
    XB = X.merge(B, on=["t", "province_code"])
    for m in P2.MULTS:
        XB[f"gbase_{m}"] = XB[f"base_{m}"] - XB[f"hl_{m}"]
    th = L.e40_spec()
    for m in P2.MULTS:                                   # distance-to-threshold features (LGB-C only)
        XB[f"dfood_{m}"] = XB[f"base_{m}"] - XB["province_code"].map(th["food"])
        XB[f"dgap_{m}"] = XB[f"gbase_{m}"] - XB["province_code"].map(th["gap"])
    tr = XB[XB["t"] + 2 <= t - 1].assign(q=lambda f: f["t"] + 2).merge(FG, on=["province_code", "q"])
    tr["PS"] = ((tr["F_true"] > tr["province_code"].map(th["food"]))
                | (tr["G_true"] > tr["province_code"].map(th["gap"]))).astype(int)
    te = XB[XB["t"] == t].set_index("province_code").loc[L.PROVS].reset_index()
    return tr, te


def pcols(groups=P2.ALL_GROUPS, policy=True):
    return [c for g in groups for c in P2.PRICE_GROUPS[g]] + (M.POLICY if policy else [])


def ok(tr, te) -> bool:
    return tr["q"].nunique() >= P2.MIN_PRICE_Q and not te[[f"base_{m}" for m in P2.MULTS]].isna().all().all()


# ---------------------------------------------------------------- LightGBM residual component
class LGBRes:
    def __init__(self, cols, leaves, trees, linear=False):
        self.cols, self.leaves, self.trees, self.linear = cols, leaves, trees, linear

    def fit(self, X, y):
        import lightgbm as lgb
        kw = dict(LGB_FIXED, num_leaves=self.leaves, n_estimators=self.trees)
        if self.linear:
            kw.update(linear_tree=True, linear_lambda=10.0)
        self.m = lgb.LGBMRegressor(**kw).fit(X[self.cols].astype(float), np.asarray(y, float))
        return self

    def predict(self, X):
        return self.m.predict(X[self.cols].astype(float))


def lgb_grid(linear=False):
    g = [{"mult": m, "res": None} for m in P2.MULTS]
    for m in P2.MULTS:
        for lv in (2, 4):
            for n in (50, 200):
                for f in ("all", "market"):
                    g.append({"mult": m, "res": "lgb", "leaves": lv, "trees": n, "feat": f, "linear": linear})
    return g


def lgb_simplicity(c):
    mult = [1.0, 0.5, 0.0].index(c["mult"])
    if c["res"] is None:
        return (0, 0, 0, 0, mult)
    return (1, c["leaves"], c["trees"], 0 if c["feat"] == "market" else 1, mult)


def _lgb_cols(c, cols_all):
    return P2.PRICE_GROUPS["market"] if c["feat"] == "market" else cols_all


def _lgb_oof(args):
    tr, c, cols_all, ycol, bfmt = args
    b = bfmt.format(c["mult"])
    tr = tr.dropna(subset=[b, ycol])
    out = []
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
        res = 0.0
        if c["res"] is not None:
            res = LGBRes(_lgb_cols(c, cols_all), c["leaves"], c["trees"], c["linear"]).fit(fit, fit[ycol] - fit[b]).predict(hold)
        out.append(hold[["q", "province_code"]].assign(y_true=hold[ycol].to_numpy(), y_hat=hold[b].to_numpy() + res))
    if not out:
        return float("inf"), pd.DataFrame(columns=["q", "province_code", "y_true", "y_hat"])
    o = pd.concat(out, ignore_index=True)
    return float(np.sqrt(np.mean((o["y_hat"] - o["y_true"]) ** 2))), o


def lgb_component(tr, te, cols_all, ycol, bfmt, linear, n_jobs):
    from joblib import Parallel, delayed
    g = lgb_grid(linear)
    res = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_lgb_oof)((tr, c, cols_all, ycol, bfmt)) for c in g)
    best = min(range(len(g)), key=lambda i: (round(res[i][0], 10), lgb_simplicity(g[i])))
    c, (rmse, o) = g[best], res[best]
    b = bfmt.format(c["mult"])
    trb = tr.dropna(subset=[b, ycol])
    model = None if c["res"] is None else LGBRes(_lgb_cols(c, cols_all), c["leaves"], c["trees"], c["linear"]).fit(
        trb, trb[ycol] - trb[b])
    hat = te[b].to_numpy() + (0.0 if model is None else model.predict(te))
    return {"cfg": c, "rmse": rmse, "oof": o, "model": model, "hat": hat, "base": te[b].to_numpy()}


# ---------------------------------------------------------------- price forecasts (R0 / LGB-R / LGB-RL / ablations)
def price_forecast(d, X, B, t, learner="ridge", groups=P2.ALL_GROUPS, policy=True, n_jobs=8):
    tr, te = frame(d, X, B, t)
    if not ok(tr, te):
        return None
    cols = pcols(groups, policy)
    if learner == "ridge":
        fc = I7.component(tr, te, cols, "F_true", "base_{}", False, "forward", False, n_jobs)
        gc = I7.component(tr, te, cols, "G_true", "gbase_{}", False, "forward", False, n_jobs)
    else:
        lin = learner == "lgb_linear"
        fc = lgb_component(tr, te, cols, "F_true", "base_{}", lin, n_jobs)
        gc = lgb_component(tr, te, cols, "G_true", "gbase_{}", lin, n_jobs)
    if not (np.isfinite(fc["rmse"]) and np.isfinite(gc["rmse"])):
        return None
    j = fc["oof"].merge(gc["oof"], on=["q", "province_code"], suffixes=("_F", "_G"))
    rho = float(np.corrcoef(j["y_hat_F"] - j["y_true_F"], j["y_hat_G"] - j["y_true_G"])[0, 1]) if len(j) > 2 else 0.0
    rho = 0.0 if not np.isfinite(rho) else rho
    ps = P2.p_price_biv(fc["hat"], gc["hat"], fc["rmse"], gc["rmse"], rho, te["province_code"])
    # inner out-of-fold probabilities and their as-of PS labels (calibration data; targets <= t-1 only)
    th = L.e40_spec()
    j["p_oof"] = P2.p_price_biv(j["y_hat_F"], j["y_hat_G"], fc["rmse"], gc["rmse"], rho, j["province_code"])
    j["y_oof"] = ((j["y_true_F"] > j["province_code"].map(th["food"]))
                  | (j["y_true_G"] > j["province_code"].map(th["gap"]))).astype(int)
    return {"t": t, "p": np.asarray(ps), "F_hat": fc["hat"], "G_hat": gc["hat"], "F_base": fc["base"],
            "G_base": gc["base"], "rho": rho, "food_rmse": fc["rmse"], "gap_rmse": gc["rmse"], "food_cfg": fc["cfg"],
            "gap_cfg": gc["cfg"], "food_model": fc["model"], "gap_model": gc["model"], "te": te, "tr": tr,
            "pcols": cols, "oof": j[["q", "province_code", "p_oof", "y_oof"]]}


# ---------------------------------------------------------------- calibrators (C1 intercept, C2 Platt)
def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    return np.clip(np.log(p / (1 - p)), -6, 6)


def fit_calibrator(p_oof, y_oof, kind: str) -> dict:
    """MAP fit with the protocol's priors; identity when < 10 rows or one class."""
    from scipy.optimize import minimize
    y = np.asarray(y_oof, float)
    if len(y) < 10 or len(set(y)) < 2:
        return {"a": 1.0, "b": 0.0, "fitted": False, "n": int(len(y))}
    z = _logit(p_oof)

    def nlp(v):
        a, b = (v[0], v[1]) if kind == "C2" else (1.0, v[0])
        s = a * z + b
        ll = np.sum(y * s - np.logaddexp(0, s))
        pri = b ** 2 / 2 + ((a - 1) ** 2 / (2 * 0.25) if kind == "C2" else 0.0)
        return -ll + pri
    x0 = [1.0, 0.0] if kind == "C2" else [0.0]
    r = minimize(nlp, x0, method="BFGS")
    a, b = (float(r.x[0]), float(r.x[1])) if kind == "C2" else (1.0, float(r.x[0]))
    return {"a": a, "b": b, "fitted": True, "n": int(len(y))}


def apply_calibrator(cal: dict, p):
    s = cal["a"] * _logit(p) + cal["b"]
    return 1 / (1 + np.exp(-s))


# ---------------------------------------------------------------- LGB-C classifier
def lgbc_cols(cols):
    return cols + [f"{k}_{m}" for m in P2.MULTS for k in ("base", "gbase", "dfood", "dgap")]


def lgbc_grid():
    return [{"kind": "constant"}] + [{"kind": "lgb", "leaves": lv, "trees": n} for lv in (2, 4) for n in (50, 200)]


def _lgbc_simplicity(c):
    return (0, 0, 0) if c["kind"] == "constant" else (1, c["leaves"], c["trees"])


def _lgbc_fit_predict(c, fit, hold, cols):
    import lightgbm as lgb
    prev = float(fit["PS"].mean())
    if c["kind"] == "constant" or fit["PS"].nunique() < 2:
        return np.full(len(hold), prev)
    m = lgb.LGBMClassifier(**dict(LGB_FIXED, num_leaves=c["leaves"], n_estimators=c["trees"])).fit(
        fit[cols].astype(float), fit["PS"].to_numpy())
    return m.predict_proba(hold[cols].astype(float))[:, 1]


def lgbc_forecast(d, X, B, t):
    tr, te = frame(d, X, B, t)
    if not ok(tr, te):
        return None
    cols = lgbc_cols(pcols())
    g = lgbc_grid()
    scores = []
    for c in g:
        ll, n = 0.0, 0
        for q, fq in I7.folds(tr["q"].unique(), "forward"):
            fit, hold = tr[tr["q"].isin(fq)], tr[tr["q"] == q]
            p = np.clip(_lgbc_fit_predict(c, fit, hold, cols), 1e-6, 1 - 1e-6)
            y = hold["PS"].to_numpy()
            ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
            n += len(y)
        scores.append(ll / n if n else float("inf"))
    best = min(range(len(g)), key=lambda i: (round(scores[i], 10), _lgbc_simplicity(g[i])))
    p = _lgbc_fit_predict(g[best], tr, te, cols)
    return {"t": t, "p": np.asarray(p), "cfg": g[best], "logloss": scores[best]}


# ---------------------------------------------------------------- metrics (E51 e51_compare.metrics / block, unchanged)
def metrics(y, yhat, p):
    from sklearn.metrics import roc_auc_score
    y, yhat, p = np.asarray(y, int), np.asarray(yhat, int), np.asarray(p, float)
    tp, tn = int(((yhat == 1) & (y == 1)).sum()), int(((yhat == 0) & (y == 0)).sum())
    fp, fn = int(((yhat == 1) & (y == 0)).sum()), int(((yhat == 0) & (y == 1)).sum())
    rh = tp / (tp + fn) if tp + fn else None
    rl = tn / (tn + fp) if tn + fp else None
    pr = tp / (tp + fp) if tp + fp else None
    return {"n": int(len(y)), "accuracy": float((y == yhat).mean()),
            "balanced_accuracy": None if rh is None or rl is None else (rh + rl) / 2, "recall_HIGH": rh, "recall_LOW": rl,
            "precision_HIGH": pr, "f1_HIGH": (2 * pr * rh / (pr + rh)) if pr and rh else None,
            "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 and len(set(p)) > 1 else None,
            "confusion": {"TP": tp, "TN": tn, "FP": fp, "FN": fn}, "share_HIGH_calls": float(yhat.mean())}


def block(df, arms, seed=51):
    rng = np.random.default_rng(seed)
    out = {}
    qs_ = df["target"].unique()
    for a in arms:
        m = metrics(df["y"], df[f"{a}_yhat"], df[f"{a}_p"])
        vals = [float(np.mean(np.concatenate([(df[df["target"] == q][f"{a}_yhat"] == df[df["target"] == q]["y"]).to_numpy()
                                              for q in rng.choice(qs_, len(qs_))]))) for _ in range(1000)]
        m["accuracy_ci95"] = [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]
        m["by_quarter"] = {q: float((g[f"{a}_yhat"] == g["y"]).mean()) for q, g in df.groupby("target")}
        out[a] = m
    return out


def calibration(y, p) -> dict:
    """CITL, logistic calibration slope/intercept, reliability table."""
    from sklearn.linear_model import LogisticRegression
    y, p = np.asarray(y, int), np.asarray(p, float)
    z = _logit(p).reshape(-1, 1)
    lr = LogisticRegression(C=1e6).fit(z, y) if len(set(y)) == 2 else None
    bins = []
    for lo in np.arange(0, 1, 0.2):
        s = (p >= lo) & ((p < lo + 0.2) if lo < 0.8 else (p <= 1))
        bins.append({"bin": f"{lo:.1f}-{lo + 0.2:.1f}", "n": int(s.sum()),
                     "mean_p": float(p[s].mean()) if s.any() else None, "observed": float(y[s].mean()) if s.any() else None})
    return {"citl": float(y.mean() - p.mean()), "slope": None if lr is None else float(lr.coef_[0][0]),
            "intercept": None if lr is None else float(lr.intercept_[0]), "reliability": bins}


def by_quarter_confusion(df, a):
    out = {}
    for q, g in df.groupby("target"):
        out[q] = {"TP": int(((g[f"{a}_yhat"] == 1) & (g["y"] == 1)).sum()), "TN": int(((g[f"{a}_yhat"] == 0) & (g["y"] == 0)).sum()),
                  "FP": int(((g[f"{a}_yhat"] == 1) & (g["y"] == 0)).sum()), "FN": int(((g[f"{a}_yhat"] == 0) & (g["y"] == 1)).sum())}
    return out


def paired_brier(df, a, ref="R0", seed=53, n=1000):
    rng = np.random.default_rng(seed)
    qs_ = df["target"].unique()
    d_ = ((df[f"{a}_p"] - df["y"]) ** 2) - ((df[f"{ref}_p"] - df["y"]) ** 2)
    vals = [float(np.mean(np.concatenate([d_[df["target"] == q].to_numpy() for q in rng.choice(qs_, len(qs_))])))
            for _ in range(n)]
    return {"diff": float(d_.mean()), "ci95": [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]}
