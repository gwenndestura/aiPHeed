"""
scripts/supplementary/investigate_2024.py

Why is 2024 the weakest period for MODEL-B? Diagnostic only, on the baseline
(timing-valid, default LightGBM) walk-forward predictions; nothing is tuned.
Writes evidence/2026-10-08_optimization/investigation_2024.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import scripts.supplementary.algorithm4_timing_valid as A
import scripts.supplementary.reliability_diagnostics as R

OUT = Path("evidence/2026-10-08_optimization")


def main():
    f, labels, cols = A.frame_t2()
    d = R.pairs(f, labels, 1)
    r = R.walk(d, cols, None)
    r["pred"] = (r["p"] >= 0.5).astype(int)
    r["year"] = r["target_quarter"].str[:4]

    by_year = r.groupby("year").agg(rows=("y", "size"), high_share=("y", "mean"),
                                    mean_prob=("p", "mean"), acc=("pred", lambda s: 0))
    by_year["acc"] = r.assign(c=(r["pred"] == r["y"]).astype(float)).groupby("year")["c"].mean()
    by_year["missed_high"] = r[(r["y"] == 1) & (r["pred"] == 0)].groupby("year").size()
    by_year["false_high"] = r[(r["y"] == 0) & (r["pred"] == 1)].groupby("year").size()
    by_year = by_year.fillna(0)

    fold = []
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    for q in tq[R.MIN_TRAIN:]:
        tr = d[d["target_quarter"].map(R.qi) < R.qi(q)]
        te = r[r["target_quarter"] == q]
        fold.append({"test_quarter": q, "train_high_share": round(float(tr["y"].mean()), 3),
                     "test_high": int(te["y"].sum()), "mean_prob": round(float(te["p"].mean()), 3),
                     "acc": round(float((te["pred"] == te["y"]).mean()), 2)})

    # Distribution shift: 2024 test feature rows vs. the training rows available
    # for the first 2024 fold (target quarters before 2024-Q1).
    test24 = d[d["target_quarter"].str.startswith("2024")]
    train_pre = d[d["target_quarter"].map(R.qi) < R.qi("2024-Q1")]
    shift = []
    for c in cols:
        a, b = train_pre[c], test24[c]
        sd = a.std() or 1.0
        shift.append({"feature": c, "smd": round(float((b.mean() - a.mean()) / sd), 2),
                      "share_outside_train_range": round(float(((b < a.min()) | (b > a.max())).mean()), 2)})
    shift = sorted(shift, key=lambda x: -abs(x["smd"]))

    fssi = pd.read_parquet("data/processed/fssi_quarterly.parquet")
    fssi["year"] = fssi["quarter"].str[:4]
    news = fssi.groupby("year")["article_count"].agg(["sum", "count"]).rename(
        columns={"sum": "articles", "count": "province_quarters_with_news"}).to_dict(orient="index")

    lab = labels.copy()
    lab["year"] = lab["quarter"].str[:4]
    sws_by_year = lab.groupby("year")["sws_hunger_pct"].mean().round(2).to_dict()
    cpi_by_year = f.assign(year=f["quarter"].str[:4]).groupby("year")[["food_cpi_yoy", "rice_price_regular_accel"]].mean().round(2).to_dict()

    out = {"by_year": by_year.round(3).reset_index().to_dict(orient="records"), "by_fold": fold,
           "largest_shift_features_2024": shift[:12], "news_by_year": news,
           "sws_mean_by_year": sws_by_year, "cpi_and_rice_by_year": cpi_by_year}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "investigation_2024.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    o = main()
    print(json.dumps(o["by_year"], indent=1)); print(json.dumps(o["by_fold"], indent=1))
    print(json.dumps(o["largest_shift_features_2024"], indent=1)); print(o["news_by_year"]); print(o["sws_mean_by_year"])
