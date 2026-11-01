"""
The ONE point-in-time selector. Every feature and target path in app.forecasting calls as_of(): a row may be used at
an issue date only if it was published strictly before that date (00:00 Asia/Manila on the issue day, exclusive), the
P-DASH rule of the frozen protocol (docs/aipheed/PROTOCOL_LOCK.md, E1). News uses the article publication timestamp.

A row without a publication date is never silently kept: it raises (strict) or is returned as NOT_YET_PUBLISHED.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pandas as pd

PH = ZoneInfo("Asia/Manila")


class LeakageError(ValueError):
    """Raised when information dated on or after the issue date would enter a forecast."""


def issue_instant(issue: date | datetime | str) -> pd.Timestamp:
    """00:00 Asia/Manila on the issue day (a datetime is used as given, converted to Manila time)."""
    if isinstance(issue, str):
        issue = datetime.fromisoformat(issue)
    if isinstance(issue, datetime):
        ts = pd.Timestamp(issue)
        return ts.tz_localize(PH) if ts.tzinfo is None else ts.tz_convert(PH)
    return pd.Timestamp(datetime.combine(issue, time(0, 0)), tz=PH)


def _published(s: pd.Series) -> pd.Series:
    ts = pd.to_datetime(s, errors="coerce")
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize(PH)
    else:
        ts = ts.dt.tz_convert(PH)
    return ts


def as_of(df: pd.DataFrame, issue: date | datetime | str, published_col: str = "published", strict: bool = True) -> pd.DataFrame:
    """Rows of df published strictly before the issue instant. strict: a missing/unparseable publication date raises."""
    if published_col not in df.columns:
        raise LeakageError(f"no '{published_col}' column: cannot prove when the data became available")
    pub = _published(df[published_col])
    if strict and pub.isna().any():
        raise LeakageError(f"{int(pub.isna().sum())} row(s) without a valid '{published_col}' date")
    return df[pub < issue_instant(issue)].copy()


def assert_point_in_time(df: pd.DataFrame, issue: date | datetime | str, published_col: str = "published") -> None:
    """Guard for an already-built feature table: fails loudly if any row was published on or after the issue."""
    pub = _published(df[published_col])
    bad = (pub >= issue_instant(issue)) | pub.isna()
    if bad.any():
        raise LeakageError(f"{int(bad.sum())} row(s) published on/after the issue date {issue}")
