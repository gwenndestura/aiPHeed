"""PROTOCOL_E114 (hash checked): one unified LightGBM forecasts the change in SWS hunger by area at Leads 1-2 from
point-in-time inputs; comparators RW, MEAN, DAMP, AR1, RIDGE; DEV 2003-12, untouched TEST 2013-20 (scored once),
SECONDARY 2021+; group ablation, robustness, leakage checks.

    python run_e114.py            # ../out/e114_results.json, ../out/e114_rows.csv
"""
from __future__ import annotations

import hashlib
import json
import math
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression

import e114_lib as L

AREAS = list(L.AREAS)
LEADS = (1, 2)
GROUPS = {"hunger_history": ["h_last", "MR", "d_last", "stale"],
          "market_prices": ["P-FOOD", "P-DFOOD", "P-RICE"],
          "climate": ["C-ONI", "C-TC", "P-PALAY"],
          "employment": ["P-UNEMP"],
          "news_nlp": ["N-SUP", "N-AST"]}
FEATS = sum(GROUPS.values(), []) + ["lead"] + [f"A-{a}" for a in AREAS]
GRID = [dict(depth=d, trees=n) for d in (1, 2) for n in (100, 300)]
SPLITS = {"DEV": (L.qi("2003-Q1"), L.qi("2012-Q4")), "TEST": (L.qi("2013-Q1"), L.qi("2020-Q4")),
          "SECONDARY": (L.qi("2021-Q1"), L.qi("2026-Q3"))}
MODELS = ["ULGBM", "RW", "MEAN", "DAMP", "AR1", "RIDGE"]


def split_of(q):
    for s, (a, b) in SPLITS.items():
        if a <= q <= b:
            return s
    return None


def published(q, a):
    r = L.rounds()
    g = r[(r["area"] == a) & (r["q"] == q)]
    return str(g["published"].max()) if len(g) else None


def ar1(s, steps):
    q = np.array([x[0] for x in s]); h = np.array([x[1] for x in s])
    ok = np.where(np.diff(q) == 1)[0]
    if len(ok) < 8:
        return h[-1]
    x, y = h[ok], h[ok + 1]
    phi, c = np.polyfit(x, y, 1)
    phi = float(np.clip(phi, -0.99, 0.99))
    f = h[-1]
    for _ in range(int(steps)):
        f = c + phi * f
    return float(f)


def build_rows():
    rows = []
    for a in AREAS:
        for t in range(L.qi("1999-Q1"), L.LAST_ORIGIN + 1):
            iss = L.issue(t)
            s = L.known(iss, a)
            if len(s) < 4:
                continue
            ql, hl = s[-1][0], s[-1][1]
            hs = [h for _, h, _ in s]
            for k in LEADS:
                f = L.features(t, k, a)
                q = t + k
                y = L.outcome(q, a)
                rows.append({"area": a, "t": t, "lead": k, "q": q, "issue": iss, "y": y, "pub_target": published(q, a),
                             "h_last": hl, "q_last": ql, "MR": hl - float(np.mean(hs)), "d_last": hl - s[-2][1],
                             "stale": t - ql, "mean_known": float(np.mean(hs)), "usual": float(np.median(hs)),
                             "AR1": ar1(s, q - ql),
                             **{c: f[c] for c in ("P-FOOD", "P-DFOOD", "P-RICE", "P-PALAY", "P-UNEMP", "C-ONI", "C-TC")},
                             "N-SUP": f["N-SUP@0"], "N-AST": f["N-AST@0"], "lead": k,
                             **{f"A-{b}": float(b == a) for b in AREAS}})
    R = pd.DataFrame(rows)
    R["dy"] = R["y"] - R["h_last"]
    R["split"] = R["q"].map(split_of)
    return R


