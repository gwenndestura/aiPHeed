"""
E162 provincial priority, per docs/e162/CRITERIA.md (fixed before results).

    python -m app.e162.rank
"""
from __future__ import annotations

import json
import warnings
from itertools import combinations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import kendalltau, spearmanr

from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e160 import arms as A
from app.fi5.target import qlabel
from app.paths import BACKEND_DIR

warnings.filterwarnings("ignore")
D = BACKEND_DIR / "data"
OUT = D / "e162" / "out"
ARMS = ["E158", "RP", "OH", "FH", "SS"]
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
pct = lambda y: 100 / (1 + np.exp(-np.asarray(y, float)))


def ss(S, rel, te, tr, remap=None):
    """Pv.small_area, SS arm only; remap gives a province another province's survey history for the forecast (shuffled control)."""
    b = S.base[S.base["survey"].isin(rel)].copy()
    psa = pd.concat([tr[["key", "p_poverty"]], te[["key", "p_poverty"]]]).groupby("key")["p_poverty"].mean().dropna()
    b["x"] = b["key"].map(psa)
    b["x"] = b["x"].fillna(b["x"].mean()).fillna(0.0)
    X = np.column_stack([np.ones(len(b)), b["x"]])
    w = np.sqrt(1 / (b["se_y"].values ** 2 + 0.1))
    beta = np.linalg.lstsq(X * w[:, None], b["y"].values * w, rcond=None)[0]
    res = b["y"].values - X @ beta
    su2 = max(0.01, float(np.mean(res ** 2 - b["se_y"].values ** 2)))
    xbar = float(b["x"].mean())
    prior = lambda k: float(beta[0] + beta[1] * psa.get(k, xbar))
    best, bq = np.inf, 0.0
    groups = {k: g.sort_values("year") for k, g in b.groupby("key")}
    for q in (0.0, 0.005, 0.01, 0.02, 0.05, 0.1):
        ll = 0.0
        for k, g in groups.items():
            for j in range(1, len(g)):
                m, v = Pv._kalman(g.iloc[:j], q, prior(k), su2, float(g["year"].iloc[j]))
                s = v + g["se_y"].iloc[j] ** 2
                ll += 0.5 * (np.log(s) + (g["y"].iloc[j] - m) ** 2 / s)
        if ll < best:
            best, bq = ll, q
    mu, var = [], []
    for k, t in zip(te["key"], te["T"].values):
        g = groups.get((remap or {}).get(k, k))
        m, v = Pv._kalman(g, bq, prior(k), su2, float(t) / 4.0) if g is not None else (prior(k), su2)
        mu.append(m)
        var.append(v)
    return np.array(mu), np.array(var), bq


def task(survey, seeds):
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    S = Pv.Store2(None)
    i = M8.RQ[survey] - 1
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN[survey])
    tg = Ev.targets_2021(S) if survey == "ENNS2021" else M8.targets(S.s8, [survey])
    te = Pv.add_inputs(S, M.rows_for(S, tg, [1], Pv.ORIGIN[survey]))
    tr = Pv.add_inputs(S, P.tr)
    out = te[["key", "survey"]].copy()
    out["mu_SS_check"], _, _ = ss(S, P.rel, te, tr)
    b = S.base[S.base["survey"].isin(P.rel)].drop_duplicates("key")[["key", "region"]]
    for sd in seeds:
        r = np.random.default_rng(sd)
        remap = {}
        for _, g in b.groupby("region"):
            k = g["key"].values
            remap.update(dict(zip(k, r.permutation(k))))
        out[f"mu_SS_shuf{sd}"], _, _ = ss(S, P.rel, te, tr, remap)
    return out


def pairs(x, arms):
    rows = []
    for (s, r), g in x.groupby(["survey", "region"]):
        for a, b in combinations(g.index, 2):
            dy = x.at[a, "y_true"] - x.at[b, "y_true"]
            if dy == 0:
                continue
            o = {"cluster": f"{s}|{r}", "survey": s, "region": r, "a": x.at[a, "province"], "b": x.at[b, "province"]}
            for k in arms:
                d = x.at[a, f"mu_{k}"] - x.at[b, f"mu_{k}"]
                o[k] = 0.5 if d == 0 else float(np.sign(d) == np.sign(dy))
            rows.append(o)
    return pd.DataFrame(rows)


def boot(P, cols, rng, n=2000):
    cl = P["cluster"].unique()
    by = {c: P[P["cluster"] == c] for c in cl}
    bs = {c: [] for c in cols}
    for _ in range(n):
        S = pd.concat([by[c] for c in rng.choice(cl, len(cl))])
        for c in cols:
            bs[c].append(S[c].mean())
    return {c: {"est": round(float(P[c].mean()), 3), "ci95": [round(float(np.percentile(bs[c], 2.5)), 3), round(float(np.percentile(bs[c], 97.5)), 3)]} for c in cols}


