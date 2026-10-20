"""E71 library (PROTOCOL.md): dimension indicators, the FIR71 index and class, the as-of feature frame and the
forecast arms. The E63/E56 code path is read-only from AIPHEED_EXP (clean export, no default).

Indicators (PROTOCOL section 3), province-quarter q:
  ACCESS        a1 food CPI YoY (province), a2 mean(unemployment, underemployment) (national), a3 remittance YoY (national, lower = adverse)
  AVAILABILITY  v1 palay+corn production YoY (province, lower = adverse), v2 fish+aquaculture YoY (province, lower = adverse)
  STABILITY     s1 tropical cyclones (province), s2 PAGASA drought alert (province, 0/1 used as the value)
SWS hunger is NOT an input anywhere in this file except `sws_quarters` (validation only).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
if not os.environ.get("AIPHEED_EXP"):
    raise SystemExit("set AIPHEED_EXP to the clean library export; no default is allowed")
EXP = Path(os.environ["AIPHEED_EXP"])
E71 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP / "E63_Lead_Time_Study" / "runner"))
import e63_lib as H  # noqa: E402

L, P2, np, pd = H.L, H.P2, H.np, H.pd
PROVS = list(L.PROVS)
REF = (L.qi("2021-Q1"), L.qi("2022-Q4"))
DIMS = {"ACCESS": ["a1", "a2", "a3"], "AVAILABILITY": ["v1", "v2"], "STABILITY": ["s1", "s2"]}
ADVERSE_HIGH = {"a1": True, "a2": True, "a3": False, "v1": False, "v2": False, "s1": True, "s2": True, "gap": True}
BINARY = {"s2"}
STRESS = 0.75
PCT = 60
MARKET = list(P2.PRICE_GROUPS["market"])
NEWS = list(P2.PRICE_GROUPS["news"])
LGBM_CFG = dict(num_leaves=4, max_depth=2, n_estimators=50, learning_rate=0.05, min_child_samples=5, reg_lambda=10.0,
                deterministic=True, force_row_wise=True, random_state=71, n_jobs=1, verbose=-1)


def q_of_ym(ym):
    return (np.asarray(ym) // 12) * 4 + (np.asarray(ym) % 12) // 3


# ================================================================================================ indicators
def indicators(d, x) -> pd.DataFrame:
    """One row per province-quarter with the raw indicator values (NaN when not observed)."""
    y = d.yoy.assign(q=q_of_ym(d.yoy["ym"]))
    g = y.groupby(["province_code", "commodity", "q"])["yoy"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3]
    food = g[g["commodity"] == "food"].set_index(["province_code", "q"])["mean"]
    allit = g[g["commodity"] == "all_items"].set_index(["province_code", "q"])["mean"]
    lf = d.lfs.assign(q=q_of_ym(d.lfs["ym"])).groupby(["series", "q"])["value"].agg(["mean", "size"]).reset_index()
    lf = lf[lf["size"] >= 2].pivot(index="q", columns="series", values="mean")
    a2 = lf[["ur", "under"]].mean(axis=1, skipna=False)
    o = x["ofw"].drop_duplicates("q").set_index("q")["ofw_remit_yoy_pct"]
    pr = d.prod.pivot_table(index=["province_code", "q"], columns="series", values="value", aggfunc="sum")
    crop = pr["palay"] + pr["corn"]
    fish = pr["fish"] + pr["aqua"]
    cl = x["climate"].assign(q=lambda f: f["quarter"].map(L.qi)).set_index(["province_code", "q"])
    qs = range(L.qi("2021-Q1"), L.qi("2027-Q1") + 1)
    rows = []
    for p in PROVS:
        for q in qs:
            def yoy(s):
                a, b = s.get((p, q)), s.get((p, q - 4))
                return np.nan if a is None or b is None or not np.isfinite(a) or not np.isfinite(b) or b == 0 else 100 * (a / b - 1)
            f, h = food.get((p, q), np.nan), allit.get((p, q), np.nan)
            c = cl.loc[(p, q)] if (p, q) in cl.index else None
            rows.append({"province_code": p, "q": q, "quarter": L.qs(q), "a1": f, "gap": f - h,
                         "a2": a2.get(q, np.nan), "a3": o.get(q, np.nan), "v1": yoy(crop), "v2": yoy(fish),
                         "s1": np.nan if c is None else float(c["tc_count"]),
                         "s2": np.nan if c is None else float(c["drought_alert"])})
    return pd.DataFrame(rows)


def reference(ind: pd.DataFrame) -> dict:
    r = ind[(ind["q"] >= REF[0]) & (ind["q"] <= REF[1])]
    return {k: np.sort(r[k].dropna().to_numpy(float)) for k in ADVERSE_HIGH}


def pct(ref: np.ndarray, v, adverse_high: bool):
    """Mid-rank percentile in the adverse direction; NaN stays NaN."""
    v = np.asarray(v, float)
    out = np.full(v.shape, np.nan)
    ok = np.isfinite(v)
    if not len(ref):
        return out
    lo = np.searchsorted(ref, v[ok], "left")
    hi = np.searchsorted(ref, v[ok], "right")
    p = (lo + 0.5 * (hi - lo)) / len(ref)
    out[ok] = p if adverse_high else 1 - p
    return out


def score(ind: pd.DataFrame, ref: dict, access_key: str = "a1", drop_dim: str | None = None) -> pd.DataFrame:
    """Indicator percentiles, dimension scores, FIR71 (mean of dimensions; NaN unless all used dimensions exist)."""
    S = ind[["province_code", "q", "quarter"]].copy()
    for k in ADVERSE_HIGH:
        S[f"p_{k}"] = ind[k].to_numpy(float) if k in BINARY else pct(ref[k], ind[k], ADVERSE_HIGH[k])
    dims = {d: [access_key if i == "a1" else i for i in v] for d, v in DIMS.items()}
    for dname, items in dims.items():
        S[dname] = S[[f"p_{i}" for i in items]].mean(axis=1, skipna=True)
    use = [dn for dn in DIMS if dn != drop_dim]
    S["FIR71"] = S[use].mean(axis=1, skipna=False)
    S["n_stressed"] = (S[use] > STRESS).sum(axis=1)
    return S


def threshold(S: pd.DataFrame, pctl: float = PCT) -> float:
    r = S[(S["q"] >= REF[0]) & (S["q"] <= REF[1]) & S["FIR71"].notna()]
    return float(np.percentile(r["FIR71"], pctl))


def labels(S: pd.DataFrame, thr: float) -> pd.DataFrame:
    out = S.copy()
    out["HIGH"] = np.where(out["FIR71"].notna(), (out["FIR71"] > thr).astype(float), np.nan)
    return out


# ================================================================================================ as-of features
def climatology_s1(ind, p, target_q, last_q):
    h = ind[(ind["province_code"] == p) & (ind["q"] <= last_q) & (ind["q"] % 4 == target_q % 4)]["s1"].dropna()
    return float(h.mean()) if len(h) else np.nan


def features(ind, ref, Xh, Bh, t, h, thr) -> pd.DataFrame:
    """Rows for origin t (5 provinces): only indicator rows q <= t-1 are read; projections for t+h."""
    known = ind[ind["q"] <= t - 1]
    last = known[known["q"] == t - 1].set_index("province_code")
    rows = []
    xb = Xh[Xh["t"] == t].set_index("province_code")
    bb = Bh[Bh["t"] == t].set_index("province_code")
    for p in PROVS:
        r = {"province_code": p, "t": t}
        lv = last.loc[p] if p in last.index else None
        for k in ("a1", "a2", "a3", "v1", "v2", "s1", "s2"):
            r[f"last_{k}"] = np.nan if lv is None else float(lv[k])
        proj = {"a1": float(bb.loc[p, "base_1.0"]) if p in bb.index else np.nan,
                "a2": r["last_a2"], "a3": r["last_a3"], "v1": r["last_v1"], "v2": r["last_v2"],
                "s1": climatology_s1(known, p, t + h, t - 1), "s2": r["last_s2"]}
        r.update({f"proj_{k}": v for k, v in proj.items()})
        for c in MARKET + NEWS:
            r[c] = float(xb.loc[p, c]) if (p in xb.index and c in xb.columns) else np.nan
        rows.append(r)
    F = pd.DataFrame(rows)
    for pre in ("last", "proj"):
        tmp = F[[f"{pre}_{k}" for k in ("a1", "a2", "a3", "v1", "v2", "s1", "s2")]].copy()
        tmp.columns = ["a1", "a2", "a3", "v1", "v2", "s1", "s2"]
        tmp["gap"] = np.nan
        sc = score(tmp.assign(province_code=F["province_code"], q=t, quarter=""), ref)
        for dn in list(DIMS) + ["FIR71"]:
            F[f"{pre}_{dn}"] = sc[dn].to_numpy()
    return F


FEAT_DIM = [f"{p}_{d}" for p in ("proj", "last") for d in list(DIMS) + ["FIR71"]]
FEAT_PSA = FEAT_DIM + [f"{p}_{k}" for p in ("proj", "last") for k in ("a1", "a2", "a3", "v1", "v2", "s1", "s2")] + MARKET
FEAT_LGBM = FEAT_DIM + MARKET + NEWS
FEAT_LGBM_NONEWS = FEAT_DIM + MARKET


# ================================================================================================ models
def _const(y, n):
    return np.full(n, float(np.mean(y)))


def fit_lr(tr, te, cols):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    y = tr["HIGH"].to_numpy(int)
    if len(set(y)) < 2:
        return _const(y, len(te))
    med = tr[cols].median()
    Xtr, Xte = tr[cols].fillna(med).fillna(0.0), te[cols].fillna(med).fillna(0.0)
    keep = [c for c in cols if Xtr[c].std() > 0]
    if not keep:
        return _const(y, len(te))
    sc = StandardScaler().fit(Xtr[keep])
    m = LogisticRegression(C=1.0, max_iter=2000).fit(sc.transform(Xtr[keep]), y)
    return m.predict_proba(sc.transform(Xte[keep]))[:, 1]


def fit_lgbm(tr, te, cols):
    import lightgbm as lgb
    y = tr["HIGH"].to_numpy(int)
    if len(set(y)) < 2:
        return _const(y, len(te))
    m = lgb.LGBMClassifier(objective="binary", **LGBM_CFG).fit(tr[cols].astype(float), y)
    return m.predict_proba(te[cols].astype(float))[:, 1]


def fit_dimfuse(tr, te, thr):
    from sklearn.linear_model import LogisticRegression
    ok = tr["proj_FIR71"].notna()
    y = tr.loc[ok, "HIGH"].to_numpy(int)
    z = te["proj_FIR71"].to_numpy(float)
    rule = np.where(np.isfinite(z), (z > thr).astype(float), np.nan)
    if ok.sum() < 10 or len(set(y)) < 2:
        return rule, "rule"
    m = LogisticRegression(C=1e6, max_iter=2000).fit(tr.loc[ok, ["proj_FIR71"]].to_numpy(float), y)
    p = np.full(len(te), np.nan)
    f = np.isfinite(z)
    p[f] = m.predict_proba(z[f].reshape(-1, 1))[:, 1]
    return p, "logistic"