def train_at(R, t):
    """Rows of earlier origins whose target reading was published before O(t); targets as known at O(t)."""
    iss = L.issue(t)
    tr = R[(R["t"] < t) & R["pub_target"].notna() & (R["pub_target"] < iss)].copy()
    kn = {a: {q: h for q, h, _ in L.known(iss, a)} for a in AREAS}
    tr["y_known"] = [kn[a].get(q, np.nan) for a, q in zip(tr["area"], tr["q"])]
    tr = tr[tr["y_known"].notna()]
    tr["dy_known"] = tr["y_known"] - tr["h_last"]
    return tr


def lgbm(cfg):
    import lightgbm as lgb
    return lgb.LGBMRegressor(objective="l2", learning_rate=0.03, max_depth=cfg["depth"], num_leaves=2 ** cfg["depth"],
                             n_estimators=cfg["trees"], min_child_samples=20, reg_lambda=5.0, random_state=L.SEED,
                             deterministic=True, force_row_wise=True, n_jobs=1, verbose=-1)


def select(tr, cols):
    origins = sorted(tr["t"].unique())[-4:]
    sc = {}
    for i, c in enumerate(GRID):
        err = []
        for o in origins:
            f = tr[(tr["t"] < o) & (tr["pub_target"] < L.issue(o))]
            h = tr[tr["t"] == o]
            if len(f) < 40 or not len(h):
                continue
            m = lgbm(c).fit(f[cols].astype(float), f["dy_known"])
            err.append(((m.predict(h[cols].astype(float)) - h["dy_known"]) ** 2).to_numpy())
        sc[i] = float(np.mean(np.concatenate(err))) if err else np.inf
    return GRID[min(sc, key=lambda i: (round(sc[i], 9), i))]


def ridge(tr, te, cols, alpha=10.0):
    mu, sd = tr[cols].mean(), tr[cols].std().replace(0, 1).fillna(1)
    X = ((tr[cols] - mu) / sd).fillna(0).to_numpy()
    Xt = ((te[cols] - mu) / sd).fillna(0).to_numpy()
    X1, Xt1 = np.c_[np.ones(len(X)), X], np.c_[np.ones(len(Xt)), Xt]
    P = np.eye(X1.shape[1]) * alpha
    P[0, 0] = 0
    b = np.linalg.solve(X1.T @ X1 + P, X1.T @ tr["dy_known"].to_numpy())
    return Xt1 @ b


def rolling(R, cols=FEATS, origins=None, with_ridge=True, train_filter=None):
    out = []
    for t in origins if origins is not None else sorted(R["t"].unique()):
        tr = train_at(R, int(t))
        if train_filter is not None:
            tr = tr[train_filter(tr)]
        te = R[R["t"] == t]
        if len(tr) < 60 or tr["t"].nunique() < 8 or not len(te):
            continue
        cfg = select(tr, cols)
        m = lgbm(cfg).fit(tr[cols].astype(float), tr["dy_known"])
        o = te[["area", "t", "lead"]].copy()
        o["ULGBM"] = te["h_last"].to_numpy() + m.predict(te[cols].astype(float))
        o["cfg"] = f"d{cfg['depth']}n{cfg['trees']}"
        if with_ridge:
            o["RIDGE"] = te["h_last"].to_numpy() + ridge(tr, te, cols)
        o["train_rows"], o["train_max_pub"] = len(tr), str(tr["pub_target"].max())
        out.append(o)
    return pd.concat(out, ignore_index=True)


def add_probabilities(R):
    """sigma from each model's own earlier out-of-sample errors (same lead, target published before the issue, >= 8)."""
    for m in MODELS:
        R[f"{m}_sig"] = np.nan
    for k in LEADS:
        g = R[R["lead"] == k]
        for t in sorted(g["t"].unique()):
            iss = L.issue(int(t))
            h = g[(g["t"] < t) & g["pub_target"].notna() & (g["pub_target"] < iss) & g["y"].notna()]
            idx = g.index[g["t"] == t]
            for m in MODELS:
                e = (h[m] - h["y"]).dropna()
                if len(e) >= 8:
                    R.loc[idx, f"{m}_sig"] = float(np.sqrt(np.mean(e ** 2)))
    for m in MODELS:
        R[f"{m}_pU"] = 1 - norm.cdf((R["usual"] - R[m]) / R[f"{m}_sig"])
        R[f"{m}_p11"] = 1 - norm.cdf((11.3 - R[m]) / R[f"{m}_sig"])
    R["yU"] = (R["y"] > R["usual"]).astype(float)
    R["y11"] = (R["y"] > 11.3).astype(float)
    return R


