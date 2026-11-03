"""Validate poverty-weighted provincial and LGU priority against the production formula (FI9-X follow-up).

    python -m app.fi9x.priority       # writes data/fi9x/out/priority_validation.json and priority_alternatives_*.csv

Production formula (app/fi5/rankings.py), unchanged here:
    V = wp * pct_rank(LGU poverty 2021 SAE) + (1 - wp) * pct_rank(LGU density 2024), wp = 0.5
    province = population-weighted mean of V; priority = 100 * P(HIGH, regional) * V (P is common, so order = V)
Scenarios: wp = 0.5 (current), 0.65 (moderate), 0.8 (strong), 1.0 (poverty-only benchmark); 0.0 (density-only, reference);
plus a 0..1 sweep reported as a curve only (weights are NOT chosen by maximum correlation).
Validation reference: FNRI 2015 HFIAS (one wave, five provinces), with its published standard errors.
"""
from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd
from scipy import stats

from app.fi5 import rankings as R
from app.fi9x import OUT
from app.paths import BACKEND_DIR

SCEN = {"current (0.5 poverty / 0.5 density)": 0.5, "moderate (0.65 / 0.35)": 0.65, "strong (0.8 / 0.2)": 0.8,
        "poverty only (benchmark)": 1.0, "density only (reference)": 0.0}
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
DRAWS, SEED = 2000, 20261103


def lgu() -> pd.DataFrame:
    t = R.lgu_table()
    s = pd.read_csv(BACKEND_DIR / "data" / "reference" / "sae2021_calabarzon_municipal.csv", dtype={"lgu_code": str})
    t = t.merge(s[["lgu_code", "ci90_low_2021", "ci90_high_2021"]], left_on="lgu_psgc", right_on="lgu_code", how="left").drop(columns="lgu_code")
    t["poverty_sd"] = (t["ci90_high_2021"] - t["ci90_low_2021"]) / (2 * 1.645)
    lucena = t["poverty_sd"].isna()
    t.loc[lucena, "poverty_sd"] = t.loc[lucena, "poverty_incidence_2021"] * t["cv_2021"].median() / 100   # assumption, disclosed
    return t


def V(t, wp, pov=None):
    p = t["poverty_incidence_2021"] if pov is None else pov
    return wp * p.rank(pct=True) + (1 - wp) * t["density_2024"].rank(pct=True)


def province_scores(t, wp, pov=None) -> pd.Series:
    v = V(t, wp, pov)
    return (v * t["population_2024"]).groupby(t["province_name"]).sum() / t.groupby("province_name")["population_2024"].sum()


def hfias():
    h = pd.read_csv(BACKEND_DIR / "data" / "fi_labels" / "clean" / "published_hfias_2015_calabarzon.csv")
    h = h[h["geography"].isin(PROV)]
    g = lambda c: h[h["category"] == c].set_index("geography")
    ms = g("moderately_food_insecure")["percent"] + g("severely_food_insecure")["percent"]
    ms_se = np.sqrt(g("moderately_food_insecure")["se"] ** 2 + g("severely_food_insecure")["se"] ** 2)
    return {"mod_sev": (ms.loc[PROV], ms_se.loc[PROV]), "severe": (g("severely_food_insecure")["percent"].loc[PROV], g("severely_food_insecure")["se"].loc[PROV]),
            "not_food_secure": (100 - g("food_secure")["percent"].loc[PROV], g("food_secure")["se"].loc[PROV])}


def exact_p(x, y) -> float:
    """One-sided exact permutation p-value of Spearman rho (5! orderings)."""
    r0 = stats.spearmanr(x, y).statistic
    rs = [stats.spearmanr(x, np.asarray(y)[list(p)]).statistic for p in itertools.permutations(range(len(y)))]
    return float(np.mean(np.array(rs) >= r0 - 1e-12))


