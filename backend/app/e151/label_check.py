"""
E151 upgrade 2: a label check. A random sample of eligible stories is read and labelled before the model's output is looked at, then compared.
One reader, who also wrote the system: this is a check by the author, not independent human annotation.

    python -m app.e151.label_check sample  -> prints the sample, text only
    python -m app.e151.label_check compare -> data/e151/out/label_check.json (reads docs/e151/label_check_reader.csv)
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from app.e151 import OUT, RAW
from app.paths import BACKEND_DIR

N = 80
READER = BACKEND_DIR.parent / "docs" / "e151" / "label_check_reader.csv"
READER2 = BACKEND_DIR.parent / "docs" / "e151" / "label_check_reader_fresh.csv"


def sample(seed: int = 151, n: int = N) -> pd.DataFrame:
    d = pd.read_parquet(RAW / "stories.parquet", columns=["id", "story", "published", "site", "geo_level", "provinces", "score_text", "hash"]).drop_duplicates("story")
    if seed != 151:
        d = d[~d["story"].isin(sample()["story"])]
    return d.sample(n, random_state=seed).reset_index(drop=True)


def fresh() -> pd.DataFrame:
    return sample(1510, 80)


def show():
    for i, r in fresh().iterrows():
        print(f"{i}|{r.score_text[:240]}")


def compare():
    from app.e151.topics import EVENTS, event_probs
    s = fresh()
    h = pd.read_csv(READER2)
    e = event_probs()
    s = s.reset_index().rename(columns={"index": "i"}).merge(h, on="i").merge(e, on="hash", how="left")
    cols = [f"pr_{k}" for k in EVENTS]
    s["model"] = s[cols].idxmax(axis=1).str[3:]
    s.loc[s["pr_none"] >= .5, "model"] = "none"
    s["model2"] = s[cols].apply(lambda r: r.sort_values().index[-2][3:], axis=1)
    rele = s["reader"] != "none"
    out = {"sample": "fresh, labelled after the rule was fixed and before its output was read", "n": int(len(s)), "reader": "Claude, the system's author; labels written before the model output was read; not independent human annotation",
           "top_event_agreement": float((s["reader"] == s["model"]).mean()), "top2_agreement": float(((s["reader"] == s["model"]) | (s["reader"] == s["model2"])).mean()),
           "reader_share_none": float((~rele).mean()), "filter_kept_by_pr_none_lt_half_when_reader_relevant": float((s.loc[rele, "pr_none"] < .5).mean()), "filter_removed_when_reader_none": float((s.loc[~rele, "pr_none"] >= .5).mean()) if (~rele).any() else None,
           "reader_problem_vs_model_problem_agreement": float(((s["reader_problem"] == 1) == (s["problem"] > .5)).mean()),
           "by_reader_label": {k: {"n": int(len(g)), "model_agrees": float((g["model"] == k).mean())} for k, g in s.groupby("reader")},
           "wilson_note": "With n = 80 a share near 0.6 carries about +/- 0.11 at 95 %."}
    s[["i", "reader", "reader_problem", "model", "model2", "pr_none", "problem"]].round(3).to_csv(OUT / "label_check_rows.csv", index=False, lineterminator="\n")
    (OUT / "label_check.json").write_text(json.dumps(out, indent=1), newline="\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"sample": show, "compare": compare}[sys.argv[1]]()
