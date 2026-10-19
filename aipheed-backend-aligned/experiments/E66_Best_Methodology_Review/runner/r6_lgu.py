"""E66 r6 (PROTOCOL 2.6): 142-LGU audit and rank sensitivity of the approved Objective 3 method.

    cd backend && venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E66_Best_Methodology_Review/runner/r6_lgu.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import e66_lib as H  # noqa: E402

np, pd = H.np, H.pd
sys.path.insert(0, str(H.BACKEND))
import app.quarterly.lgu_poverty as LP  # noqa: E402
from app.quarterly.lgu_audit import audit_inputs  # noqa: E402

VUL = H.BACKEND / "data" / "inputs" / "lgu_vulnerability.csv"
ROS = H.BACKEND / "data" / "reference" / "calabarzon_lgus.csv"
RECORD = H.BACKEND / "data" / "e58" / "e58_record.json"


def rank(vuln, prob, wp=0.6, exact=False):
    census = vuln[["lgu_code", "lgu_name", "province_code", "population_2024", "land_area_km2"]]
    pov = vuln[["lgu_code", "poverty_lgu_estimate", "poverty_value_used"]].rename(
        columns={"poverty_value_used": "poverty_province_value"})
    old = (LP.POVERTY_WEIGHT, LP.DENSITY_WEIGHT)
    LP.POVERTY_WEIGHT, LP.DENSITY_WEIGHT = wp, 1 - wp
    try:
        m = LP.rank_lgus(census, pov, prob, exact_ranks=exact)
    finally:
        LP.POVERTY_WEIGHT, LP.DENSITY_WEIGHT = old
    return m.set_index("lgu_code")


def main():
    H.verify_protocol()
    vul = pd.read_csv(VUL, dtype={"lgu_code": str})
    ros = pd.read_csv(ROS, dtype={"lgu_psgc": str})
    both, checks = audit_inputs(vul, ros)
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    prob = {c: p["forecast"]["probability"] for c, p in rec["provinces"].items()}
    base = rank(both, prob)
    exact = rank(both, prob, exact=True)
    out = {"input_checks_pass": checks["passes"], "lgus": int(len(base)), "unique": int(base.index.nunique()),
           "per_province": both.groupby("province").size().to_dict(),
           "finite_risk_index": int(np.isfinite(base["risk_index"]).sum()),
           "substitutes": checks["province_mean_substitutes"], "lgu_estimates": checks["lgu_specific_poverty_estimates"],
           "province_probabilities_2027Q1_e58": prob}
    # 1. within-province order equals the vulnerability order whatever the province probability
    same = all((g["rank_in_province"] == g["vulnerability_rank_in_province"]).all()
               for _, g in exact.groupby("province_code"))
    out["within_province_rank_equals_vulnerability_rank"] = bool(same)
    # 2. ties created by 4-dp rounding of small probabilities
    out["tied_lgus_rounded_4dp"] = int(base["risk_index"].duplicated(keep=False).sum())
    out["tied_lgus_exact"] = int(exact["risk_index_exact"].duplicated(keep=False).sum())
    out["rank_region_changes_exact_vs_4dp"] = int((exact["rank_region"] != base.loc[exact.index, "rank_region"]).sum())
    # 3. weight sensitivity of within-province order
    sens = []
    for wp in (0.0, 0.5, 0.7, 1.0):
        alt = rank(both, prob, wp, exact=True)
        for pc, g in exact.groupby("province_code"):
            a = alt.loc[g.index]
            top5 = set(g.nsmallest(5, "rank_in_province").index)
            top5a = set(a.nsmallest(5, "rank_in_province").index)
            sens.append({"poverty_weight": wp, "province_code": pc, "n": len(g),
                         "spearman_vs_approved": float(g["rank_in_province"].corr(a["rank_in_province"], method="spearman")),
                         "top5_overlap": len(top5 & top5a)})
    S = pd.DataFrame(sens)
    H.write_csv(S, H.TABLES / "r6_lgu_weight_sensitivity.csv")
    # 4. region-wide order: how much is the province probability vs the within-province index
    out["region_rank_spearman_with_province_probability"] = float(
        exact["rank_region"].corr(exact["province_probability"].rank(ascending=False), method="spearman"))
    out["region_rank_spearman_with_vulnerability"] = float(
        exact["rank_region"].corr(exact["vulnerability_index"].rank(ascending=False), method="spearman"))
    # 5. the substitute LGU (Lucena) position sensitivity: substitute value at province min / max
    subs = both[both["poverty_lgu_estimate"].isna()]
    sub_rows = []
    for _, r in subs.iterrows():
        prov = both[both["province_code"] == r["province_code"]]
        for label, val in (("approved substitute", r["poverty_value_used"]),
                           ("province min", prov["poverty_lgu_estimate"].min()),
                           ("province max", prov["poverty_lgu_estimate"].max())):
            alt = both.copy()
            alt.loc[alt["lgu_code"] == r["lgu_code"], "poverty_value_used"] = val
            a = rank(alt, prob, exact=True)
            sub_rows.append({"lgu": r["lgu_name"], "case": label, "poverty_value": val,
                             "rank_in_province": int(a.loc[r["lgu_code"], "rank_in_province"]),
                             "of": int((a["province_code"] == r["province_code"]).sum())})
    U = pd.DataFrame(sub_rows)
    H.write_csv(U, H.TABLES / "r6_substitute_sensitivity.csv")
    exact.reset_index()[["lgu_code", "lgu_name", "province_code", "poverty_value_kind", "vulnerability_index",
                         "province_probability", "risk_index", "risk_index_exact", "rank_region", "rank_in_province"]].pipe(
        lambda d: H.write_csv(d, H.TABLES / "r6_lgu_ranking_2027Q1_e58_exact.csv"))
    out["weight_sensitivity_summary"] = S.groupby("poverty_weight")[["spearman_vs_approved", "top5_overlap"]].mean().to_dict()
    out["substitute_sensitivity"] = U.to_dict("records")
    H.dump(out, H.OUT / "r6_lgu.json")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