def dm(d_by_q: pd.Series, lag: int) -> dict:
    d = d_by_q.to_numpy(float)
    n = len(d)
    if n < 6:
        return {"n_quarters": n, "mean_diff": float(np.mean(d)) if n else None, "p_one_sided": None}
    m = d.mean()
    g = [np.mean((d[j:] - m) * (d[:n - j] - m)) for j in range(lag + 1)]
    v = g[0] + 2 * sum((1 - j / (lag + 1)) * g[j] for j in range(1, lag + 1))
    z = m / math.sqrt(max(v, 1e-12) / n)
    return {"n_quarters": n, "mean_diff": float(m), "z": float(z), "p_one_sided": float(norm.cdf(z))}


def boot_q(d_by_q, draws=4000, seed=2031):
    d = d_by_q.to_numpy(float)
    rng = np.random.default_rng(seed)
    b = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(draws)]
    return [float(np.quantile(b, .05)), float(np.quantile(b, .95))]


def binm(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    k = (p >= .5).astype(int)
    tp, fp, fn, tn = (int(((k == a) & (y == b)).sum()) for a, b in ((1, 1), (1, 0), (0, 1), (0, 0)))
    rec = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    prec = tp / (tp + fp) if tp + fp else float("nan")
    out = {"n": int(len(y)), "pos": int(y.sum()), "accuracy": float((k == y).mean()), "balanced_accuracy": float(np.nanmean([rec, spec])),
           "precision": prec, "recall": rec, "f1": (2 * prec * rec / (prec + rec)) if tp else 0.0, "brier": float(np.mean((p - y) ** 2)),
           "tp_fp_fn_tn": [tp, fp, fn, tn], "predicted_pos_rate": float(k.mean()), "observed_pos_rate": float(y.mean())}
    if 0 < y.sum() < len(y):
        lp = np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
        out["calibration_slope"] = float(LogisticRegression(C=1e6).fit(lp.reshape(-1, 1), y).coef_[0, 0])
        out["calibration_in_the_large"] = float(p.mean() - y.mean())
    return out


def evaluate(R, models=MODELS):
    res = {}
    for k in LEADS:
        for sp in SPLITS:
            g = R[(R["lead"] == k) & (R["split"] == sp) & R["y"].notna()].dropna(subset=models)
            if not len(g):
                continue
            key = f"L{k}|{sp}"
            res[key] = {"rows": int(len(g)), "quarters": int(g["q"].nunique()), "areas": sorted(g["area"].unique())}
            for m in models:
                e = g[m] - g["y"]
                gp = g.dropna(subset=[f"{m}_pU"])
                res[key][m] = {"mse": float((e ** 2).mean()), "mae": float(e.abs().mean()),
                               "mse_BL": float(((g.loc[g["area"] == "BL", m] - g.loc[g["area"] == "BL", "y"]) ** 2).mean()),
                               "mae_by_area": {a: float(e[g["area"] == a].abs().mean()) for a in AREAS if (g["area"] == a).any()},
                               "above_usual": binm(gp["yU"], gp[f"{m}_pU"]) if len(gp) else None,
                               "above_11.3": binm(gp["y11"], gp[f"{m}_p11"]) if len(gp) else None}
                if m != "RW":
                    d = ((g[m] - g["y"]) ** 2 - (g["RW"] - g["y"]) ** 2).groupby(g["q"]).mean()
                    res[key][m]["vs_RW_mse_dm"] = dm(d, k) | {"ci90": boot_q(d)}
                    dbl = ((g[m] - g["y"]) ** 2 - (g["RW"] - g["y"]) ** 2)[g["area"] == "BL"].groupby(g["q"]).mean()
                    res[key][m]["vs_RW_mse_BL"] = dm(dbl, k)
                    halves = {}
                    for h, (a, b) in {"first": (SPLITS[sp][0], (SPLITS[sp][0] + SPLITS[sp][1]) // 2),
                                      "second": ((SPLITS[sp][0] + SPLITS[sp][1]) // 2 + 1, SPLITS[sp][1])}.items():
                        hh = d[(d.index >= a) & (d.index <= b)]
                        halves[h] = float(hh.mean()) if len(hh) else None
                    res[key][m]["vs_RW_mse_halves"] = halves
    return res


def criteria(ev, k):
    r = ev.get(f"L{k}|TEST")
    if not r:
        return None
    u, rw, mn = r["ULGBM"], r["RW"], r["MEAN"]
    c = {"1_pooled_mse_below_RW_dm_p<0.10": u["vs_RW_mse_dm"]["mean_diff"] < 0 and (u["vs_RW_mse_dm"]["p_one_sided"] or 1) < .10,
         "2_BL_mse_below_RW": u["mse_BL"] < rw["mse_BL"],
         "3_above_usual_brier_below_RW_and_MEAN": u["above_usual"]["brier"] < min(rw["above_usual"]["brier"], mn["above_usual"]["brier"]),
         "4_above_usual_balanced_ge_RW": u["above_usual"]["balanced_accuracy"] >= rw["above_usual"]["balanced_accuracy"],
         "5_mse_gain_in_both_halves": all(v is not None and v < 0 for v in u["vs_RW_mse_halves"].values())}
    return c | {"passes": all(c.values())}


def main():
    proto = L.E114 / "PROTOCOL_E114.md"
    assert hashlib.sha256(proto.read_bytes()).hexdigest() == (L.HERE / "PROTOCOL_SHA256.txt").read_text().strip(), "protocol changed"
    L.OUT.mkdir(exist_ok=True)
    res = {"protocol_sha256": hashlib.sha256(proto.read_bytes()).hexdigest(),
           "data_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(L.DATA.glob("*.csv"))}}
    R = build_rows()
    R["RW"], R["MEAN"] = R["h_last"], R["mean_known"]
    R["DAMP"] = R["mean_known"] + 0.5 ** R["lead"] * (R["h_last"] - R["mean_known"])
    P = rolling(R)
    R = R.merge(P, on=["area", "t", "lead"], how="left")
    # leakage checks
    rr = L.rounds()

    def used_ok(a, t, q, h):
        g = rr[(rr["area"] == a) & (rr["q"] == q) & (rr["published"] < L.issue(int(t)))]
        return len(g) > 0 and abs(float(g["H"].mean()) - h) < 1e-9          # only rounds published before the issue

    res["leakage"] = {"train_targets_published_before_issue": bool((P["train_max_pub"] < [L.issue(int(t)) for t in P["t"]]).all()),
                      "latest_reading_published_before_issue": bool(all(used_ok(a, t, q, h) for a, t, q, h in zip(R["area"], R["t"], R["q_last"], R["h_last"]))),
                      "usual_and_mean_from_known_readings_only": "by construction (e114_lib.known keeps rounds published < issue)"}
    assert res["leakage"]["train_targets_published_before_issue"] and res["leakage"]["latest_reading_published_before_issue"]
    R = add_probabilities(R)
    R.to_csv(L.OUT / "e114_rows.csv", index=False, lineterminator="\n", float_format="%.6g")
    ev = evaluate(R)
    res["evaluation"] = ev
    res["criteria"] = {k: criteria(ev, k) for k in LEADS}
    res["config_counts"] = P["cfg"].value_counts().to_dict()
    print("criteria", json.dumps(res["criteria"], indent=1), flush=True)
    for key, v in ev.items():
        print(key, v["rows"], v["quarters"], {m: (round(v[m]["mse"], 2), round(v[m]["above_usual"]["brier"], 3) if v[m]["above_usual"] else None) for m in MODELS}, flush=True)
    # ablation on TEST origins (refit without each group)
    test_origins = sorted(R.loc[R["split"] == "TEST", "t"].unique())
    base = R[R["split"] == "TEST"].dropna(subset=["ULGBM", "y"])
    abl = {}
    for gname, gc in GROUPS.items():
        Q = rolling(R, cols=[c for c in FEATS if c not in gc], origins=test_origins, with_ridge=False)
        X = base.merge(Q[["area", "t", "lead", "ULGBM"]].rename(columns={"ULGBM": "X"}), on=["area", "t", "lead"])
        abl[gname] = {}
        for k in LEADS:
            g = X[X["lead"] == k]
            d = ((g["X"] - g["y"]) ** 2 - (g["ULGBM"] - g["y"]) ** 2).groupby(g["q"]).mean()
            dd = dm(-d, k)                                              # H1: removing the group raises MSE
            abl[gname][k] = {"delta_mse_removed_minus_full": float(d.mean()), "ci90": boot_q(d), "p_group_helps": dd["p_one_sided"]}
        print("ablation", gname, {k: round(v["delta_mse_removed_minus_full"], 3) for k, v in abl[gname].items()}, flush=True)
    for k in LEADS:
        ps = {g: abl[g][k]["p_group_helps"] or 1.0 for g in GROUPS}
        items, run, hp = sorted(ps.items(), key=lambda kv: kv[1]), 0.0, {}
        for i, (g, p) in enumerate(items):
            run = max(run, min(1.0, (len(items) - i) * p))
            hp[g] = run
        for g in GROUPS:
            abl[g][k]["holm_p"] = hp[g]
    res["ablation_TEST"] = abl
    # robustness: train on pre-2013 targets only, for TEST rows
    Q = rolling(R, origins=test_origins, with_ridge=False, train_filter=lambda tr: tr["q"] <= L.qi("2012-Q4"))
    X = base.merge(Q[["area", "t", "lead", "ULGBM"]].rename(columns={"ULGBM": "X"}), on=["area", "t", "lead"])
    res["robust_train_pre2013_only"] = {k: {"mse": float(((X.loc[X["lead"] == k, "X"] - X.loc[X["lead"] == k, "y"]) ** 2).mean()),
                                            "mse_RW": float(((X.loc[X["lead"] == k, "RW"] - X.loc[X["lead"] == k, "y"]) ** 2).mean()),
                                            "mse_full": float(((X.loc[X["lead"] == k, "ULGBM"] - X.loc[X["lead"] == k, "y"]) ** 2).mean())} for k in LEADS}
    # robustness: pre-2021 publication = month end + 100 days
    L.set_sample("b", file="sws_area_rounds_full_lag100.csv")
    R2 = build_rows()
    R2["RW"] = R2["h_last"]
    Q2 = rolling(R2, origins=test_origins, with_ridge=False)
    X2 = R2[R2["split"] == "TEST"].merge(Q2[["area", "t", "lead", "ULGBM"]], on=["area", "t", "lead"]).dropna(subset=["y"])
    res["robust_lag100"] = {k: {"mse": float(((X2.loc[X2["lead"] == k, "ULGBM"] - X2.loc[X2["lead"] == k, "y"]) ** 2).mean()),
                                "mse_RW": float(((X2.loc[X2["lead"] == k, "RW"] - X2.loc[X2["lead"] == k, "y"]) ** 2).mean()),
                                "rows": int((X2["lead"] == k).sum())} for k in LEADS}
    (L.OUT / "e114_results.json").write_text(json.dumps(res, indent=1, default=float))
    print("robust", res["robust_train_pre2013_only"], res["robust_lag100"])


if __name__ == "__main__":
    sys.exit(main())
