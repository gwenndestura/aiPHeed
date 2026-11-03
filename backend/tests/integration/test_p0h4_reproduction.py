"""
P0H4 evaluation integrity: the served Lead-1 rows (backend/data/ch1_engine/rows.csv) reproduce the stored evaluation
(evaluation.json) exactly, and R7's "thirds" follow the frozen implementation (numpy array_split of the sorted target
quarters, ch1_lib.py). Read-only.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "ch1_engine"


def _lead1():
    r = pd.read_csv(DATA / "rows.csv", dtype={"province_code": str})
    r = r[(r["lead"] == 1) & r["observed"].isin(["HIGH", "LOW"])].copy()
    r["y"] = (r["observed"] == "HIGH").astype(int)
    r["yh"] = (r["probability"] >= 0.5).astype(int)
    return r


def test_served_lead1_rows_reproduce_the_stored_metrics():
    r = _lead1()
    ev = json.loads((DATA / "evaluation.json").read_text(encoding="utf-8"))["leads"]["1"]
    m = ev["metrics"]
    tp, fp = int(((r.yh == 1) & (r.y == 1)).sum()), int(((r.yh == 1) & (r.y == 0)).sum())
    fn, tn = int(((r.yh == 0) & (r.y == 1)).sum()), int(((r.yh == 0) & (r.y == 0)).sum())
    assert (tp, fp, fn, tn) == (m["tp"], m["fp"], m["fn"], m["tn"])
    assert len(r) == ev["n"] and r["quarter"].nunique() == ev["n_quarters"]
    assert abs(float(np.mean((r["probability"] - r["y"]) ** 2)) - m["brier"]) < 1e-6
    assert not r.duplicated(["province_code", "quarter"]).any()
    assert ((r["pi_hunger"] * r["pi_price"] - r["probability"]).abs() < 1e-5).all()


def test_r7_thirds_follow_the_frozen_split():
    r = _lead1()
    ev = json.loads((DATA / "evaluation.json").read_text(encoding="utf-8"))["leads"]["1"]
    thirds = np.array_split(np.array(sorted(r["quarter"].unique())), 3)
    acc = [float((r[r["quarter"].isin(t)].yh == r[r["quarter"].isin(t)].y).mean()) for t in thirds]
    assert [round(a, 4) for a in acc] == [round(a, 4) for a in ev["acc_thirds"]]
