"""
scripts/recover_new_corpus_leads.py
------------------------------------
Same recovery logic as recover_article_leads.py (Google News token resolution
-> publisher fetch -> Wayback fallback), pointed at the Sept-19 raw corpus
(data/raw/corpus_raw.parquet) instead of the older, already-curated
calabarzon_food_insecurity_dataset.parquet. That corpus's articles are 96%
title-only (no body text), which is why the strict reanalysis pipeline
retained zero of them -- there was nothing for the NLI classifier to read.

Output: data/processed/_recovered_leads_new_corpus.parquet
  article_id, resolved_url, lead, lead_chars, recovery_path, error
"""
from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.recover_article_leads import MIN_LEAD, recover_one  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recover_new")

RAW = Path("data/raw/corpus_raw.parquet")
OUT = Path("data/processed/_recovered_leads_new_corpus.parquet")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    df = pd.read_parquet(RAW)
    df["lead_len"] = df["summary"].fillna("").astype(str).str.len()
    todo = df[df["lead_len"] == 0][["article_id", "link"]].rename(columns={"link": "url"})
    log.info("rows missing lead: %d of %d", len(todo), len(df))

    done = pd.DataFrame()
    if OUT.exists():
        done = pd.read_parquet(OUT)
        keep = set(done[done["lead_chars"] >= MIN_LEAD]["article_id"])
        todo = todo[~todo["article_id"].isin(keep)]
        log.info("checkpoint: %d already recovered, %d remaining", len(keep), len(todo))

    if args.limit:
        todo = todo.head(args.limit)
    if todo.empty:
        log.info("nothing to do")
        return

    recs = todo.to_dict("records")
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(recover_one, r): r for r in recs}
        for n, f in enumerate(as_completed(futs), 1):
            results.append(f.result())
            if n % 10 == 0 or n == len(recs):
                ok = sum(1 for x in results if x["lead_chars"] >= MIN_LEAD)
                log.info("processed %d/%d | recovered %d", n, len(recs), ok)

    new = pd.DataFrame(results)
    if not done.empty:
        new = pd.concat(
            [done[~done["article_id"].isin(set(new["article_id"]))], new],
            ignore_index=True,
        )
    new.to_parquet(OUT, index=False)

    ok = new[new["lead_chars"] >= MIN_LEAD]
    log.info("saved %d rows -> %s", len(new), OUT)
    log.info("recovered %d (%.1f%%)", len(ok), 100 * len(ok) / max(len(new), 1))
    if not ok.empty:
        log.info("by path: %s", dict(ok["recovery_path"].value_counts()))


if __name__ == "__main__":
    main()
