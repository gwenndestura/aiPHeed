"""E73 WS3 (PROTOCOL section 3): robustness of the approved LGU prioritization (0.6 poverty + 0.4 density, min-max
within province) to reasonable alternative weights and normalisations. Run with cwd = backend."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

E73 = Path(__file__).resolve().parents[1]
v = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
v["density"] = v["population_2024"] / v["land_area_km2"]
v["log_density"] = np.log(v["density"])


def mm(s):
    return (s - s.min()) / (s.max() - s.min())


def score(g, wp, norm="minmax", dens="density"):
    if norm == "rank":
        p, d = g["poverty_value_used"].rank(pct=True), g[dens].rank(pct=True)
    else:
        p, d = mm(g["poverty_value_used"]), mm(g[dens])
    return wp * p + (1 - wp) * d


ALT = {"0.5/0.5": (0.5, "minmax", "density"), "0.7/0.3": (0.7, "minmax", "density"), "0.8/0.2": (0.8, "minmax", "density"),
       "poverty only": (1.0, "minmax", "density"), "density only": (0.0, "minmax", "density"),
       "rank 0.6/0.4": (0.6, "rank", "density"), "log-density 0.6/0.4": (0.6, "minmax", "log_density")}
res = {}
for name, (wp, norm, dens) in ALT.items():
    per = {}
    for prov, g in v.groupby("province"):
        base = score(g, 0.6)
        alt = score(g, wp, norm, dens)
        top_b, top_a = set(base.nlargest(5).index), set(alt.nlargest(5).index)
        terc_b = pd.qcut(base.rank(method="first"), 3, labels=False)
        terc_a = pd.qcut(alt.rank(method="first"), 3, labels=False)
        per[prov] = {"n": int(len(g)), "spearman": float(spearmanr(base, alt)[0]), "top5_overlap": len(top_b & top_a),
                     "tercile_changed": int((terc_b != terc_a).sum())}
    res[name] = {"per_province": per, "min_spearman": min(p["spearman"] for p in per.values()),
                 "lgus_changing_tercile": sum(p["tercile_changed"] for p in per.values())}
robust = all(res[k]["min_spearman"] >= 0.9 for k, (wp, _, _) in ALT.items() if wp >= 0.5)
out = {"alternatives": res, "robust_rule": "every alternative with poverty weight >= 0.5 keeps Spearman >= 0.9 in every province",
       "robust": robust, "substitute_poverty": v.loc[v["poverty_source"].str.contains("substitut|fallback|province", case=False, na=False), "lgu_name"].tolist(),
       "lgus": int(len(v))}
(E73 / "out" / "lgu_weight_sensitivity.json").write_text(json.dumps(out, indent=1))
for k, r in res.items():
    print(f"{k:22s} min rho {r['min_spearman']:.3f}  tercile changes {r['lgus_changing_tercile']}/{len(v)}  top5 overlap " +
          ", ".join(f"{p[:3]} {x['top5_overlap']}" for p, x in r["per_province"].items()))
print("robust:", robust, "| poverty substitutes/fallbacks:", len(out["substitute_poverty"]))
