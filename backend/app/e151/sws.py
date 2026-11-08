"""
E151 Tier 1: does corrected news add forecast information? Area-quarter SWS hunger, expanding window. See docs/e151/PROTOCOL.md.

    python -m app.e151.sws lock | dev | confirm | signal
"""
from __future__ import annotations

import hashlib
import json
import sys
import warnings
from datetime import datetime, timezone

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm, rankdata
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score

from app.e144 import data as D
from app.e147 import features as Fe
from app.e148 import panel as Pn
from app.e150 import response as R150
from app.e151 import OUT
from app.fi5.target import qindex, qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
SEED = 151
AREAS = ["metro_manila", "balance_luzon", "visayas", "mindanao"]
GOV = R150.INPUTS
STATE = ["sws_last", "sws_anom", "lead"]
GROUPS5 = ["market", "climate", "employment", "remittance", "poverty"]
PAR = dict(objective="regression", n_estimators=200, learning_rate=0.03, num_leaves=7, max_depth=3, min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, n_jobs=1, verbose=-1)
LEADS_TRAIN = list(range(1, 9))
FIRST_ISSUE = qindex("2015-Q1")
LAST_ISSUE = Pn.LAST
DEV_LAST_T = qindex("2020-Q4")
CONF_FIRST_T = qindex("2021-Q1")


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def hashes():
    h = {"protocol": _sha(BACKEND_DIR.parent / "docs" / "e151" / "PROTOCOL.md"), "news_panel": _sha(OUT / "news_panel.parquet")}
    for f in ("corpus", "features", "topics", "score", "sws"):
        h[f] = _sha(BACKEND_DIR / "app" / "e151" / f"{f}.py")
    return h


def lock():
    (OUT / "PROTOCOL_LOCK.json").write_text(json.dumps({"locked_utc": datetime.now(timezone.utc).isoformat(), "hashes": hashes()}, indent=1), newline="\n")
    print("locked")


def news_wide(geo_lag):
    P = pd.read_parquet(OUT / "news_panel.parquet")
    return P[P["lag_m"] == geo_lag].set_index(["stream", "qi"])


NEWS_COLS_E = [f"e_{g}" for g in GROUPS5 + ["response"]] + ["e_hunger", "e_net", "intensity", "diversity", "emerging"]
NEWS_COLS_T = [f"tp_{g}" for g in GROUPS5 + ["response"]]
_cache = {}


def attach(A: pd.DataFrame, geo: str, lag: int) -> pd.DataFrame:
    """A has area and qi. Adds news columns for this geography and lag, and the change in net stress against the previous window."""
    key = (geo, lag)
    if key in _cache:
        return _cache[key]
    W, W2 = news_wide(lag), news_wide(lag + 3)
    streams = {"nat": lambda a: "nat", "pool": lambda a: "all", "area": lambda a: "area:" + a}
    use = {"nat": ["nat"], "pool": ["pool"], "area": ["area"], "area+nat": ["area", "nat"]}[geo]
    idx = A[["area", "qi"]].drop_duplicates().copy()
    for u in use:
        cols = [c for c in NEWS_COLS_E + NEWS_COLS_T if c in W.columns]
        tk = pd.MultiIndex.from_arrays([idx["area"].map(streams[u]), idx["qi"]])
        v = W.reindex(tk)[cols].reset_index(drop=True)
        v2 = W2.reindex(tk)["e_net"].reset_index(drop=True)
        v = v.fillna({c: 0.0 for c in cols if c not in ("intensity", "diversity", "emerging")})
        v["e_chg"] = v["e_net"] - v2.fillna(0.0)
        v.columns = [f"{u}_{c}" for c in v.columns]
        v.index = idx.index
        idx = pd.concat([idx, v], axis=1)
    out = A.merge(idx, on=["area", "qi"], how="left")
    _cache[key] = out
    return out


def news_cols(geo: str, content: str, overall=False):
    use = {"nat": ["nat"], "pool": ["pool"], "area": ["area"], "area+nat": ["area", "nat"]}[geo]
    base = []
    for u in use:
        if overall:
            base += [f"{u}_e_net", f"{u}_e_hunger", f"{u}_intensity", f"{u}_e_chg"]
            continue
        if content in ("events", "both"):
            base += [f"{u}_{c}" for c in NEWS_COLS_E] + [f"{u}_e_chg"]
        if content in ("topics", "both"):
            base += [f"{u}_{c}" for c in NEWS_COLS_T]
    return base