def rank_measures(x, arms):
    P = pairs(x, arms)
    c = boot(P, arms, np.random.default_rng(159))
    spk = {s: {k: {"spearman": round(float(spearmanr(g[f"mu_{k}"], g["y_true"]).correlation), 3), "kendall": round(float(kendalltau(g[f"mu_{k}"], g["y_true"]).correlation), 3)} for k in arms} for s, g in x.groupby("survey")}
    top, pos = {k: [] for k in arms}, {k: [] for k in arms}
    for _, g in x.groupby(["survey", "region"]):
        n = len(g)
        if n >= 2:
            ro = g["y_true"].rank(ascending=False)
            for k in arms:
                pos[k].append(float(np.mean(np.abs(g[f"mu_{k}"].rank(ascending=False) - ro)) / (n - 1)))
        if n >= 3:
            for k in arms:
                top[k].append(int(g[f"mu_{k}"].idxmax() == g["y_true"].idxmax()))
    per = {s: {k: round(float(g[k].mean()), 3) for k in arms} | {"pairs": int(len(g))} for s, g in P.groupby("survey")}
    return P, {"pairs": int(len(P)), "clusters": int(P["cluster"].nunique()), "concordance": c, "per_round_concordance": per, "spearman_kendall": spk,
               "top_hit": {k: f"{sum(v)}/{len(v)}" for k, v in top.items()}, "position_error": {k: round(float(np.mean(v)), 3) for k, v in pos.items()}}


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    F = pd.read_csv(D / "e160" / "out" / "oof_arms.csv")
    G = pd.read_csv(D / "e151" / "out" / "prov_oof.csv")[["key", "survey", "lead", "mu_SS", "SS", "mu_FH", "FH"]]
    x = F[F["lead"] == 1].merge(G[G["lead"] == 1], on=["key", "survey", "lead"]).reset_index(drop=True)
    assert len(x) == 72
    res = {}
    P, res["ranking"] = rank_measures(x, ARMS)
    P.to_csv(OUT / "pairs.csv", index=False, lineterminator="\n")

    # nested selection on concordance
    hits, picks = [], {}
    for s in sorted(x["survey"].unique()):
        trn, tst = P[P["survey"] != s], P[P["survey"] == s]
        best = max(ARMS, key=lambda a: trn[a].mean())
        picks[s] = best
        hits += list(tst[best].values)
    best_single = max(ARMS, key=lambda a: P[a].mean())
    res["nested"] = {"picks": picks, "nested_concordance": round(float(np.mean(hits)), 3), "best_single": best_single, "best_single_concordance": round(float(P[best_single].mean()), 3), "OVERFIT_SELECTION": bool(P[best_single].mean() - np.mean(hits) > 0.05)}

    # shuffled history control
    Sh = pd.concat(Parallel(n_jobs=3)(delayed(task)(s, (1, 2, 3)) for s in ("ENNS2018", "ENNS2019", "ENNS2021")), ignore_index=True)
    m = x.merge(Sh, on=["key", "survey"])
    res["ss_reproduced_max_abs_diff"] = float(np.max(np.abs(m["mu_SS"] - m["mu_SS_check"])))
    sh = {}
    for sd in (1, 2, 3):
        y = m.assign(**{f"mu_SH{sd}": m[f"mu_SS_shuf{sd}"]})
        sh[sd] = pairs(y, ["SS", f"SH{sd}"])
    Q = sh[1][["cluster", "survey", "SS"]].copy()
    Q["SH"] = np.mean([sh[sd][f"SH{sd}"].values for sd in (1, 2, 3)], axis=0)
    Q["diff"] = Q["SS"] - Q["SH"]
    res["shuffled_control"] = boot(Q, ["SS", "SH", "diff"], np.random.default_rng(162))

    l = res["ranking"]
    g = {"P1": l["concordance"]["SS"]["ci95"][0] > 0.5, "P2": all(v["SS"]["spearman"] > 0 for v in l["spearman_kendall"].values()), "P3": all(v["SS"] >= 0.5 for v in l["per_round_concordance"].values()), "P4": res["shuffled_control"]["diff"]["ci95"][0] > 0}
    g["all"] = all(g.values())
    res["gates_SS"] = g

    # bias
    rng = np.random.default_rng(162)
    nrounds = x["key"].map(pd.read_csv(D / "e160" / "out" / "oof_arms.csv").groupby("key")["survey"].nunique())
    hist = Pv.target_rows()
    hist["rq"] = hist["survey"].map(M8.RQ)
    x["n_released"] = [int(((hist["key"] == k) & (hist["rq"] + M8.Pn.ANCHOR_LAG <= M8.RQ[s] - 1)).sum()) for k, s in zip(x["key"], x["survey"])]
    med = x["gap_q"].median()
    grp = {"island:Luzon": x["island"] == "Luzon", "island:Visayas": x["island"] == "Visayas", "island:Mindanao": x["island"] == "Mindanao", "observed:HIGH": x["y_high"] == 1, "observed:LOW": x["y_high"] == 0,
           "released_rounds<=2": x["n_released"] <= 2, "released_rounds>=3": x["n_released"] >= 3, "survey_older": x["gap_q"] > med, "survey_newer": x["gap_q"] <= med}
    bias = {}
    for a in ("E158", "SS"):
        e = pd.Series(pct(x[f"mu_{a}"]) - pct(x["y_true"]))
        bb = {}
        for name, mk in grp.items():
            mk = mk.values
            if mk.sum() == 0:
                bb[name] = {"n": 0, "flag": "empty"}
                continue
            ev, rg = e.values[mk], x["region"].values[mk]
            gs = list(pd.Series(range(len(ev))).groupby(rg).indices.values())
            v = [np.mean(ev[np.concatenate([gs[j] for j in rng.integers(0, len(gs), len(gs))])]) for _ in range(2000)]
            ci = [round(float(np.percentile(v, 2.5)), 2), round(float(np.percentile(v, 97.5)), 2)]
            bb[name] = {"n": int(mk.sum()), "mean_signed_error_pts": round(float(np.mean(ev)), 2), "ci95": ci, "flag": "too small" if mk.sum() < 10 else ("BIAS" if (ci[0] > 0 or ci[1] < 0) and abs(np.mean(ev)) > 3 else "not shown")}
        bias[a] = bb
    # ranking error by group: concordance of pairs touching an older/fewer-round province
    old = set(x.loc[x["gap_q"] > med, "province"] + "|" + x.loc[x["gap_q"] > med, "survey"])
    P["touches_older"] = [(f"{a}|{s}" in old) or (f"{b}|{s}" in old) for a, b, s in zip(P["a"], P["b"], P["survey"])]
    bias["pair_concordance_by_survey_age"] = {str(k): {a: round(float(g_[a].mean()), 3) for a in ARMS} | {"pairs": int(len(g_))} for k, g_ in P.groupby("touches_older")}
    res["bias"] = bias
    res["calabarzon_pairs"] = P[P["region"] == "CALABARZON"].to_dict("records")
    res["n_released_by_row"] = x[["province", "survey", "n_released", "gap_q"]].to_dict("records")

    # live 2027-Q1
    from app.e160.trace import build
    S, Pp, tr, m_, te = build()
    mu, var, bq = ss(S, Pp.rel, te, tr)
    r = np.random.default_rng(162)
    draw = mu[None, :] + r.standard_normal((10000, len(te))) * np.sqrt(var)[None, :]
    top = np.bincount(draw.argmax(axis=1), minlength=len(te)) / 10000
    E = pd.read_csv(D / "e160" / "out" / "live_arms_2027-Q1.csv")
    e158 = E[E["arm"] == "E158"].set_index("province")
    live = [{"province": te["province"].iloc[k], "SS_level": round(float(pct(mu[k])), 1), "SS_90": [round(float(pct(mu[k] - 1.645 * np.sqrt(var[k]))), 1), round(float(pct(mu[k] + 1.645 * np.sqrt(var[k]))), 1)], "SS_p_highest": round(float(top[k]), 3),
             "E158_score": float(e158.at[te["province"].iloc[k], "score"]), "E158_class": e158.at[te["province"].iloc[k], "class"], "E158_p_highest": float(e158.at[te["province"].iloc[k], "p_highest"])} for k in range(len(te))]
    res["live_2027Q1"] = {"q_per_year": bq, "rows": live}
    method = "SS" if g["all"] else "E158"
    pq = {r_["province"]: (r_["SS_p_highest"] if method == "SS" else r_["E158_p_highest"]) for r_ in live}
    lead_p = max(pq, key=pq.get)
    res["display"] = {"priority_method": method, "most_likely_highest": lead_p, "p": pq[lead_p], "rank_first_shown": bool(g["all"] and pq[lead_p] >= 0.80), "note": "condition (c), direct comparative evidence, is assessed in the report"}

    # LGU: v2 kept; poverty-only sensitivity
    v2 = pd.read_csv(D / "e160" / "out" / "lgu_priority_v2_2027-Q1.csv")
    sens = v2.sort_values(["tier", "pct_poverty"], ascending=[True, False], kind="mergesort").reset_index(drop=True)
    sens["sensitivity_rank"] = np.arange(1, len(sens) + 1)
    sens.to_csv(OUT / "lgu_poverty_only_sensitivity.csv", index=False, lineterminator="\n")
    res["lgu"] = {"v2_top20_by_province": v2.head(20)["province_name"].value_counts().to_dict(), "poverty_only_top20_by_province": sens.head(20)["province_name"].value_counts().to_dict(),
                  "poverty_only_top10": sens.head(10)[["lgu_name", "province_name", "poverty_incidence_2021"]].to_dict("records")}
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    run()
