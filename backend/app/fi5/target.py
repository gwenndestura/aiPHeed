"""Objective 2 target: above-normal involuntary hunger in Balance Luzon.

What is measured. SWS asks each household whether it "experienced hunger and did not have anything to eat" at least
once in the past three months. That is an experience-based measure of the most severe food-insecurity experience,
the same construct as the severe end of the FAO Food Insecurity Experience Scale (items "ran out of food" / "were
hungry but did not eat"; Cafiero et al. 2018). It is not undernourishment (PoU, a calorie-supply model) and not
poverty. It is the only food-insecurity measurement with a quarterly history for CALABARZON (1998-Q3 to 2026-Q3).
Its smallest published geography is the SWS area "Balance Luzon", which contains CALABARZON; no province-quarter
food-insecurity observation exists (DOST-FNRI FIES provincial estimates exist for at most three survey years).

The label. HIGH when the quarter's hunger rate is above the mean of the readings in the preceding 20 quarters (the
five-year average), with at least 8 earlier readings. "Above the five-year average" is the convention FEWS NET and
FAO GIEWS use for "worse than normal", so the threshold comes from early-warning practice, not from test results.
Quarters without an SWS round have no label (never LOW). Several rounds in one quarter are averaged. The continuous
hunger rate is kept for the level-forecast check.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.sources import sws_rounds

AREA = "balance_luzon"
BASELINE_Q = 20
MIN_BASELINE_OBS = 8


def qindex(label: str) -> int:
    y, q = label.split("-Q")
    return int(y) * 4 + int(q) - 1


def qlabel(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def q_end(i: int) -> pd.Timestamp:
    return pd.Timestamp(year=i // 4, month=3 * (i % 4 + 1), day=1) + pd.offsets.MonthEnd(0)


def quarterly(area: str = AREA) -> pd.DataFrame:
    """One row per quarter with an SWS reading: hunger (%), published (date the last round was released), n_rounds."""
    r = sws_rounds()
    g = r.groupby("quarter").agg(hunger=(area, "mean"), published=("published", "max"), n_rounds=(area, "count"),
                                 mode=("mode", "last"), respondent_base=("respondent_base", "last"))
    g = g.dropna(subset=["hunger"]).reset_index()
    g["qi"] = g["quarter"].map(qindex)
    return g.sort_values("qi").reset_index(drop=True)


def baseline(q: pd.DataFrame, qi: int, known: pd.Series | None = None) -> tuple[float, int]:
    """Mean of readings in quarters qi-20..qi-1 (optionally only those flagged known)."""
    m = (q["qi"] >= qi - BASELINE_Q) & (q["qi"] < qi)
    if known is not None:
        m &= known
    v = q.loc[m, "hunger"]
    return (float(v.mean()) if len(v) >= MIN_BASELINE_OBS else np.nan), int(len(v))


def labels(area: str = AREA) -> pd.DataFrame:
    q = quarterly(area)
    rows = []
    for _, r in q.iterrows():
        b, n = baseline(q, int(r["qi"]))
        rows.append({**r.to_dict(), "baseline_5y": b, "baseline_n": n,
                     "anomaly": r["hunger"] - b if not np.isnan(b) else np.nan,
                     "y": (int(r["hunger"] > b) if not np.isnan(b) else np.nan)})
    return pd.DataFrame(rows)
