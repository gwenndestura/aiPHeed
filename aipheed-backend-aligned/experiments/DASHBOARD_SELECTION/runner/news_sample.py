"""Blind stratified headline sample for the independent news review (run from backend/).

v3 (model pipeline, Main = current): 10 relevant per trigger (5 triggers) + 40 not relevant; feed (current branch's
final_engine news): 6 per category. De-duplicated by normalised title, shuffled (seed 2034). The blind file has no
pipeline labels; the key file has them and is not read during annotation.

    python ../aipheed-backend-aligned/experiments/DASHBOARD_SELECTION/runner/news_sample.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import pandas as pd  # noqa: E402

from app.news import pipeline_v3 as P  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "out"
SEED = 2034


def main():
    c = pd.DataFrame(P.corpus())
    c["year"] = c["ph_date"].str[:4]
    rel = c[c["relevant"] == 1]
    parts = [rel[rel["trigger"] == t].sample(10, random_state=SEED) for t in sorted(rel["trigger"].unique())]
    parts.append(c[c["relevant"] == 0].sample(40, random_state=SEED))
    v3 = pd.concat(parts).assign(source="v3", v3_relevant=lambda d: d["relevant"], v3_trigger=lambda d: d["trigger"],
                                 feed_categories="", feed_kind="")
    f = pd.read_csv(Path.cwd() / "data" / "final_engine" / "news_events.csv", keep_default_na=False)
    f["cat1"] = f["categories"].str.split(";").str[0]
    fs = pd.concat([g.sample(min(6, len(g)), random_state=SEED) for _, g in f.groupby("cat1")])
    fs = fs.assign(source="feed", ph_date=fs["published"], v3_relevant="", v3_trigger="", feed_categories=fs["categories"],
                   feed_kind=fs["kind"])
    S = pd.concat([v3[["source", "ph_date", "outlet", "title", "v3_relevant", "v3_trigger", "feed_categories", "feed_kind"]],
                   fs[["source", "ph_date", "outlet", "title", "v3_relevant", "v3_trigger", "feed_categories", "feed_kind"]]])
    S["norm"] = S["title"].map(P.norm_title)
    S = S.drop_duplicates("norm").sample(frac=1, random_state=SEED).reset_index(drop=True)
    S["id"] = [f"N{i:03d}" for i in range(len(S))]
    # feed membership of every sampled title (for the feed's recall on 2025-26 items)
    S["in_feed"] = S["norm"].isin(set(f["title"].map(P.norm_title)))
    S[["id", "ph_date", "outlet", "title"]].to_csv(OUT / "news_review_blind.csv", index=False, lineterminator="\n")
    S.drop(columns=["norm"]).to_csv(OUT / "news_review_key.csv", index=False, lineterminator="\n")
    print(len(S), S["source"].value_counts().to_dict())


if __name__ == "__main__":
    main()
