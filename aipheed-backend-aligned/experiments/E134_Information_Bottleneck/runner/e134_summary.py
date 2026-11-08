"""
E134 headline numbers and the machine-readable deliverables:
  out/e134_summary.json, E134_MODEL_COMPARISON.csv, E134_WALK_FORWARD_RESULTS.csv, E134_FEATURE_CONTRIBUTION_REPORT.csv

    python -I runner/e134_summary.py      (after e134_run.py and e134_diagnostics.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e134_run as E  # noqa: E402

L, OUT, ROOT = E.L, E.OUT, E.ROOT
E133 = E.EXP / "E133_Forecasting_Breakthrough"
SELECTABLE = ["E134-AREA-T", "E134-AREA-O", "E134-ENS", "HFM-X", "SEAS-LLM"]


def main():
    Mt = pd.read_csv(OUT / "e134_metrics.csv")
    rules = json.loads((OUT / "e134_rules.json").read_text())
    s = {}
    g = Mt[(Mt.set == "S-U") & (Mt.policy == "P-DASH") & (Mt.lead == 2) & Mt.model.isin(SELECTABLE)]
    g = g.sort_values(["within_tolerance", "mae"], ascending=[False, True])
    cand = g["model"].iloc[0]
    s["selection"] = {"rule": "highest Lead-2 within, S-U, P-DASH; ties lower MAE", "candidate": cand,
                      "table": g[["model", "n", "n_quarters", "within_tolerance", "mae", "rmse"]].round(4).to_dict("records")}
    passed, s["rules_by_lead"] = {}, {}
    for m in ["HFM-X", "SEAS-LLM", "E134-AREA-T", "E134-AREA-O", "E134-ONI", "E134-ENS"]:
        for k in L.LEADS:
            su, se = rules[f"S-U|P-DASH|{k}|{m}"], rules.get(f"S-E132|P-DASH|{k}|{m}")
            ok = su["passed"] and se is not None and se["rules"]["N2_within_tolerance_75"] and se["rules"]["N3_beats_every_baseline_mae_rmse"]
            if m == cand:
                passed[k] = bool(ok)
            s["rules_by_lead"][f"{m}|{k}"] = {"S-U_failed": [n for n, v in su["rules"].items() if not v], "within": su["within"],
                                              "mae": su["mae"], "rows": su["n_rows"], "quarters": su["n_quarters"],
                                              "coverage80": su["coverage80"], "p_vs_persistence": su["p_vs_persistence"],
                                              "S-E132_failed": [n for n, v in se["rules"].items() if not v] if se else None,
                                              "validated": bool(ok)}
    s["maximum_reliable_lead"] = L.maximum_reliable_lead(passed)
    s["any_rule_set_passed"] = [k for k, v in rules.items() if v["passed"]]
    s["any_model_any_lead_75"] = bool((Mt.loc[Mt.set.isin(["S-U", "S-E132"]), "within_tolerance"] >= 0.75).any())
    gap = Mt[(Mt.set == "S-U") & (Mt.policy == "P-DASH") & (Mt.lead == 2) & (Mt.model == cand)].iloc[0]
    s["gap_to_75_lead2_rows"] = {"within": float(gap["within_tolerance"]), "rows": int(gap["n"]),
                                 "rows_within": int(round(gap["within_tolerance"] * gap["n"])),
                                 "rows_needed_for_75": int(-(-0.75 * gap["n"] // 1)),
                                 "additional_rows_needed": int(-(-0.75 * gap["n"] // 1) - round(gap["within_tolerance"] * gap["n"]))}
    L.dump(s, OUT / "e134_summary.json")

    keep = Mt[Mt.model.isin(["PERSIST", "CLIM", "LLM", "SEAS-LLM", "HFM-NS-DES", "HFM-X", *E.NEW, *E.R.E132_BASE])]
    cols = [c for c in ["set", "policy", "lead", "model", "n", "n_quarters", "mae", "rmse", "bias", "within_tolerance",
                        "coverage80", "direction_accuracy", "bias_low", "bias_mid", "bias_high", "sharp_n", "sharp_within",
                        "within_metro_manila", "within_balance_luzon", "within_visayas", "within_mindanao"] if c in keep]
    keep[cols].sort_values(["set", "policy", "lead", "model"]).to_csv(ROOT / "E134_MODEL_COMPARISON.csv", index=False)
    P = pd.read_csv(OUT / "e134_predictions.csv")
    wf = ["policy", "D", "issue", "lead", "target", "area", "period", "n_obs", "h", "y_latest", "y_true", "se", "tol"]
    fm = ["PERSIST", "SEAS-LLM", "HFM-X", *E.NEW]
    W = P[wf + [f"f_{m}" for m in fm] + [f"lo80_{m}" for m in fm if f"lo80_{m}" in P] + [f"hi80_{m}" for m in fm if f"hi80_{m}" in P]].copy()
    for m in fm:
        W[f"within_{m}"] = (W[f"f_{m}"] - W["y_true"]).abs() <= W["tol"]
    W.to_csv(ROOT / "E134_WALK_FORWARD_RESULTS.csv", index=False)

    tc = pd.read_csv(E133 / "out" / "e133_ablation.csv")
    tc = tc[tc.policy == "P-DASH"].copy()
    tc["source"] = "E133 ablation on HFM-X (reproduced exactly in E134 baseline)"
    tc = tc.rename(columns={"variant": "comparison", "p_full_better_sq_error": "p_with_group_better_sq_error"})
    ab = pd.read_csv(OUT / "e134_area_ablation.csv")
    ab = ab[ab.policy == "P-DASH"].copy()
    ab["source"] = "E134 area-driver ablation on E134-AREA-T"
    ab = ab.rename(columns={"mae_reference": "mae_full", "mae_variant": "mae_variant", "within_reference": "within_full",
                            "p_reference_better_sq_error": "p_with_group_better_sq_error",
                            "delta_mae_variant_minus_reference": "delta_mae_when_removed",
                            "delta_within_variant_minus_reference": "delta_within_when_removed"})
    F = pd.concat([tc, ab], ignore_index=True)
    rm = F["comparison"].astype(str).str.contains("minus")
    F["demonstrated_E133_criterion"] = rm & (F["delta_mae_when_removed"] > 0) & (F["delta_within_when_removed"] < 0) & (F["p_with_group_better_sq_error"] < 0.10)
    F[["source", "lead", "comparison", "rows", "mae_full", "mae_variant", "within_full", "within_variant",
       "delta_mae_when_removed", "delta_within_when_removed", "p_with_group_better_sq_error",
       "demonstrated_E133_criterion"]].to_csv(ROOT / "E134_FEATURE_CONTRIBUTION_REPORT.csv", index=False)
    print(json.dumps({k: s[k] for k in ("selection", "maximum_reliable_lead", "any_rule_set_passed", "any_model_any_lead_75",
                                        "gap_to_75_lead2_rows")}, indent=1)[:3000])
    for k in L.LEADS:
        print(k, s["rules_by_lead"][f"{cand}|{k}"])


if __name__ == "__main__":
    main()
