"""FI12 study: do aiPHeed's provincial outputs agree with independently measured provincial outcomes?

    python -m app.fi12.study lock     # freeze PROTOCOL + code hash before any agreement is computed
    python -m app.fi12.study run      # writes data/fi12/out/*.json|csv

Every outcome is a sparse survey or poverty-statistics cross-section of five provinces, so the analysis is:
  1. measurement: are provinces distinguishable at all (Cochran Q on published SEs) and how well could even a perfect
     predictor rank them against the noisy published value (simulated noise ceiling);
  2. ranking agreement of each matched model and each baseline (Spearman, exact permutation p, top-1 / top-2);
  3. level accuracy (MAE, RMSE, bias) for food poverty only, where repeated waves allow temporal validation;
  4. association of each FI10 trigger-group feature and each FIRI v2 family with the outcomes (descriptive).
No HIGH/LOW label is created unless a province is significantly above the CALABARZON estimate.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

from app.fi12 import OUT, PROVINCES, VERSION
from app.fi12 import match as M
from app.fi12 import outcomes as O
from app.paths import BACKEND_DIR

PROTOCOL = {
    "version": VERSION,
    "outcomes": {k: v[1] for k, v in O.OUTCOMES.items()},
    "primary": {"A": "FNRI15_SEV (only verified direct provincial outcome)", "B": "PSA_SUB_FAM pooled over 2018, 2021, 2023"},
    "matching": "mean of out-of-sample quarterly scores with target quarter in the reference year, per lead 1-4; issue before target quarter; ENNS matched province by province to its own reference year",
    "availability_rule": "a survey value is usable from 1 January of reference year + 2 (conservative)",
    "rank_metrics": "Spearman (average ranks) with exact one-sided permutation p over 120 orders; pooled = mean within-year rho, exact p by convolution; top-1 hit; top-2 overlap",
    "baselines_rank": ["prior wave of the same PSA indicator", "latest provincial poverty incidence available by 1 Jan of the reference year",
                       "FNRI 2015 severe food insecurity (for reference years >= 2017)"],
    "level_candidates": {"L0": "prior wave (persistence)", "L1": "CALABARZON prior-wave value for every province",
                         "L2": "mean of the province's prior waves", "L3": "prior wave shrunk to the regional prior wave by w = tau2/(tau2+se2), tau2 = max(0, var(prior) - mean(se2))",
                         "L4": "ridge alpha=1 on standardized [prior subsistence, prior poverty, FI10 Lead-2 mean price-pressure p] trained on the 2018->2021 transition; 2023 only"},
    "noise": {"simulations": 10000, "seed": 12},
    "classification": "HIGH only if province > CALABARZON with |z| > 1.96 (z uses both SEs); classification metrics only if at least 3 HIGH and 3 LOW exist",
    "decision": {"rank_skill": "exact p < 0.05 and rho above the best baseline on the same observations",
                 "level_skill": "MAE below L0 and L1 in every test wave",
                 "lead_reliable_provincial_fi": "rank skill on a track-A outcome in at least two independent reference years"},
    "features_fi10": {"market": ["f_m", "z_food", "gap_known", "head_m", "rice_m"], "climate": ["rain_anom_3m", "tc_365d", "oni", "palay_yoy"],
                      "employment": ["unemp_rate", "remit_yoy"], "poverty": ["poverty_inc"], "news": ["news_prov_z"]},
    "features_firi_2023": ["val_A3", "val_V1", "val_C1", "val_C2", "val_C3", "val_C4", "val_E1", "val_E2", "val_N1", "val_H1", "A1_food", "A1_gap", "pi_price"],
}


def _digest():
    return hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True).encode()).hexdigest()


def _code():
    return hashlib.sha256(b"".join((BACKEND_DIR / "app" / "fi12" / f).read_bytes().replace(b"\r\n", b"\n")
                                   for f in ("study.py", "outcomes.py", "match.py"))).hexdigest()


# ---------- statistics ----------
def _rank(x):
    return pd.Series(x).rank(method="average").to_numpy()


def spearman(a, b) -> float | None:
    ra, rb = _rank(a), _rank(b)
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def _perm_dist(score, obs) -> np.ndarray:
    rs = _rank(score)
    return np.array([np.corrcoef(rs, _rank(np.array(obs)[list(p)]))[0, 1] for p in itertools.permutations(range(len(obs)))])


def exact_p(score, obs) -> float | None:
    r = spearman(score, obs)
    if r is None:
        return None
    return float(np.mean(_perm_dist(score, obs) >= r - 1e-9))


def pooled_p(pairs) -> tuple[float | None, float | None]:
    """Mean within-year rho and its exact one-sided p (independent within-year permutations)."""
    rs, dists = [], []
    for s, o in pairs:
        r = spearman(s, o)
        if r is None:
            continue
        rs.append(r)
        dists.append(np.round(_perm_dist(s, o), 9))
    if not rs:
        return None, None
    acc = {0.0: 1.0}
    for d in dists:
        vals, cnt = np.unique(d, return_counts=True)
        nxt = {}
        for a, pa in acc.items():
            for v, c in zip(vals, cnt):
                nxt[round(a + v, 9)] = nxt.get(round(a + v, 9), 0) + pa * c / len(d)
        acc = nxt
    m = float(np.mean(rs))
    return m, float(sum(p for v, p in acc.items() if v / len(rs) >= m - 1e-9))


def _top(score, obs, k):
    return len(set(np.argsort(-np.asarray(score))[:k]) & set(np.argsort(-np.asarray(obs))[:k]))


def rank_eval(score, obs) -> dict:
    r = spearman(score, obs)
    return {"n": len(obs), "spearman": r, "p_one_sided": exact_p(score, obs) if r is not None else None,
            "kendall": float(stats.kendalltau(score, obs)[0]) if r is not None else None,
            "top1_hit": int(_top(score, obs, 1)), "top2_overlap": int(_top(score, obs, 2))}


# ---------- measurement ----------
def measurement(T) -> dict:
    rng = np.random.default_rng(PROTOCOL["noise"]["seed"])
    out = {}
    for (oid, y), g in T.groupby(["outcome", "reference_year"]):
        g = g.sort_values("province")
        res = {"n": len(g), "values": dict(zip(g["province"], g["value"])), "se": dict(zip(g["province"], g["se"].round(3)))}
        if len(g) == 5 and g["se"].notna().all():
            w = 1 / g["se"] ** 2
            mu = float((w * g["value"]).sum() / w.sum())
            q = float((w * (g["value"] - mu) ** 2).sum())
            res["cochran_q"], res["q_p"] = q, float(stats.chi2.sf(q, len(g) - 1))
            v, se = g["value"].to_numpy(), g["se"].to_numpy()
            sims = [spearman(v, v + rng.normal(0, se)) for _ in range(PROTOCOL["noise"]["simulations"])]
            tops = [int(np.argmax(v + rng.normal(0, se)) == np.argmax(v)) for _ in range(2000)]
            res["noise_ceiling_rho_median"] = float(np.median(sims))
            res["noise_ceiling_rho_p10_p90"] = [float(np.percentile(sims, 10)), float(np.percentile(sims, 90))]
            res["top1_reproducible_share"] = float(np.mean(tops))
            reg = O.regional(oid, int(y))
            if reg:
                rv, rse = reg
                z = (g["value"] - rv) / np.sqrt(g["se"] ** 2 + (0 if np.isnan(rse) else rse ** 2))
                res["regional"] = {"value": rv, "se": None if np.isnan(rse) else rse}
                res["z_vs_region"] = dict(zip(g["province"], z.round(2)))
                res["significantly_above_region"] = [p for p, zz in zip(g["province"], z) if zz > 1.96]
        out[f"{oid}|{y}"] = res
    return out


# ---------- baselines ----------
def baseline_scores(T) -> pd.DataFrame:
    """Province scores a forecaster could have formed by 1 January of the reference year."""
    pov = O.psa_poverty()
    pov = pov[pov["geo"].isin(PROVINCES)]
    rows = []
    for y in M.YEARS:
        cut = pd.Timestamp(f"{y}-01-01")
        avail = pov[pov["year"].map(lambda w: pd.Timestamp(f"{w + 2}-01-01") <= cut)]
        if len(avail):
            w = avail["year"].max()
            for _, r in avail[avail["year"] == w].iterrows():
                rows.append({"baseline": "poverty_prior", "province": r["geo"], "year": y, "score": r["value"], "from_wave": int(w)})
        for oid in ("PSA_SUB_FAM", "PSA_SUB_POP"):
            prev = T[(T["outcome"] == oid) & (T["reference_year"] < y) & (pd.to_datetime(T["available_from"]) <= cut)]
            if len(prev):
                w = prev["reference_year"].max()
                for _, r in prev[prev["reference_year"] == w].iterrows():
                    rows.append({"baseline": f"prior_wave_{oid}", "province": r["province"], "year": y, "score": r["value"], "from_wave": int(w)})
        if y >= 2017:
            for _, r in T[T["outcome"] == "FNRI15_SEV"].iterrows():
                rows.append({"baseline": "fnri2015_severe", "province": r["province"], "year": y, "score": r["value"], "from_wave": 2015})
    return pd.DataFrame(rows)


# ---------- ranking evaluation ----------
def _vec(S, key, year, provs):
    s = S[(S["key"] == key) & (S["year"] == year)].set_index("province")["score"]
    return None if not set(provs) <= set(s.index) else s.loc[provs].to_numpy()


def ranking(T, A, B) -> pd.DataFrame:
    A = A.assign(key=A["model"] + "|L" + A["lead"].astype(str))
    B = B.assign(key="BASE:" + B["baseline"])
    S = pd.concat([A[["key", "province", "year", "score"]], B[["key", "province", "year", "score"]]])
    cov = A.groupby("key")["coverage"].agg(lambda s: "full" if (s == "full").all() else "partial")
    rows = []
    for oid in O.OUTCOMES:
        g = T[T["outcome"] == oid]
        mixed = g["reference_year"].nunique() > 1 and g.groupby("reference_year").size().max() < 5
        groups = [("mixed", g)] if mixed else list(g.groupby("reference_year"))
        for key in S["key"].unique():
            pairs = []
            for y, gy in groups:
                gy = gy.sort_values("province")
                provs = list(gy["province"])
                if mixed:
                    sc = [S[(S["key"] == key) & (S["year"] == r["reference_year"]) & (S["province"] == r["province"])]["score"] for _, r in gy.iterrows()]
                    if any(len(x) == 0 for x in sc):
                        continue
                    s = np.array([float(x.iloc[0]) for x in sc])
                else:
                    s = _vec(S, key, y, provs)
                    if s is None:
                        continue
                obs = gy["value"].to_numpy()
                pairs.append((s, obs))
                rows.append({"outcome": oid, "track": O.OUTCOMES[oid][0], "year": str(y), "key": key, **rank_eval(s, obs),
                             "coverage": cov.get(key, "baseline"), "mixed_years": mixed})
            if len(pairs) > 1:
                m, p = pooled_p(pairs)
                rows.append({"outcome": oid, "track": O.OUTCOMES[oid][0], "year": "pooled", "key": key, "n": sum(len(o) for _, o in pairs),
                             "spearman": m, "p_one_sided": p, "years_positive": sum((spearman(s, o) or 0) > 0 for s, o in pairs),
                             "n_years": len(pairs), "coverage": cov.get(key, "baseline"), "mixed_years": False})
    return pd.DataFrame(rows)


# ---------- level accuracy (food poverty) ----------
def levels(T) -> pd.DataFrame:
    fi10 = M.build()
    pv = O.psa_poverty()
    rows = []
    for oid in ("PSA_SUB_FAM", "PSA_SUB_POP"):
        g = T[T["outcome"] == oid].pivot(index="province", columns="reference_year", values="value")
        se = T[T["outcome"] == oid].pivot(index="province", columns="reference_year", values="se")
        reg = {y: O.regional(oid, y) for y in (2018, 2021, 2023)}
        for test, prior in ((2021, [2018]), (2023, [2018, 2021])):
            last = prior[-1]
            v_prior, se_prior = g[last], se[last]
            tau2 = max(0.0, float(v_prior.var(ddof=1) - (se_prior ** 2).mean()))
            w = tau2 / (tau2 + se_prior ** 2)
            cand = {"L0": v_prior, "L1": pd.Series(reg[last][0], index=g.index), "L2": g[prior].mean(axis=1),
                    "L3": w * v_prior + (1 - w) * reg[last][0]}
            if test == 2023:
                pp = fi10[(fi10["model"] == "FI10_L2sel") & (fi10["lead"] == 2)].set_index(["province", "year"])["score"]

                def X(y, y_prev):
                    return np.column_stack([g[y_prev], pv[pv["year"] == y_prev].set_index("geo").loc[g.index, "value"],
                                            pp.loc[[(p, y) for p in g.index]].to_numpy()])
                Xtr, ytr, Xte = X(2021, 2018), g[2021].to_numpy(), X(2023, 2021)
                mu, sd = Xtr.mean(0), Xtr.std(0, ddof=0)
                Z, Zt = (Xtr - mu) / sd, (Xte - mu) / sd
                beta = np.linalg.solve(Z.T @ Z + np.eye(3), Z.T @ (ytr - ytr.mean()))
                cand["L4"] = pd.Series(ytr.mean() + Zt @ beta, index=g.index)
            obs = g[test]
            floor = float(np.mean(se[test]) * np.sqrt(2 / np.pi))
            for k, pred in cand.items():
                e = pred.loc[g.index] - obs
                rows.append({"outcome": oid, "test_year": test, "candidate": k, "n": len(e), "mae": float(e.abs().mean()),
                             "rmse": float(np.sqrt((e ** 2).mean())), "bias": float(e.mean()),
                             "spearman": spearman(pred.loc[g.index], obs), "noise_floor_mae": floor})
    return pd.DataFrame(rows)


# ---------- feature association ----------
def features(T) -> pd.DataFrame:
    D = pd.read_csv(BACKEND_DIR / "data" / "fi10" / "out" / "dataset.csv")
    D = D[D["lead"] == 1]
    D["year"] = D["target_quarter"].str[:4].astype(int)
    F = D.groupby(["province", "year"]).mean(numeric_only=True)
    rp = M.realised_price_pressure().set_index(["province", "year"])
    rows = []
    feats = [(grp, c) for grp, cols in PROTOCOL["features_fi10"].items() for c in cols] + [("construct check", "price_excess")]
    for oid, years in (("FNRI15_SEV", [2015]), ("FNRI15_INSEC", [2015]), ("PSA_SUB_FAM", [2018, 2021, 2023]), ("PSA_SUB_POP", [2018, 2021, 2023])):
        for grp, c in feats:
            src = rp if c == "price_excess" else F
            pairs, vary = [], True
            for y in years:
                g = T[(T["outcome"] == oid) & (T["reference_year"] == y)].sort_values("province")
                x = src.loc[[(p, y) for p in g["province"]], c].to_numpy(dtype=float)
                if np.isnan(x).any():
                    vary = "missing for at least one province-year"
                    break
                if np.std(x) < 1e-9:
                    vary = "no provincial variation (national or regional series)"
                    break
                pairs.append((x, g["value"].to_numpy()))
            if vary is not True:
                rows.append({"outcome": oid, "group": grp, "feature": c, "status": vary})
                continue
            m, p = pooled_p(pairs) if len(pairs) > 1 else (spearman(*pairs[0]), exact_p(*pairs[0]))
            rows.append({"outcome": oid, "group": grp, "feature": c, "status": "ok", "n_years": len(pairs), "mean_spearman": m, "p_one_sided_positive": p})
    R = pd.DataFrame(rows)
    rows = []
    E = pd.read_csv(BACKEND_DIR / "data" / "ch1_engine" / "rows.csv")
    E = E[(E["lead"] == 1) & E["quarter"].str.startswith("2023")].groupby("province").mean(numeric_only=True)
    for oid in ("PSA_SUB_FAM", "PSA_SUB_POP"):
        g = T[(T["outcome"] == oid) & (T["reference_year"] == 2023)].sort_values("province")
        for c in PROTOCOL["features_firi_2023"]:
            x = E.loc[g["province"], c].to_numpy(dtype=float)
            if np.nanstd(x) < 1e-9 or np.isnan(x).any():
                rows.append({"outcome": oid, "group": "FIRI v2 (served rows, 2023)", "feature": c, "status": "no provincial variation or missing"})
                continue
            r = spearman(x, g["value"].to_numpy())
            rows.append({"outcome": oid, "group": "FIRI v2 (served rows, 2023)", "feature": c, "status": "ok", "n_years": 1, "mean_spearman": r,
                         "p_one_sided_positive": exact_p(x, g["value"].to_numpy())})
    R = pd.concat([R, pd.DataFrame(rows)], ignore_index=True)
    ok = R["status"] == "ok"
    for oid, g in R[ok].groupby("outcome"):
        p = g["p_one_sided_positive"].fillna(1).to_numpy()
        pt = np.minimum(1, 2 * np.minimum(p, 1 - p))
        order = np.argsort(pt)
        holm = np.empty_like(pt)
        run = 0.0
        for i, j in enumerate(order):
            run = max(run, min(1.0, (len(pt) - i) * pt[j]))
            holm[j] = run
        R.loc[g.index, "p_two_sided"] = pt
        R.loc[g.index, "holm_two_sided"] = holm
    return R


def run() -> dict:
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    if lock["sha256"] != _digest() or lock["code_sha256"] != _code():
        raise RuntimeError("FI12 protocol or code changed after lock")
    T = O.build()
    T.to_csv(OUT / "outcomes.csv", index=False)
    M.write()
    A = pd.read_csv(OUT / "model_scores_by_reference_year.csv")
    B = baseline_scores(T)
    B.to_csv(OUT / "baseline_scores.csv", index=False)
    meas = measurement(T)
    R = ranking(T, A, B)
    L = levels(T)
    F = features(T)
    R.to_csv(OUT / "ranking_agreement.csv", index=False)
    L.to_csv(OUT / "level_accuracy.csv", index=False)
    F.to_csv(OUT / "feature_association.csv", index=False)
    match_rows = T.merge(A, left_on=["province", "reference_year"], right_on=["province", "year"], how="left")
    match_rows.to_csv(OUT / "forecast_observation_matches.csv", index=False)
    res = {"protocol_sha256": _digest(), "code_sha256": _code(), "measurement": meas,
           "n_outcome_records": len(T), "n_matches": int(match_rows["model"].notna().sum())}
    (OUT / "evaluation.json").write_text(json.dumps(res, indent=1, default=float))
    return res


if __name__ == "__main__":
    if sys.argv[1:] == ["lock"]:
        p = OUT / "PROTOCOL_LOCK.json"
        if p.exists():
            sys.exit("already locked")
        p.write_text(json.dumps({"sha256": _digest(), "code_sha256": _code(), "locked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                 "protocol": PROTOCOL}, indent=1))
        print(_digest())
    elif sys.argv[1:] == ["run"]:
        r = run()
        print(r["n_outcome_records"], r["n_matches"])