def area_table() -> pd.DataFrame:
    P = R150.province_inputs()
    a = P[P["sws_area"].isin(AREAS)].groupby(["sws_area", "qi"])[GOV].mean().reset_index().rename(columns={"sws_area": "area"})
    n = P.groupby("qi")[GOV].mean().reset_index().assign(area="metro_manila")          # no province rows exist for Metro Manila: national means, and this is disclosed
    a = pd.concat([a, n], ignore_index=True)
    s = D.sws_quarterly()
    rows = []
    for _, r in a.iterrows():
        if r["qi"] < Pn.FIRST:
            continue
        g = s[(s["area"] == r["area"]) & (s["published"] < Pn.q_start(int(r["qi"])))].sort_values("qi")
        if g.empty:
            continue
        h = Fe._logit(g["hunger"].values)
        st = {"sws_last": float(h[-1]), "sws_anom": float(h[-1] - np.mean(h[-9:-1])) if len(h) >= 3 else np.nan, "last_q": int(g["qi"].iloc[-1])}
        for ld in LEADS_TRAIN:
            T = int(r["qi"]) + ld
            t = s[(s["area"] == r["area"]) & (s["qi"] == T)]
            row = {**r.to_dict(), **st, "lead": ld, "T": T, "dy": np.nan, "published": pd.NaT}
            if len(t):
                row["dy"] = float(Fe._logit(t["hunger"].iloc[0])) - st["sws_last"]
                row["published"] = t["published"].iloc[0]
            rows.append(row)
    d = pd.DataFrame(rows)
    d["qi"] = d["qi"].astype(int)
    return d


def _screen(t, cols):
    """Training-only Granger-type screen: does the lagged news feature add to an autoregression with area effects? Keeps p < 0.10."""
    x = t[t["lead"] == 1]
    if len(x) < 30:
        return []
    Z0 = np.column_stack([np.ones(len(x)), x["sws_last"], pd.get_dummies(x["area"], drop_first=True).values.astype(float)])
    y = x["dy"].values
    keep = []
    for c in cols:
        v = x[c].fillna(0.0).values
        if np.std(v) < 1e-9:
            continue
        Z = np.column_stack([Z0, v])
        beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
        e = y - Z @ beta
        s2 = e @ e / max(1, len(y) - Z.shape[1])
        cov = s2 * np.linalg.pinv(Z.T @ Z)
        tv = beta[-1] / np.sqrt(cov[-1, -1])
        if 2 * (1 - norm.cdf(abs(tv))) < 0.10:
            keep.append(c)
    return keep


def _issue(i, A, sets, seeds, leads, shuffle=None):
    """Forecast rows of issue i from every configuration, fitted on outcomes already published."""
    cut = Pn.q_start(i)
    tr = A[A["dy"].notna() & (A["published"] < cut)]
    te = A[(A["qi"] == i) & A["lead"].isin(leads) & A["dy"].notna()]
    if len(tr) < 60 or te.empty:
        return None
    o = te[["area", "qi", "T", "lead", "dy", "sws_last"]].copy()
    for name, cols, screen in sets:
        use = list(cols)
        if screen:
            news = [c for c in use if c not in GOV + STATE]
            use = [c for c in use if c in GOV + STATE] + _screen(tr, news)
        p = np.zeros(len(te))
        for s in range(seeds):
            p += lgb.LGBMRegressor(**PAR, random_state=SEED + s).fit(tr[use], tr["dy"]).predict(te[use]) / seeds
        o[name] = p
    return o


def _lin(i, A, cols, leads):
    cut = Pn.q_start(i)
    tr = A[A["dy"].notna() & (A["published"] < cut)]
    te = A[(A["qi"] == i) & A["lead"].isin(leads) & A["dy"].notna()]
    if len(tr) < 60 or te.empty:
        return None
    med = tr[cols].median()
    sd = tr[cols].std().replace(0, 1)
    m = Ridge(alpha=10.0).fit(((tr[cols] - med) / sd).fillna(0.0), tr["dy"])
    return te.assign(LR=m.predict(((te[cols] - med) / sd).fillna(0.0)))[["area", "T", "lead", "LR"]]


