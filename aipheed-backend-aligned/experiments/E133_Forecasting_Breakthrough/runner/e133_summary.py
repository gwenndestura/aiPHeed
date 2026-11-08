"""
E133 headline numbers for the final package (out/e133_summary.json, out/e133_trigger_contribution.csv), all read
from the run outputs: frozen-rule selection, N1-N7 by lead, maximum reliable lead, trigger-group status, in-sample
versus out-of-sample error, beta stability.

    python -I runner/e133_summary.py      (after e133_run.py, e133_diagnostics.py, e133_sensitivity.py)
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e133_models as M  # noqa: E402
import e133_run as R  # noqa: E402

X, L = R.X, R.L
OUT = R.OUT
SELECTABLE = R.NEW + ["SEAS-LLM"]


def main():
    Mt = pd.read_csv(OUT / "e133_metrics.csv")
    rules = json.loads((OUT / "e133_rules.json").read_text())
    s = {}
    g = Mt[(Mt.set == "S-U") & (Mt.policy == "P-DASH") & (Mt.lead == 2) & Mt.model.isin(SELECTABLE)]
    g = g.sort_values(["within_tolerance", "mae"], ascending=[False, True])
    cand = g["model"].iloc[0]
    s["selection"] = {"rule": "highest Lead-2 within, S-U, P-DASH; ties lower MAE", "candidate": cand,
                      "table": g[["model", "n", "within_tolerance", "mae", "rmse"]].round(4).to_dict("records")}
    passed = {}
    s["candidate_rules"] = {}
    for k in L.LEADS:
        su = rules[f"S-U|P-DASH|{k}|{cand}"]
        se = rules.get(f"S-E132|P-DASH|{k}|{cand}")
        ok = su["passed"] and se is not None and se["rules"]["N2_within_tolerance_75"] and se["rules"]["N3_beats_every_baseline_mae_rmse"]
        passed[k] = bool(ok)
        s["candidate_rules"][k] = {"S-U_failed": [n for n, v in su["rules"].items() if not v],
                                   "S-U_within": su["within"], "S-U_mae": su["mae"], "S-U_rows": su["n_rows"],
                                   "S-U_quarters": su["n_quarters"], "p_vs_persistence": su["p_vs_persistence"],
                                   "coverage80": su["coverage80"], "within_thirds": su["within_thirds"],
                                   "S-E132_failed": [n for n, v in se["rules"].items() if not v] if se else None,
                                   "validated": bool(ok)}
    s["maximum_reliable_lead"] = L.maximum_reliable_lead(passed)
    s["any_model_any_lead_75"] = bool((Mt["within_tolerance"] >= 0.75).any())
    s["best_within_any"] = Mt.sort_values("within_tolerance", ascending=False).head(5)[
        ["set", "policy", "lead", "model", "n", "within_tolerance"]].to_dict("records")
    s["any_rule_set_passed"] = [k for k, v in rules.items() if v["passed"]]

    # trigger groups: demonstrated = removing the group worsens MAE and within and p < 0.10 (protocol section 5)
    A = pd.read_csv(OUT / "e133_ablation.csv")
    A = A[(A.policy == "P-DASH") & A.variant.str.startswith("X-minus-")]
    A["group"] = A["variant"].str[-1]
    A["demonstrated"] = (A["delta_mae_when_removed"] > 0) & (A["delta_within_when_removed"] < 0) & (A["p_full_better_sq_error"] < 0.10)
    A.to_csv(OUT / "e133_trigger_contribution.csv", index=False)
    s["trigger_demonstrated_by_lead"] = {int(k): sorted(g.loc[g.demonstrated, "group"]) for k, g in A.groupby("lead")}

    # in-sample versus out-of-sample (HFM-X at the seal date)
    rr = X.rounds()
    issue = date(2026, 11, 1)
    qa = X.asof(rr, issue)
    drv = {"rice": R.Drivers("rice")}
    fit, Z, vals, last, w = R.x_fit(qa, issue, drv["rice"], "rice", R.ALL_GROUPS)
    b = R.base_fits(qa)
    innov = M.kfilter(b["Yd"], b["R"], b["idx"], fit, R.BRK, Z, w)[3]
    P = pd.read_csv(OUT / "e133_predictions.csv")
    p1 = P[(P.policy == "P-DASH") & (P.lead == 1) & (P.n_obs >= 8)]
    s["overfitting"] = {"parameters": 5 + len(R.ALL_GROUPS), "observations": int(np.isfinite(b["Y"]).sum()),
                        "in_sample_one_step_mae": float(np.mean(np.abs(list(innov.values())))),
                        "out_of_sample_lead1_mae": float(np.abs(p1["f_HFM-X"] - p1["y_true"]).mean()),
                        "beta_at_seal": fit.beta}
    betas = P[(P.policy == "P-DASH") & (P.n_obs >= 8)].groupby("D")[[f"beta_{g}" for g in R.ALL_GROUPS]].first()
    s["beta_by_issue"] = betas.round(3).to_dict("index")
    L.dump(s, OUT / "e133_summary.json")
    print(json.dumps({k: s[k] for k in ("selection", "candidate_rules", "maximum_reliable_lead", "any_model_any_lead_75",
                                        "any_rule_set_passed", "trigger_demonstrated_by_lead", "overfitting")}, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
