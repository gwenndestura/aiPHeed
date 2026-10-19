"""E64 r3 (Objective 3): the 142-LGU ranking audit.

1. Completeness and identity: app.quarterly.lgu_audit.audit_inputs (142 codes, province mapping, PSGC prefix, names,
   population, area, poverty range, substitutes).
2. Reproducibility: build_ranking twice on the same inputs -> identical rows_sha256; the served API rows equal it.
3. Formula replica: vulnerability = w_p * minmax(poverty) + w_d * minmax(density) within province; risk = P x vulnerability
   (4 dp). The replica must equal the served risk_index at (0.6, 0.4) before any sensitivity number is reported.
4. Drivers: within-province Spearman of the order with poverty, density and population size.
5. Weight sensitivity (no change to the served weights): (0.5,0.5), (0.7,0.3), (0.8,0.2), (1,0), (0,1), and rank instead
   of min-max normalisation; Spearman with the reference order and overlap of each province's top-5 shortlist.
6. Stability over time: within-province order across the 12 quarters of the E58 record (expected constant by
   construction) and region-wide order (changes only through the province estimates).
7. Independent municipal outcomes: none in the project data (stated, not imputed).

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E64_Objectives_1_3_Completion/runner/r3_lgu_audit.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ["AIPHEED_LEAD2_MODEL"] = "e58"
E64 = Path(__file__).resolve().parents[1]
BACKEND = E64.parents[2] / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))
sys.dont_write_bytecode = True

from app.ml.inference import e41_lead2 as L2  # noqa: E402
from app.quarterly.lgu_audit import audit_inputs, build_ranking  # noqa: E402

VUL = pd.read_csv("data/inputs/lgu_vulnerability.csv", dtype={"lgu_code": str})
ROS = pd.read_csv("data/reference/calabarzon_lgus.csv", dtype={"lgu_psgc": str})
NAME2CODE = {"Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000",
             "Rizal": "PH040400000"}


def replica(prob: dict, wp: float, wd: float, norm: str = "minmax") -> pd.DataFrame:
    v = VUL.copy()
    v["lgu_code"] = v["lgu_code"].str.zfill(9)
    v["province_code"] = v["province"].map(NAME2CODE)
    v["density"] = v["population_2024"] / v["land_area_km2"]

    def scale(s):
        if norm == "rank":
            return (s.rank(method="average") - 1) / max(len(s) - 1, 1)
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else s * 0.0
    v["pn"] = v.groupby("province")["poverty_value_used"].transform(scale)
    v["dn"] = v.groupby("province")["density"].transform(scale)
    v["vul"] = wp * v["pn"] + wd * v["dn"]
    v["risk"] = (v["province_code"].map(prob) * v["vul"]).clip(0, 1).round(4)
    return v


def spearman(a: pd.Series, b: pd.Series) -> float:
    return float(a.rank().corr(b.rank()))


def main():
    rec = L2.record()
    res = {}
    both, checks = audit_inputs(VUL, ROS)
    res["completeness"] = {k: v for k, v in checks.items() if k != "per_province"} | {"per_province": checks["per_province"]}
    prob = {c: v["forecast"]["probability"] for c, v in rec["provinces"].items()}
    r1 = build_ranking(VUL, ROS, prob, {"source": "E58 record 2027-Q1"})
    r2 = build_ranking(VUL, ROS, prob, {"source": "E58 record 2027-Q1"})
    res["reproducible_sha"] = r1["rows_sha256"] == r2["rows_sha256"]
    res["rows_sha256"] = r1["rows_sha256"]
    served = pd.DataFrame(r1["rows"])
    rep = replica(prob, 0.6, 0.4)
    m = served.merge(rep[["lgu_code", "risk"]], on="lgu_code")
    res["replica_max_abs_diff"] = float((m["risk_index"] - m["risk"]).abs().max())
    assert res["replica_max_abs_diff"] < 1e-9, "replica does not reproduce the served index"
    res["method"] = r1["method"]
    zero = served[served["risk_index"] == 0.0][["lgu_name", "province"]].to_dict("records")
    res["lgus_with_index_exactly_0"] = zero
    drv = {}
    rep["pop"] = rep["population_2024"]
    for p, g in rep.groupby("province"):
        drv[p] = {"n": int(len(g)), "spearman_vs_density": round(spearman(g["vul"], g["density"]), 3),
                  "spearman_vs_poverty": round(spearman(g["vul"], g["poverty_value_used"]), 3),
                  "spearman_vs_population": round(spearman(g["vul"], g["pop"]), 3),
                  "spearman_poverty_vs_density": round(spearman(g["poverty_value_used"], g["density"]), 3)}
    res["within_province_drivers"] = drv
    sens = []
    ref = rep
    for name, wp, wd, nm in [("0.5/0.5", .5, .5, "minmax"), ("0.7/0.3", .7, .3, "minmax"), ("0.8/0.2", .8, .2, "minmax"),
                             ("poverty only", 1, 0, "minmax"), ("density only", 0, 1, "minmax"),
                             ("0.6/0.4 rank-normalised", .6, .4, "rank")]:
        alt = replica(prob, wp, wd, nm)
        for p, g in ref.groupby("province"):
            a = alt[alt["province"] == p].set_index("lgu_code")["vul"]
            b = g.set_index("lgu_code")["vul"]
            top_ref = set(b.sort_values(ascending=False).index[:5])
            top_alt = set(a.sort_values(ascending=False).index[:5])
            sens.append({"variant": name, "province": p, "spearman_with_reference": round(spearman(a, b.loc[a.index]), 3),
                         "top5_overlap": len(top_ref & top_alt)})
    S = pd.DataFrame(sens)
    S.to_csv(E64 / "tables" / "r3_lgu_weight_sensitivity.csv", index=False, lineterminator="\n")
    res["sensitivity_summary"] = S.groupby("variant").agg(min_spearman=("spearman_with_reference", "min"),
                                                          mean_top5_overlap=("top5_overlap", "mean")).round(3).to_dict("index")
    # stability over the record's quarters
    stab = []
    prev_reg = None
    for q in sorted(L2.candidate_quarters(), key=lambda x: (int(x[:4]), int(x[-1]))):
        rows = L2.rows_for(q)
        pq = {r["province_code"]: r["risk_probability"] for r in rows}
        rq = replica(pq, 0.6, 0.4)
        # unrounded P x vulnerability keeps the vulnerability order whenever P > 0; the served 4-dp rounding can tie LGUs
        within_same = all(spearman(g["vul"] * pq[g["province_code"].iloc[0]], g["vul"]) > 0.999 for _, g in rq.groupby("province"))
        tied_lgus = int(sum((g["risk"].duplicated(keep=False)).sum() for _, g in rq.groupby("province")))
        reg = rq.set_index("lgu_code")["risk"]
        stab.append({"quarter": q, "within_province_order_equals_vulnerability_order": within_same,
                     "lgus_tied_within_province_after_4dp_rounding": tied_lgus,
                     "region_spearman_with_previous_quarter": None if prev_reg is None else round(spearman(reg, prev_reg.loc[reg.index]), 3),
                     "province_probabilities": {k: round(v, 3) for k, v in pq.items()}})
        prev_reg = reg
    res["stability"] = stab
    res["independent_municipal_outcomes"] = ("none in the project data: no CBMS, no municipal FIES, no PSA SAE after "
                                             "2021; the SAE 2021 poverty used here is an input, so it cannot validate "
                                             "the ranking")
    pd.DataFrame(r1["rows"]).to_csv(E64 / "tables" / "r3_lgu_ranking_2027Q1_e58.csv", index=False, lineterminator="\n")
    (E64 / "out" / "r3_lgu_audit.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("stability", "completeness")}, indent=1, default=str)[:4000])
    print("completeness passes:", checks["passes"], "| stability within-province constant:",
          all(s["within_province_order_equals_vulnerability_order"] for s in stab))
    print([(s["quarter"], s["region_spearman_with_previous_quarter"], s["lgus_tied_within_province_after_4dp_rounding"]) for s in stab])


if __name__ == "__main__":
    main()
