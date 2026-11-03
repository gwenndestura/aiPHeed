"""
E141 provincial candidate: the same LightGBM (E140 LGBM-AUTO) trained on all THREE measured HFIAS rounds (2013, 2015,
2018/2019; 203 province-rounds, every 2015+ row with its previous measured round), issued for the dashboard's display
quarter through the shared E140 issue path.

    python -m app.e141.issue      -> data/e141/out/issue/{forecast_next_quarter.json, lgus_next_quarter.csv,
                                     sealed_prediction_<issue>.json} + provincial prospective register record
"""
from __future__ import annotations

import pandas as pd

from app.e140.issue import issue_candidate
from app.e141 import OUT
from app.e141 import panel as P

MODEL_ID = "e141-lgbm-3round-1.0"
CLAIM = ("Estimated relative risk for the display quarter: P(the province's HFIAS moderate-or-severe food insecurity is above the "
         "national level), from information public before the issue date. Evidence (E141): on the untouched 2013 round the "
         "model ranks provinces well (AUC 0.94) but is under-calibrated (ECE 0.14); forecasting the next measured round "
         "(three survey-to-survey origins) it is not significantly better than the previous survey or the region's previous "
         "level. Quarter-to-quarter change is NOT validated: no quarterly provincial measurement exists.")
STATUS = "CANDIDATE - E141 forecast gate not passed; validation pending; not a released forecast"


def run(issue: pd.Timestamp | None = None) -> dict:
    out_dir = OUT / "issue"
    out_dir.mkdir(parents=True, exist_ok=True)
    return issue_candidate(P.data(1), MODEL_ID, out_dir, CLAIM, STATUS, issue)


if __name__ == "__main__":
    o = run()
    print(o["target_quarter"], o["final_model"], o["p_rank_first"])
    for p in o["provinces"]:
        print(p["province"], p["p_elevated"], p["p_interval90"], p["risk_class"], [(e["group"], e["contribution_logit"]) for e in p["explanations"]])
