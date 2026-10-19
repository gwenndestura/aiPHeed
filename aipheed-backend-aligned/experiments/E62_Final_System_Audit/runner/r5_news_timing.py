"""E62 r5: independent check of the E60 improved-news features (timing, dates, duplicates, retrospective collection)
and of how much news actually reaches the served E56/E58 model.

  1. Date handling in the E60 store: published_raw (GMT) + 8 h == ph_date; quarter == quarter(ph_date).
  2. Collection time: first_seen_at of every E60 article (retrospective if after the issue date of its quarter).
  3. Duplicates: article_key unique; syndicated copies (same normalised title, different key) per province-quarter.
  4. Recompute nz_coverage, nz_events and the five nz_<trigger>_share columns from classified_articles.csv with my
     own code (articles of quarter t, PH date before O(t) = day 1 of quarter t+1) and compare with news_features.csv.
  5. Zero / near-zero share of the old (E40) and new (E60) news features on the 50 evaluation rows.
  6. Did the served E58/E56 record use any E60 feature? (feature schema vs E60 column names)

    backend/venv/Scripts/python.exe -B runner/r5_news_timing.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
E62 = Path(__file__).resolve().parents[1]
EXP = E62.parent
ROOT = EXP.parents[1]
E60 = EXP / "E60_E58_Accuracy_Optimization"
STORE = E60 / "data" / "news_e60" / "articles.jsonl"
CLS = E60 / "data" / "classified_articles.csv"
FEAT = E60 / "data" / "news_features.csv"
OLD = EXP / "E40_SWS_CPI_Tiers" / "runs" / "triggers" / "composition.csv"
SCHEMA = ROOT / "backend" / "data" / "e56" / "model" / "feature_schema.json"
PROVS = ["PH040100000", "PH040200000", "PH040300000", "PH040400000", "PH040500000"]
TRIG = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]


def qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


def qs(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def q_of_date(s: str) -> str:
    return f"{s[:4]}-Q{(int(s[5:7]) - 1) // 3 + 1}"


def origin_date(t: int) -> str:
    n = t + 1
    return f"{n // 4}-{(n % 4) * 3 + 1:02d}-01"


def norm(t: str) -> str:
    w = re.sub(r"[^a-z0-9 ]", "", str(t).lower()).split()
    return " ".join(w[:8])


def main():
    res = {}
    st = pd.DataFrame([json.loads(x) for x in STORE.open(encoding="utf-8")])
    raw = pd.to_datetime(st["published_raw"], format="%a, %d %b %Y %H:%M:%S GMT", utc=True)
    ph = (raw + pd.Timedelta(hours=8)).dt.strftime("%Y-%m-%d")
    seen = pd.to_datetime(st["first_seen_at"], utc=True)
    res["e60_store"] = {
        "articles": int(len(st)), "unique_keys": int(st["article_key"].nunique()),
        "ph_date_mismatch_vs_gmt_plus_8": int((ph != st["ph_date"]).sum()),
        "quarter_mismatch": int((st["ph_date"].map(q_of_date) != st["quarter"]).sum()),
        "date_kind": st["date_kind"].value_counts().to_dict(),
        "outside_requested_window": int(st["outside_requested_window"].astype(bool).sum()),
        "ph_date_range": [st["ph_date"].min(), st["ph_date"].max()],
        "first_seen_range_utc": [str(seen.min()), str(seen.max())],
        "collected_after_issue_date_of_its_quarter": int(sum(
            s.strftime("%Y-%m-%d") >= origin_date(qi(q)) for s, q in zip(seen, st["quarter"]))),
    }
    c = pd.read_csv(CLS, dtype={"geo_province_code": str})
    c["q"] = c["quarter"].map(qi)
    res["classified"] = {"articles": int(len(c)), "unique_keys": int(c["article_key"].nunique()),
                         "relevant": int(c["relevant"].sum()),
                         "relevant_attributed": int(((c["relevant"] == 1) & c["geo_province_code"].notna()).sum()),
                         "pre_2021": int((c["ph_date"] < "2021-01-01").sum()),
                         "after_2026_10_14": int((c["ph_date"] > "2026-10-14").sum()),
                         "quarter_mismatch": int((c["ph_date"].map(q_of_date) != c["quarter"]).sum())}
    rel = c[c["relevant"] == 1].copy()
    rel["norm"] = rel["title"].map(norm)
    dup = rel[rel["geo_province_code"].notna()].groupby(["geo_province_code", "q", "norm"]).size()
    res["syndicated_relevant_copies"] = {"groups_with_more_than_one_copy": int((dup > 1).sum()),
                                         "extra_copies": int((dup - 1).clip(lower=0).sum())}
    # 4. recompute features
    f = pd.read_csv(FEAT, dtype={"province_code": str})
    mine = []
    for t in sorted(f["t"].unique()):
        O = origin_date(t)
        w = rel[(rel["q"] == t) & (rel["ph_date"] < O)]
        for p in PROVS:
            wp = w[w["geo_province_code"] == p]
            r = {"t": t, "province_code": p, "my_cov": float(len(wp)), "my_events": float(wp["norm"].nunique())}
            for k in TRIG:
                r[f"my_{k}"] = float((wp["trigger"] == k).sum() / len(wp)) if len(wp) else 0.0
            mine.append(r)
    M = f.merge(pd.DataFrame(mine), on=["t", "province_code"])
    diffs = {"nz_coverage": float((M["nz_coverage"] - M["my_cov"]).abs().max()),
             "nz_events": float((M["nz_events"] - M["my_events"]).abs().max())}
    for k in TRIG:
        diffs[f"nz_{k}_share"] = float((M[f"nz_{k}_share"] - M[f"my_{k}"]).abs().max())
    res["feature_recompute_max_abs_diff"] = diffs
    # 5. zero shares on the evaluation origins (2023-Q4..2026-Q1) and at the 2027-Q1 origin
    ev = M[(M["t"] >= qi("2023-Q4")) & (M["t"] <= qi("2026-Q1"))]
    old = pd.read_csv(OLD, dtype={"province_code": str})
    old["t"] = old["quarter"].map(qi)
    oev = old[(old["t"] >= qi("2023-Q4")) & (old["t"] <= qi("2026-Q1"))]
    res["zero_share_eval_rows"] = {
        "rows": int(len(ev)),
        "E60_v2": {k: round(float((ev[f"nz_{k}_share"] == 0).mean()), 3) for k in TRIG},
        "E40_v1_served_hits_over_articles": {k: round(float((oev[f"hits_{k}"] == 0).mean()), 3) for k in TRIG},
        "E60_province_quarters_with_no_relevant_attributed_article": int((ev["nz_coverage"] == 0).sum())}
    # 6. served schema
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    names = json.dumps(schema)
    res["served_schema_uses_E60_features"] = any(x in names for x in ("nz_", "hist_ps"))
    res["served_schema_news_columns"] = sorted(set(re.findall(r'"(news_[a-z_]+)"', names)))
    (E62 / "out" / "r5_news_timing.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
