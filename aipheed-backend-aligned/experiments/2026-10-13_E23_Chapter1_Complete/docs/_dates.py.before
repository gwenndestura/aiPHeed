"""
app/ml/corpus/_dates.py
-----------------------
One place that turns whatever a feed calls a publication date into an ISO
string, so that every fetcher stores a value `pandas.Timestamp` can read.

WHY THIS EXISTS. RSS feeds publish dates in RFC 822 -- "Mon, 25 May 2020
08:14:00 GMT" -- and `gnews_rss_fetcher` previously stored that string verbatim
whenever `published_parsed` was unavailable. Something downstream then truncated
the stored value to ten characters, the width of an ISO date, leaving "Mon, 25
Ma": weekday, day, and two letters of the month, with the year gone.

213 of the 1,684 geocoded articles carry a value in that state. They cannot be
recovered. The weekday does constrain the year, but across the corpus's real
2005-2026 span not one of the 213 resolves to a single date -- every one has at
least two candidates, and picking among them would be inventing the answer
rather than reading it. Those articles were scored and geocoded but belong to no
quarter, so they contribute to no province-quarter cell and are lost to the FSSI.

The fix is therefore preventive: normalise at the point of collection so the
stored value is always ISO and a truncation of this kind cannot destroy a year.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)


def normalize_published(value) -> str | None:
    """
    Return an ISO 8601 string for `value`, or None when it cannot be read.

    Accepts a datetime, an ISO string, or an RFC 822 feed date. Returning None
    rather than the raw string is deliberate: an unparseable date stored as text
    looks like data until it silently drops an article from every quarter.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return None

    try:
        from pandas import Timestamp

        return Timestamp(text).isoformat()
    except Exception:
        pass

    try:
        return parsedate_to_datetime(text).isoformat()
    except Exception:
        pass

    try:  # RFC 822 without a timezone
        return datetime.strptime(text, "%a, %d %b %Y %H:%M:%S").replace(
            tzinfo=timezone.utc).isoformat()
    except Exception:
        pass

    logger.warning(
        "normalize_published: could not read %r as a date; the article will "
        "carry no quarter and will not reach any province-quarter cell", text[:40],
    )
    return None
