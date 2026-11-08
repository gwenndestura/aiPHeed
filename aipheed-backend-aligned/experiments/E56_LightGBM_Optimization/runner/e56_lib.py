"""E56 library (PROTOCOL.md): bounded, reproducible hyperparameter optimization of the E55 LightGBM food-insecurity model
(two-quarter horizon), selected per forecast origin by nested chronological validation, plus the province-spread
diagnostics and the saved-artifact export used by serving.

Structure is E55-LGBM's: P(T43) = P_hunger (I7 regional component) x P_price (LightGBM with the structural CPI offset,
intercept-free boosting). E56 searches the LightGBM hyperparameters and the structural options together.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.dont_write_bytecode = True
E56 = Path(__file__).resolve().parents[1]
EXP = E56.parent
sys.path.insert(0, str(EXP / "E55_Food_Insecurity_LightGBM" / "runner"))
import e55_lib as F  # noqa: E402

E, I7, L, P2, M, np, pd = F.E, F.I7, F.L, F.P2, F.M, F.np, F.pd
SEED, N_RANDOM = 56, 48
SPACE = {"leaves": [2, 3, 4, 6], "depth": [1, 2, 3], "lr": [0.02, 0.05, 0.1], "trees": [10, 25, 50, 100],
         "min_child": [5, 10, 20], "ff": [0.6, 0.8, 1.0], "bf": [0.7, 1.0], "l1": [0.0, 1.0], "l2": [1.0, 10.0, 30.0],
         "cw": [None, "balanced"], "m": [1.0, 0.5, 0.0], "hl": [None, 6], "feat": ["market", "all"], "pov": [None, "AS"]}
E55_DEFAULTS = dict(leaves=2, depth=1, lr=0.05, min_child=10, ff=1.0, bf=1.0, l1=0.0, l2=10.0, cw=None, pov=None)


def search_space() -> list[dict]:
    """The 24 E55 configurations followed by 48 configurations drawn once (seed 56) from SPACE, de-duplicated."""
    e55 = [dict(E55_DEFAULTS, **c) for c in F.grid()]
    keys = list(SPACE)
    allc = list(itertools.product(*[SPACE[k] for k in keys]))
    rng = np.random.default_rng(SEED)
    pick = rng.choice(len(allc), size=N_RANDOM * 3, replace=False)
    out, seen = list(e55), {tuple(sorted((k, str(v)) for k, v in c.items())) for c in e55}
    for i in pick:
        c = dict(zip(keys, allc[i]))
        c["leaves"] = min(c["leaves"], 2 ** c["depth"])
        key = tuple(sorted((k, str(v)) for k, v in c.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
        if len(out) == len(e55) + N_RANDOM:
            break
    for i, c in enumerate(out):
        c["id"] = i
    return out


def simplicity(c):
    return (c["trees"] * (c["leaves"] - 1), c["leaves"], 0 if c["feat"] == "market" else 1, 0 if c["pov"] is None else 1,
            0 if c["hl"] is None else 1, 0 if c["cw"] is None else 1, F.MULTS.index(c["m"]), c["id"])


class PriceLGB2(F.PriceLGB):
    """E55 PriceLGB with the full E56 hyperparameter set (offset + intercept-free always on)."""

    def __init__(self, cols, c: dict):
        super().__init__(cols, c["m"], c["trees"], leaves=c["leaves"], offset=True, centred=True, hl=c["hl"],
                         unbalance=c["cw"] == "balanced", min_child=c["min_child"])
        self.cfg = c

    def fit(self, fit):
        import lightgbm as lgb
        y = fit["PS"].to_numpy(float)
        self.scale = F.struct_scale(fit, self.m)
        init = F.struct_logit(fit, self.m, self.scale)
        w = F.recency_weights(fit["q"], self.hl)
        if self.unbalance and 0 < y.sum() < len(y):
            cw = np.where(y == 1, (len(y) - y.sum()) / y.sum(), 1.0)
            w = cw if w is None else w * cw
        self.const = None
        if len(set(y)) < 2:
            self.const = float(y.mean())
            return self
        c = self.cfg
        kw = dict(F.LGB_BASE, num_leaves=c["leaves"], max_depth=c["depth"], learning_rate=c["lr"], n_estimators=c["trees"],
                  min_child_samples=c["min_child"], colsample_bytree=c["ff"], subsample=c["bf"],
                  subsample_freq=1 if c["bf"] < 1 else 0, reg_alpha=c["l1"], reg_lambda=c["l2"],
                  objective=F._objective(True))
        self.model = lgb.LGBMRegressor(**kw)
        self.model.fit(self._X(fit), y, sample_weight=w, init_score=init)
        tf = self.model.booster_.predict(self._X(fit), raw_score=True)
        self.c = float(np.average(tf, weights=w))
        return self


def cols_for(c, drop=()):
    return F.feature_cols(c["feat"], "AS" if c["pov"] == "AS" else None, drop)


def _inner(args):
    tr, c = args
    cols = cols_for(c)
    ll, n = 0.0, 0
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = np.clip(PriceLGB2(cols, c).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
        y = hold["PS"].to_numpy(float)
        ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        n += len(y)
    return ll / n if n else float("inf")


def tuned_forecast(d, X, B, t, space=None, n_jobs=8):
    """E56-TUNED at origin t: nested selection over the search space by embargoed forward log-loss (training only)."""
    from joblib import Parallel, delayed
    tr, te = F.frame(d, X, B, t, "AS")                    # pov column present (NaN before 2025); used only if c["pov"]
    if not E.ok(tr, te):
        return None
    hc = F.hunger(d, X, t)
    if hc is None:
        return None
    g = space or search_space()
    scores = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner)((tr, c)) for c in g)
    best = min(range(len(g)), key=lambda i: (round(scores[i], 10), simplicity(g[i])))
    c = g[best]
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = PriceLGB2(cols_for(c), c).fit(fit)
    pp = mdl.predict(te)
    return {"t": t, "p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "H_hat": hc["H_hat"], "hc": hc, "cfg": c,
            "inner_logloss": scores[best], "scores": scores, "model": mdl, "te": te, "tr": fit, "cols": cols_for(c),
            "n_train_rows": int(len(fit)), "n_train_q": int(fit["q"].nunique()), "n_train_HIGH": int(fit["PS"].sum())}


# ================================================================================================ province spread
def province_spread(R: pd.DataFrame, arm: str) -> dict:
    """Does the arm distinguish provinces within a quarter? within-quarter AUC (pairs in the same quarter with
    different labels), mean within-quarter SD of probabilities, quarters whose five decisions are not all equal."""
    num = den = 0.0
    sds, mixed = [], 0
    for _, g in R.groupby("target"):
        p, y = g[f"{arm}_p"].to_numpy(), g["y"].to_numpy()
        sds.append(float(np.std(p)))
        mixed += int(g[f"{arm}_yhat"].nunique() > 1)
        for i in np.where(y == 1)[0]:
            for j in np.where(y == 0)[0]:
                den += 1
                num += 1.0 if p[i] > p[j] else (0.5 if p[i] == p[j] else 0.0)
    return {"within_quarter_auc": (num / den) if den else None, "within_quarter_pairs": int(den),
            "mean_within_quarter_sd": float(np.mean(sds)), "quarters_with_mixed_decisions": mixed,
            "quarters": int(R["target"].nunique())}


def by_province(R: pd.DataFrame, arm: str) -> dict:
    out = {}
    for p, g in R.groupby("province_code"):
        out[L.NAMES[p]] = {"n": int(len(g)), "HIGH": int(g["y"].sum()), "accuracy": float((g[f"{arm}_yhat"] == g["y"]).mean()),
                           "mean_p": float(g[f"{arm}_p"].mean()), "brier": float(np.mean((g[f"{arm}_p"] - g["y"]) ** 2))}
    return out


def low_precision(R, arm):
    tn = int(((R[f"{arm}_yhat"] == 0) & (R["y"] == 0)).sum())
    fn = int(((R[f"{arm}_yhat"] == 0) & (R["y"] == 1)).sum())
    return tn / (tn + fn) if tn + fn else None
