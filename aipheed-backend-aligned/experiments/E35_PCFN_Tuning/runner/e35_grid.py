"""E32-PCFN as a function of its hyperparameters (PROTOCOL.md section 3).

The E32 engine (e32_lib.pcfn) is decomposed into the parts that do not depend on a hyperparameter (the H filter, the
raw news slope, tau, the D training rows) and the parts that do (news-shift shrinkage lambda, D regressor set, spread
scale c). The default configuration reproduces e32_lib.pcfn exactly (tests/test_e35_reproduce.py).

    P(HIGH) = 1 - Phi((tau - (mu_H + lambda * slope * (news_reg - mean_news) + 2 mu_D[S])) / (c * sqrt(V_H + 4 s_S^2)))
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import lru_cache

from scipy.stats import norm

import e35_common as E

np, C, L, P = E.np, E.C, E.L, E.P

D_SETS = {"D1": ("D_last",), "D2": ("D_last", "Dnow"), "D3": ("D_last", "Dnow", "rice_rel"),
          "D4": ("D_last", "Dnow", "rice_rel", "news_n")}
LAMBDAS = (0.0, 0.5, 1.0)
SCALES = (0.8, 1.0, 1.25)
DEFAULT = (0.5, "D4", 1.0)                         # the frozen E32-PCFN
ALL_COLS = D_SETS["D4"]


@dataclass(frozen=True)
class Config:
    lam: float
    dset: str
    c: float

    @property
    def id(self) -> str:
        return f"lam{self.lam:.1f}|{self.dset}|c{self.c:.2f}"

    def changes(self) -> int:
        return int(self.lam != DEFAULT[0]) + int(self.dset != DEFAULT[1]) + int(self.c != DEFAULT[2])

    def tie_key(self):
        """Tie order (PROTOCOL 5.3): fewest changes from E32-PCFN, then fewer D regressors, then c nearer 1, then
        smaller lambda."""
        return (self.changes(), len(D_SETS[self.dset]), abs(np.log(self.c)), self.lam)


GRID = [Config(l, s, c) for l, s, c in itertools.product(LAMBDAS, D_SETS, SCALES)]
DEFAULT_CFG = Config(*DEFAULT)


@lru_cache(maxsize=None)
def components(d: "L.Data", t: int, k: int) -> dict:
    """Everything PCFN needs at origin O(t) for lead k, for every configuration. Mirrors e32_lib.pcfn line by line."""
    o = L.origin(t)
    rr = P.rounds_at_origin(d.rounds, o)
    times, ys = rr["quarter"].map(C.qk).to_numpy(float), rr["H"].to_numpy(float)
    hf = P.h_forecast(times, ys, float(t + k))
    Hp = d.H_posted(o)
    qs_ = sorted(Hp)
    pairs = [(np.log1p(d.nw[("REGION", q - 1)].n_rel), Hp[q] - Hp[q - 1]) for q in qs_
             if (q - 1) in Hp and ("REGION", q - 1) in d.nw]
    slope, mean_news = 0.0, 0.0
    if len(pairs) >= 6:
        a = np.array(pairs)
        mean_news = float(a[:, 0].mean())
        xc = a[:, 0] - mean_news
        slope = float((xc * (a[:, 1] - a[:, 1].mean())).sum() / max((xc ** 2).sum(), 1e-12))
    X = d.features(t, k)
    news_dev = float(X["news_reg"].iloc[0]) - mean_news
    rows, yt = [], []
    for tp in range(C.qk("2021-Q2"), t - k):
        F = d.features(tp, k) if tp >= C.qk("2021-Q3") else None
        if F is None:
            continue
        for r in F.itertuples():
            dt = d.Dm.get((r.province_code, tp + k))
            v = [getattr(r, c) for c in ALL_COLS]
            if dt is None or any(x != x for x in v):
                continue
            rows.append(v)
            yt.append(dt)
    D = {}
    if len(yt) < 25:                                    # E32 DEVIATIONS A3: PCF21 D-model fallback, same for every set
        b, s, _ = P.d_fit(d.Dm, d.Nm, t, k, False)
        muD = {r.province_code: float(b[0] * r.D_last) for r in X.itertuples()}
        for name in D_SETS:
            D[name] = {"muD": muD, "s": float(s), "coef": [float(b[0])], "fallback": True}
    else:
        A_all, yv = np.asarray(rows, float), np.asarray(yt, float)
        for name, cols in D_SETS.items():
            idx = [ALL_COLS.index(c) for c in cols]
            A = A_all[:, idx]
            b, *_ = np.linalg.lstsq(A, yv, rcond=None)
            res = yv - A @ b
            s = float(np.sqrt((res ** 2).sum() / max(len(yv) - len(cols), 1)))
            muD = {}
            for r in X.itertuples():
                v = np.array([getattr(r, c) for c in cols], float)
                v = np.where(np.isnan(v), 0.0, v)
                muD[r.province_code] = float(v @ b)
            D[name] = {"muD": muD, "s": s, "coef": [float(x) for x in b], "fallback": False}
    return {"mu_H": float(hf["mu_H"]), "V_H": float(hf["V_H"]), "slope": slope, "news_dev": news_dev,
            "n_news_pairs": len(pairs), "D_pairs": len(yt), "tau": float(d.tau(t)), "D": D}


def probs(comp: dict, cfg: Config) -> dict[str, float]:
    Dc = comp["D"][cfg.dset]
    muH = comp["mu_H"] + (cfg.lam * comp["slope"]) * comp["news_dev"]
    sd = cfg.c * float(np.sqrt(comp["V_H"] + 4 * Dc["s"] ** 2))
    return {p: float(1 - norm.cdf((comp["tau"] - (muH + 2 * Dc["muD"][p])) / sd)) for p in C.PROVS}


def all_probs(d: "L.Data", t: int, k: int) -> dict[str, dict[str, float]]:
    comp = components(d, t, k)
    return {cfg.id: probs(comp, cfg) for cfg in GRID}
