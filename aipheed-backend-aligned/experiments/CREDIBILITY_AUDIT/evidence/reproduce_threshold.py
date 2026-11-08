"""Reproduce the 11.3% SWS hunger threshold of E40 and its sensitivity (CREDIBILITY_AUDIT, read-only).

    python reproduce_threshold.py      (backend venv; run from this folder)

Inputs: backend/data/inputs/sws_rounds.csv (definition_A rounds, the file E40 read) and FORECAST_RESEARCH's label
snapshot. Writes threshold_reproduction.json next to this script.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
r = pd.read_csv(ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv")
a = r[r["definition_A"].astype(str) == "True"]
qm = a.groupby("quarter")["H"].mean()
w = qm[(qm.index >= "2021-Q1") & (qm.index <= "2022-Q4")]
out = {"window_quarter_means": w.round(3).to_dict(), "n": int(len(w)),
       "percentiles_linear": {p: float(np.percentile(w.values, p)) for p in (50, 60, 65, 70, 75, 80, 85)},
       "p60_by_method": {m: float(np.percentile(w.values, 60, method=m)) for m in
                         ("linear", "lower", "higher", "nearest", "midpoint", "hazen", "weibull", "median_unbiased")},
       "p60_equals_2022Q4_reading": bool(abs(np.percentile(w.values, 60) - w["2022-Q4"]) < 1e-9),
       "2022Q4_published": str(a[a["quarter"] == "2022-Q4"]["published"].max())}
lab = pd.read_csv(HERE.parents[1] / "FORECAST_RESEARCH" / "data" / "labels_t43c.csv", dtype={"province_code": str})
hq = lab.drop_duplicates("q")
sens = []
for th in (9.6, 10.3, 11.3, 12.6, 14.3, 17.0, 21.1):
    sens.append({"threshold": th, "hunger_quarters": int((hq["H"] > th).sum()), "quarters": int(len(hq)),
                 "HIGH_rows": int(((lab["H"] > th) & (lab["price"] == 1)).sum()), "rows": int(len(lab))})
out["label_sensitivity"] = sens
out["quarters_within_5.7_of_11.3"] = int((abs(hq["H"] - 11.3) <= 5.7).sum())
(HERE / "threshold_reproduction.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
