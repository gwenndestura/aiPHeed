"""Walk-forward validation of the FOOD INSECURITY RISK estimate (expected HFIAS moderate+severe probability) on the existing FINAL
forecasts. No refit. Rows: ENNS 2018/2019/2021 x Leads 1-2 (72 province-rounds per lead), 5 seeds averaged.

Run from the repository root:  backend/venv python docs/food_insecurity_risk/validate_risk.py
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.final.risk import expected_risk   # noqa: E402

X = pd.concat([pd.read_csv(f) for f in glob.glob(str(ROOT / "research_notes/aiPHeed_final_7of7_20261113/parts_mix/FINALMIX__*.csv"))])
X = X[X.lead.isin([1, 2])].copy()
X["sd_raw"] = X["mu"] / norm.ppf(X["p"].clip(1e-12, 1 - 1e-12))
raw = X.groupby(["survey", "lead", "seed"])["sd_raw"].transform("std").fillna(1) < 1e-6     # raw calibration: one sd per fold
L = pd.read_csv(ROOT / "backend/data/e158/out/oof.csv")[["key", "survey", "lead", "y_true", "se_true", "y_anchor"]]
sig = lambda z: 1 / (1 + np.exp(-np.asarray(z, float)))


def score(df, col):
    e = 100 * (df[col] - df["p_obs"])
    r, p = df[col].clip(1e-6, 1 - 1e-6), df["p_obs"]
    return {"mae_pp": round(float(e.abs().mean()), 2), "rmse_pp": round(float(np.sqrt((e ** 2).mean())), 2), "bias_pp": round(float(e.mean()), 2),
            "household_brier": round(float(((df[col] - p) ** 2 + p * (1 - p)).mean()), 4),
            "household_log_loss": round(float((-(p * np.log(r) + (1 - p) * np.log(1 - r))).mean()), 4),
            "high_class_accuracy": round(float(((df[col] >= 0.5) == (p >= 0.5)).mean()), 3)}


out = {}
for sd_2021 in ("fold2019", 0.40, 0.70):
    rows = []
    for (s, lead, seed), g in X.groupby(["survey", "lead", "seed"]):
        g = g.copy()
        if raw[g.index].all() and s != "ENNS2021":
            sd = g["sd_raw"].values
        else:                                   # 2021 folds chose linear/Platt calibration: the raw sd is not stored
            sd = np.full(len(g), X[(X.survey == "ENNS2019") & (X.lead == lead) & (X.seed == seed)]["sd_raw"].iloc[0]
                         if sd_2021 == "fold2019" else sd_2021)
        g["median_level"] = sig(g["mu"])
        g["risk"] = expected_risk(g["mu"].values, sd)
        rows.append(g)
    R = pd.concat(rows).groupby(["key", "survey", "lead"], as_index=False)[["median_level", "risk", "mu"]].mean().merge(L, on=["key", "survey", "lead"])
    R["p_obs"] = sig(R["y_true"])
    R["persistence"] = sig(R["y_anchor"])
    res = {}
    for lead in (1, 2):
        D = R[R.lead == lead]
        res[f"lead{lead}"] = {"n": len(D), **{c: score(D, c) for c in ("risk", "median_level", "persistence")},
                              "by_round_mae_pp": {s: {c: round(float((100 * (d[c] - d["p_obs"])).abs().mean()), 2) for c in ("risk", "persistence")}
                                                  for s, d in D.groupby("survey")},
                              "class_agrees_with_mu_sign": bool(((D["risk"] >= 0.5) == (D["mu"] >= 0)).all())}
    out[f"sd_2021={sd_2021}"] = res
    if sd_2021 == "fold2019":
        R.to_csv(ROOT / "docs/food_insecurity_risk/walk_forward_rows.csv", index=False, lineterminator="\n")
(ROOT / "docs/food_insecurity_risk/walk_forward_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out["sd_2021=fold2019"], indent=1))
print("sensitivity (Lead 1 risk MAE pp):", {k: v["lead1"]["risk"]["mae_pp"] for k, v in out.items()})
