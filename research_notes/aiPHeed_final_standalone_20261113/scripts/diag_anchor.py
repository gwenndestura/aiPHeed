r"""Outcome-free: how much of FINAL's 2021 predicted fall comes from the chosen anchor vs the RATE increment. Run: python -I diag_anchor.py"""
import glob, json, pickle
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
CACHE = RN / "aiPHeed_objective_completion_20261111" / "cache"
inv = lambda z: 100 / (1 + np.exp(-z))
S = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112/parts_fwd/FINAL__*__1__*.csv"))])
out = {}
for sv in ("ENNS2018", "ENNS2019", "ENNS2021"):
    o = pickle.load(open(CACHE / f"{sv}_1.pkl", "rb"))
    te, tr, AN = o["te"].reset_index(drop=True), o["tr"], o["AN"]
    m = S[S.survey == sv].groupby("key")["mu"].mean()
    d = te[["key", "y_anchor"]].assign(**{f"anc_{a}": np.asarray(AN[a][1]) for a in AN}, mu=te["key"].map(m))
    hi = d[inv(d.y_anchor) >= 60]
    out[sv] = {"high_anchor_rows": int(len(hi)),
               **{f"anchor_{a}_minus_survey_pp": round(float((inv(hi[f"anc_{a}"]) - inv(hi.y_anchor)).mean()), 2) for a in AN},
               "forecast_minus_survey_pp": round(float((inv(hi.mu) - inv(hi.y_anchor)).mean()), 2),
               "training_anchor_spread": {a: round(float(np.std(AN[a][0])), 3) for a in AN}}
json.dump(out, open(HERE / "evidence" / "D3_anchor_vs_rate_outcome_free.json", "w"), indent=1)
print(json.dumps(out, indent=1))