def provincial(t) -> dict:
    H = hfias()
    rng = np.random.default_rng(SEED)
    out = {"scenarios": {}, "sweep": []}
    sc = {name: province_scores(t, wp).loc[PROV] for name, wp in SCEN.items()}
    for ref, (val, se) in H.items():
        draws = rng.normal(val.to_numpy()[None, :], se.to_numpy()[None, :], size=(DRAWS, 5))
        cur = sc["current (0.5 poverty / 0.5 density)"].to_numpy()
        rho_cur = np.array([stats.spearmanr(cur, d).statistic for d in draws])
        for name, s in sc.items():
            r = stats.spearmanr(s, val).statistic
            rd = np.array([stats.spearmanr(s.to_numpy(), d).statistic for d in draws])
            lopo = [stats.spearmanr(np.delete(s.to_numpy(), k), np.delete(val.to_numpy(), k)).statistic for k in range(5)]
            lopo_cur = [stats.spearmanr(np.delete(cur, k), np.delete(val.to_numpy(), k)).statistic for k in range(5)]
            out["scenarios"].setdefault(name, {})[ref] = {
                "spearman": float(r), "kendall": float(stats.kendalltau(s, val).statistic), "exact_p_one_sided": exact_p(s.to_numpy(), val.to_numpy()),
                "mean_spearman_under_hfias_sampling": float(np.nanmean(rd)),
                "prob_better_than_current_under_sampling": float(np.nanmean(rd > rho_cur)) if name != "current (0.5 poverty / 0.5 density)" else None,
                "leave_one_province_out_spearman": [round(float(x), 2) for x in lopo],
                "lopo_better_than_current": int(sum(a > b + 1e-12 for a, b in zip(lopo, lopo_cur)))}
    for wp in np.round(np.arange(0, 1.0001, 0.05), 2):
        s = province_scores(t, wp).loc[PROV]
        out["sweep"].append({"w_poverty": float(wp), "spearman_mod_sev": float(stats.spearmanr(s, H["mod_sev"][0]).statistic),
                             "order": " > ".join(s.sort_values(ascending=False).index)})
    out["province_table"] = []
    for p in PROV:
        row = {"province": p, "hfias2015_mod_sev": float(H["mod_sev"][0][p]), "hfias_rank": int(H["mod_sev"][0].rank(ascending=False)[p]),
               "poverty2021_popweighted": float(np.average(t.loc[t["province_name"] == p, "poverty_incidence_2021"], weights=t.loc[t["province_name"] == p, "population_2024"])),
               "density2024": float(t.loc[t["province_name"] == p, "population_2024"].sum() / t.loc[t["province_name"] == p, "land_area_km2"].sum())}
        for name, s in sc.items():
            row[f"score | {name}"] = round(float(s[p]), 3)
            row[f"rank | {name}"] = int(s.rank(ascending=False)[p])
        out["province_table"].append(row)
    pw = pd.DataFrame(out["province_table"]).set_index("province")
    out["poverty2021_vs_hfias2015_spearman"] = float(stats.spearmanr(pw["poverty2021_popweighted"], pw["hfias2015_mod_sev"]).statistic)
    out["density_vs_hfias2015_spearman"] = float(stats.spearmanr(pw["density2024"], pw["hfias2015_mod_sev"]).statistic)
    out["hfias_pairwise_distinguishable"] = _pairwise(H["mod_sev"])
    pd.DataFrame(out["province_table"]).to_csv(OUT / "priority_alternatives_province.csv", index=False, lineterminator="\n")
    return out


def _pairwise(ref) -> dict:
    v, se = ref
    pairs = {}
    for a, b in itertools.combinations(PROV, 2):
        z = abs(v[a] - v[b]) / np.sqrt(se[a] ** 2 + se[b] ** 2)
        pairs[f"{a}-{b}"] = round(float(z), 2)
    return {"z_scores": pairs, "n_pairs_significant_at_95": int(sum(z > 1.96 for z in pairs.values())), "n_pairs": len(pairs)}


