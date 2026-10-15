"""
app/ml/corpus/language_filter.py
---------------------------------
Figure 3.6.2, News Data Track: "A language detection filter will then be
applied to retain only Filipino and English articles, discarding those outside
the intended linguistic scope."

Most of that scoping already happens where articles are collected, which is the
stronger place for it:

  * `gdelt_fetcher` constrains the GDELT DOC 2.0 query with
    `sourcelang=english tagalog`, so no other language is requested;
  * `gnews_rss_fetcher` queries in English and in Filipino/Tagalog and reads
    Google News RSS for the Philippines;
  * `rss_fetcher` reads an allowlist of Philippine outlets.

This module is the explicit filter the flowchart names, applied after text
extraction and before geocoding. It is a backstop rather than the primary
mechanism, and on the current corpus it removes nothing — which is the outcome
the collection design predicts, and is reported rather than assumed.

Detection is by script, not by classifier. English and Filipino are both written
in Latin script, so text that is predominantly non-Latin is outside the scope by
construction. That rule is auditable and needs no model or extra dependency; a
word-frequency classifier would be worse here, because Philippine headlines are
short, code-switch freely between English and Filipino mid-sentence, and carry
place names that belong to neither vocabulary.

Usage:
    from app.ml.corpus.language_filter import filter_in_scope
    kept, dropped = filter_in_scope(articles_df)
"""

from __future__ import annotations

import logging
import unicodedata

import pandas as pd

logger = logging.getLogger(__name__)

# Share of alphabetic characters that may fall outside Latin script before an
# article is treated as out of scope. A Filipino or English article quoting a
# foreign name stays in; an article written in another script does not.
MAX_NON_LATIN_SHARE = 0.30


def non_latin_share(text: str) -> float:
    """Share of alphabetic characters that are not Latin script (0.0–1.0)."""
    letters = [c for c in str(text or "") if c.isalpha()]
    if not letters:
        return 0.0
    non_latin = sum(
        1 for c in letters if "LATIN" not in unicodedata.name(c, "")
    )
    return non_latin / len(letters)


def is_in_scope(title: str, summary: str = "") -> bool:
    """True when the article is within the Filipino/English scope."""
    return non_latin_share(f"{title or ''} {summary or ''}") <= MAX_NON_LATIN_SHARE


def filter_in_scope(
    articles_df: pd.DataFrame,
    title_col: str = "title",
    summary_col: str = "summary",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split a corpus into in-scope and out-of-scope articles.

    Returns (kept, dropped). The dropped frame is returned rather than discarded
    so a run can report what the filter removed instead of only how many
    survived.
    """
    if articles_df.empty:
        return articles_df, articles_df

    titles = articles_df.get(title_col, pd.Series("", index=articles_df.index))
    summaries = articles_df.get(summary_col, pd.Series("", index=articles_df.index))
    in_scope = [
        is_in_scope(t, s) for t, s in zip(titles.fillna(""), summaries.fillna(""))
    ]
    mask = pd.Series(in_scope, index=articles_df.index)

    kept, dropped = articles_df[mask], articles_df[~mask]
    if len(dropped):
        logger.warning(
            "language filter: dropped %d of %d articles as outside the "
            "Filipino/English scope", len(dropped), len(articles_df),
        )
    else:
        logger.info(
            "language filter: all %d articles are within the Filipino/English "
            "scope (the collection queries already constrain language)",
            len(articles_df),
        )
    return kept, dropped
