r"""Training-only diagnosis of RATE's linear-in-gap assumption (PROTOCOL_SA section 3). Uses the TRAINING rows of each fold
(outcomes released before that fold's origin), one row per province-transition. Run: python -I diag_rate.py"""
import json
import pickle
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
CACHE = HERE.parent / "aiPHeed_objective_completion_20261111" / "cache"
inv = lambda z: 100 / (1 + np.exp(-z))
out = {}
for sv in ("ENNS2018", "ENNS2019", "ENNS2021"):
    tr = pickle.load(open(CACHE / f"{sv}_1.pkl", "rb"))["tr"]
    d = tr.drop_duplicates(["key", "survey", "ref_anchor"])[["key", "survey", "ref_anchor", "gap_q", "y_true", "y_anchor"]].copy()
    d["chg_logit"], d["chg_pp"] = d.y_true - d.y_anchor, inv(d.y_true) - inv(d.y_anchor)
    d["per_q"] = d.chg_logit / d.gap_q
    by = d.groupby("gap_q").agg(n=("key", "size"), transitions=("survey", lambda s: sorted(set(s))), mean_change_pp=("chg_pp", "mean"),
                                mean_change_logit=("chg_logit", "mean"), mean_change_per_quarter=("per_q", "mean")).reset_index()
    # reversion: slope of change on anchor level, per transition
    rev = {f"{a}->{s}": round(float(np.polyfit(g.y_anchor, g.chg_logit, 1)[0]), 3) for (a, s), g in d.groupby(["ref_anchor", "survey"]) if len(g) > 5}
    hi = d[d.y_anchor > np.log(0.6 / 0.4)]
    out[sv] = {"transitions_by_gap": by.round(4).to_dict("records"), "reversion_slope_change_on_anchor_logit": rev,
               "high_anchor_ge60pct": {"n": int(len(hi)), "share_still_HIGH": round(float((hi.y_true >= 0).mean()), 3) if len(hi) else None,
                                       "mean_change_pp": round(float(hi.chg_pp.mean()), 1) if len(hi) else None}}
json.dump(out, open(HERE / "evidence" / "D1_rate_gap_training_only.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
