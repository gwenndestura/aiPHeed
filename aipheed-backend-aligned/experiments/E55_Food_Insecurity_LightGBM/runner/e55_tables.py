"""E55 tables from the committed run (no refitting): metrics, per-quarter accuracy, LightGBM diagnostics, poverty and
trigger ablations, reliability, sample-size calculation; and the prospective status of the frozen 2027-Q1 forecast.

    backend/venv/Scripts/python.exe -B runner/e55_tables.py   -> tables/*.csv, tables/sample_size.json, prospective_status.json
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

E55 = Path(__file__).resolve().parents[1]
RUN = E55 / "runs" / "20261017T153947Z"
OUT = E55 / "tables"


def main():
    r = json.loads((RUN / "results.json").read_text())
    M = r["metrics"]
    rows = []
    for a, m in M.items():
        rows.append({"arm": a, "n": m["n"], "accuracy": m["accuracy"], "acc_ci_low": m["accuracy_ci95"][0],
                     "acc_ci_high": m["accuracy_ci95"][1], "balanced_accuracy": m["balanced_accuracy"],
                     "recall_HIGH": m["recall_HIGH"], "recall_LOW": m["recall_LOW"], "precision_HIGH": m["precision_HIGH"],
                     "f1_HIGH": m["f1_HIGH"], "brier": m["brier"], "auc": m["auc"], **m["confusion"],
                     "citl": r["calibration"].get(a, {}).get("citl"), "cal_slope": r["calibration"].get(a, {}).get("slope"),
                     "paired_brier_vs_E55": r["paired_brier_vs_E55_LGBM"].get(a, {}).get("diff"),
                     "paired_ci_low": (r["paired_brier_vs_E55_LGBM"].get(a, {}).get("ci95") or [None, None])[0],
                     "paired_ci_high": (r["paired_brier_vs_E55_LGBM"].get(a, {}).get("ci95") or [None, None])[1]})
    pd.DataFrame(rows).round(4).to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame({a: M[a]["by_quarter"] for a in ("E55-LGBM", "I7", "E52", "B1_PERSIST", "LOW", "F2_offset")}).round(3) \
        .to_csv(OUT / "per_quarter.csv")
    R = pd.read_csv(RUN / "rows.csv", dtype={"province_code": str})
    pd.DataFrame([{"quarter": q, "rows": len(g), "HIGH": int(g["y"].sum()), "LOW": int((g["y"] == 0).sum())}
                  for q, g in R.groupby("target")]).to_csv(OUT / "rows_by_quarter.csv", index=False)
    pd.DataFrame(r["calibration"]["E55-LGBM"]["reliability"]).to_csv(OUT / "reliability_e55.csv", index=False)
    pd.DataFrame([{"arm": a, "verdict": v["verdict"], "dBrier": v["paired_brier"]["diff"],
                   "ci_low": v["paired_brier"]["ci95"][0], "ci_high": v["paired_brier"]["ci95"][1]}
                  for a, v in {**r["poverty"], **r["trigger_ablation"]}.items()]).round(5).to_csv(OUT / "poverty_and_ablation.csv", index=False)
    # sample size: quarters needed so that the 95% lower bound of quarter-clustered accuracy reaches 0.75
    pq = np.array(list(M["E55-LGBM"]["by_quarter"].values()))
    sd = float(pq.std(ddof=1))
    need = {str(true): (math.ceil((1.96 * sd / (true - 0.75)) ** 2) if true > 0.75 else None) for true in (0.78, 0.80, 0.85)}
    (OUT / "sample_size.json").write_text(json.dumps({
        "per_quarter_accuracy_sd": sd, "quarters_observed": int(len(pq)),
        "quarters_needed_for_lower_bound_0.75_given_true_accuracy": need,
        "rows_per_quarter": 5,
        "note": "normal approximation over quarter means (5 provinces per quarter); E55-LGBM per-quarter SD"}, indent=1))
    # prospective status
    fz = json.loads((E55 / "frozen" / "E55_LGBM_PROSPECTIVE_2027Q1.json").read_text())
    (E55 / "prospective_status.json").write_text(json.dumps({
        "file": "frozen/E55_LGBM_PROSPECTIVE_2027Q1.json",
        "sha256": (E55 / "frozen" / "E55_LGBM_PROSPECTIVE_2027Q1.json.sha256").read_text().split()[0],
        "targetQuarter": fz["targetQuarter"], "status": "PENDING",
        "outcome_needs": ["SWS 2027-Q1 hunger round (Balance Luzon) posted", "PSA provincial CPI Jan-Mar 2027 published"],
        "scoring": "T43 label per PROTOCOL section 2; decision p >= 0.5; accuracy, balanced accuracy, recalls, Brier"},
        indent=1))
    print("tables written; sample size", need, "sd", round(sd, 3))


if __name__ == "__main__":
    main()
