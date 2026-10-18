"""E56 tables from the committed run (no refitting): metrics, per quarter, per province, selected configurations,
province spread, reliability, and the 50-row supplementary block.

    backend/venv/Scripts/python.exe -B runner/e56_tables.py   -> tables/*.csv
"""
import json
from pathlib import Path

import pandas as pd

E56 = Path(__file__).resolve().parents[1]
RUN = sorted(p for p in (E56 / "runs").glob("2026*"))[0]
OUT = E56 / "tables"


def main():
    r = json.loads((RUN / "results.json").read_text())
    rows = []
    for a, m in r["metrics"].items():
        cal = r["calibration"].get(a, {})
        pb = r["paired_brier_E56_minus"].get(a, {})
        rows.append({"model": a, "n": m["n"], "quarters": m["n_quarters"], "accuracy": m["accuracy"],
                     "acc_ci_low": m["accuracy_ci95"][0], "acc_ci_high": m["accuracy_ci95"][1],
                     "balanced_accuracy": m["balanced_accuracy"], "recall_HIGH": m["recall_HIGH"],
                     "precision_HIGH": m["precision_HIGH"], "recall_LOW": m["recall_LOW"], "precision_LOW": m["precision_LOW"],
                     "f1_HIGH": m["f1_HIGH"], "brier": m["brier"], "auc": m["auc"], **m["confusion"],
                     "citl": cal.get("citl"), "cal_slope": cal.get("slope"),
                     "E56_minus_model_brier": pb.get("diff"), "ci_low": (pb.get("ci95") or [None])[0],
                     "ci_high": (pb.get("ci95") or [None, None])[1]})
    pd.DataFrame(rows).round(4).to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame({a: r["metrics"][a]["by_quarter"] for a in ("E56-TUNED", "E55-LGBM", "I7", "E52", "B1_PERSIST", "LOW")}) \
        .round(3).to_csv(OUT / "per_quarter.csv")
    pd.DataFrame(r["by_province"]["E56-TUNED"]).T.round(3).to_csv(OUT / "by_province_e56.csv")
    pd.DataFrame(r["province_spread"]).T.round(3).to_csv(OUT / "province_spread.csv")
    pd.DataFrame(r["calibration"]["E56-TUNED"]["reliability"]).to_csv(OUT / "reliability_e56.csv", index=False)
    sel = json.loads((RUN / "selections.json").read_text())
    pd.DataFrame([{"origin": k, "target": None, **v["cfg"], "inner_logloss": v["inner_logloss"],
                   "n_train_rows": v["n_train_rows"], "n_train_HIGH": v["n_train_HIGH"], "e55_config": v["is_e55_config"]}
                  for k, v in sel.items()]).to_csv(OUT / "selected_configs.csv", index=False)
    s = r["supplementary_50_rows"]["metrics"]
    pd.DataFrame([{"model": a, "accuracy": m["accuracy"], "balanced_accuracy": m["balanced_accuracy"], "brier": m["brier"]}
                  for a, m in s.items()]).round(4).to_csv(OUT / "supplementary_50_rows.csv", index=False)
    print("tables written from", RUN.name)


if __name__ == "__main__":
    main()
