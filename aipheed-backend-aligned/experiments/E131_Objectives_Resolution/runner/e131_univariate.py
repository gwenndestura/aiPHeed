"""
E131 X1 univariate evaluation (protocol section 2: each model is evaluated on every dashboard quarter where it has
at least 8 observed quarters for the area). Persistence, climatology, LLM and DLLM on that larger set, with N1-N7
against persistence and climatology (the learned baselines do not exist on the early rows).

    python -I runner/e131_univariate.py      (after e131_x1.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT.parent / "E130_Provincial_Risk_Score_Forecasting" / "runner"))
import e130_lib as L  # noqa: E402

UNI = ["PERSIST", "CLIM", "LLM", "DLLM"]


def main():
    P = pd.read_csv(ROOT / "out" / "x1_predictions.csv")
    P = P[(P["n_obs"] >= 8)].dropna(subset=[f"f_{m}" for m in UNI])
    rows, rules = [], {}
    for (pol, k), g in P.groupby(["policy", "lead"]):
        d = g.rename(columns={"y_true": "y", "area": "province", "f_PERSIST": "f_persistence", "f_CLIM": "f_climatology"})
        for m in UNI:
            col = {"PERSIST": "f_persistence", "CLIM": "f_climatology"}.get(m, f"f_{m}")
            met = L.numeric_metrics(d["y"], d[col], d["se"], prev=d["y_latest"], clim=d["f_climatology"])
            met.update(policy=pol, lead=int(k), model=m, n_target_quarters=int(d["target_q"].nunique()),
                       first_target=d["target"].min(), last_target=d["target"].max())
            if m in ("LLM", "DLLM"):
                met["coverage80"] = float(np.mean((d["y"] >= d[f"lo80_{m}"]) & (d["y"] <= d[f"hi80_{m}"])))
                rel = L.numeric_reliability(d, m, ["persistence", "climatology"])
                rules[f"{pol}|{k}|{m}"] = {"rules": rel["rules"], "passed": rel["passed"], "within_thirds": rel["within_thirds"],
                                           "loqo_min_within": rel["loqo_min_within"], "p_vs_persistence": rel["p_sq_error_vs_persistence"],
                                           "p_vs_climatology": rel["p_sq_error_vs_climatology"], "per_area": rel["per_province"]}
            rows.append(met)
    M = pd.DataFrame(rows)
    M.to_csv(ROOT / "out" / "x1_univariate_metrics.csv", index=False)
    L.dump(rules, ROOT / "out" / "x1_univariate_rules.json")
    print(M.pivot_table(index=["policy", "model"], columns="lead", values="within_tolerance").round(3).to_string())
    print(M.pivot_table(index=["policy", "model"], columns="lead", values="mae").round(2).to_string())
    print(M[M.model == "LLM"][["policy", "lead", "n", "n_target_quarters", "first_target", "last_target", "coverage80"]].to_string(index=False))
    for key, r in rules.items():
        print(key, "passed" if r["passed"] else "failed", [k for k, v in r["rules"].items() if not v])


if __name__ == "__main__":
    main()
