"""LEAD2_TUNING feature arms (no outcome is read; only months <= psa_newest_month of each row).

F1 market pressure x vulnerability: XV_food = A1_food x V1, XV_gap = A1_gap x V1. The same projected affordability
   pressure is expected to matter more where households are poorer; the depth-1 stumps P0H4-U usually selects cannot
   represent that interaction.
F2 deviation from the province's own history: OWN_food, OWN_gap = (newest 3-month mean y/y - mean of the province's
   earlier monthly y/y since 2022-01) / their SD, for food and food-minus-headline; NaN with fewer than 9 earlier months.
   It measures how unusual current pressure is for that province, which the frozen 2021-22 thresholds do not, and
   targets mean reversion (the false alarms where above-threshold pressure fell back).

    python features_v5.py       # ../data/stack_v5.csv, ../out/features_v5_audit.json
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd

import lt_lib as T

sys.path.insert(0, str(T.EXP / "FORECAST_RESEARCH_II" / "runner"))
import ii_lib as II  # noqa: E402

F1 = ["XV_food", "XV_gap"]
F2 = ["OWN_food", "OWN_gap"]
MIN_HIST = 9


def yoy_frames():
    W = II.index_wide()
    f, a = W["food"], W["all"]
    yf = 100 * (f / f.shift(12) - 1)
    ya = 100 * (a / a.shift(12) - 1)
    return yf, yf - ya


def own_dev(Y: pd.DataFrame, p: str, m0: int) -> float:
    s = Y[p].dropna()
    cur = s[(s.index > m0 - 3) & (s.index <= m0)]
    hist = s[s.index <= m0 - 3]
    if len(cur) < 3 or len(hist) < MIN_HIST or hist.std() == 0:
        return np.nan
    return float((cur.mean() - hist.mean()) / hist.std())


def main():
    S = pd.read_csv(T.DATA / "stack_v4.csv", dtype={"province_code": str})
    pm = pd.to_datetime(S["psa_newest_month"], format="%Y-%m")
    m0 = pm.dt.year * 12 + pm.dt.month - 1
    assert (m0 == (S["t"] // 4) * 12 + (S["t"] % 4) * 3 + 1).all()
    S["XV_food"], S["XV_gap"] = S["A1_food"] * S["V1"], S["A1_gap"] * S["V1"]
    yf, yg = yoy_frames()
    cache = {}
    for p, m in set(zip(S["province_code"], m0)):
        cache[(p, m)] = (own_dev(yf, p, int(m)), own_dev(yg, p, int(m)))
    v = np.array([cache[(p, m)] for p, m in zip(S["province_code"], m0)])
    S["OWN_food"], S["OWN_gap"] = v[:, 0], v[:, 1]
    S.to_csv(T.DATA / "stack_v5.csv", index=False, lineterminator="\n", float_format="%.10g")
    o = S.drop_duplicates(["t", "province_code"])
    ev = o[o["t"] >= 8091]
    audit = {"coverage_eval_origins": {c: float(ev[c].notna().mean()) for c in F1 + F2},
             "first_origin_with_value": {c: int(o.loc[o[c].notna(), "t"].min()) for c in F1 + F2},
             "corr_eval": {c: {b: float(ev[[c, b]].corr().iloc[0, 1]) for b in ("A1_food", "A1_gap", "F_ex", "G_ex")}
                           for c in F1 + F2},
             "newest_month_read_max": str(S["psa_newest_month"].max())}
    (T.OUT / "features_v5_audit.json").write_text(json.dumps(audit, indent=1))
    print(json.dumps(audit, indent=1))


if __name__ == "__main__":
    main()
