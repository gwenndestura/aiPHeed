"""E39 label diagnostics (labels only; no model). Nothing here changes the frozen specification.

    <backend venv python> -B runner/e39_diagnostics.py   -> runs/diagnostics.json, DIAGNOSTICS.md
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

E39 = Path(__file__).resolve().parents[1]
ROOT = E39.parents[2]
INP = ROOT / "backend" / "data" / "inputs"
E12 = E39.parent / "E25_Reliable_Forecasts_2021_2026" / "inputs" / "e12" / "realized_components_2021_2025.csv"
FREEZE = json.loads((E39 / "frozen" / "E39_FREEZE.json").read_text())


def kappa(a: pd.Series, b: pd.Series) -> float:
    po = (a == b).mean()
    pe = sum((a == c).mean() * (b == c).mean() for c in set(a) | set(b))
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def main():
    for f, h in FREEZE["sha256"].items():
        assert hashlib.sha256((E39 / f).read_bytes()).hexdigest() == h, f"{f} changed after freezing"
    L = pd.read_csv(E39 / "label_v2.csv", dtype={"province_code": str})
    L["year"] = L["quarter"].str[:4]
    hi = L["label_A"] == "HIGH"
    per_q = L.assign(hi=hi).groupby("quarter")["hi"].sum()
    out = {"labelled_dates_A_B": sorted(L["quarter"].unique()),
           "labelled_dates_C": sorted(L.dropna(subset=["H"])["quarter"].unique()),
           "previously_missing_quarters_now_with_CPI_values": {q: bool((L["quarter"] == q).any())
                                                              for q in ("2021-Q1", "2022-Q1", "2025-Q2", "2025-Q3")},
           "D1_prevalence": {"overall": {"HIGH": int(hi.sum()), "rows": int(len(L)), "share": float(hi.mean())},
                             "by_year": {y: {"HIGH": int((g["label_A"] == "HIGH").sum()), "rows": int(len(g)),
                                             "share": float((g["label_A"] == "HIGH").mean())}
                                         for y, g in L.groupby("year")}},
           "D2_dates": {"with_at_least_one_HIGH": int((per_q > 0).sum()), "with_none": int((per_q == 0).sum()),
                        "dates_with_none": per_q[per_q == 0].index.tolist(), "total": int(len(per_q))},
           "D3_mixed": {"mixed_dates": int(((per_q > 0) & (per_q < 5)).sum()), "all_five_HIGH": int((per_q == 5).sum()),
                        "all_five_HIGH_dates": per_q[per_q == 5].index.tolist(), "HIGH_count_by_date": per_q.astype(int).to_dict()}}
    # D4 recomputation: 2021-2025 F against the E12 published quarter means; 2026 checked at build time
    e12 = pd.read_csv(E12, dtype={"province_code": str})
    m = L.merge(e12[["province_code", "quarter", "F"]], on=["province_code", "quarter"], suffixes=("", "_e12"))
    out["D4_recompute"] = {"rows_compared": int(len(m)), "max_abs_diff": float((m["F"] - m["F_e12"]).abs().max()),
                           "labels_reproduced": bool(((m["F_e12"] > 4.0) == (m["F"] > 4.0)).all()),
                           "2026_rows": "F equals the mean of the PSA published monthly YoY (asserted when label_v2.csv was built)"}
    # D5 sensitivity (information only)
    sens = {}
    for c in ("label_A_3pct_info", "label_A_5pct_info"):
        sens[c.split("_")[2]] = {"HIGH_share": float((L[c] == "HIGH").mean()),
                                 "dates_with_HIGH": int(L.assign(h=L[c] == "HIGH").groupby("quarter")["h"].sum().gt(0).sum()),
                                 "kappa_vs_4pct": kappa(L[c], L["label_A"])}
    out["D5_sensitivity_information_only"] = {**sens, "rule": "reported only; the 4% threshold is not changed"}
    # D6 descriptive context only
    vul = pd.read_csv(INP / "lgu_vulnerability.csv", dtype={"lgu_code": str})
    v = vul[vul["poverty_lgu_estimate"].notna()]
    pov = (v.assign(w=v.population_2024 * v.poverty_lgu_estimate).groupby("province")[["w", "population_2024"]].sum())
    pov = (pov["w"] / pov["population_2024"]).sort_values(ascending=False)
    meanF = L.groupby("province")["F"].mean().sort_values(ascending=False)
    out["D6_context_no_validation"] = {
        "mean_F_by_province_2021_2026": meanF.round(3).to_dict(),
        "PSA_2021_poverty_pop_weighted_SAE": pov.round(2).to_dict(),
        "spearman_meanF_vs_poverty": float(meanF.rank().corr(pov.reindex(meanF.index).rank(), method="spearman")),
        "NNS_2023_FIES_CALABARZON": "19.1% of households (annual, regional, absolute experience scale): different "
                                    "geography, period and construct; no comparison is a validation",
        "HIGH_share_2023": out["D1_prevalence"]["by_year"].get("2023", {}).get("share"),
        "statement": "context only; no validation is claimed"}
    # D7 v1 vs v2 per date (v1 at its lead-1 tau, from Phase 0)
    p0 = json.loads((E39 / "runs" / "phase0_v1_check.json").read_text())
    tau = {x["target"]: x["tau"] for x in p0["per_date"] if x["tau"] is not None}
    s1 = pd.read_csv(INP / "s1_labels.csv", dtype={"province_code": str})
    j = s1[s1["quarter"].isin(tau)].merge(L, on=["province_code", "quarter"])
    j["v1"] = (j["S1"] > j["quarter"].map(tau)).map({True: "HIGH", False: "NOT HIGH"})
    cm = pd.crosstab(j["v1"], j["label_A"])
    out["D7_v1_vs_v2"] = {"rows": int(len(j)), "confusion_v1_rows_v2_cols": cm.to_dict(),
                          "agreement": float((j["v1"] == j["label_A"]).mean()),
                          "per_date": {q: {"v1_HIGH": int((g["v1"] == "HIGH").sum()), "v2_HIGH": int((g["label_A"] == "HIGH").sum()),
                                           "disagree": int((g["v1"] != g["label_A"]).sum())} for q, g in j.groupby("quarter")},
                          "explanation": "v1 HIGH follows regional hunger above a lagging median (shared by all "
                                         "provinces); v2 HIGH follows each province's own food inflation above 4%. "
                                         "They disagree when hunger is high while food inflation is low (2024-2026) "
                                         "and when food inflation is high while hunger is near its median (2022-2023)."}
    out["D8_no_leakage"] = ("each label uses only its own quarter's published CPI (and, for C, its own posted rounds); "
                            "the only constant is 4.0 (BSP target ceiling); no reference window, no fitted anchor")
    (E39 / "runs").mkdir(exist_ok=True)
    (E39 / "runs" / "diagnostics.json").write_bytes(json.dumps(out, indent=1, default=float).encode())
    md = ["# E39 diagnostics: Food Price Pressure (exploratory)", "",
          "Labels only, no model. Nothing here changed the frozen specification (4% fixed).", "",
          f"- Labelled dates, A and B: {len(out['labelled_dates_A_B'])} (2021-Q1..2026-Q3). The quarters missing for "
          "SWS (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3) all have CPI-based values.",
          f"- Labelled dates, C (regional hunger): {len(out['labelled_dates_C'])}.",
          f"- D1 HIGH overall: {out['D1_prevalence']['overall']['HIGH']}/{out['D1_prevalence']['overall']['rows']} "
          f"({out['D1_prevalence']['overall']['share']:.1%}). By year: " +
          ", ".join(f"{y} {v['HIGH']}/{v['rows']}" for y, v in out["D1_prevalence"]["by_year"].items()),
          f"- D2 dates with at least one HIGH province: {out['D2_dates']['with_at_least_one_HIGH']}; with none: "
          f"{out['D2_dates']['with_none']} ({', '.join(out['D2_dates']['dates_with_none'])}).",
          f"- D3 mixed dates: {out['D3_mixed']['mixed_dates']}; all five HIGH: {out['D3_mixed']['all_five_HIGH']} "
          f"({', '.join(out['D3_mixed']['all_five_HIGH_dates'])}).",
          f"- D4 recomputation: {out['D4_recompute']['rows_compared']} rows vs the PSA published quarter means, max diff "
          f"{out['D4_recompute']['max_abs_diff']:.1e}; labels reproduced: {out['D4_recompute']['labels_reproduced']}.",
          "- D5 sensitivity (information only): " + "; ".join(
              f"{k}: HIGH share {v['HIGH_share']:.1%}, dates with HIGH {v['dates_with_HIGH']}, kappa vs 4% {v['kappa_vs_4pct']:.2f}"
              for k, v in sens.items()),
          f"- D6 context only: mean food inflation by province {out['D6_context_no_validation']['mean_F_by_province_2021_2026']}; "
          f"PSA 2021 poverty {out['D6_context_no_validation']['PSA_2021_poverty_pop_weighted_SAE']}; Spearman "
          f"{out['D6_context_no_validation']['spearman_meanF_vs_poverty']:.2f} (n = 5). NNS 2023 FIES 19.1% is a different "
          "construct; no validation is claimed.",
          f"- D7 v1 vs v2: agreement {out['D7_v1_vs_v2']['agreement']:.1%} on {out['D7_v1_vs_v2']['rows']} rows. "
          + out["D7_v1_vs_v2"]["explanation"],
          "- D8 " + out["D8_no_leakage"], ""]
    (E39 / "DIAGNOSTICS.md").write_bytes("\n".join(md).encode())
    print("\n".join(md))
    print(json.dumps(out["D7_v1_vs_v2"]["confusion_v1_rows_v2_cols"]))


if __name__ == "__main__":
    main()
