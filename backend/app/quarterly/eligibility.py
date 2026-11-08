"""
app/quarterly/eligibility.py
----------------------------
Publication-time eligibility. The ONLY date that decides whether an article can support a forecast is its
original publication timestamp, converted to Philippine time. Retrieval, indexing and processing dates are
never used to place an article in a quarter. An article without a verifiable publication date is
QUARANTINED: it is kept for audit but feeds no feature, count, explanation or report.

Statuses
    ELIGIBLE        news_window_start <= published_ph <= news_window_end (end = min(cutoff, quarter end))
    AFTER_CUTOFF    published after the cutoff (includes target-quarter and later news)
    BEFORE_WINDOW   published before the reference quarter
    UNDATED         no verifiable publication date (quarantined)
    DUPLICATE       same canonical URL as an earlier-listed eligible/ineligible article
"""
from __future__ import annotations

import hashlib

import pandas as pd

from app.quarterly.config import ForecastPeriod
from app.quarterly.periods import PH_TZ

ELIGIBLE, AFTER, BEFORE, UNDATED, DUP = "ELIGIBLE", "AFTER_CUTOFF", "BEFORE_WINDOW", "UNDATED", "DUPLICATE"
MIN_ARTICLES = 5          # province-quarters with fewer eligible articles carry LIMITED_SIGNAL


def _published_ph(v):
    from app.ml.corpus._dates import published_in_ph
    try:
        return published_in_ph(v)
    except Exception:
        return None


def url_key(url) -> str | None:
    if url is None or (isinstance(url, float) and url != url):
        return None
    u = str(url).strip().lower().split("#")[0].rstrip("/")
    for pre in ("https://", "http://"):
        if u.startswith(pre):
            u = u[len(pre):]
    if u.startswith("www."):
        u = u[4:]
    return hashlib.sha256(u.encode("utf-8")).hexdigest()


def classify_news(df: pd.DataFrame, period: ForecastPeriod, published_col: str = "published",
                  url_col: str = "link") -> pd.DataFrame:
    """Return df with published_ph (Asia/Manila) and eligibility status columns. Pure function."""
    out = df.copy()
    out["published_ph"] = out[published_col].map(_published_ph)
    start, end = period.news_window_start, period.news_window_end

    def status(ts):
        if ts is None or pd.isna(ts):
            return UNDATED
        if ts > end:
            return AFTER
        if ts < start:
            return BEFORE
        return ELIGIBLE
    out["eligibility"] = out["published_ph"].map(status)
    if url_col in out.columns:
        k = out[url_col].map(url_key)
        dup = k.notna() & k.duplicated(keep="first")
        out.loc[dup, "eligibility"] = DUP
    return out


def eligible_news(df: pd.DataFrame, period: ForecastPeriod, **kw) -> pd.DataFrame:
    c = classify_news(df, period, **kw)
    return c[c["eligibility"] == ELIGIBLE].copy()


def news_summary(classified: pd.DataFrame, provinces: list[str], province_col: str = "province_code") -> dict:
    e = classified[classified["eligibility"] == ELIGIBLE]
    by = {p: int((e[province_col] == p).sum()) if province_col in e.columns else 0 for p in provinces}
    return {"eligible": int(len(e)),
            "excluded_after_cutoff": int((classified["eligibility"] == AFTER).sum()),
            "excluded_before_window": int((classified["eligibility"] == BEFORE).sum()),
            "quarantined_undated": int((classified["eligibility"] == UNDATED).sum()),
            "duplicates": int((classified["eligibility"] == DUP).sum()),
            "by_province": by,
            "limited_signal": {p: n < MIN_ARTICLES for p, n in by.items()},
            "earliest_eligible": e["published_ph"].min().isoformat() if len(e) else None,
            "latest_eligible": e["published_ph"].max().isoformat() if len(e) else None}


def indicator_rows_available(df: pd.DataFrame, cutoff: pd.Timestamp, available_col: str = "available_at") -> pd.DataFrame:
    """Rows whose own availability time is on or before the cutoff. Unknown availability = unavailable."""
    av = pd.to_datetime(df[available_col], errors="coerce", utc=True).dt.tz_convert(PH_TZ)
    return df[av.notna() & (av <= cutoff)].copy()
