"""E32 library: as-of features, labels, the four candidates (PROTOCOL.md section 4) and publication-aware references.

Every function takes the origin O(t) and uses only what was posted/released before it (see DEVIATIONS.md part A).
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import e32_common as C

np, pd, P = C.np, C.pd, C.P

FEATURES = ["H_last", "H_gap", "H_trend", "H_margin", "D_last", "Dnow", "rice_rel", "news_n", "news_reg",
            "news_direct_share", "fssi_v2", "fssi_missing", "y_last"]
RICE = C.E32 / "data_acquired" / "provincial_rice_cpi_yoy_2021_2026.csv"
LGBM_PARAMS = dict(objective="binary", num_leaves=4, min_data_in_leaf=5, n_estimators=150, learning_rate=0.05,
                   feature_fraction=0.8, bagging_fraction=1.0, bagging_freq=0, seed=32, deterministic=True,
                   force_col_wise=True, verbose=-1)


def origin(t: int) -> pd.Timestamp:
    """O(t) = 00:00 PHT on the first day of quarter t+1 (naive = PHT, the engine's convention)."""
    y, n = divmod(t + 1, 4)
    return pd.Timestamp(y, 3 * n + 1, 1)


class Data:
    def __init__(self):
        d = C.load()
        self.rounds, self.S1, self.Dm, self.Nm, self.news = d["rounds"], d["S1"], d["Dm"], d["Nm"], d["news"]
        self.S1 = self.S1.assign(tq=self.S1["quarter"].map(C.qk))
        self.Sv = {(p, t): s for p, t, s in zip(self.S1["province_code"], self.S1["tq"], self.S1["S1"])}
        self.defA = self.rounds[self.rounds["definition_A"].astype(str).str.lower() == "true"].copy()
        self.defA["tq"] = self.defA["quarter"].map(C.qk)
        self.defA["usable"] = P._usable_from(self.defA)
        r = pd.read_csv(RICE, dtype={"province_code": str})
        r["y"], r["m"] = r["reference_month"].str[:4].astype(int), r["reference_month"].str[5:7].astype(int)
        r["tq"] = r["y"] * 4 + (r["m"] - 1) // 3
        r["rel"] = r["rice_cpi_yoy_pct"] - r.groupby("reference_month")["rice_cpi_yoy_pct"].transform("mean")
        r = r[((r["m"] - 1) % 3) < 2]                                     # months 1-2 of each quarter
        self.rice = r.groupby(["province_code", "tq"])["rel"].mean().to_dict()
        nw = self.news.assign(tq=self.news["quarter"].map(C.qk))
        self.nw = {(x.province_code, x.tq): x for x in nw.itertuples()}

    # ---------------------------------------------------------------- publication
    def posted_quarters(self, o: pd.Timestamp) -> list[int]:
        """Labelled quarters whose definition-A rounds were ALL posted before o."""
        out = []
        for tq, g in self.defA.groupby("tq"):
            if g["usable"].notna().all() and (g["usable"] < o).all():
                out.append(int(tq))
        return sorted(out)

    @lru_cache(maxsize=256)
    def tau(self, t: int) -> float:
        return float(P.threshold_at(self.S1, self.rounds, t, origin(t))[0])

    def H_posted(self, o: pd.Timestamp) -> dict[int, float]:
        rr = P.rounds_at_origin(self.rounds, o)
        return rr.assign(tq=rr["quarter"].map(C.qk)).groupby("tq")["H"].mean().to_dict()

    def label(self, p: str, target: int, t: int):
        s = self.Sv.get((p, target))
        return None if s is None or s != s else int(s > self.tau(t))

    # ---------------------------------------------------------------- features
    @lru_cache(maxsize=512)
    def features(self, t: int, k: int) -> pd.DataFrame:
        o = origin(t)
        Hp = self.H_posted(o)
        qs_ = sorted(Hp)
        L = qs_[-1]
        prevH = Hp[qs_[-2]] if len(qs_) > 1 else np.nan
        tau = self.tau(t)
        posted = [q for q in self.posted_quarters(o) if q <= t - 1]
        last_lab = posted[-1] if posted else None
        reg = self.nw.get(("REGION", t))
        rows = []
        for p in C.PROVS:
            n = self.nw.get((p, t))
            f = np.nan if n is None or n.fssi_v2 != n.fssi_v2 else float(n.fssi_v2)
            s_last = self.Sv.get((p, last_lab)) if last_lab is not None else None
            rows.append({"province_code": p, "t": t, "k": k, "tau": tau,
                         "H_last": Hp[L], "H_gap": float(t + k - L), "H_trend": Hp[L] - prevH,
                         "H_margin": Hp[L] - tau, "D_last": self.Dm.get((p, t - 1), np.nan),
                         "Dnow": self.Nm.get((p, t), np.nan), "rice_rel": self.rice.get((p, t), np.nan),
                         "news_n": np.log1p(n.n_rel) if n is not None else 0.0,
                         "news_reg": np.log1p(reg.n_rel) if reg is not None else 0.0,
                         "news_direct_share": (n.n_direct / n.n_rel) if (n is not None and n.n_rel) else 0.0,
                         "fssi_v2": 0.0 if f != f else f, "fssi_missing": float(f != f),
                         "y_last": (float(s_last > tau) if s_last is not None and s_last == s_last else np.nan),
                         "H_last_quarter": C.qs(L), "last_label_quarter": C.qs(last_lab) if last_lab else None})
        return pd.DataFrame(rows)

    def training_pairs(self, t: int, k: int) -> pd.DataFrame:
        """(X(t'), label of t'+k at tau(t')) for t'+k <= t-1 whose rounds were posted before O(t)."""
        posted = set(self.posted_quarters(origin(t)))
        out = []
        for tp in range(C.qk("2021-Q2"), t - k):
            if tp + k not in posted:
                continue
            try:
                X = self.features(tp, k)
            except (IndexError, KeyError, ValueError):
                continue
            ys = [self.Sv.get((p, tp + k)) for p in X["province_code"]]
            X = X.assign(S1_target=ys, target_q=tp + k)
            X["y"] = (X["S1_target"] > X["tau"]).astype(int)
            out.append(X[X["S1_target"].notna()])
        return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


# =================================================================== references (publication-aware)
def references(d: Data, t: int, k: int) -> dict[str, dict[str, float]]:
    X = d.features(t, k)
    tr = d.training_pairs(t, k)
    out = {"B1": {}, "B1p": {}, "CLIM": {}, "ALWAYS_HIGH": {}}
    clim = (tr["y"].sum() + 1) / (len(tr) + 2) if len(tr) else 0.5
    for r in X.itertuples():
        yl = r.y_last
        out["B1"][r.province_code] = float(yl) if yl == yl else 0.5
        if len(tr) and yl == yl:
            g = tr[tr["y_last"] == yl]
            out["B1p"][r.province_code] = float((g["y"].sum() + 1) / (len(g) + 2))
        else:
            out["B1p"][r.province_code] = 0.5
        out["CLIM"][r.province_code] = float(clim)
        out["ALWAYS_HIGH"][r.province_code] = 1.0
    return out


def pcf21(d: Data, t: int, k: int) -> dict[str, float]:
    fc = P.forecast(origin(t), t, [k], d.rounds, d.S1, d.Dm, d.Nm, {})
    return {p: v["risk"]["p_high"] for p, v in fc["leads"][str(k)]["provinces"].items()}


# =================================================================== candidates
def pcfn(d: Data, t: int, k: int, info: dict | None = None) -> dict[str, float]:
    """E32-PCFN: PCF21's H filter shifted by the regional news signal; D regressed on prices, rice and news."""
    from scipy.stats import norm

    o = origin(t)
    rr = P.rounds_at_origin(d.rounds, o)
    times, ys = rr["quarter"].map(C.qk).to_numpy(float), rr["H"].to_numpy(float)
    hf = P.h_forecast(times, ys, float(t + k))
    # news shift: round-to-round change of H on the previous quarter's regional validated-news volume
    Hp = d.H_posted(o)
    qs_ = sorted(Hp)
    pairs = [(np.log1p(d.nw[("REGION", q - 1)].n_rel), Hp[q] - Hp[q - 1]) for q in qs_
             if (q - 1) in Hp and ("REGION", q - 1) in d.nw]
    beta, mean_news = 0.0, 0.0
    if len(pairs) >= 6:
        a = np.array(pairs)
        mean_news = float(a[:, 0].mean())
        xc = a[:, 0] - mean_news
        beta = 0.5 * float((xc * (a[:, 1] - a[:, 1].mean())).sum() / max((xc ** 2).sum(), 1e-12))
    X = d.features(t, k)
    muH = hf["mu_H"] + beta * (float(X["news_reg"].iloc[0]) - mean_news)
    # D regression
    cols = ["D_last", "Dnow", "rice_rel", "news_n"]
    Xt, yt = [], []
    for tp in range(C.qk("2021-Q2"), t - k):
        F = d.features(tp, k) if tp >= C.qk("2021-Q3") else None
        if F is None:
            continue
        for r in F.itertuples():
            dt = d.Dm.get((r.province_code, tp + k))
            v = [getattr(r, c) for c in cols]
            if dt is None or any(x != x for x in v):
                continue
            Xt.append(v)
            yt.append(dt)
    fallback = len(yt) < 25
    if fallback:
        b, s, _ = P.d_fit(d.Dm, d.Nm, t, k, False)
        muD = {r.province_code: float(b[0] * r.D_last) for r in X.itertuples()}
    else:
        A, yv = np.asarray(Xt, float), np.asarray(yt, float)
        b, *_ = np.linalg.lstsq(A, yv, rcond=None)
        res = yv - A @ b
        s = float(np.sqrt((res ** 2).sum() / max(len(yv) - len(cols), 1)))
        muD = {}
        for r in X.itertuples():
            v = np.array([getattr(r, c) for c in cols], float)
            v = np.where(np.isnan(v), 0.0, v)
            muD[r.province_code] = float(v @ b)
    tau = d.tau(t)
    sd = float(np.sqrt(hf["V_H"] + 4 * s ** 2))
    if info is not None:
        info.update({"beta_news_H": beta, "D_pairs": len(yt), "D_fallback": fallback, "D_coef": list(map(float, np.atleast_1d(b))),
                     "sigma_D": s, "mu_H": muH})
    return {p: float(1 - norm.cdf((tau - (muH + 2 * muD[p])) / sd)) for p in C.PROVS}


def _xy(tr: pd.DataFrame):
    tr = tr.dropna(subset=["D_last", "Dnow", "y_last"])
    return tr[FEATURES].to_numpy(float), tr["y"].to_numpy(int)


def lr(d: Data, t: int, k: int) -> dict[str, float]:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    X, y = _xy(d.training_pairs(t, k))
    te = d.features(t, k)
    if len(set(y)) < 2:
        r = (y.sum() + 1) / (len(y) + 2)
        return {p: float(r) for p in te["province_code"]}
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(X), y)
    Z = np.nan_to_num(te[FEATURES].to_numpy(float), nan=0.0)
    return dict(zip(te["province_code"], m.predict_proba(sc.transform(Z))[:, 1].astype(float)))


def lgbm(d: Data, t: int, k: int) -> dict[str, float]:
    import lightgbm as lgb

    X, y = _xy(d.training_pairs(t, k))
    te = d.features(t, k)
    if len(set(y)) < 2:
        r = (y.sum() + 1) / (len(y) + 2)
        return {p: float(r) for p in te["province_code"]}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = lgb.LGBMClassifier(**LGBM_PARAMS).fit(pd.DataFrame(X, columns=FEATURES), y)
        pr = m.predict_proba(te[FEATURES].astype(float))[:, 1]
    return dict(zip(te["province_code"], pr.astype(float)))


def ens(d: Data, t: int, k: int) -> dict[str, float]:
    a, b = pcfn(d, t, k), references(d, t, k)["B1p"]
    return {p: 0.5 * (a[p] + b[p]) for p in a}


CANDIDATES = {"E32-PCFN": pcfn, "E32-LR": lr, "E32-LGBM": lgbm, "E32-ENS": ens}
SIMPLICITY = ["E32-PCFN", "E32-LR", "E32-ENS", "E32-LGBM"]
