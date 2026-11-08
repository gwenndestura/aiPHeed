"""E13 Amendment 1 runner. Implements EXPERIMENT_PROTOCOL_AMENDMENT_1.md (frozen; hash checked first).

Reads the sealed v1 forecasts (runs/20261013T022702Z/predictions.csv) and the E13 allowlisted inputs through the
E13 guard. Does not modify e13_lib.py, run_e13.py or any v1 run output.
Usage: python -B runner/run_amendment1.py [--deliverables]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "21")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import e13_lib as L  # noqa: E402
import loaders  # noqa: E402

EXP = guard.EXP
V1_RUN = EXP / "runs" / "20261013T022702Z"
V1_PRED_SHA = "868581d5196f576d1e225d8ef5ac24cba6b15172267db81cbee3a6769ef4654e"
V1_PROTOCOL_SHA = "c379c039847d37208d931803219ec1d88b8406f45a614cd71b65f2775c2519f3"
LGBM_PARAMS = dict(n_estimators=100, learning_rate=0.05, num_leaves=4, min_child_samples=5, reg_lambda=0.0,
                   subsample=1.0, colsample_bytree=1.0, random_state=0, deterministic=True, n_jobs=1, verbose=-1)

BASELINES = {"A": ["A_cf", "A_mean", "A_drift"],
             "B1": ["B1_cf", "B1_regional", "B1_mean", "B1_pmean", "B1_drift"],
             "B2": ["B2_zero", "B2_cf", "B2_pmean"]}
V1_CANDS = {"A": ["A_ridge_H", "A_ridge_HF"], "B1": ["B1_ridge_F", "B1_ridge_FR", "B1_tree"],
            "B2": ["B2_ridge_D", "B2_ridge_DP", "B2_tree"]}
A1_CANDS = {"A": [], "B1": ["B1_lgbm"], "B2": ["B2_lgbm"]}
DESC = {"A_drift": "H_last + g*H_age (training-only average quarterly change)",
        "B1_drift": "F[p,T-2] + 2*g_p (province average quarterly change 2021-Q1..T-2)",
        "B1_lgbm": "LightGBM fixed config (F_lag2, F5_lag2) - exploratory, not selectable",
        "B2_lgbm": "LightGBM fixed config (D_lag2, Dbar_p) - exploratory, not selectable"}
STEPS = {"A": ["A_cf", "A_ridge_H", "A_ridge_HF"],
         "B1": ["B1_cf", "B1_ridge_F", "B1_ridge_FR", "B1_tree", "B1_lgbm"],
         "B2": ["B2_cf", "B2_ridge_D", "B2_ridge_DP", "B2_tree", "B2_lgbm"]}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jdefault(o):
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    raise TypeError(type(o))


def lgbm_fit_predict(Xtr, ytr, Xte):
    from lightgbm import LGBMRegressor
    m = LGBMRegressor(**LGBM_PARAMS).fit(Xtr, ytr)
    return m.predict(Xte)


# ============================================================================ new arms (primary, lag 2)
def a_drift(rounds, comp, T, h_last_value, h_age):
    qv = L.quarter_values(rounds, as_of=L.origin(T))
    c = qv[(qv["complete_as_of"]) & (qv["quarter"].map(L.qi) < L.qi(T))]
    if len(c) < 2:
        return np.nan
    first, last = c.iloc[0], c.iloc[-1]
    g = (last["H_visible"] - first["H_visible"]) / (L.qi(last["quarter"]) - L.qi(first["quarter"]))
    return float(h_last_value + g * h_age)


def new_arms_primary(rounds, comp, v1A, v1B, Ts_A=None, Ts_B=None):
    rows = []
    for T in (Ts_A if Ts_A is not None else sorted(v1A["quarter"].unique(), key=L.qi)):
        fe = L.a_features(rounds, comp, T)
        rows.append({"target": "A", "quarter": T, "province_code": "REGION", "arm": "A_drift",
                     "forecast": a_drift(rounds, comp, T, fe["H_last"], fe["H_age_quarters"])})
    for T in (Ts_B if Ts_B is not None else sorted(v1B["quarter"].unique(), key=L.qi)):
        fe = L.b_features(comp, T).reset_index(drop=True)
        lag = L.qs(L.qi(T) - 2)
        first = comp[comp["quarter"] == "2021-Q1"].set_index("province_code")["F"]
        steps = L.qi(lag) - L.qi("2021-Q1")
        tr = L.b_training(comp, T)
        trF = tr.dropna(subset=["F_lag2", "F5_lag2", "F"])
        trD = tr.dropna(subset=["D_lag2", "Dbar_p", "D"])
        pF = lgbm_fit_predict(trF[["F_lag2", "F5_lag2"]].to_numpy(float), trF["F"].to_numpy(float),
                              fe[["F_lag2", "F5_lag2"]].to_numpy(float))
        pD = lgbm_fit_predict(trD[["D_lag2", "Dbar_p"]].to_numpy(float), trD["D"].to_numpy(float),
                              fe[["D_lag2", "Dbar_p"]].to_numpy(float))
        for i, r in fe.iterrows():
            pc = r["province_code"]
            g = (r["F_lag2"] - first[pc]) / steps
            rows.append({"target": "B1", "quarter": T, "province_code": pc, "arm": "B1_drift",
                         "forecast": float(r["F_lag2"] + 2 * g)})
            rows.append({"target": "B1", "quarter": T, "province_code": pc, "arm": "B1_lgbm", "forecast": float(pF[i])})
            rows.append({"target": "B2", "quarter": T, "province_code": pc, "arm": "B2_lgbm", "forecast": float(pD[i])})
    return pd.DataFrame(rows)


# ============================================================================ S-T3 (inputs and training targets <= T-3)
def b_features_lag(comp, T, lag):
    lq = L.qs(L.qi(T) - lag)
    hist = comp[comp["quarter"].map(L.qi) <= L.qi(lq)]
    cur = comp[comp["quarter"] == lq].set_index("province_code")
    out = []
    for pc in L.PROVINCES:
        h = hist[hist["province_code"] == pc]
        out.append({"province_code": pc, "F_lag": cur["F"].get(pc, np.nan), "D_lag": cur["D"].get(pc, np.nan),
                    "F5_lag": cur["mean5"].get(pc, np.nan), "Fbar_p": h["F"].mean(), "Dbar_p": h["D"].mean()})
    return pd.DataFrame(out)


def b_training_lag(comp, T, lag):
    first = L.qi("2021-Q1") + lag
    rows = []
    for i in range(first, L.qi(T) - lag + 1):          # training targets q <= T-lag
        q = L.qs(i)
        f = b_features_lag(comp, q, lag)
        y = comp[comp["quarter"] == q].set_index("province_code")
        f["quarter"] = q
        f["F"] = f["province_code"].map(y["F"])
        f["D"] = f["province_code"].map(y["D"])
        rows.append(f)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def st3_forecasts(comp, Ts=None, lag=3):
    allq = sorted(comp["quarter"].unique(), key=L.qi)
    cand = [q for q in allq if L.qi(q) >= L.qi("2023-Q2")] if Ts is None else Ts
    rows, skipped = [], {}
    for T in cand:
        tr = b_training_lag(comp, T, lag)
        ntq = int(tr["quarter"].nunique()) if len(tr) else 0
        if ntq < L.MIN_TRAIN_QUARTERS:
            skipped[T] = f"{ntq} training quarters (< {L.MIN_TRAIN_QUARTERS})"
            continue
        fe = b_features_lag(comp, T, lag)
        first = comp[comp["quarter"] == "2021-Q1"].set_index("province_code")["F"]
        steps = L.qi(T) - lag - L.qi("2021-Q1")
        fc = {"B1_cf": fe["F_lag"].to_numpy(float), "B1_regional": fe["F5_lag"].to_numpy(float),
              "B1_mean": np.full(5, tr["F"].mean()), "B1_pmean": fe["Fbar_p"].to_numpy(float),
              "B1_drift": (fe["F_lag"] + lag * (fe["F_lag"] - fe["province_code"].map(first)) / steps).to_numpy(float),
              "B2_zero": np.zeros(5), "B2_cf": fe["D_lag"].to_numpy(float), "B2_pmean": fe["Dbar_p"].to_numpy(float)}
        fc["B1_ridge_F"], _ = L.ridge_fit_predict(tr[["F_lag"]].to_numpy(float), tr["F"].to_numpy(float),
                                                  fe[["F_lag"]].to_numpy(float))
        fc["B1_ridge_FR"], _ = L.ridge_fit_predict(tr[["F_lag", "F5_lag"]].to_numpy(float), tr["F"].to_numpy(float),
                                                   fe[["F_lag", "F5_lag"]].to_numpy(float))
        fc["B2_ridge_D"], _ = L.ridge_fit_predict(tr[["D_lag"]].to_numpy(float), tr["D"].to_numpy(float),
                                                  fe[["D_lag"]].to_numpy(float))
        fc["B2_ridge_DP"], _ = L.ridge_fit_predict(tr[["D_lag", "Dbar_p"]].to_numpy(float), tr["D"].to_numpy(float),
                                                   fe[["D_lag", "Dbar_p"]].to_numpy(float))
        for i, r in fe.iterrows():
            for arm, v in fc.items():
                rows.append({"target": arm[:2], "quarter": T, "province_code": r["province_code"], "arm": arm,
                             "forecast": float(v[i]), "lag_value": float(r["F_lag"] if arm.startswith("B1") else r["D_lag"]),
                             "n_train_quarters": ntq})
    return pd.DataFrame(rows), skipped


def perturb_check(rounds, comp, new, st3):
    res = {"primary": {}, "S-T3": {}}
    for T in sorted(new["quarter"].unique(), key=L.qi):
        r2 = rounds.copy()
        r2.loc[r2["published"] >= L.origin(T), "H"] = 999.0
        c2 = comp.copy()
        c2.loc[c2["quarter"].map(L.qi) >= L.qi(T) - 1, ["F", "mean5", "D", "H", "S1"]] = 999.0
        tA = [T] if (new["target"].eq("A") & new["quarter"].eq(T)).any() else []
        tB = [T] if (new["target"].ne("A") & new["quarter"].eq(T)).any() else []
        p2 = new_arms_primary(r2, c2, None, None, Ts_A=tA, Ts_B=tB)
        a = new[new["quarter"] == T].sort_values(["target", "province_code", "arm"])["forecast"].to_numpy()
        b = p2.sort_values(["target", "province_code", "arm"])["forecast"].to_numpy()
        res["primary"][T] = bool(np.array_equal(a, b, equal_nan=True))
    for T in sorted(st3["quarter"].unique(), key=L.qi):
        c2 = comp.copy()
        c2.loc[c2["quarter"].map(L.qi) >= L.qi(T) - 2, ["F", "mean5", "D", "H", "S1"]] = 999.0
        p2, _ = st3_forecasts(c2, [T])
        a = st3[st3["quarter"] == T]["forecast"].to_numpy()
        res["S-T3"][T] = bool(np.array_equal(a, p2["forecast"].to_numpy(), equal_nan=True))
    if not all(res["primary"].values()) or not all(res["S-T3"].values()):
        raise RuntimeError(f"E13-A1: future-perturbation check failed: {res}")
    return res


# ============================================================================ evaluation
def events(target, y, f, lagv):
    out = {}
    if target == "A":
        out["increase_vs_H_last"] = (y > lagv, f > lagv, f - lagv)
    elif target == "B1":
        out["above_4pct"] = (y > L.F_EVENT_THRESHOLD, f > L.F_EVENT_THRESHOLD, f)
        out["rising_vs_T-2"] = (y > lagv, f > lagv, f - lagv)
    else:
        out["above_zero"] = (y > 0, f > 0, f)
        out["rising_vs_T-2"] = (y > lagv, f > lagv, f - lagv)
    return out


def evaluate(wide, target, baselines, v1c, a1c, label):
    """wide: one row per (quarter, province_code) with y, lagv and one column per arm."""
    arms = [a for a in baselines + v1c + a1c if a in wide.columns]
    res = {"target": target, "analysis": label, "quarters": sorted(wide["quarter"].unique().tolist(), key=L.qi),
           "n_rows": int(len(wide)), "arms": {}}
    for a in arms:
        m = L.point_metrics(wide["y"], wide[a])
        m["n_quarters"] = int(wide["quarter"].nunique())
        if target != "A":
            taus = [L.kendall_tau(g[a], g["y"]) for _, g in wide.groupby("quarter")]
            taus = [t for t in taus if t is not None]
            m["mean_kendall_tau"] = float(np.mean(taus)) if taus else None
        m["events"] = {}
        for k, (yb, pb, sc) in events(target, wide["y"].to_numpy(float), wide[a].to_numpy(float),
                                      wide["lagv"].to_numpy(float)).items():
            ev = L.classification(yb, pb)
            ev.update(L.auc_scores(yb, sc))
            m["events"][k] = ev
        res["arms"][a] = m
    bases = [a for a in baselines if a in wide.columns]
    best = min(bases, key=lambda a: res["arms"][a]["MAE"])
    res["best_baseline"] = best
    comps, pv = {}, {}
    for mdl in [c for c in v1c + a1c if c in wide.columns]:
        pq = wide.assign(dm=(wide[mdl] - wide["y"]).abs() - (wide[best] - wide["y"]).abs()).groupby("quarter")["dm"].mean()
        pv[mdl] = L.sign_flip_p(pq.to_numpy())
        loqo = [bool((w[mdl] - w["y"]).abs().mean() < (w[best] - w["y"]).abs().mean())
                for q in res["quarters"] for w in [wide[wide["quarter"] != q]]]
        comps[mdl] = {"vs_best": L.cluster_bootstrap_mae_diff(wide[["quarter", "y", mdl, best]], mdl, best),
                      "vs_all": {b: L.cluster_bootstrap_mae_diff(wide[["quarter", "y", mdl, b]], mdl, b) for b in bases},
                      "quarters_better": int((pq < 0).sum()), "quarters_total": int(len(pq)), "loqo_better": loqo,
                      "p_signflip": pv[mdl], "family": "v1" if mdl in v1c else "A1 (exploratory)"}
    ph_v1 = L.holm({k: v for k, v in pv.items() if k in v1c}) if any(k in v1c for k in pv) else {}
    ph_all = L.holm(pv) if pv else {}
    for mdl, c in comps.items():
        c["p_holm_v1_family"] = ph_v1.get(mdl)
        c["p_holm_with_lgbm"] = ph_all.get(mdl)
        p_rule = c["p_holm_v1_family"] if mdl in v1c else c["p_holm_with_lgbm"]
        c["cond1"] = all(res["arms"][mdl]["MAE"] < res["arms"][b]["MAE"] for b in bases)
        c["cond2"] = c["vs_best"]["ci_high"] < 0
        c["cond3"] = p_rule < 0.05
        c["cond4"] = all(c["loqo_better"])
        c["all_conditions"] = bool(c["cond1"] and c["cond2"] and c["cond3"] and c["cond4"])
        c["selectable"] = mdl in v1c
    res["comparisons"] = comps
    # feature increments
    inc = []
    st = [s for s in STEPS[target] if s in wide.columns]
    for prev, nxt in zip(st[:-1], st[1:]):
        if nxt in ("B1_lgbm", "B2_lgbm"):
            prev = st[st.index(nxt) - 2] if nxt.endswith("lgbm") else prev   # lgbm compared with the ridge it extends
        bt = L.cluster_bootstrap_mae_diff(wide[["quarter", "y", nxt, prev]], nxt, prev)
        pq = wide.assign(dm=(wide[nxt] - wide["y"]).abs() - (wide[prev] - wide["y"]).abs()).groupby("quarter")["dm"].mean()
        inc.append({"from": prev, "to": nxt, **bt, "quarters_better": int((pq < 0).sum())})
    res["feature_increments"] = inc
    # stability: halves
    qs = res["quarters"]
    k = len(qs) // 2 if target != "A" else 4
    halves = {"first": qs[:k if target == "A" else 5], "second": qs[(k if target == "A" else 5):]}
    stab = {}
    cf = {"A": "A_cf", "B1": "B1_cf", "B2": "B2_cf"}[target]
    for h, hq in halves.items():
        w = wide[wide["quarter"].isin(hq)]
        stab[h] = {"quarters": hq, "MAE": {a: float((w[a] - w["y"]).abs().mean()) for a in arms}}
    stab["better_than_cf_in_both_halves"] = {a: bool(stab["first"]["MAE"][a] < stab["first"]["MAE"][cf]
                                                     and stab["second"]["MAE"][a] < stab["second"]["MAE"][cf])
                                             for a in arms if a != cf}
    res["stability_halves"] = stab
    return res


def ranking_stability(wide, arms):
    out = {}
    qs = sorted(wide["quarter"].unique(), key=L.qi)
    for a in arms + ["y"]:
        t = []
        for q0, q1 in zip(qs[:-1], qs[1:]):
            g0 = wide[wide["quarter"] == q0].set_index("province_code")[a]
            g1 = wide[wide["quarter"] == q1].set_index("province_code")[a].reindex(g0.index)
            v = L.kendall_tau(g0, g1)
            if v is not None:
                t.append(v)
        out[a] = {"mean_consecutive_kendall": float(np.mean(t)) if t else None, "pairs": len(t)}
    return out


def intervals(rounds, comp, wide_A, wide_B1, wide_B2):
    """80% empirical intervals: forecast + [q10, q90] of training errors (y - forecast) at each origin."""
    res, rows = {}, []
    specs = [("A", "A_cf", wide_A), ("B1", "B1_cf", wide_B1), ("B2", "B2_cf", wide_B2),
             ("B2", "B2_ridge_D", wide_B2), ("B2", "B2_ridge_DP", wide_B2)]
    for tgt, arm, w in specs:
        for T, g in w.groupby("quarter"):
            if tgt == "A":
                tr = L.a_training(rounds, comp, T)
                err = (tr["y"] - tr["H_last"]).to_numpy(float)
            else:
                tr = L.b_training(comp, T).dropna(subset=["D_lag2", "Dbar_p", "D", "F_lag2", "F"])
                if arm == "B1_cf":
                    err = (tr["F"] - tr["F_lag2"]).to_numpy(float)
                elif arm == "B2_cf":
                    err = (tr["D"] - tr["D_lag2"]).to_numpy(float)
                else:
                    feats = ["D_lag2"] if arm == "B2_ridge_D" else ["D_lag2", "Dbar_p"]
                    X = tr[feats].to_numpy(float)
                    fit, _ = L.ridge_fit_predict(X, tr["D"].to_numpy(float), X)
                    err = (tr["D"].to_numpy(float) - fit)
            lo, hi = np.quantile(err, 0.10), np.quantile(err, 0.90)
            for r in g.itertuples():
                f = getattr(r, arm)
                rows.append({"target": tgt, "arm": arm, "quarter": T, "province_code": r.province_code,
                             "forecast": f, "lower80": f + lo, "upper80": f + hi, "y": r.y,
                             "covered": bool(f + lo <= r.y <= f + hi), "n_train_errors": int(len(err)),
                             "errors_in_sample": arm.startswith("B2_ridge")})
    df = pd.DataFrame(rows)
    for (tgt, arm), g in df.groupby(["target", "arm"]):
        res[f"{tgt}|{arm}"] = {"coverage": float(g["covered"].mean()), "nominal": 0.80, "n": int(len(g)),
                               "mean_width": float((g["upper80"] - g["lower80"]).mean()),
                               "errors_in_sample": bool(g["errors_in_sample"].iloc[0])}
    return res, df


def regional_vs_provincial(rounds, comp):
    qv = L.quarter_values(rounds).set_index("quarter")["H"]
    m5 = comp.drop_duplicates("quarter").set_index("quarter")["mean5"]
    out = {}
    for lag in (0, 1, 2):
        pairs = [(qv[q], m5.get(L.qs(L.qi(q) - lag))) for q in qv.index if L.qs(L.qi(q) - lag) in m5.index]
        a = pd.DataFrame(pairs, columns=["H", "F5"]).dropna()
        out[f"lag{lag}"] = {"n_quarters": int(len(a)), "pearson": float(a["H"].corr(a["F5"])),
                            "spearman": float(a["H"].rank().corr(a["F5"].rank()))}
    dsum = comp.groupby("quarter")["D"].sum().abs().max()
    out["max_abs_sum_D_per_quarter"] = float(dsum)
    return out


def official_comparison(comp, rounds, ext):
    sub = ext["subsistence"].copy()
    sub["se"] = sub["subsistence_pct"] * sub["subsistence_cv"] / 100
    sub["ci_low_calc"] = sub["subsistence_pct"] - 1.96 * sub["se"]
    sub["ci_high_calc"] = sub["subsistence_pct"] + 1.96 * sub["se"]
    sub["ci_consistent"] = ((sub["ci_low_calc"] - sub["subsistence_ci_low"]).abs() <= 0.15) & \
                           ((sub["ci_high_calc"] - sub["subsistence_ci_high"]).abs() <= 0.15)
    c = comp.copy()
    c["year"] = c["quarter"].str[:4].astype(int)
    ann = c.groupby(["year", "province_code"])[["F", "D"]].mean()
    prov = sub[sub["geographic_level"] == "province"]
    pairs = []
    for y, g in prov.groupby("year"):
        g = g.reset_index(drop=True)
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                a, b = g.iloc[i], g.iloc[j]
                z = (a["subsistence_pct"] - b["subsistence_pct"]) / np.sqrt(a["se"] ** 2 + b["se"] ** 2)
                hi, lo = (a, b) if a["subsistence_pct"] > b["subsistence_pct"] else (b, a)
                dh, dl = ann.loc[(int(y), hi["psgc_code"]), "D"], ann.loc[(int(y), lo["psgc_code"]), "D"]
                fh, fl = ann.loc[(int(y), hi["psgc_code"]), "F"], ann.loc[(int(y), lo["psgc_code"]), "F"]
                pairs.append({"year": int(y), "higher_subsistence": hi["area_name"], "lower_subsistence": lo["area_name"],
                              "diff_pct": float(hi["subsistence_pct"] - lo["subsistence_pct"]), "z": float(abs(z)),
                              "distinguishable": bool(abs(z) >= 1.96),
                              "meanD_higher": float(dh), "meanD_lower": float(dl), "D_concordant": bool(dh > dl),
                              "meanF_higher": float(fh), "meanF_lower": float(fl), "F_concordant": bool(fh > fl)})
    P = pd.DataFrame(pairs)
    dist = P[P["distinguishable"]]
    f = ext["fies"]
    r25 = rounds[rounds["quarter"].str.startswith("2025")]
    return {"ci_check": sub[["year", "area_name", "geographic_level", "subsistence_pct", "subsistence_cv", "se",
                             "subsistence_ci_low", "ci_low_calc", "subsistence_ci_high", "ci_high_calc",
                             "ci_consistent"]].to_dict("records"),
            "pairs": P.to_dict("records"),
            "summary": {"pairs_total": int(len(P)), "pairs_distinguishable": int(len(dist)),
                        "distinguishable_D_concordant": int(dist["D_concordant"].sum()),
                        "distinguishable_F_concordant": int(dist["F_concordant"].sum()),
                        "all_pairs_D_concordant": int(P["D_concordant"].sum())},
            "fies_vs_sws_2025": {"fies_regional_moderate_severe_pct": float(f["fies_moderate_severe_pct"].iloc[0]),
                                 "fies_distinct_values_in_5_rows": int(f["fies_moderate_severe_pct"].nunique()),
                                 "sws_2025_rounds": r25[["quarter", "H", "definition_A"]].to_dict("records"),
                                 "sws_2025_mean": float(r25["H"].mean())}}


def write_csv(df, p):
    df.to_csv(p, index=False, lineterminator="\n", float_format="%.10g")


def main(deliverables: bool):
    frozen = (EXP / "runner" / "PROTOCOL_AMENDMENT_1_SHA256.txt").read_text(encoding="utf-8").split()[0]
    if sha(EXP / "EXPERIMENT_PROTOCOL_AMENDMENT_1.md") != frozen:
        raise SystemExit("E13-A1: amendment differs from its frozen hash; stop.")
    if sha(EXP / "EXPERIMENT_PROTOCOL.md") != V1_PROTOCOL_SHA or sha(V1_RUN / "predictions.csv") != V1_PRED_SHA:
        raise SystemExit("E13-A1: v1 protocol or sealed v1 predictions changed; stop.")
    started = datetime.now(timezone.utc)
    out = EXP / "runs" / f"a1_{started.strftime('%Y%m%dT%H%M%SZ')}"
    out.mkdir(parents=True)
    allow_start = guard.verify_allowlist()
    comp = loaders.load_components()
    rounds = loaders.load_rounds(loaders.load_details())
    ext = loaders.load_external()
    v1 = pd.read_csv(V1_RUN / "predictions.csv", dtype={"province_code": str})
    v1 = v1[(v1["analysis"] == "primary") & (v1["status"] == "OK")]
    v1A, v1B = v1[v1["target"] == "A"], v1[v1["target"] != "A"]

    # ---------------------------------------------------------------- forecasts only (sealed before outcomes)
    new = new_arms_primary(rounds, comp, v1A, v1B)
    st3, st3_skipped = st3_forecasts(comp)
    pert = perturb_check(rounds, comp, new, st3)
    p_a1 = pd.concat([new.assign(analysis="primary"), st3.drop(columns=["lag_value"]).assign(analysis="S-T3")],
                     ignore_index=True)
    p_a1 = p_a1.sort_values(["analysis", "target", "quarter", "province_code", "arm"]).reset_index(drop=True)
    write_csv(p_a1, out / "predictions_a1.csv")
    seal = {"predictions_a1_sha256": sha(out / "predictions_a1.csv"), "sealed_utc": datetime.now(timezone.utc).isoformat(),
            "amendment_sha256": frozen, "v1_predictions_sha256": V1_PRED_SHA, "rows": int(len(p_a1)),
            "note": "Sealed before realized values were joined. All 2021-2025 values were seen in E1-E13 v1."}
    (out / "SEAL_A1.json").write_text(json.dumps(seal, indent=1), encoding="utf-8", newline="\n")

    # ---------------------------------------------------------------- realized values
    qvA = L.quarter_values(rounds).set_index("quarter")["H"]
    cy = comp.set_index(["quarter", "province_code"])
    allp = pd.concat([v1[["target", "quarter", "province_code", "arm", "forecast"]], new], ignore_index=True)
    wides = {}
    for tgt in ["A", "B1", "B2"]:
        d = allp[allp["target"] == tgt]
        w = d.pivot_table(index=["quarter", "province_code"], columns="arm", values="forecast").reset_index()
        lagsrc = v1[(v1["target"] == tgt)].drop_duplicates(["quarter", "province_code"]).set_index(["quarter", "province_code"])
        if tgt == "A":
            w["y"] = w["quarter"].map(qvA)
            w["lagv"] = [lagsrc.loc[(q, p), "H_last"] for q, p in zip(w["quarter"], w["province_code"])]
        else:
            col = "F" if tgt == "B1" else "D"
            w["y"] = [cy.loc[(q, p), col] for q, p in zip(w["quarter"], w["province_code"])]
            w["lagv"] = [lagsrc.loc[(q, p), "F_lag2" if tgt == "B1" else "D_lag2"]
                         for q, p in zip(w["quarter"], w["province_code"])]
        wides[tgt] = w.sort_values(["quarter", "province_code"], key=lambda s: s.map(L.qi) if s.name == "quarter" else s)
    results = {t: evaluate(wides[t], t, BASELINES[t], V1_CANDS[t], A1_CANDS[t], "primary") for t in wides}
    # S-T3 and primary on the same quarters
    st3w = {}
    for tgt in ["B1", "B2"]:
        d = st3[st3["target"] == tgt]
        w = d.pivot_table(index=["quarter", "province_code"], columns="arm", values="forecast").reset_index()
        lv = d.drop_duplicates(["quarter", "province_code"]).set_index(["quarter", "province_code"])["lag_value"]
        col = "F" if tgt == "B1" else "D"
        w["y"] = [cy.loc[(q, p), col] for q, p in zip(w["quarter"], w["province_code"])]
        w["lagv"] = [lv[(q, p)] for q, p in zip(w["quarter"], w["province_code"])]
        st3w[tgt] = w
        results[f"{tgt}|S-T3"] = evaluate(w, tgt, [b for b in BASELINES[tgt]], V1_CANDS[tgt], [], "S-T3")
        same = wides[tgt][wides[tgt]["quarter"].isin(w["quarter"].unique())]
        results[f"{tgt}|primary_on_S-T3_quarters"] = evaluate(same, tgt, BASELINES[tgt], V1_CANDS[tgt], A1_CANDS[tgt],
                                                              "primary_on_S-T3_quarters")
    rank_stab = {t: ranking_stability(wides[t], [a for a in wides[t].columns if a.startswith(t + "_")
                                                 and a not in ("B1_regional", "B1_mean", "B2_zero")])
                 for t in ["B1", "B2"]}
    pi, pi_rows = intervals(rounds, comp, wides["A"], wides["B1"], wides["B2"])
    # consistency: ridge refits inside intervals() reproduce the v1 forecasts
    metrics = {"amendment_sha256": frozen, "predictions_a1_sha256": seal["predictions_a1_sha256"],
               "perturbation_check": pert, "S-T3_skipped": st3_skipped, "results": results,
               "ranking_stability": rank_stab, "prediction_intervals": pi,
               "regional_vs_provincial": regional_vs_provincial(rounds, comp),
               "official_comparison": official_comparison(comp, rounds, ext),
               "lgbm_params": LGBM_PARAMS}
    (out / "metrics_a1.json").write_text(json.dumps(metrics, indent=1, default=jdefault), encoding="utf-8", newline="\n")
    for t, w in wides.items():
        write_csv(w, out / f"scored_wide_{t}.csv")
    for t, w in st3w.items():
        write_csv(w, out / f"scored_wide_{t}_ST3.csv")
    write_csv(pi_rows, out / "prediction_intervals.csv")

    # ---------------------------------------------------------------- comparison tables
    brow, mrow = [], []
    for key, r in results.items():
        for a, m in r["arms"].items():
            ev = m["events"]
            evk = list(ev)[0]
            common = {"protocol": "A1", "target": r["target"], "analysis": r["analysis"], "arm": a,
                      "description": DESC.get(a, ""), "n_rows": m["n"], "n_quarters": m["n_quarters"], "MAE": m["MAE"],
                      "RMSE": m["RMSE"], "bias": m["bias"], "mean_kendall_tau": m.get("mean_kendall_tau"),
                      "MAE_ratio_to_cf": m["MAE"] / r["arms"][{"A": "A_cf", "B1": "B1_cf", "B2": "B2_cf"}[r["target"]]]["MAE"]}
            for k, e in ev.items():
                common[f"event_{k}_BA"] = e["balanced_accuracy"]
                common[f"event_{k}_TP_FP_FN_TN"] = f"{e['TP']}/{e['FP']}/{e['FN']}/{e['TN']}"
            if a in BASELINES[r["target"]]:
                brow.append({**common, "is_best_baseline": a == r["best_baseline"]})
            else:
                c = r["comparisons"][a]
                mrow.append({**common, "family": c["family"], "selectable": c["selectable"],
                             "best_baseline": r["best_baseline"], "MAE_diff_vs_best": c["vs_best"]["diff"],
                             "ci_low": c["vs_best"]["ci_low"], "ci_high": c["vs_best"]["ci_high"],
                             "quarters_better": c["quarters_better"], "quarters_total": c["quarters_total"],
                             "p_signflip": c["p_signflip"], "p_holm_v1_family": c["p_holm_v1_family"],
                             "p_holm_with_lgbm": c["p_holm_with_lgbm"],
                             "loqo_better": f"{sum(c['loqo_better'])}/{len(c['loqo_better'])}",
                             "cond1": c["cond1"], "cond2": c["cond2"], "cond3": c["cond3"], "cond4": c["cond4"],
                             "all_conditions": c["all_conditions"]})
    B, M = pd.DataFrame(brow), pd.DataFrame(mrow)
    write_csv(B, out / "baseline_comparison_a1.csv")
    write_csv(M, out / "model_comparison_a1.csv")
    if deliverables:
        b1 = pd.read_csv(V1_RUN / "baseline_comparison.csv").assign(protocol="v1")
        m1 = pd.read_csv(V1_RUN / "model_comparison.csv").assign(protocol="v1")
        write_csv(pd.concat([b1, B], ignore_index=True), EXP / "BASELINE_COMPARISON.csv")
        write_csv(pd.concat([m1, M], ignore_index=True), EXP / "MODEL_COMPARISON.csv")
    manifest = {"started_utc": started.isoformat(), "finished_utc": datetime.now(timezone.utc).isoformat(),
                "amendment_sha256": frozen, "v1_protocol_sha256": V1_PROTOCOL_SHA, "v1_predictions_sha256": V1_PRED_SHA,
                "allowlist_sha256_start": allow_start, "allowlist_sha256_end": guard.verify_allowlist(),
                "code_sha256": {p.name: sha(p) for p in sorted((EXP / "runner").glob("*.py"))},
                "outputs_sha256": {p.name: sha(p) for p in sorted(out.glob("*")) if p.name != "manifest.json"},
                "deliverables_written": deliverables,
                "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                                "lightgbm": __import__("lightgbm").__version__},
                "access_log": guard.ACCESS_LOG}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")
    print(out)


if __name__ == "__main__":
    main("--deliverables" in sys.argv)
