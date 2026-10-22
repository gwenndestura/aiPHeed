"""E97 Q6 (PROTOCOL.md): audit of the 142-LGU vulnerability ranking and its sensitivity to defensible alternatives.
The served within-province ranking is 0.6 x poverty_norm + 0.4 x density_norm (min-max within province; approved
weights, not learned). Run from backend/."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

import common as C

VARIANTS = {
    "served_0.6_0.4": dict(wp=0.6),
    "w_0.5_0.5": dict(wp=0.5), "w_0.7_0.3": dict(wp=0.7), "w_0.8_0.2": dict(wp=0.8),
    "poverty_only": dict(wp=1.0), "density_only": dict(wp=0.0),
    "log_density": dict(wp=0.6, logd=True), "percentile_norm": dict(wp=0.6, pct=True),
}


def index(v: pd.DataFrame, wp: float, logd: bool = False, pct: bool = False) -> pd.Series:
    x = v.assign(dens=np.log(v["density"]) if logd else v["density"])
    out = pd.Series(index=v.index, dtype=float)
    for _, g in x.groupby("province"):
        if pct:
            pn, dn = g["poverty_value_used"].rank(pct=True), g["dens"].rank(pct=True)
        else:
            mm = lambda s: (s - s.min()) / ((s.max() - s.min()) or 1)  # noqa: E731
            pn, dn = mm(g["poverty_value_used"]), mm(g["dens"])
        out.loc[g.index] = wp * pn + (1 - wp) * dn
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    o = C.E97 / "runs" / f"{stamp}_lgu"
    o.mkdir(parents=True, exist_ok=True)
    v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
    v["density"] = v["population_2024"] / v["land_area_km2"]
    geo = json.loads((C.BACKEND.parent / "frontend/public/calabarzon-municities.json").read_text(encoding="utf-8"))
    feats = {(f["properties"]["province_name"], f["properties"]["name"]) for f in geo["features"]}
    audit = {
        "rows": len(v), "unique_codes": int(v["lgu_code"].nunique()), "by_province": v["province"].value_counts().to_dict(),
        "lgu_specific_poverty": int(v["poverty_lgu_estimate"].notna().sum()),
        "substituted": v.loc[v["poverty_lgu_estimate"].isna(), ["lgu_code", "lgu_name", "province", "poverty_value_used", "poverty_source"]].to_dict(orient="records"),
        "missing_population_or_area": int((v["population_2024"].isna() | v["land_area_km2"].isna() | (v["land_area_km2"] <= 0)).sum()),
        "map_features": len(feats),
        "psgc_province_prefix_consistent": bool((v["lgu_code"].str[:4].map({"0410": "Batangas", "0421": "Cavite", "0434": "Laguna",
                                                                               "0456": "Quezon", "0458": "Rizal"}) == v["province"]).all()),
        "map_name_join_unmatched_in_input_table": sorted(f"{p}/{n}" for p, n in feats - set(zip(v["province"], v["lgu_name"]))),
    }
    # Dominance: scale of each normalised term and its share of the within-province variance of the served index
    dom = {}
    for p, g in v.groupby("province"):
        mm = lambda s: (s - s.min()) / ((s.max() - s.min()) or 1)  # noqa: E731
        a, b = 0.6 * mm(g["poverty_value_used"]), 0.4 * mm(g["density"])
        tot = np.var(a + b)
        dom[p] = {"poverty_term_var_share": float((np.var(a) + np.cov(a, b, ddof=0)[0, 1]) / tot),
                  "density_term_var_share": float((np.var(b) + np.cov(a, b, ddof=0)[0, 1]) / tot),
                  "density_skew": float(g["density"].skew()), "poverty_density_spearman": float(spearmanr(g["poverty_value_used"], g["density"]).statistic),
                  "n": len(g)}
    idx = {k: index(v, **kw) for k, kw in VARIANTS.items()}
    rk = {k: s.groupby(v["province"]).rank(ascending=False, method="min") for k, s in idx.items()}
    sens = {}
    for k in VARIANTS:
        if k == "served_0.6_0.4":
            continue
        per = {}
        for p, g in v.groupby("province"):
            a, b = rk["served_0.6_0.4"].loc[g.index], rk[k].loc[g.index]
            top = lambda r, n: set(g.loc[r.loc[g.index] <= n, "lgu_code"])  # noqa: E731
            per[p] = {"spearman_with_served": float(spearmanr(a, b).statistic),
                      "top3_overlap": len(top(a, 3) & top(b, 3)), "top5_overlap": len(top(a, 5) & top(b, 5)),
                      "max_rank_shift": int((a - b).abs().max())}
        sens[k] = per
    # Lucena excluded: Quezon ranks of the other 40 LGUs
    q = v[v["province"] == "Quezon"]
    qx = q[q["poverty_lgu_estimate"].notna()]
    r_with = index(v, 0.6).loc[qx.index].rank(ascending=False)
    r_wo = index(v.drop(q.index.difference(qx.index)), 0.6).loc[qx.index].rank(ascending=False)
    sens["lucena_excluded"] = {"Quezon": {"spearman_with_served": float(spearmanr(r_with, r_wo).statistic),
                                          "max_rank_shift": int((r_with - r_wo).abs().max())}}
    v["served_index"], v["served_rank_in_province"] = idx["served_0.6_0.4"], rk["served_0.6_0.4"]
    for k in VARIANTS:
        v[f"rank_{k}"] = rk[k]
    v.to_csv(o / "lgu_rank_variants.csv", index=False)
    res = {"stamp": stamp, "protocol_sha256": (C.E97 / "PROTOCOL.sha256").read_text().split()[0],
           "weights_status": "approved heuristic weights (Chapter I / Backend Guide v3), not learned from data",
           "audit": audit, "dominance": dom, "sensitivity": sens}
    (o / "lgu_sensitivity.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(json.dumps(audit, indent=1, default=str)[:1500])
    for p, d in dom.items():
        print(p, {k: round(x, 3) if isinstance(x, float) else x for k, x in d.items()})
    for k, per in sens.items():
        print(k, {p: (round(x["spearman_with_served"], 3), x.get("top3_overlap"), x.get("top5_overlap"), x["max_rank_shift"]) for p, x in per.items()})
    print(o)


if __name__ == "__main__":
    main()
