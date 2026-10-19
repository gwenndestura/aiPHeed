"""E61 candidate price learners (PROTOCOL section 2). Imported by c1_predict.py and by joblib workers."""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e61_lib as X  # noqa: E402

np, pd, L, F, G, E, I7 = X.np, X.pd, X.L, X.F, X.G, X.E, X.I7


class Debiased(G.PriceLGB2):
    """C2: the CPI projection shifted by its mean error on the fitting rows (scale = SD of the errors)."""

    def _shift(self, rows):
        r = rows.copy()
        m = self.cfg["m"]
        r[f"base_{m}"] = r[f"base_{m}"] + self.muF
        r[f"gbase_{m}"] = r[f"gbase_{m}"] + self.muG
        return r

    def fit(self, fit):
        m = self.cfg["m"]
        eF, eG = fit["F_true"] - fit[f"base_{m}"], fit["G_true"] - fit[f"gbase_{m}"]
        ok = eF.notna() & eG.notna()
        self.muF, self.muG = float(eF[ok].mean()), float(eG[ok].mean())
        return super().fit(self._shift(fit))

    def raw(self, rows):
        return super().raw(self._shift(rows))


ARMS = {"C2": (Debiased, (), ()), "C3": (G.PriceLGB2, ("ps_margin_now",), ()),
        "C23": (Debiased, ("ps_margin_now",), ()), "C4": (G.PriceLGB2, (), ("news",))}


def add_margin(fr: pd.DataFrame) -> pd.DataFrame:
    th = L.e40_spec()
    fr = fr.copy()
    fr["ps_margin_now"] = np.maximum(fr["F_now"] - fr["province_code"].map(th["food"]),
                                     fr["gap_now"] - fr["province_code"].map(th["gap"]))
    return fr


def cols_for(c, extra=(), drop=()):
    cols = F.feature_cols(c["feat"], "AS" if c["pov"] == "AS" else None, drop)
    if "news" in drop:
        cols = [x for x in cols if not x.startswith("news_")]
    return cols + list(extra)


def _inner(args):
    tr, c, arm = args
    cls, extra, drop = ARMS[arm]
    cols = cols_for(c, extra, drop)
    ll, n = 0.0, 0
    for q, fq in I7.folds(tr["q"].unique(), "forward"):
        fit = tr[tr["q"].isin(fq)].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
        hold = tr[tr["q"] == q].dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}"])
        if not len(hold) or not len(fit):
            continue
        p = np.clip(cls(cols, c).fit(fit).predict(hold), 1e-6, 1 - 1e-6)
        y = hold["PS"].to_numpy(float)
        ll += float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
        n += len(y)
    return ll / n if n else float("inf")


def tuned(d, Xf, B, t, arm, space, n_jobs=8):
    """The E56-TUNED procedure (nested selection by embargoed forward log-loss on training targets) for one arm."""
    from joblib import Parallel, delayed
    cls, extra, drop = ARMS[arm]
    tr, te = F.frame(d, Xf, B, t, "AS")
    tr, te = add_margin(tr), add_margin(te)
    if not E.ok(tr, te):
        return None
    hc = F.hunger(d, Xf, t)
    if hc is None:
        return None
    scores = Parallel(n_jobs=n_jobs, backend="loky")(delayed(_inner)((tr, c, arm)) for c in space)
    best = min(range(len(space)), key=lambda i: (round(scores[i], 10), G.simplicity(space[i])))
    c = space[best]
    fit = tr.dropna(subset=[f"base_{c['m']}", f"gbase_{c['m']}", "F_true", "G_true"])
    mdl = cls(cols_for(c, extra, drop), c).fit(fit)
    pp = mdl.predict(te)
    return {"p": hc["p"] * pp, "p_price": pp, "p_hunger": hc["p"], "cfg": c, "te": te,
            "mu": (getattr(mdl, "muF", None), getattr(mdl, "muG", None))}