def ablock(g, a, b, rng, n=5000):
    Q = g["T"].unique()
    d = (g[a] - g["dy"]) ** 2 - (g[b] - g["dy"]) ** 2
    v = d.groupby(g["T"]).sum()
    c = d.groupby(g["T"]).size()
    idx = rng.integers(0, len(Q), (n, len(Q)))
    q = v.reindex(Q).values
    w = c.reindex(Q).values
    boots = q[idx].sum(axis=1) / w[idx].sum(axis=1)
    m = d.groupby(g["T"]).mean()
    dm = float(m.mean() / (m.std(ddof=1) / np.sqrt(len(m)))) if len(m) > 2 else np.nan
    return {"diff": float(d.mean()), "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))], "dm_t": dm, "dm_p": float(2 * (1 - norm.cdf(abs(dm)))) if dm == dm else None, "n": int(len(g)), "quarters": int(len(Q))}


def score_sets(O, names):
    out = {}
    for n in names:
        e = O[n] - O["dy"]
        rise = O["dy"] > 0
        out[n] = {"mse": float((e ** 2).mean()), "mae": float(e.abs().mean()), "direction_accuracy": float(((O[n] > 0) == rise).mean()), "auc_rise": float(roc_auc_score(rise, O[n])) if O[n].nunique() > 1 else None, "spearman_change": float(pd.Series(rankdata(O[n])).corr(pd.Series(rankdata(O["dy"])))) if O[n].nunique() > 1 else None}
    return out


def dev():
    A0 = area_table()
    grid = [(g, c, l, s) for g in ("nat", "pool", "area", "area+nat") for c in ("events", "topics", "both") for l in (0, 3) for s in (False, True)]
    def one(g, c, l, s):
        A = attach(A0, g, l)
        cols = STATE + GOV + news_cols(g, c)
        res = [_issue(i, A, [("GNT", cols, s)], 1, [1]) for i in range(FIRST_ISSUE, LAST_ISSUE + 1) if i + 1 <= DEV_LAST_T]
        O = pd.concat([x for x in res if x is not None])
        return {"geo": g, "content": c, "lag": l, "screen": s, "mse": float(((O["GNT"] - O["dy"]) ** 2).mean()), "n": int(len(O))}
    R = pd.DataFrame(Parallel(n_jobs=20)(delayed(one)(*x) for x in grid))
    R = R.sort_values("mse")
    base = []
    A = attach(A0, "nat", 0)
    for i in range(FIRST_ISSUE, LAST_ISSUE + 1):
        if i + 1 <= DEV_LAST_T:
            x = _issue(i, A, [("AR", STATE, False), ("GOV", STATE + GOV, False)], 3, [1])
            if x is not None:
                base.append(x)
    B = pd.concat(base)
    res = {"grid": R.round(5).to_dict(orient="records"), "dev_mse_PERS": float((B["dy"] ** 2).mean()), "dev_mse_AR": float(((B["AR"] - B["dy"]) ** 2).mean()), "dev_mse_GOV": float(((B["GOV"] - B["dy"]) ** 2).mean()), "n": int(len(B)), "selected": R.iloc[0][["geo", "content", "lag", "screen"]].to_dict()}
    (OUT / "sws_dev.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps({k: res[k] for k in res if k != "grid"}, indent=1, default=float))
    print(R.head(12).to_string())
    print(R.groupby("geo")["mse"].median(), R.groupby("content")["mse"].median(), R.groupby("lag")["mse"].median(), R.groupby("screen")["mse"].median())


def sets_for(sel):
    g, c, l, s = sel["geo"], sel["content"], int(sel["lag"]), bool(sel["screen"])
    return g, c, l, s, [("AR", STATE, False), ("GOV", STATE + GOV, False), ("NEWS", STATE + news_cols(g, c), s), ("GN", STATE + GOV + news_cols(g, c, overall=True), s), ("GNT", STATE + GOV + news_cols(g, c), s)]


def confirm():
    rec = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    bad = [k for k, v in rec["hashes"].items() if hashes().get(k) != v and k != "sws"]
    if bad:
        raise RuntimeError(f"lock mismatch {bad}")
    sel = json.loads((OUT / "sws_dev.json").read_text())["selected"]
    g, c, l, s, sets = sets_for(sel)
    A = attach(area_table(), g, l)
    allc = STATE + GOV + news_cols(g, c)
    leads = [1, 2, 3, 4]
    R = Parallel(n_jobs=20)(delayed(_issue)(i, A, sets, 5, leads) for i in range(FIRST_ISSUE, LAST_ISSUE + 1))
    O = pd.concat([x for x in R if x is not None], ignore_index=True)
    L = [x for x in Parallel(n_jobs=20)(delayed(_lin)(i, A, allc, leads) for i in range(FIRST_ISSUE, LAST_ISSUE + 1)) if x is not None]
    O = O.merge(pd.concat(L), on=["area", "T", "lead"], how="left")
    O["PERS"] = 0.0
    O["set"] = np.where(O["T"] <= DEV_LAST_T, "development", "confirmation")
    O.to_csv(OUT / "sws_predictions.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(SEED)
    names = ["PERS", "AR", "LR", "GOV", "NEWS", "GN", "GNT"]
    res = {"selected": sel, "metrics": {}, "tests": {}}
    for st in ("development", "confirmation"):
        for h in leads:
            x = O[(O["set"] == st) & (O["lead"] == h)]
            res["metrics"][f"{st}_L{h}"] = {"n": int(len(x)), "quarters": int(x["T"].nunique()), **score_sets(x, names)}
            res["tests"][f"{st}_L{h}"] = {f"{a}-{b}": ablock(x, a, b, rng) for a, b in (("GNT", "GOV"), ("GNT", "AR"), ("GNT", "PERS"), ("NEWS", "AR"), ("GOV", "AR"), ("GN", "GOV"))}
    x = O[O["lead"] == 1]
    for st in ("development", "confirmation"):
        res["by_area_" + st] = {a: score_sets(z, ["AR", "GOV", "GNT"]) | {"n": int(len(z))} for a, z in x[x["set"] == st].groupby("area")}
    # deterioration: a rise in the top quartile of training changes; threshold set on development rows at 50 % precision
    dv, cf = x[x["set"] == "development"], x[x["set"] == "confirmation"]
    q75 = float(dv["dy"].quantile(0.75))
    det = {"event_threshold_logit": q75, "events_dev": int((dv["dy"] > q75).sum()), "events_conf": int((cf["dy"] > q75).sum())}
    for n in ("AR", "GOV", "GNT"):
        grid = np.sort(dv[n].unique())
        th = next((t for t in grid if (dv["dy"][dv[n] >= t] > q75).mean() >= 0.5), grid[-1])
        hit = cf[n] >= th
        det[n] = {"threshold": float(th), "conf_precision": float((cf["dy"][hit] > q75).mean()) if hit.any() else None, "conf_recall": float(hit[cf["dy"] > q75].mean())}
    res["deterioration_L1"] = det
    (OUT / "sws_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res["selected"]), json.dumps(res["metrics"]["confirmation_L1"], indent=0), json.dumps(res["tests"]["confirmation_L1"]["GNT-GOV"]), json.dumps(res["tests"]["development_L1"]["GNT-GOV"]), json.dumps(det))


def _placebo(seed, A, sel):
    g, c, l, s, _ = sets_for(sel)
    cols = news_cols(g, c)
    r = np.random.default_rng(seed)
    q = np.array(sorted(A["qi"].unique()))
    mp = dict(zip(q, r.permutation(q)))
    W = A[["area", "qi"] + cols].drop_duplicates(["area", "qi"]).copy()
    W["qi"] = W["qi"].map({v: k for k, v in mp.items()})
    Z = A.drop(columns=cols).merge(W, on=["area", "qi"], how="left")
    O = [_issue(i, Z, [("GNT", STATE + GOV + cols, s)], 1, [1]) for i in range(FIRST_ISSUE, LAST_ISSUE + 1) if i + 1 >= CONF_FIRST_T]
    O = pd.concat([x for x in O if x is not None])
    return float(((O["GNT"] - O["dy"]) ** 2).mean())


def placebo():
    sel = json.loads((OUT / "sws_dev.json").read_text())["selected"]
    g, c, l, s, _ = sets_for(sel)
    A = attach(area_table(), g, l)
    p = np.array(Parallel(n_jobs=20)(delayed(_placebo)(1000 + k, A, sel) for k in range(200)))
    res = json.loads((OUT / "sws_results.json").read_text())
    real = res["metrics"]["confirmation_L1"]["GNT"]["mse"]
    res["placebo_L1"] = {"real_mse": real, "placebo_mean": float(p.mean()), "placebo_p5": float(np.percentile(p, 5)), "share_placebo_better_or_equal": float((p <= real).mean()), "n": 200}
    t = res["tests"]["confirmation_L1"]["GNT-GOV"]
    res["news_pass_q1"] = bool(t["ci95"][1] < 0 and res["placebo_L1"]["share_placebo_better_or_equal"] <= 0.05)
    (OUT / "sws_results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(res["placebo_L1"], res["news_pass_q1"])


def _signal_issue(i, A, P, sets):
    cut = Pn.q_start(i)
    tr = A[A["dy"].notna() & (A["published"] < cut)]
    x = P[P["qi"] == i]
    if len(tr) < 60 or x.empty:
        return None
    (_, ar_cols, _), (_, gnt_cols, screen) = sets[0], sets[-1]
    use = list(gnt_cols)
    if screen:
        news = [c for c in use if c not in GOV + STATE]
        use = [c for c in use if c in GOV + STATE] + _screen(tr, news)
    m1 = [lgb.LGBMRegressor(**PAR, random_state=SEED + s).fit(tr[use], tr["dy"]) for s in range(3)]
    m0 = [lgb.LGBMRegressor(**PAR, random_state=SEED + s).fit(tr[ar_cols], tr["dy"]) for s in range(3)]
    out = []
    for h in LEADS_TRAIN:
        z = x.assign(lead=h)
        out.append(pd.DataFrame({"key": z["key"].values, "i": i, "lead": h, "h2": np.mean([m.predict(z[use]) for m in m1], axis=0) - np.mean([m.predict(z[ar_cols]) for m in m0], axis=0)}))
    return pd.concat(out)


def signal():
    """The Tier 1 model applied as of each issue to each province's own government inputs, with its area and national news. An input to the province model, never a label."""
    sel = json.loads((OUT / "sws_dev.json").read_text())["selected"]
    g, c, l, s, sets = sets_for(sel)
    A = attach(area_table(), g, l)
    P = R150.province_inputs()
    P = P[P["sws_area"].isin(AREAS)].rename(columns={"sws_area": "area"})
    st = A[A["lead"] == 1][["area", "qi", "sws_last", "sws_anom"]].drop_duplicates()
    nw = A[A["lead"] == 1][["area", "qi"] + [x for x in A.columns if x.startswith(("area_", "nat_", "pool_"))]].drop_duplicates(["area", "qi"])
    P = P.merge(st, on=["area", "qi"], how="left").merge(nw, on=["area", "qi"], how="left")
    H = pd.concat([x for x in Parallel(n_jobs=20)(delayed(_signal_issue)(i, A, P, sets) for i in range(FIRST_ISSUE, LAST_ISSUE + 1)) if x is not None], ignore_index=True)
    H.to_parquet(OUT / "h2_signal.parquet", index=False)
    print(H.shape, H["h2"].describe().round(3).to_dict())


def _mse_conf(A, use, s, leads=(1,)):
    R = [_issue(i, A, [("X", use, s)], 3, list(leads)) for i in range(FIRST_ISSUE, LAST_ISSUE + 1) if i + 1 >= CONF_FIRST_T]
    return pd.concat([x for x in R if x is not None])


def ablate():
    """Exploratory, on confirmation rows at Lead 1: which part of the news carries anything? Labelled exploratory in the protocol; never used to choose a model."""
    sel = json.loads((OUT / "sws_dev.json").read_text())["selected"]
    g, c, l, s, _ = sets_for(sel)
    A = attach(area_table(), g, l)
    full = STATE + GOV + news_cols(g, c)
    news = news_cols(g, c)
    jobs = {"full": full, "no_news": STATE + GOV}
    for k in GROUPS5 + ["response"]:
        jobs["drop_news_" + k] = [x for x in full if not x.endswith(f"_e_{k}") and not x.endswith(f"_tp_{k}")]
        jobs["only_news_" + k] = STATE + GOV + [x for x in news if x.endswith(f"_e_{k}") or x.endswith(f"_tp_{k}")]
    jobs["drop_topics"] = [x for x in full if "_tp_" not in x]
    jobs["drop_events"] = [x for x in full if x in STATE + GOV or "_tp_" in x]
    jobs["drop_net_direction"] = [x for x in full if not x.endswith(("_e_net", "_e_chg"))]
    jobs["drop_hunger"] = [x for x in full if not x.endswith("_e_hunger")]
    jobs["drop_volume_diversity"] = [x for x in full if not x.endswith(("_intensity", "_diversity", "_emerging"))]
    names = list(jobs)
    R = Parallel(n_jobs=20)(delayed(_mse_conf)(A, jobs[n], s) for n in names)
    base = R[names.index("no_news")].rename(columns={"X": "no_news"})
    rng = np.random.default_rng(SEED)
    out = {}
    for n, x in zip(names, R):
        z = base[["area", "T", "lead", "dy", "no_news"]].merge(x[["area", "T", "lead", "X"]], on=["area", "T", "lead"])
        out[n] = {"mse": float(((z["X"] - z["dy"]) ** 2).mean()), "n": int(len(z)), "minus_no_news": ablock(z, "X", "no_news", rng, n=2000) if n != "no_news" else None}
    lags = {}
    for lg_ in (0, 3, 6):
        _cache.clear()
        B = attach(area_table(), g, lg_)
        x = _mse_conf(B, full, s)
        lags[str(lg_)] = float(((x["X"] - x["dy"]) ** 2).mean())
    res = {"selected": sel, "ablation_L1_confirmation": out, "window_lag_months_mse": lags}
    p = OUT / "news_panel_no_top_outlet.parquet"
    if p.exists():
        global news_wide
        keep = news_wide
        def alt(lag):
            X = pd.read_parquet(p)
            return X[X["lag_m"] == lag].set_index(["stream", "qi"])
        news_wide = alt
        _cache.clear()
        B = attach(area_table(), g, l)
        x = _mse_conf(B, full, s)
        news_wide = keep
        res["without_largest_outlet_mse"] = float(((x["X"] - x["dy"]) ** 2).mean())
        res["largest_outlet"] = json.loads((OUT / "news_feature_audit.json").read_text()).get("largest_outlet")
    # SHAP at the last fit, group shares
    tr = A[A["dy"].notna() & (A["published"] < Pn.q_start(LAST_ISSUE))]
    m = lgb.LGBMRegressor(**PAR, random_state=SEED).fit(tr[full], tr["dy"])
    C = np.abs(m.booster_.predict(tr[full], pred_contrib=True)[:, :-1]).mean(axis=0)
    gr = {}
    for n, v in zip(full, C):
        k = "state" if n in STATE else "government" if n in GOV else "news_" + n.split("_", 1)[1].replace("e_", "").replace("tp_", "")
        gr[k] = gr.get(k, 0.0) + float(v)
    tot = sum(gr.values()) or 1.0
    res["shap_share_last_fit"] = {k: round(v / tot, 4) for k, v in sorted(gr.items(), key=lambda t: -t[1])}
    (OUT / "sws_ablation.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=0, default=float)[:6000])


def seal():
    """Blind evidence: forecasts of quarters not yet published, written once and hashed."""
    sel = json.loads((OUT / "sws_dev.json").read_text())["selected"]
    g, c, l, s, sets = sets_for(sel)
    A = attach(area_table(), g, l)
    i = int(A["qi"].max())
    cut = Pn.q_start(i)
    tr = A[A["dy"].notna() & (A["published"] < cut)]
    te = A[(A["qi"] == i) & A["lead"].isin([1, 2, 3, 4])]
    rows = te[["area", "T", "lead", "sws_last", "last_q"]].copy()
    rows["T_label"] = rows["T"].map(lambda t: qlabel(int(t)))
    rows["last_label"] = rows["last_q"].map(lambda t: qlabel(int(t)))
    for name, cols, sc in sets:
        use = list(cols)
        if sc:
            news = [x for x in use if x not in GOV + STATE]
            use = [x for x in use if x in GOV + STATE] + _screen(tr, news)
        p = np.mean([lgb.LGBMRegressor(**PAR, random_state=SEED + k).fit(tr[use], tr["dy"]).predict(te[use]) for k in range(5)], axis=0)
        rows["pct_" + name] = 100 / (1 + np.exp(-(rows["sws_last"].values + p)))
    rows["pct_PERS"] = 100 / (1 + np.exp(-rows["sws_last"]))
    f = OUT / f"sealed_sws_{qlabel(i)}.json"
    if f.exists():
        print("already sealed", _sha(f))
        return
    f.write_text(json.dumps({"sealed_utc": datetime.now(timezone.utc).isoformat(), "issue": qlabel(i), "selected": sel, "forecasts": rows.drop(columns=["T", "last_q", "sws_last"]).round(2).to_dict(orient="records")}, indent=1, default=float), newline="\n")
    print("seal", _sha(f))


if __name__ == "__main__":
    {"lock": lock, "dev": dev, "confirm": confirm, "placebo": placebo, "signal": signal, "ablate": ablate, "seal": seal}[sys.argv[1]]()
