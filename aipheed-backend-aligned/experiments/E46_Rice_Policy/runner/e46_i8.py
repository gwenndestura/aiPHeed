"""E46 iteration I8 (ADDENDUM_I8.md): I7 issued at the deployed scheduler's time, the 15th of the first month of
quarter t+1, with the data published by then (CPI through month 3 of t; SWS rounds and policy events before that day).

Importing this module re-points e41_lib.m0_of and e41_lib.origin; every E41/E43/E44/E46 cut reads those two
functions, so it must be imported before any data are loaded (and never together with an O(t)-convention run).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e46_i7 as I7  # noqa: E402

M, C, K, L, P2, np, pd = I7.M, I7.C, I7.K, I7.L, I7.P2, I7.np, I7.pd
ISSUE_DAY = 15


def m0_mid(t: int) -> int:
    """Latest CPI month at O'(t): month 3 of quarter t."""
    return (t // 4) * 12 + (t % 4) * 3 + 2


def origin_mid(t: int) -> pd.Timestamp:
    n = t + 1
    return pd.Timestamp(year=n // 4, month=(n % 4) * 3 + 1, day=ISSUE_DAY)


L.m0_of = m0_mid
L.origin = origin_mid
forecast = I7.forecast


def persist_labels(d, t: int) -> pd.Series:
    """Latest T43 label per province whose SWS rounds (all of them) and CPI quarter were published before O'(t)."""
    c = d.cut(t)
    lab = K.label_frame(c)
    full_n, cut_n = d.sws.groupby("q").size(), c.sws.groupby("q").size()
    complete = {q for q in cut_n.index if cut_n[q] == full_n.get(q, -1)}
    lab = lab[lab["q"].isin(complete) & (lab["q"] <= t)]
    return lab.sort_values("q").groupby("province_code")["y"].last()
