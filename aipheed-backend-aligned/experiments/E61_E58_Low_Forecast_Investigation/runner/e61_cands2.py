"""E61 addendum-1 learners (PROTOCOL_ADDENDUM_1.md sections 2-5). Imported by d1_predict.py and by joblib workers."""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_cands as C  # noqa: E402

X, np, pd, L, F, G, E, I7, P2 = C.X, C.np, C.pd, C.L, C.F, C.G, C.E, C.I7, C.X.P2

FA_DROP = {"FA-rice": ["rice_whsl_yoy"], "FA-emp": ["ur_yoy", "under_yoy", "news_employment"],
           "FA-ofw": ["remit_usd_yoy", "remit_php_yoy", "fx_yoy", "news_ofw_remittance"]}


# ------------------------------------------------------------------------------------------------ D2 projection
def proj_recent(c, t, p, commodity, months=6):
    """E44 `proj` with the drift taken from the last `months` monthly log changes to m0 (data as of d.cut(t))."""
    m0 = L.m0_of(t)
    I = L._series(c, p, commodity)
    if m0 not in I.index:
        return np.nan
    lnI = np.log(I)
    ch = lnI.diff().dropna()
    ch = ch[(ch.index > m0 - months) & (ch.index <= m0) & (ch.index - 1 >= L.FIRST_YM)]
    ms = L.target_months(t, 2)
    if len(ch) < months or any((m - 12) not in I.index for m in ms):
        return np.nan
    g = float(ch.mean())
    return float(np.mean([100 * (math.exp(lnI[m0] + g * (m - m0)) / I[m - 12] - 1) for m in ms]))


def bases_recent(d, origins):
    rows = []
    for t in origins:
        c = d.cut(t)
        for p in L.PROVS:
            rows.append({"t": t, "province_code": p, "base_r6": proj_recent(c, t, p, "food"),
                         "hl_r6": proj_recent(c, t, p, "all_items")})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ D3 learner
class NoOffset:
    """Binary LightGBM on the latest observed indicators; no projection offset, standard intercept."""

    def __init__(self, cols, c):
        self.cols, self.cfg = list(cols), c

    def fit(self, fit):
        import lightgbm as lgb
        y = fit["PS"].to_numpy(int)
        self.const = None
        if len(set(y)) < 2:
            self.const = float(y.mean())
            return self
        c = self.cfg
        w = F.recency_weights(fit["q"], c["hl"])
        kw = dict(F.LGB_BASE, num_leaves=c["leaves"], max_depth=c["depth"], learning_rate=c["lr"], n_estimators=c["trees"],
                  min_child_samples=c["min_child"], colsample_bytree=c["ff"], subsample=c["bf"],
                  subsample_freq=1 if c["bf"] < 1 else 0, reg_alpha=c["l1"], reg_lambda=c["l2"], objective="binary",
                  class_weight="balanced" if c["cw"] == "balanced" else None)
        self.model = lgb.LGBMClassifier(**kw).fit(fit[self.cols].astype(float), y, sample_weight=w)
        return self

    def predict(self, rows):
        if self.const is not None:
            return np.full(len(rows), self.const)
        return self.model.predict_proba(rows[self.cols].astype(float))[:, 1]


# ------------------------------------------------------------------------------------------------ arms
def _key(c):
    return tuple(sorted((k, str(v)) for k, v in c.items() if k != "id"))


def space_for(arm, space):
    if arm == "D1":
        return [c for c in space if c["m"] == 1.0]
    if arm in ("D2", "D3"):
        mm = "r6" if arm == "D2" else 0.0
        out, seen = [], set()
        for c in space:
            c2 = dict(c, m=mm)
            if _key(c2) not in seen:
                seen.add(_key(c2))
                out.append(c2)
        return out
    return space


def simp(c):
    return G.simplicity(dict(c, m=1.0) if c["m"] == "r6" else c)


def arm_parts(arm):
    """(learner class, extra columns, dropped columns)"""
    if arm == "D3":
        return NoOffset, ("ps_margin_now",), ()
    if arm in FA_DROP:
        return G.PriceLGB2, (), tuple(FA_DROP[arm])
    return G.PriceLGB2, (), ()


