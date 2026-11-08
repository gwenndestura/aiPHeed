"""
v10 news gate (docs/aipheed/v10/NEWS_AUDIT.md). Every news window passes through the one as_of selector on the
publication timestamp, never the crawl date. Volume-normalised share with missing kept distinct from zero, and a guard
that refuses a topic model fitted on anything published on or after the forecast origin.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.forecasting.as_of import LeakageError, as_of, issue_instant


def visible_news(articles: pd.DataFrame, issue) -> pd.DataFrame:
    """Articles published strictly before the issue. A missing publication time raises (as_of strict)."""
    return as_of(articles, issue, published_col="published_ph")


def food_stress_share(articles: pd.DataFrame, issue, start, province: str | None) -> dict:
    """N1 and N7 for one window ending before the issue. No article: share is NaN (no coverage), never 0."""
    v = visible_news(articles, issue)
    pub = pd.to_datetime(v["published_ph"], utc=True)
    v = v[pub >= issue_instant(start)]
    v = v[v["geo_province_code"].isna()] if province is None else v[v["geo_province_code"] == province]
    n = len(v)
    return {"share": float(v["relevant"].astype(bool).mean()) if n else np.nan, "count": n,
            "sources": int(v["source_domain"].nunique()) if n else 0}


def assert_topic_fit_is_past_only(fit_published: pd.Series, origin) -> None:
    """A topic model fitted on any article published on or after the origin leaks later vocabulary into features."""
    pub = pd.to_datetime(fit_published, utc=True, errors="coerce")
    if pub.isna().any():
        raise LeakageError("topic fit includes an article without a valid publication time")
    if (pub >= issue_instant(origin).tz_convert("UTC")).any():
        raise LeakageError(f"topic model fitted on articles published on or after the origin {origin}")
