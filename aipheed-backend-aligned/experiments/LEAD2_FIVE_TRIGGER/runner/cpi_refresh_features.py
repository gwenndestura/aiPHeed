"""LEAD2_CPI_REFRESH feature builder (no outcome is read).

At each origin t the served stack builds the CPI columns from month m0 = month 2 of quarter t (the newest month
published at the quarter-start issue). The Lead-2+ forecasts are re-issued later (S-AB schedule B: after the SWS
release, at the latest day 1 of month 3 of quarter t+1); by then PSA has usually published one or two more months.
This builds, for every stack row of Lead >= 2:

- m0r: the newest CPI month published before the row's schedule-B issue date under the conservative day-10 rule
  (E113_CPI_VALIDATION: month m counts as published from day 10 of month m+1);
- A1_food_r, A1_gap_r, A_mom_r: the same E107 projection and ch1_lib momentum, with m0 replaced by m0r.

Check: with m0r = m0 the builder reproduces the stack's A1_food, A1_gap and A_mom.

    python cpi_refresh_features.py   # ../data/cpi_refresh.csv, ../out/cpi_refresh_features_audit.json
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date

import numpy as np
import pandas as pd

import lt_lib as T

sys.path.insert(0, str(T.EXP / "E107_Twelve_Indicator_LightGBM" / "runner"))
import e107_lib as E  # noqa: E402

L, F, KEY = E.L, T.F, T.KEY
RELEASE_DAY = 10


def newest_month(iss: str, m0: int) -> int:
    """Newest CPI month m >= m0 with day RELEASE_DAY of month m+1 strictly before the issue date."""
    d = date.fromisoformat(iss)
    m = m0
    while True:
        n = m + 2                                   # month m+1 is published in month m+2 (ym = year*12 + month0)
        if date(n // 12, n % 12 + 1, RELEASE_DAY) < d:
            m += 1
        else:
            return m


def series(d, p: str, commodity: str, m: int) -> pd.Series:
    s = L._series(d, p, commodity)
    return s[s.index <= m]


def projection(d, t: int, k: int, p: str, commodity: str, m: int) -> float:
    s = series(d, p, commodity, m)
    if m not in s.index:
        return float("nan")
    vals = [100 * (s[m] / s[b] - 1) for b in E.projection_bases(t, k) if b in s.index]
    return float(np.mean(vals)) if len(vals) >= 2 else float("nan")


def a_mom(d, p: str, m: int) -> float:
    s = series(d, p, "food", m)
    return float(100 * (math.log(s[m]) - math.log(s[m - 3]))) if m in s.index and (m - 3) in s.index else float("nan")


def cols(d, th, t: int, k: int, p: str, m: int) -> tuple[float, float, float]:
    f, h = projection(d, t, k, p, "food", m), projection(d, t, k, p, "all_items", m)
    return f - th["food"][p], (f - h) - th["gap"][p], a_mom(d, p, m)


def main():
    S = T.stack()
    d, _ = E.data()
    th = L.e40_spec()
    rows, rep = [], []
    for t, k, p in zip(S["t"], S["lead"], S["province_code"]):
        t, k = int(t), int(k)
        m0 = L.m0_of(t)
        rep.append(cols(d, th, t, k, p, m0))
        if k >= 2:
            iss = F.issue(t, "B")
            m = newest_month(iss, m0)
            assert m <= m0 + 2
            rows.append({"t": t, "lead": k, "province_code": p, "issue_B": iss, "m0": m0, "m0r": m,
                         **dict(zip(("A1_food_r", "A1_gap_r", "A_mom_r"), cols(d, th, t, k, p, m)))})
    R = pd.DataFrame(rows)
    rep = np.array(rep)
    audit = {"rows_lead_ge_2": int(len(R)),
             "reproduce_A1_food_max_abs": float(np.nanmax(np.abs(rep[:, 0] - S["A1_food"]))),
             "reproduce_A1_gap_max_abs": float(np.nanmax(np.abs(rep[:, 1] - S["A1_gap"]))),
             "reproduce_A_mom_max_abs": float(np.nanmax(np.abs(rep[:, 2] - S["A_mom"]))),
             "reproduce_nan_pattern_equal": bool((np.isnan(rep[:, 0]) == S["A1_food"].isna()).all()),
             "extra_months": R["m0r"].sub(R["m0"]).value_counts().sort_index().to_dict(),
             "cpi_data_max_month": L.ym_s(int(d.idx["ym"].max())), "max_m0r": L.ym_s(int(R["m0r"].max()))}
    R = R[R["m0r"] <= int(d.idx["ym"].max())]
    R.to_csv(T.DATA / "cpi_refresh.csv", index=False, lineterminator="\n", float_format="%.10g")
    (T.OUT / "cpi_refresh_features_audit.json").write_text(json.dumps(audit, indent=1, default=str))
    print(json.dumps(audit, indent=1, default=str))


if __name__ == "__main__":
    main()