def lgu_level(t) -> dict:
    rng = np.random.default_rng(SEED)
    n = len(t)
    k = int(np.ceil(n / 3))
    cur = V(t, 0.5)
    res = {"data": {
        "n_lgus": n, "poverty_year": 2021, "density_year": 2024, "poverty_source": "PSA 2021 city/municipal small-area estimates (141) + Lucena HUC published estimate (1)",
        "cv_bins": {"<=10%": int((t["cv_2021"] <= 10).sum()), "10-20%": int(t["cv_2021"].between(10, 20, inclusive="right").sum()),
                    "20-30%": int(t["cv_2021"].between(20, 30, inclusive="right").sum()), ">30%": int((t["cv_2021"] > 30).sum()), "no CV (Lucena)": int(t["cv_2021"].isna().sum())},
        "spearman_poverty_vs_density": float(stats.spearmanr(t["poverty_incidence_2021"], t["density_2024"]).statistic),
        "lucena_sd_assumption": "Lucena has no published CV; its sd uses the median CV of the other 141 LGUs"},
        "scenarios": {}}
    pov_draws = np.clip(rng.normal(t["poverty_incidence_2021"].to_numpy()[None, :], t["poverty_sd"].to_numpy()[None, :], size=(DRAWS, n)), 0, None)
    top_cur = set(cur.sort_values(ascending=False).index[:k])
    alts, ptop = {}, {}
    for name, wp in SCEN.items():
        v = V(t, wp)
        top = set(v.sort_values(ascending=False).index[:k])
        in_top = np.zeros(n)
        ranks = np.zeros((DRAWS, n))
        for d in range(DRAWS):
            vd = wp * pd.Series(pov_draws[d]).rank(pct=True).to_numpy() + (1 - wp) * t["density_2024"].rank(pct=True).to_numpy()
            r = (-vd).argsort().argsort()
            ranks[d] = r + 1
            in_top += r < k
        p_top = in_top / DRAWS
        width = np.percentile(ranks, 95, axis=0) - np.percentile(ranks, 5, axis=0)
        cv_hi = (t["cv_2021"] > 20).to_numpy()
        alts[name] = v
        ptop[name] = p_top
        res["scenarios"][name] = {
            "spearman_vs_current": float(stats.spearmanr(v, cur).statistic), "top_third_changed_vs_current": len(top - top_cur),
            "top_third_by_province": pd.Series([t.loc[i, "province_name"] for i in top]).value_counts().to_dict(),
            "share_lgus_with_stable_top_third_membership": float(np.mean((p_top >= 0.9) | (p_top <= 0.1))),
            "median_90pct_rank_interval_width": float(np.median(width)),
            "median_rank_interval_width_lgus_cv_gt_20": float(np.median(width[cv_hi])),
            "drop_lucena_spearman": float(stats.spearmanr(V(t.drop(t.index[t["cv_2021"].isna()]), wp), v.drop(t.index[t["cv_2021"].isna()])).statistic),
            "drop_cv_gt_30_top_third_changed": _drop_effect(t, wp, k)}
    tab = t[["province_name", "lgu_psgc", "lgu_name", "lgu_type", "poverty_incidence_2021", "cv_2021", "density_2024", "population_2024"]].copy()
    for name, v in alts.items():
        tab[f"V | {name}"] = v.round(4)
        tab[f"rank | {name}"] = v.rank(ascending=False, method="min").astype(int)
        tab[f"p_top_third | {name}"] = np.round(ptop[name], 3)
    tab["poor_population_2021"] = (tab["poverty_incidence_2021"] / 100 * tab["population_2024"]).round()
    tab.sort_values("rank | current (0.5 poverty / 0.5 density)").to_csv(OUT / "priority_alternatives_lgu.csv", index=False, lineterminator="\n")
    poor = tab["poor_population_2021"]
    res["scale_indicator_note"] = {"spearman_poor_population_vs_density": float(stats.spearmanr(poor, t["density_2024"]).statistic),
                                   "spearman_poor_population_vs_poverty_rate": float(stats.spearmanr(poor, t["poverty_incidence_2021"]).statistic)}
    return res


def _drop_effect(t, wp, k) -> int:
    keep = t[~(t["cv_2021"] > 30)]
    a = set(V(t, wp).sort_values(ascending=False).index[:k]) & set(keep.index)
    b = set(V(keep, wp).sort_values(ascending=False).index[:int(np.ceil(len(keep) / 3))])
    return len(b - a)


def run() -> dict:
    t = lgu()
    res = {"formula": {"current": "V = 0.5 pct_rank(poverty 2021) + 0.5 pct_rank(density 2024); province = population-weighted mean of V",
                       "scenarios": SCEN}, "provincial": provincial(t), "lgu": lgu_level(t)}
    (OUT / "priority_validation.json").write_text(json.dumps(res, indent=1, default=str))
    return res


if __name__ == "__main__":
    r = run()
    P = r["provincial"]
    for name, v in P["scenarios"].items():
        m = v["mod_sev"]
        print(f"{name:38s} rho={m['spearman']:+.2f} tau={m['kendall']:+.2f} p={m['exact_p_one_sided']:.3f} rho|sampling={m['mean_spearman_under_hfias_sampling']:+.2f} "
              f"P(better)={m['prob_better_than_current_under_sampling']} LOPO={m['leave_one_province_out_spearman']} better_in={m['lopo_better_than_current']}/5 | severe rho={v['severe']['spearman']:+.2f}")
    for s in P["sweep"]:
        print(s)
    print("pov2021 vs hfias", P["poverty2021_vs_hfias2015_spearman"], "density vs hfias", P["density_vs_hfias2015_spearman"], P["hfias_pairwise_distinguishable"])
    for name, v in r["lgu"]["scenarios"].items():
        print(name, {k: v[k] for k in v if k != "top_third_by_province"}, v["top_third_by_province"])
    print(r["lgu"]["data"], r["lgu"]["scale_indicator_note"])