def cols_for(c, extra, drop_cols):
    return [x for x in C.cols_for(c) if x not in drop_cols] + list(extra)


def _fit_rows(tr, c):
    return tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])


def _inner(args):
    tr, c, arm = args
    cls, extra, drop_cols = arm_parts(arm)
    cols = cols_for(c, extra, drop_cols)
    ll, n = 0.0, 0
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit = _fit_rows(tr[tr["q"].isin(fq)], c)
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = np.clip(cls(cols, c).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
        y = hold["PS"].to_numpy(float)
        ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        n += len(y)
    return ll / n if n else float("inf")


def frames(d, Xf, B, B6, t):
    Bx = B.merge(B6, on=["t", "province_code"], how="left")
    tr, te = F.frame(d, Xf, Bx, t, "AS")
    for fr in (tr, te):
        fr["gbase_r6"] = fr["base_r6"] - fr["hl_r6"]
    return C.add_margin(tr), C.add_margin(te)


def tuned(d, Xf, B, B6, t, arm, space, n_jobs=8):
    """E56 nested selection for one addendum arm. K1 restricts the fitting rows to hunger-high target quarters."""
    from joblib import Parallel, delayed
    tr, te = frames(d, Xf, B, B6, t)
    if not E.ok(tr, te):
        return None
    hc = F.hunger(d, Xf, t)
    info = {}
    if arm == "K1":
        Y = F.t43_labels(d.cut(t))
        hq = set(Y.loc[Y["H_all"] > 11.3, "q"])
        trh = tr[tr["q"].isin(hq)]
        info["K1_hunger_high_quarters"] = int(trh["q"].nunique())
        if trh["q"].nunique() < 6:
            info["K1_fallback"] = True
            return {"fallback": True, **info}
        tr = trh
    sp = space_for(arm, space)
    scores = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner)((tr, c, arm)) for c in sp)
    best = min(range(len(sp)), key=lambda i: (round(scores[i], 10), simp(sp[i])))
    c = sp[best]
    cls, extra, drop_cols = arm_parts(arm)
    mdl = cls(cols_for(c, extra, drop_cols), c).fit(_fit_rows(tr, c))
    pp = mdl.predict(te)
    return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "cfg": c, "fallback": False, **info}


# ------------------------------------------------------------------------------------------------ hunger variants
def hunger_variant(d, Xf, t, variant):
    hcols = [c for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g]]
    if variant == "H1":
        hcols = [c for c in hcols if c != "news_n"]
    elif variant == "H2":
        hcols = []
    htr, hte = P2.hunger_frame(Xf, P2.h_series(d, t, False), t, hcols)
    if len(htr) < P2.MIN_H_PAIRS or not len(hte):
        return None
    hc = P2.hunger_component(htr, hte, hcols)
    return {"H_hat": hc["H_hat"], "p": hc["p"], "rmse_train": hc["rmse"], "alpha": hc["alpha"],
            "H_base": float(hte["H_base"].iloc[0])}


# ------------------------------------------------------------------------------------------------ K2 combination
def k2_fit(z1, z2, y, lam=1.0):
    """Penalized logistic regression y ~ b + a1*z1 + a2*z2 (priors a1=a2=1, b=0)."""
    from scipy.optimize import minimize
    z1, z2, y = map(lambda v: np.asarray(v, float), (z1, z2, y))

    def nll(v):
        b, a1, a2 = v
        s = b + a1 * z1 + a2 * z2
        return -np.sum(y * s - np.logaddexp(0, s)) + lam / 2 * (b ** 2 + (a1 - 1) ** 2 + (a2 - 1) ** 2)
    r = minimize(nll, [0.0, 1.0, 1.0], method="BFGS")
    return {"b": float(r.x[0]), "a1": float(r.x[1]), "a2": float(r.x[2])}


def zlogit(p):
    p = np.clip(np.asarray(p, float), 1e-12, 1 - 1e-12)
    return np.clip(np.log(p / (1 - p)), -6, 6)
