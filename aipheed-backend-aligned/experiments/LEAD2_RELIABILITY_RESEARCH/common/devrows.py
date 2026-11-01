"""Development rows 2005-Q1..2020-Q4 (EXPERIMENT_PLAN_PHASE2.md section 4): one row per (lead, area, fit, target) with
the RW comparator from Phase 1 (rlib.forecast) and the candidate columns supplied by the caller."""
from __future__ import annotations

import pandas as pd

import p2lib as P

R = P.R
T_FIRST, T_LAST = R.qi("2005-Q1"), R.qi("2020-Q4")
ALL = tuple(R.AREAS)
HELD = ("NCR", "VIS", "MIN")


def build(cands: dict, leads=(2,), bl_only: set = frozenset()) -> pd.DataFrame:
    """cands: name -> f(area, t, k, fit_areas) -> probability. Names in bl_only are evaluated for BL pooled only."""
    obs = R.observed()
    rows = []
    for k in leads:
        for area in R.AREAS:
            fits = {"pooled": ALL, **({"heldout": HELD} if area == "BL" else {})}
            for tgt in range(T_FIRST, T_LAST + 1):
                if (area, tgt) not in obs:
                    continue
                t = tgt - k
                for fit, fa in fits.items():
                    f = R.forecast(area, t, k, fa)
                    if f is None:
                        continue
                    row = {"lead": k, "area": area, "fit": fit, "t": t, "q": tgt, "target": R.qs(tgt),
                           "level": obs[(area, tgt)], "y": int(obs[(area, tgt)] > R.H_LINE), "h": f["h"], "RW": f["RW"]}
                    for name, fn in cands.items():
                        if name in bl_only and not (area == "BL" and fit == "pooled"):
                            row[name] = float("nan")
                        else:
                            row[name] = fn(area, t, k, fa)
                    rows.append(row)
    d = pd.DataFrame(rows)
    assert d["target"].max() <= "2020-Q4", "a 2021+ outcome entered development"
    return d
