"""Calendar arithmetic for the Lead-1 outlook: computed from a date, never hardcoded."""
from __future__ import annotations

import pandas as pd


def qi_of(date) -> int:
    d = pd.Timestamp(date)
    return d.year * 4 + (d.month - 1) // 3


def label(qi: int) -> str:
    return f"{qi // 4}-Q{qi % 4 + 1}"


def index(lbl: str) -> int:
    y, q = lbl.split("-Q")
    return int(y) * 4 + int(q) - 1


def start(qi: int) -> pd.Timestamp:
    return pd.Timestamp(year=qi // 4, month=3 * (qi % 4) + 1, day=1)


def end(qi: int) -> pd.Timestamp:
    return start(qi + 1) - pd.Timedelta(days=1)


def scheduled_issue(qi: int) -> pd.Timestamp:
    """FI7 operational issue: last day of the quarter's second month (after the previous quarter's SWS release)."""
    return start(qi) + pd.DateOffset(months=2) - pd.Timedelta(days=1)


def lead1(date) -> dict:
    """Issue quarter = the quarter containing `date`; target = the next calendar quarter (Lead 1)."""
    c = qi_of(date)
    return {"current_quarter": label(c), "issue_quarter": label(c), "target_quarter": label(c + 1), "horizon": 1,
            "scheduled_issue_date": scheduled_issue(c).date().isoformat()}
