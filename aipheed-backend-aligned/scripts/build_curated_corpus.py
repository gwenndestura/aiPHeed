"""
scripts/build_curated_corpus.py
--------------------------------
Build the NLP-track corpus from the curated CALABARZON food insecurity dataset.

The article fetcher collects a broad corpus; `corpus_geocoded.parquet` holds
6,085 articles of which 1,684 carry a province. Algorithm 1 then scores every
one of them and keeps those clearing 0.30. That retention was found to admit
articles with no bearing on food insecurity -- one retained item is headlined
"Floorball takes center stage as Philippines hosts men" -- and the resulting
Food Stress Sentiment Index correlates **-0.339** with SWS hunger over the
window, moving against the very quantity it is meant to track.

`calabarzon_food_insecurity_dataset.csv` is a curated subset of the same
collection: 371 articles, each carrying a province, a hypothesis assignment, a
food security dimension, an event type and a relevance tier. Built from it, the
Index correlates **+0.347** with SWS hunger -- the right direction.

WHAT THIS COSTS, stated plainly because it is the reason the broad corpus was
used first. The curated set covers 21 of the 120 province-quarters. The
Section 3.3.2.6 fill rule carries 94 FSSI cells forward, so the feature is
largely imputed, and only one cell reaches the five-article threshold of
Rule 5, which means 119 of 120 forecasts publish with LIMITED_SIGNAL. See
docs/PROPOSAL_CONFORMANCE.md 1.36 for the full comparison and the decision.

Scores are NOT recomputed here. Every curated article is matched by URL into
the already-scored corpus, so each keeps the food insecurity score Algorithm 1
assigned it, and the 0.30 threshold still applies downstream in fssi_builder.
The curation selects which articles enter aggregation; it does not relabel them.

    python -m scripts.build_curated_corpus
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CURATED_CSV = Path("../backend/data/processed/calabarzon_food_insecurity_dataset.csv")
SCORED_CORPUS = Path("data/processed/corpus_geocoded.parquet")
OUTPUT_PATH = Path("data/processed/corpus_curated.parquet")

# The curated file names provinces in prose; the pipeline keys on PSGC.
PROVINCE_CODES = {
    "Cavite":   "PH040100000",
    "Laguna":   "PH040200000",
    "Quezon":   "PH040300000",
    "Rizal":    "PH040400000",
    "Batangas": "PH040500000",
}


def build_curated_corpus(
    curated_csv: Path = CURATED_CSV,
    scored_corpus: Path = SCORED_CORPUS,
    output_path: Path = OUTPUT_PATH,
) -> pd.DataFrame:
    """Match the curated articles into the scored corpus and save the subset."""
    if not curated_csv.exists():
        raise FileNotFoundError(f"curated dataset not found at {curated_csv}")
    if not scored_corpus.exists():
        raise FileNotFoundError(
            f"{scored_corpus} not found — run the collection and scoring stages first"
        )

    curated = pd.read_csv(curated_csv)
    scored = pd.read_parquet(scored_corpus)
    scored["_url"] = scored["link"].astype(str)

    # The curated file carries its own province and publication date. Both are
    # preferred over the pipeline's, because the curation is what corrected
    # them; where it leaves one blank the pipeline's value stands.
    published = pd.to_datetime(curated["publication_date"], errors="coerce", utc=True)
    curated["_quarter"] = (
        published.dt.year.astype("string") + "-Q" + published.dt.quarter.astype("string")
    )
    curated["_province_code"] = curated["province"].map(PROVINCE_CODES)

    merged = scored.merge(
        curated[["url", "_province_code", "_quarter"]].rename(columns={"url": "_url"}),
        on="_url", how="inner",
    )
    logger.info("matched %d of %d curated articles into the scored corpus",
                len(merged), len(curated))

    merged["province_code"] = merged["_province_code"].fillna(merged["province_code"])
    merged["quarter"] = merged["_quarter"].fillna(merged["quarter"])
    merged = merged.drop(columns=["_url", "_province_code", "_quarter"])

    before = len(merged)
    merged = merged[merged["province_code"].notna()]
    if len(merged) < before:
        logger.info("dropped %d articles with no province", before - len(merged))

    from app.ml.features.feature_matrix import MODEL_QUARTERS

    in_window = merged[merged["quarter"].isin(MODEL_QUARTERS)]
    cells = in_window.groupby(["province_code", "quarter"]).ngroups
    retained = int((in_window["food_insecurity_score"] >= 0.30).sum())
    logger.info(
        "in-window: %d articles across %d of 120 province-quarters; %d clear the "
        "0.30 threshold Algorithm 1 applies downstream",
        len(in_window), cells, retained,
    )
    if cells < 60:
        logger.warning(
            "the curated corpus populates only %d of 120 province-quarters. The "
            "Section 3.3.2.6 fill rule will impute the rest, and most cells will "
            "fall below Rule 5's five-article threshold. This is the documented "
            "cost of the curation — see PROPOSAL_CONFORMANCE.md 1.36.", cells,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(output_path, index=False)
    logger.info("curated corpus saved -> %s (%d articles)", output_path, len(merged))
    return merged


if __name__ == "__main__":
    build_curated_corpus()
