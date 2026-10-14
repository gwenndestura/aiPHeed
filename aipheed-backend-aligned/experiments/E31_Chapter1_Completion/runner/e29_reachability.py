"""E29 Objective 2 reachability from the reproduced E28 evaluation (runs/e28_eval/predictions.csv, B1 rows).
python -B runner/e29_reachability.py  ->  runs/e29_reachability.json
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard29  # noqa: E402

guard29.install()
EXP = guard29.EXP
sys.path.insert(0, str(EXP / "backend_dev"))
import pandas as pd  # noqa: E402

from app.quarterly import reachability as R  # noqa: E402

P = pd.read_csv(EXP / "runs" / "e28_eval" / "predictions.csv", dtype={"province_code": str})
out = {}
for tg in ("T1_A", "T2"):
    b1 = P[(P["target"] == tg) & (P["arm"] == "B1")]
    lc = R.lead_counts(b1)
    rows = lc.to_dict("records")
    # historical LOW-date rate over all leads' dates (each date is one regional draw for T1)
    p_low = float(lc["LOW_dates"].sum() / lc["dates"].sum())
    rpl = float(lc["LOW_rows"].sum() / max(1, lc["LOW_dates"].sum()))
    res = []
    for r in rows:
        g = R.c6_gap(r)
        g["counts"] = r
        g["quarters_to_evaluable_as_written"] = R.quarters_to_evaluable(r, p_low, rpl, dependence_aware=False)
        g["quarters_to_evaluable_dependence_aware"] = R.quarters_to_evaluable(r, p_low, rpl, dependence_aware=True)
        res.append(g)
    out[tg] = {"by_lead": res, "historical_LOW_date_rate": round(p_low, 3), "LOW_rows_per_LOW_date": round(rpl, 3)}
out["skill_vs_count"] = {
    "min_dates_for_any_p_below_0.05": R.min_dates_any_significance(),
    "dates_needed_80pct_power_if_arm_beats_persistence_on_share_of_dates": {
        str(w): R.dates_for_skill(w) for w in (0.6, 0.7, 0.8, 0.9)},
    "note": ("C6's counts make a lead EVALUABLE; they do not show skill. Showing that an arm beats persistence needs "
             "enough dates on which it is better; with p_win = 0.7 that is the number above, and each new quarter "
             "adds one date per lead.")}
(EXP / "runs" / "e29_reachability.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
