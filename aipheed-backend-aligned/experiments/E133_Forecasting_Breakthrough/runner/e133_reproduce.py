"""
E133 step 0: reproduce E132 (P-DASH and P-REL walk-forward) into E133/out without touching E132 outputs, and compare
every SEAS-LLM / LLM / PERSIST forecast with E132's committed predictions.

    python -I runner/e133_reproduce.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
sys.path.insert(0, str(EXP / "E132_Final_Methodology" / "runner"))
import e132_run as S  # noqa: E402

X, L = S.X, S.L


def main():
    S.OUT = ROOT / "out"
    rr = X.rounds()
    qt = X.quarter_table(rr)
    cpi, reg, pov = X.cpi_quarterly(), X.regional_covariates(), X.poverty_area()
    S.INCOME, S.RICE = S.income_area(), S.rice_affordability()
    X.features = S.features132
    S.GROUPS132.update({k: list(v) for k, v in X.GROUPS.items()})
    S.GROUPS132["A"] = S.GROUPS132["A"] + ["riceaff_chg4"]
    S.GROUPS132["E"] = S.GROUPS132["E"] + S.INC
    X.feat_cols = S.feat_cols132
    X.MODELS = S.ALL_MODELS
    P = pd.concat([S.run132(p, rr, qt, cpi, reg, pov) for p in ("P-DASH", "P-REL")], ignore_index=True)
    P = X.intervals(X.add_truth(P, qt))
    old = pd.read_csv(EXP / "E132_Final_Methodology" / "out" / "e132_predictions.csv")
    key = ["policy", "area", "D", "lead"]
    m = P.merge(old, on=key, suffixes=("", "_old"))
    rep = {"rows_new": len(P), "rows_old": len(old), "rows_matched": len(m)}
    for c in ("f_PERSIST", "f_LLM", "f_SEAS-LLM", "f_ENS", "f_LGBM-ALL", "f_HYB-RIDGE"):
        d = np.abs(m[c].astype(float) - m[c + "_old"].astype(float))
        rep[f"max_abs_diff_{c}"] = float(np.nanmax(d))
    M, R = X.evaluate(P)
    g = M[(M.policy == "P-DASH") & (M.lead == 2)].set_index("model")
    rep["lead2_shared_rows"] = int(g.loc["SEAS-LLM", "n"])
    rep["lead2_within_SEAS-LLM"] = float(g.loc["SEAS-LLM", "within_tolerance"])
    rep["lead2_mae_SEAS-LLM"] = float(g.loc["SEAS-LLM", "mae"])
    rep["lead2_rmse_SEAS-LLM"] = float(g.loc["SEAS-LLM", "rmse"])
    L.dump(rep, ROOT / "out" / "e133_reproduction_check.json")
    P.to_csv(ROOT / "out" / "e133_e132_reproduced_predictions.csv", index=False)
    print(rep)


if __name__ == "__main__":
    main()
