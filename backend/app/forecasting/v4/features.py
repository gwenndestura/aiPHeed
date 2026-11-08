"""
v4 exogenous features (PREREGISTRATION section 2.1): frozen point-in-time snapshots per (issue, area). A snapshot may
be used only at its own issue; asking for another issue's snapshot raises LeakageError.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.forecasting.as_of import LeakageError

SNAPSHOTS = Path(__file__).resolve().parents[3] / "data" / "forecasting" / "v4_feature_snapshots.csv"
FEATURES = ("rice_yoy", "typhoons_PAR", "oni_quarter_mean", "E1_unemployment_change_pp", "news_gdelt_shortage_share",
            "poverty")
GROUP = {"rice_yoy": "market", "typhoons_PAR": "climate", "oni_quarter_mean": "climate",
         "E1_unemployment_change_pp": "employment_ofw", "news_gdelt_shortage_share": "news_nlp",
         "poverty": "poverty_vulnerability"}


@lru_cache(maxsize=2)
def _load(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def table(path: Path = SNAPSHOTS) -> pd.DataFrame:
    return _load(str(path)).copy()


def snapshot(t: pd.DataFrame, issue: date | str, used_at: date | str | None = None) -> pd.DataFrame:
    """Rows of the snapshot taken at `issue`. If it is used for a forecast issued at `used_at`, both must be equal."""
    issue = str(issue)
    if used_at is not None and str(used_at) != issue:
        raise LeakageError(f"snapshot of {issue} used for a forecast issued {used_at}")
    s = t[t["issue"] == issue]
    if (s["issue"] != issue).any():
        raise LeakageError("snapshot contains another issue's rows")
    return s.set_index("area")
