"""Objective 3 addendum (read only; reported, nothing chosen): does the density term lift less-poor urban LGUs above
poorer rural ones, and how do exposure-based alternatives compare?

Variants (same province score P x poverty weight as served, C-E2 demo P for 2027-Q1):
  served            P_prov * (0.6 minmax(poverty) + 0.4 minmax(density))
  poverty_only      P_prov * minmax(poverty)
  poor_exposure     P_prov * (0.6 minmax(poverty) + 0.4 minmax(poor people = poverty% x population))
  two_dimensions    vulnerability = poverty rank, exposure = poor-people rank, reported side by side (no combination)

    python obj3_exposure.py      # -> ../out/obj3_exposure.json
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import obj3_spatial as S  # noqa: E402

HERE = S.HERE
ENG = S.ROOT / "backend" / "data" / "foodinsecurity_engine_ce2"


def index(v: pd.DataFrame, a: np.ndarray, b: np.ndarray | None, wa: float, wb: float, ps: dict) -> np.ndarray:
    out = np.empty(len(v))
    for p in v["province"].unique():
        m = (v["province"] == p).to_numpy()
        out[m] = ps[p] * (wa * S.minmax(a[m]) + (wb * S.minmax(b[m]) if b is not None else 0))
    return out


def main():
    v = pd.read_csv(ENG / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    r = pd.read_csv(ENG / "rows.csv", dtype={"province_code": str})
    r = r[r["quarter"] == "2027-Q1"]
    ps = dict(zip(r["province"], r["score"]))
    pov = v["poverty_value_used"].to_numpy(float)
    dens = (v["population_2024"] / v["land_area_km2"]).to_numpy(float)
    poor = pov / 100 * v["population_2024"].to_numpy(float)
    rk = lambda a: pd.Series(a).rank(ascending=False, method="min").to_numpy()  # noqa: E731
    V = {"served (poverty 0.6 + density 0.4)": index(v, pov, dens, .6, .4, ps),
         "poverty_only": index(v, pov, None, 1, 0, ps),
         "poor_exposure (poverty 0.6 + poor people 0.4)": index(v, pov, poor, .6, .4, ps)}
    base = V["served (poverty 0.6 + density 0.4)"]
    med = v.groupby("province")["poverty_value_used"].transform("median").to_numpy(float)
    res = {"province_scores_2027Q1": {k: round(x, 4) for k, x in ps.items()},
           "spearman": {"poverty_density": float(spearmanr(pov, dens)[0]),
                        "poverty_poor_people": float(spearmanr(pov, poor)[0])},
           "variants": {}}
    for name, x in V.items():
        top = np.argsort(-x)[:10]
        res["variants"][name] = {
            "kendall_tau_vs_served": float(kendalltau(rk(x), rk(base))[0]),
            "spearman_vs_poverty": float(spearmanr(x, pov)[0]),
            "top10": v.iloc[top]["lgu_name"].tolist(),
            "top10_below_province_median_poverty": int((pov[top] < med[top]).sum()),
            "top10_mean_poverty": round(float(pov[top].mean()), 2),
            "bottom5": v.iloc[np.argsort(x)[:5]]["lgu_name"].tolist(),
            "rank_change_vs_served": {"median_abs": float(np.median(np.abs(rk(x) - rk(base)))),
                                      "max_abs": float(np.max(np.abs(rk(x) - rk(base)))),
                                      "moved_over_20": int((np.abs(rk(x) - rk(base)) > 20).sum())}}
    tv, te = rk(pov), rk(poor)
    res["two_dimensions"] = {
        "kendall_tau_vulnerability_vs_exposure": float(kendalltau(tv, te)[0]),
        "top10_vulnerability": v.iloc[np.argsort(-pov)[:10]]["lgu_name"].tolist(),
        "top10_exposure_poor_people": v.iloc[np.argsort(-poor)[:10]]["lgu_name"].tolist(),
        "in_both_top20": v.iloc[sorted(set(np.argsort(-pov)[:20]) & set(np.argsort(-poor)[:20]))]["lgu_name"].tolist()}
    res["note"] = ("Vulnerability-weighted estimates, not measured municipal hunger; the hunger outcome is regional "
                   "(Balance Luzon). Nothing here changes the served index; the weighting is an adviser decision (D3.2).")
    (HERE / "out" / "obj3_exposure.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
