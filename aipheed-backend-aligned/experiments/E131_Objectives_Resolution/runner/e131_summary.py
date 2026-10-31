"""
E131 summary numbers for the reports and tests: target precision, required forecast precision, headline metrics,
per-area and bias breakdowns, the selection-rule outcome and the maximum reliable lead per model.

    python -I runner/e131_summary.py      (after e131_x1.py, e131_univariate.py, e131_provincial.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
sys.path.insert(0, str(ROOT.parent / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
import e130_lib as L  # noqa: E402

MODELS = ["PERSIST", "CLIM", "LLM", "DLLM", "RIDGE-H", "LGBM-H", "RIDGE-ALL", "LGBM-ALL", "PSA-ONLY", "NLP-ONLY"]
CANDIDATES = ["LLM", "DLLM", "RIDGE-H", "LGBM-H", "RIDGE-ALL", "LGBM-ALL", "PSA-ONLY", "NLP-ONLY"]


def main():
    qt = pd.read_csv(OUT / "x1_target_quarters.csv")
    M = pd.read_csv(OUT / "x1_metrics.csv")
    U = pd.read_csv(OUT / "x1_univariate_metrics.csv")
    R = json.load(open(OUT / "x1_rules.json"))
    RU = json.load(open(OUT / "x1_univariate_rules.json"))
    P = pd.read_csv(OUT / "x1_predictions.csv")
    s = {}
    s["target"] = {"area_quarters": int(len(qt)), "quarters": int(qt["quarter"].nunique()),
                   "median_se_pp": float(qt["se"].median()), "median_tolerance_pp": float(qt["tol"].median()),
                   "required_forecast_sd_pp": float(L.required_forecast_sd_over_se(0.75) * qt["se"].median())}
    lead2 = M[(M.policy == "P-DASH") & (M.lead == 2) & M.model.isin(CANDIDATES)].sort_values(["within_tolerance", "mae"],
                                                                                             ascending=[False, True])
    s["selection"] = {"candidate": lead2["model"].iloc[0], "lead2_within": float(lead2["within_tolerance"].iloc[0]),
                      "lead2_mae": float(lead2["mae"].iloc[0]), "ranking": lead2[["model", "within_tolerance", "mae"]].round(4).to_dict("records")}
    s["best_within_any"] = M.sort_values("within_tolerance", ascending=False).head(3)[["policy", "lead", "model", "within_tolerance", "n"]].to_dict("records")
    s["rows_common"] = M[M.model == "PERSIST"][["policy", "lead", "n", "n_target_quarters"]].to_dict("records")
    s["rows_univariate"] = U[U.model == "PERSIST"][["policy", "lead", "n", "n_target_quarters"]].to_dict("records")
    s["any_rule_set_passed"] = [k for k, v in {**R, **RU}.items() if v["passed"]]
    mrl = {}
    for m in CANDIDATES:
        passed = {k: bool(R.get(f"P-DASH|{k}|{m}", {}).get("passed", False)) for k in L.LEADS}
        mrl[m] = L.maximum_reliable_lead(passed)
    s["max_reliable_lead_P_DASH"] = mrl
    s["llm_lead2_rules_common"] = R["P-DASH|2|LLM"]["rules"]
    s["llm_lead2_rules_univariate"] = RU["P-DASH|2|LLM"]["rules"]
    # per area and bias, candidate at Lead 2 (P-DASH, common rows)
    c = P[(P.policy == "P-DASH") & (P.lead == 2)].dropna(subset=[f"f_{m}" for m in MODELS]).copy()
    c["err"] = c["f_LLM"] - c["y_true"]
    s["llm_lead2_per_area"] = {a: {"rows": int(len(g)), "mae": float(g["err"].abs().mean()), "bias": float(g["err"].mean()),
                                   "within": float((g["err"].abs() <= g["tol"]).mean())} for a, g in c.groupby("area")}
    c["tercile"] = pd.qcut(c["y_true"], 3, labels=["low", "middle", "high"])
    s["llm_lead2_by_level"] = {str(t): {"rows": int(len(g)), "bias": float(g["err"].mean()), "mae": float(g["err"].abs().mean())}
                               for t, g in c.groupby("tercile", observed=True)}
    jump = (c["y_true"] - c["y_latest"]) > 2 * c["se"]
    s["sharp_increases_lead2"] = {"rows": int(jump.sum()),
                                  "llm_within": float((c.loc[jump, "err"].abs() <= c.loc[jump, "tol"]).mean()) if jump.any() else None,
                                  "llm_mean_error": float(c.loc[jump, "err"].mean()) if jump.any() else None,
                                  "persist_mean_error": float((c.loc[jump, "f_PERSIST"] - c.loc[jump, "y_true"]).mean()) if jump.any() else None}
    g = P[(P.policy == "P-DASH") & (P.lead == 2)].dropna(subset=["f_LGBM-ALL"])
    s["overfitting_lgbm_all_lead2"] = {"train_mae": float(g["train_mae_LGBM-ALL"].mean()),
                                       "oos_mae": float((g["f_LGBM-ALL"] - g["y_true"]).abs().mean()),
                                       "trees_with_splits": float(g["trees_LGBM-ALL"].mean())}
    s["seeds_lgbm_all"] = pd.read_csv(OUT / "x1_seed_sensitivity.csv").groupby("lead")["mae"].agg(["min", "max"]).to_dict("index")
    a = pd.read_csv(OUT / "x3a_price_income_decomposition.csv")
    s["x3a"] = a[["province", "official_change_pp", "price_effect_pp", "income_effect_pp", "replication_gap_pp",
                  "threshold_growth_pct", "food_cpi_growth_pct", "cpi_threshold_error_pct"]].round(4).to_dict("records")
    s["x3b"] = json.load(open(OUT / "x3b_pattern_stability.json"))
    L.dump(s, OUT / "e131_summary.json")
    print(json.dumps({k: s[k] for k in ("target", "selection", "best_within_any", "any_rule_set_passed", "max_reliable_lead_P_DASH",
                                        "llm_lead2_per_area", "llm_lead2_by_level", "sharp_increases_lead2",
                                        "overfitting_lgbm_all_lead2")}, indent=1, default=str)[:4500])


if __name__ == "__main__":
    main()
