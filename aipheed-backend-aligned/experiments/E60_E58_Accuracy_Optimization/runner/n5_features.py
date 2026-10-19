"""E60 step N5: as-of news features from the E31 + E60 corpora with classifier v2 (MODEL_SELECTION_AND_VALIDATION_PROTOCOL.md
section 4). For origin t (issue O(t) = day 1 of quarter t+1) only articles published in quarter t (hence before O(t)) are
counted; change features compare with quarters t-4..t-1. Also the history features of candidate D.

    backend/venv/Scripts/python.exe -B runner/n5_features.py  -> data/news_features.csv, data/classified_articles.csv
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

E60 = Path(__file__).resolve().parents[1]
EXP = E60.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(EXP / "E55_Food_Insecurity_LightGBM" / "runner"))
import e55_lib as F  # noqa: E402
from n4_classifier import classify  # noqa: E402

L = F.L
STORES = [EXP / "E31_Chapter1_Completion" / "backend_dev" / "data" / "news_e31" / "articles.jsonl",
          E60 / "data" / "news_e60" / "articles.jsonl"]
TRIG = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
NEWS_COLS = ([f"nz_{k}_share" for k in TRIG] + [f"nz_{k}_chg" for k in TRIG] + [f"nz_reg_{k}" for k in TRIG]
             + ["nz_coverage", "nz_events"])
HIST_COLS = ["hist_ps_last", "hist_ps_share4"]


def corpus() -> pd.DataFrame:
    rows = []
    for p in STORES:
        for x in p.open(encoding="utf-8"):
            r = json.loads(x)
            rows.append({k: r.get(k) for k in ("article_key", "title", "ph_date", "published_ph", "quarter",
                                                 "geo_province_code", "source_domain", "first_query_id")} | {"store": p.parent.name})
    a = pd.DataFrame(rows).drop_duplicates("article_key")
    a = a[(a["ph_date"] >= "2021-01-01")]
    from app.ml.corpus.geocoder import geocode_to_province as g  # noqa: E402
    c = [classify(t, g) for t in a["title"]]
    a["relevant"] = [x["relevant"] for x in c]
    a["trigger"] = [x["trigger"] for x in c]
    a["rule"] = [x["rule"] for x in c]
    a["q"] = a["quarter"].map(L.qi)
    a["norm_title"] = a["title"].str.lower().str.replace(r"[^a-z0-9 ]", "", regex=True).str.split().map(lambda w: " ".join(w[:8]) if isinstance(w, list) else "")
    return a


def features(a: pd.DataFrame) -> pd.DataFrame:
    rel = a[a["relevant"] == 1]
    out = []
    for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
        O = L.origin(t)
        w = rel[(rel["q"] == t) & (pd.to_datetime(rel["published_ph"], utc=True) < O.tz_localize("Asia/Manila"))]
        hist = rel[(rel["q"] >= t - 4) & (rel["q"] <= t - 1)]
        reg_tot = max(len(w), 1)
        for p in L.PROVS:
            wp = w[w["geo_province_code"] == p]
            r = {"t": t, "province_code": p, "nz_coverage": float(len(wp)), "nz_events": float(wp["norm_title"].nunique())}
            for k in TRIG:
                ck = (wp["trigger"] == k).sum()
                r[f"nz_{k}_share"] = float(ck / len(wp)) if len(wp) else 0.0
                hk = hist[(hist["geo_province_code"] == p) & (hist["trigger"] == k)]
                base = len(hk) / 4.0
                r[f"nz_{k}_chg"] = float(np.log1p(ck) - np.log1p(base))
                r[f"nz_reg_{k}"] = float((w["trigger"] == k).sum() / reg_tot)
            out.append(r)
    return pd.DataFrame(out)


def history(d) -> pd.DataFrame:
    Y = F.t43_labels(d)
    ps = {(p, int(q)): int(v) for p, q, v in zip(Y["province_code"], Y["q"], Y["PS"])}
    out = []
    for t in range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1):
        for p in L.PROVS:
            last = ps.get((p, t - 1), np.nan)                 # CPI of quarter t-1 complete before O(t)
            prev = [ps[(p, q)] for q in range(t - 4, t) if (p, q) in ps]
            out.append({"t": t, "province_code": p, "hist_ps_last": float(last),
                        "hist_ps_share4": float(np.mean(prev)) if prev else np.nan})
    return pd.DataFrame(out)


def main():
    a = corpus()
    a[["article_key", "store", "ph_date", "quarter", "geo_province_code", "source_domain", "first_query_id", "relevant",
       "trigger", "rule", "title"]].to_csv(E60 / "data" / "classified_articles.csv", index=False)
    f = features(a).merge(history(L.load()), on=["t", "province_code"])
    f.to_csv(E60 / "data" / "news_features.csv", index=False)
    s = {"articles": int(len(a)), "relevant": int(a["relevant"].sum()),
         "relevant_by_trigger": a[a["relevant"] == 1]["trigger"].value_counts().to_dict(),
         "relevant_attributed": int(((a["relevant"] == 1) & a["geo_province_code"].notna()).sum()),
         "province_quarters_nonzero": {k: int((f[f"nz_{k}_share"] > 0).sum()) for k in TRIG}, "rows": int(len(f))}
    (E60 / "out" / "news_feature_summary.json").write_text(json.dumps(s, indent=1))
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    sys.path.insert(0, str(EXP.parents[1] / "backend"))
    main()
