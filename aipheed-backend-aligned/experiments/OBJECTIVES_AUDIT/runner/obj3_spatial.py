"""Objective 3 validation (read only; no model fit): independent recomputation of the 5 province and 142 LGU outputs
from the source tables, weight sensitivity, and rank uncertainty from the PSA small-area-estimate CVs.

    python obj3_spatial.py   # -> ../out/obj3_spatial.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[2]
ENG = ROOT / "backend" / "data" / "foodinsecurity_engine"
CB = HERE.parent / "NEW_MODEL" / "NEWS_V2" / "out"
OUT = HERE / "out"
SEED, DRAWS = 2036, 1000
PROV = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
        "PH040500000": "Batangas"}


def minmax(a: np.ndarray) -> np.ndarray:
    lo, hi = a.min(), a.max()
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


def risk(v: pd.DataFrame, pov: np.ndarray, wp: float, wd: float, prov_score: dict) -> np.ndarray:
    """Independent implementation: plain numpy, loop over provinces."""
    out = np.empty(len(v))
    dens = (v["population_2024"] / v["land_area_km2"]).to_numpy(float)
    for p in v["province"].unique():
        m = (v["province"] == p).to_numpy()
        out[m] = prov_score[p] * (wp * minmax(pov[m]) + wd * minmax(dens[m]))
    return np.clip(out, 0, 1)


def main():
    v = pd.read_csv(ENG / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    stored = pd.read_csv(CB / "cb_lgu_2026-10-01.csv", dtype={"lgu_code": str})
    stored = stored[stored["lead"] == 1].set_index("lgu_code").loc[v["lgu_code"]]
    sp = pd.read_csv(CB / "cb_province_2026-10-01.csv")
    sp = sp[sp["lead"] == 1].set_index("province")
    P = float(sp["regional_probability"].iloc[0])
    # province poverty from the PSA source table, not from evaluation.json
    src = pd.read_csv(ENG / "psa" / "psa_poverty.csv", dtype={"place_code": str})
    fam = src[(src["year"] == 2023) & (src["item"] == "Poverty Incidence Among Families (%)") & src["place_code"].isin(PROV)]
    pf = {PROV[r.place_code]: float(r.value) for r in fam.itertuples()}
    res = {"regional_probability_2026Q4": P, "province_poverty_from_source": pf}
    mx = max(pf.values())
    ps = {p: P * x / mx for p, x in pf.items()}
    res["province_recompute_max_abs_diff"] = float(max(abs(ps[p] - sp.loc[p, "province_score"]) for p in ps))
    pov = v["poverty_value_used"].to_numpy(float)
    base = risk(v, pov, .6, .4, ps)
    res["lgu_recompute_max_abs_diff"] = float(np.max(np.abs(base - stored["risk_index"].to_numpy(float))))
    res["lgu_rows"] = int(len(v))
    res["lgu_by_province"] = v["province"].value_counts().to_dict()
    res["lgu_sources"] = v["poverty_source"].str[:60].value_counts().to_dict()
    res["lgu_cv_over_20"] = int((v["poverty_cv"] > 20).sum())
    dens = (v["population_2024"] / v["land_area_km2"]).to_numpy(float)
    res["poverty_density_spearman"] = {"all": float(spearmanr(pov, dens)[0]),
                                       **{p: float(spearmanr(pov[(v["province"] == p).to_numpy()],
                                                             dens[(v["province"] == p).to_numpy()])[0])
                                          for p in PROV.values()}}
    # weight sensitivity (reported, nothing chosen from it)
    rk = lambda a: pd.Series(a).rank(ascending=False, method="min").to_numpy()  # noqa: E731
    top = lambda a, n=10: set(np.argsort(-a)[:n])  # noqa: E731
    sens = {}
    variants = {"poverty_only (1, 0)": (1, 0, ps), "(0.8, 0.2)": (.8, .2, ps), "served (0.6, 0.4)": (.6, .4, ps),
                "density_protective (0.6, -0.4)": (.6, -.4, ps), "density_only (0, 1)": (0, 1, ps),
                "paper_eq6 (0.6, 0.4), province score = P": (.6, .4, {p: P for p in ps})}
    for name, (wp, wd, s) in variants.items():
        if wd >= 0:
            r = risk(v, pov, wp, wd, s)
        else:                                         # density as a protective factor: wp pov + |wd| (1 - density)
            r = np.empty(len(v))
            for p in v["province"].unique():
                m = (v["province"] == p).to_numpy()
                r[m] = s[p] * (wp * minmax(pov[m]) + (-wd) * (1 - minmax(dens[m])))
        sens[name] = {"kendall_tau_vs_served": float(kendalltau(rk(r), rk(base))[0]),
                      "top10_overlap_with_served": len(top(r) & top(base)),
                      "top5": v.iloc[np.argsort(-r)[:5]]["lgu_name"].tolist(),
                      "spearman_rank_vs_poverty": float(spearmanr(r, pov)[0])}
    res["weight_sensitivity"] = sens
    # rank uncertainty: poverty ~ Normal(value, (cv/100 * value)^2), truncated at 0, 1000 draws, served weights
    rng = np.random.default_rng(SEED)
    sd = v["poverty_cv"].to_numpy(float) / 100 * pov
    R = np.empty((DRAWS, len(v)))
    for b in range(DRAWS):
        R[b] = rk(risk(v, np.maximum(0, rng.normal(pov, sd)), .6, .4, ps))
    lo, hi = np.percentile(R, 5, axis=0), np.percentile(R, 95, axis=0)
    width = hi - lo
    res["rank_uncertainty"] = {"draws": DRAWS, "median_90pct_interval_width": float(np.median(width)),
                               "max_width": float(width.max()),
                               "mean_top10_overlap_with_served": float(np.mean([len(set(np.argsort(x)[:10]) & top(base))
                                                                                for x in R])),
                               "top10_in_top10_share": {v["lgu_name"].iloc[i]: float(np.mean(R[:, i] <= 10))
                                                        for i in np.argsort(-base)[:10]}}
    rows = v[["lgu_code", "lgu_name", "province", "poverty_value_used", "poverty_cv"]].assign(
        risk_index=base, rank_region=rk(base), rank_p05=lo, rank_p95=hi)
    OUT.mkdir(parents=True, exist_ok=True)
    rows.to_csv(OUT / "obj3_lgu_rank_intervals.csv", index=False)
    (OUT / "obj3_spatial.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
