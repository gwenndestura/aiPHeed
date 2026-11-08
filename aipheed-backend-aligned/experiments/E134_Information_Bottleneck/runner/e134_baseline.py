"""
E134 phase 0: reproduce E133 (all models, both policies, both sets, N1-N7, ablation) into E134/out/baseline without
touching E133, compare every forecast with E133's committed predictions, and write the baseline record.

    python -I runner/e134_baseline.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
E133 = EXP / "E133_Forecasting_Breakthrough"
sys.path.insert(0, str(E133 / "runner"))
import e133_run as R  # noqa: E402

OUT = ROOT / "out" / "baseline"


def main():
    R.OUT = OUT
    R.main()
    new = pd.read_csv(OUT / "e133_predictions.csv")
    old = pd.read_csv(E133 / "out" / "e133_predictions.csv")
    key = ["policy", "area", "D", "lead"]
    m = new.merge(old, on=key, suffixes=("", "_old"))
    fcols = [c for c in old.columns if c.startswith("f_")]
    diff = {c: float(np.nanmax(np.abs(m[c] - m[c + "_old"]))) for c in fcols}
    mt_new = pd.read_csv(OUT / "e133_metrics.csv")
    mt_old = pd.read_csv(E133 / "out" / "e133_metrics.csv")
    mm = mt_new.merge(mt_old, on=["set", "policy", "lead", "model"], suffixes=("", "_old"))
    seals = {}
    for d, f in ((EXP / "E131_Objectives_Resolution" / "sealed", "E131_PROSPECTIVE_SEAL.csv"),
                 (EXP / "E132_Final_Methodology" / "sealed", "E132_PROSPECTIVE_SEAL.csv"),
                 (EXP / "E132_Final_Methodology" / "sealed", "E132_PROVINCIAL_MODEL_BASED_SEAL.csv"),
                 (E133 / "sealed", "E133_PROSPECTIVE_SEAL.csv"), (E133 / "sealed", "E133_PROVINCIAL_MODEL_BASED_SEAL.csv")):
        p = d / f
        seals[f] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    su2 = mt_new[(mt_new.set == "S-U") & (mt_new.policy == "P-DASH") & (mt_new.model.isin(["HFM-X", "SEAS-LLM", "PERSIST", "HFM-X-PH2"]))]
    rec = {"rows_new": len(new), "rows_old": len(old), "rows_matched": len(m),
           "max_abs_forecast_diff": max(diff.values()),
           "max_abs_metric_diff_within": float(np.nanmax(np.abs(mm["within_tolerance"] - mm["within_tolerance_old"]))),
           "max_abs_metric_diff_mae": float(np.nanmax(np.abs(mm["mae"] - mm["mae_old"]))),
           "baseline_table_S-U_P-DASH": su2[["model", "lead", "n", "n_quarters", "within_tolerance", "mae", "rmse", "bias",
                                              "coverage80", "sharp_n", "sharp_within", "bias_high"]].round(4).to_dict("records"),
           "seal_sha256": seals}
    R.L.dump(rec, ROOT / "out" / "e134_baseline_record.json")
    print(json.dumps({k: v for k, v in rec.items() if k != "baseline_table_S-U_P-DASH"}, indent=1))


if __name__ == "__main__":
    main()
