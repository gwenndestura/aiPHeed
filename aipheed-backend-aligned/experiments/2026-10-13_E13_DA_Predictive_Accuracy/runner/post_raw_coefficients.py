"""E13 post-analysis (descriptive, after the primary run): recover each linear arm's raw-unit coefficients per
test quarter from its own forecasts (exact least squares over the 5 provinces; ridge forecasts are linear in
the features). Reads only this experiment's run output. Writes runs/<run>/raw_coefficients.csv (new file)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RUN = guard.EXP / "runs" / sys.argv[1]
SPECS = {"B2_ridge_D": ["D_lag2"], "B2_ridge_DP": ["D_lag2", "Dbar_p"], "B1_ridge_F": ["F_lag2"]}


def main():
    s = pd.read_csv(RUN / "scored_rows.csv", dtype={"province_code": str})
    rows = []
    for arm, feats in SPECS.items():
        d = s[(s["arm"] == arm) & (s["analysis"] == "primary") & (s["status"] == "OK")]
        for q, g in d.groupby("quarter"):
            X = np.column_stack([np.ones(len(g))] + [g[f].to_numpy(float) for f in feats])
            b, res, rank, _ = np.linalg.lstsq(X, g["forecast"].to_numpy(float), rcond=None)
            fit = X @ b
            rows.append({"arm": arm, "quarter": q, "intercept": b[0],
                         **{f"coef_{f}": v for f, v in zip(feats, b[1:])},
                         "max_abs_reconstruction_error": float(np.abs(fit - g["forecast"]).max()), "rank": int(rank)})
    out = RUN / "raw_coefficients.csv"
    if out.exists():
        raise FileExistsError(out)
    pd.DataFrame(rows).to_csv(out, index=False, lineterminator="\n", float_format="%.6g")
    print(out)


if __name__ == "__main__":
    main()
