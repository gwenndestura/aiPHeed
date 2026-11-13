r"""Outcome-free diagnosis of FINAL's stored forecasts: predicted change (mu - anchor) per fold and anchor level, chosen anchor,
feature set and calibration per fit. Reads predictions and anchors only (no test outcome). Run: python -I diag_pred.py"""
import glob
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
RN = HERE.parent
S = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112/parts_fwd/FINAL__*.csv"))])
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[["key", "survey", "lead", "y_anchor", "gap_q"]]
X = S.merge(LAB, on=["key", "survey", "lead"])
inv = lambda z: 100 / (1 + np.exp(-z))
X["pred_change_pp"] = inv(X.mu) - inv(X.y_anchor)
X["anchor_band"] = pd.cut(inv(X.y_anchor), [0, 50, 60, 100], labels=["<50", "50-60", ">=60"])
X["anchor_choice"], X["fs"] = X.cfg.str.split("|").str[0], X.cfg.str.split("|").str[1]
L1 = X[X.lead == 1]
out = {"pred_change_pp_by_fold_and_anchor_band_L1": L1.groupby(["survey", "anchor_band"], observed=True).agg(rows=("p", "size"), mean_pred_change_pp=("pred_change_pp", "mean"),
            share_forecast_HIGH=("p", lambda v: float((v >= .5).mean()))).round(3).reset_index().to_dict("records"),
       "anchor_chosen_L1": L1.groupby(["survey", "anchor_choice"]).size().unstack(fill_value=0).to_dict("index"),
       "calibration_chosen_L1": L1.groupby(["survey", "cal"]).size().unstack(fill_value=0).to_dict("index"),
       "feature_set_chosen_L1": L1.groupby(["survey", "fs"]).size().unstack(fill_value=0).to_dict("index")}
json.dump(out, open(HERE / "evidence" / "D2_predicted_change_outcome_free.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
