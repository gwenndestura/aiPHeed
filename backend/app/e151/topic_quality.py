"""
BERTopic quality for the E151 news pipeline (Part 3.2 of the 2026-11-07 completion brief). Reads the fitted topics; fits
nothing. Each origin is scored only against stories published before it, the same rule the topic models were fitted under.

    NPMI coherence   mean normalised PMI over keyword pairs (document co-occurrence in the origin's earlier stories);
                     -1 to 1, above 0 means the keywords co-occur more than chance
    diversity        unique keywords / all keywords across the origin's topics (1 = no repetition)
    stability        for each topic, best keyword-set Jaccard with the previous origin's topics (mean)
    outlier rate     share of stories BERTopic left unassigned (topic -1)
    off-topic rate   share of topics removed as not about food (the pipeline's own XLM-based check)

    python -m app.e151.topic_quality -> data/e151/out/topic_quality.json
"""
from __future__ import annotations

import itertools
import json
import re

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e151" / "out"
RAW = BACKEND_DIR / "data" / "e151" / "raw"


def _kw(s: str) -> list[str]:
    return [k.strip().lower() for k in str(s).split(",") if k.strip()]


def npmi(keys: list[str], docs: list[str]) -> float | None:
    n = len(docs)
    if n < 50:
        return None
    pres = {k: np.array([bool(re.search(r"\b" + re.escape(k) + r"\b", d)) for d in docs]) for k in keys}
    vals = []
    for a, b in itertools.combinations(keys, 2):
        pa, pb, pab = pres[a].mean(), pres[b].mean(), (pres[a] & pres[b]).mean()
        if pa == 0 or pb == 0:
            continue
        if pab == 0:
            vals.append(-1.0)
            continue
        vals.append(float(np.log(pab / (pa * pb)) / -np.log(pab)))
    return float(np.mean(vals)) if vals else None


def main():
    T = pd.read_csv(OUT / "topic_report.csv")
    S = pd.read_parquet(RAW / "stories.parquet", columns=["published", "masked", "title"])
    S["doc"] = (S["title"].fillna("") + " " + S["masked"].fillna("")).str.lower()
    res, prev = {"origins": {}}, None
    for o, g in T.groupby("origin", sort=True):
        docs = S.loc[S["published"] < pd.Timestamp(o), "doc"].tolist()
        if len(docs) > 4000:                                   # fixed-seed sample keeps the run short; same rule each origin
            docs = list(np.random.default_rng(151).choice(docs, 4000, replace=False))
        on = g[~g["off_topic"].astype(bool)]
        kws = [_kw(k)[:8] for k in on["keywords"]]
        coh = [c for c in (npmi(k, docs) for k in kws) if c is not None]
        allk = [w for k in kws for w in k]
        stab = None
        if prev is not None and kws:
            stab = float(np.mean([max(len(set(k) & set(p)) / len(set(k) | set(p)) for p in prev) for k in kws]))
        a = RAW / f"topic_assign_{o}.parquet"
        outl = None
        if a.exists():
            A = pd.read_parquet(a)
            col = "topic" if "topic" in A.columns else next((c for c in A.columns if "topic" in c), None)
            outl = round(float((A[col] == -1).mean()), 3) if col else None
        res["origins"][o] = {"topics": int(len(g)), "on_topic": int(len(on)), "off_topic_rate": round(float(g["off_topic"].mean()), 3),
                             "npmi_mean": round(float(np.mean(coh)), 3) if coh else None,
                             "npmi_share_positive": round(float(np.mean(np.array(coh) > 0)), 3) if coh else None,
                             "diversity": round(len(set(allk)) / len(allk), 3) if allk else None,
                             "stability_vs_previous_origin": round(stab, 3) if stab is not None else None,
                             "outlier_rate": outl, "reference_docs": len(docs)}
        prev = kws or prev
    v = [r for r in res["origins"].values() if r["npmi_mean"] is not None]
    res["summary"] = {"npmi_mean": round(float(np.mean([r["npmi_mean"] for r in v])), 3),
                      "diversity_mean": round(float(np.mean([r["diversity"] for r in v if r["diversity"] is not None])), 3),
                      "stability_mean": round(float(np.mean([r["stability_vs_previous_origin"] for r in v if r["stability_vs_previous_origin"] is not None])), 3),
                      "off_topic_rate_mean": round(float(np.mean([r["off_topic_rate"] for r in v])), 3),
                      "note": "Interpretability is not scored automatically; topic keywords per origin are in topic_report.csv for human review."}
    (OUT / "topic_quality.json").write_text(json.dumps(res, indent=1), newline="\n")
    print(json.dumps(res["summary"], indent=1))
    for o, r in res["origins"].items():
        print(o, r)


if __name__ == "__main__":
    main()
