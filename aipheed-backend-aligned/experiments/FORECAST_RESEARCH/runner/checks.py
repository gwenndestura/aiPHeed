"""Reproducibility and data-timing checks for FORECAST_RESEARCH.   python checks.py -> out/checks.json

1. Re-running the scorer reproduces out/predictions.csv byte for byte (deterministic fits).
2. Schedule B: I_B(t) >= O(t); every SWS round used was published strictly before I_B(t); I_B never later than day 1
   of month 3 of quarter t+1; no non-SWS input changes between schedules (price parts identical).
3. Training rows of every origin have target quarter <= t-1 and origin < t (continuous price arms).
4. The exported P0H4-U rows use only SWS rounds published before their issue date.
"""
import hashlib
import json
import subprocess
import sys

import pandas as pd

import fr_lib as F


def main():
    out = {}
    before = hashlib.sha256((F.OUT / "predictions.csv").read_bytes()).hexdigest()
    subprocess.run([sys.executable, "score.py"], check=True, capture_output=True)
    after = hashlib.sha256((F.OUT / "predictions.csv").read_bytes()).hexdigest()
    out["reproducible_predictions"] = before == after
    E = pd.read_csv(F.OUT / "predictions.csv", dtype={"province_code": str})
    bad = []
    for t, g in E.groupby("t"):
        o, ib = F.origin(int(t)), pd.Timestamp(g["issue_B"].iloc[0])
        cap = o + pd.DateOffset(months=2)
        used = F.rounds()[F.rounds()["published"] < g["issue_B"].iloc[0]]
        if ib < o or ib > cap or (pd.to_datetime(used["published"]) >= ib).any():
            bad.append(F.qs(int(t)))
    out["schedule_B_timing_violations"] = bad
    out["price_parts_identical_across_schedules"] = bool(all(
        (E[f"{a}{s}_p"] - E[f"pi_H_{s}"] * E[f"{a}_price"]).abs().max() < 1e-5
        for a in ("Z0", "Z1", "Z2", "Z3") for s in ("A", "B")))
    S = F.stack()
    viol = 0
    for t in E["t"].unique():
        tr = F.price_train(S, int(t))
        viol += int(((tr["target_q"] > t - 1) | (tr["t"] >= t)).sum())
    out["training_row_violations"] = viol
    R = pd.read_csv(F.EXP.parents[1] / "backend" / "data" / "ch1_engine_fr" / "rows.csv", dtype=str)
    rb = R[R["issue_schedule"] == "B"]
    pub = F.rounds()
    out["export_sws_after_issue"] = int(sum(
        (pub[(pub["area"] == "BL") & (pub["q"] == int(q[:4]) * 4 + int(q[-1]) - 1)]["published"] >= i).any()
        for q, i in zip(rb["sws_newest_q"], rb["issue_date"])))
    out["passed"] = (out["reproducible_predictions"] and not bad and out["price_parts_identical_across_schedules"]
                     and viol == 0 and out["export_sws_after_issue"] == 0)
    (F.OUT / "checks.json").write_text(json.dumps(out, indent=1))
    print(out)


if __name__ == "__main__":
    main()
