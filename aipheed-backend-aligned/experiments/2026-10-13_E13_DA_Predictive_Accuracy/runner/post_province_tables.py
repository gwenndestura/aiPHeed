"""E13 post-analysis (descriptive): per-province and per-quarter error and event tables for the primary
B1/B2 arms, from this experiment's scored rows only. Writes runs/<run>/province_event_tables.csv and
runs/<run>/quarter_event_tables.csv (new files)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402

guard.install()
import pandas as pd  # noqa: E402

import e13_lib as L  # noqa: E402

RUN = guard.EXP / "runs" / sys.argv[1]
ARMS = ["B1_cf", "B1_regional", "B1_ridge_F", "B2_zero", "B2_cf", "B2_ridge_D", "B2_ridge_DP"]


def table(s: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = []
    for arm in ARMS:
        d = s[(s["arm"] == arm) & (s["analysis"] == "primary") & (s["status"] == "OK")]
        for k, g in d.groupby(by):
            ev = L.classification(g["event_y"].astype(bool), g["event_pred"].astype(bool))
            rows.append({"arm": arm, by: k, "n": len(g), "MAE": (g["forecast"] - g["y"]).abs().mean(),
                         "bias": (g["forecast"] - g["y"]).mean(), "mean_realized": g["y"].mean(),
                         "event_positives": ev["positives"], "TP": ev["TP"], "FP": ev["FP"], "FN": ev["FN"],
                         "TN": ev["TN"], "balanced_accuracy": ev["balanced_accuracy"]})
    return pd.DataFrame(rows)


def main():
    s = pd.read_csv(RUN / "scored_rows.csv", dtype={"province_code": str})
    for by, name in [("province", "province_event_tables.csv"), ("quarter", "quarter_event_tables.csv")]:
        out = RUN / name
        if out.exists():
            raise FileExistsError(out)
        table(s, by).to_csv(out, index=False, lineterminator="\n", float_format="%.6g")
        print(out)


if __name__ == "__main__":
    main()
