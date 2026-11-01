"""
E133 hyperparameter sensitivity (diagnostic, protocol section 9 of the directive): HFM-X with the beta prior SD at
0.5, 1 (protocol) and 2, P-DASH, S-U, Leads 1-4. Never used for selection.

    python -I runner/e133_sensitivity.py      (after e133_run.py)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e133_models as M  # noqa: E402
import e133_run as R  # noqa: E402

X, L = R.X, R.L


def main():
    rr = X.rounds()
    P = pd.read_csv(R.OUT / "e133_predictions.csv")
    P["issue"] = pd.to_datetime(P["issue"]).dt.date
    P = P[(P.policy == "P-DASH") & (P.n_obs >= 8)].copy()
    drv = {"rice": R.Drivers("rice"), "b30": R.Drivers("b30"), "oni": R.Drivers("rice", "oni_quarter_mean")}
    rows = []
    for sd in (0.5, 1.0, 2.0):
        M.PRIOR_SD = sd
        R._XFIT.clear()
        f = np.full(len(P), np.nan)
        for (D, k), g in P.groupby(["D", "lead"]):
            res = R.predict(X.asof(rr, g["issue"].iloc[0]), g["issue"].iloc[0], L.qi(g["target"].iloc[0]), drv)
            for i in g.index:
                f[P.index.get_loc(i)] = res["HFM-X"][0][X.AREAS.index(P.at[i, "area"])]
        P[f"f_sd{sd}"] = f
        for k, g in P.groupby("lead"):
            e = g[f"f_sd{sd}"] - g["y_true"]
            rows.append({"prior_sd": sd, "lead": int(k), "rows": len(g), "mae": float(e.abs().mean()),
                         "rmse": float(np.sqrt((e ** 2).mean())), "within": float((e.abs() <= g["tol"]).mean())})
    d = pd.DataFrame(rows)
    d.to_csv(R.OUT / "e133_prior_sensitivity.csv", index=False)
    print(d.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
