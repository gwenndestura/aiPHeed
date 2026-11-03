"""OLD_NEWS feasibility (report only): article counts per quarter, metadata only.

    python counts.py   # -> ../out/counts_quarterly.csv, ../out/counts_summary.json

Reads, never queries:
- E85's stored GKG rows 2021-01..2026-10 (backend/data/gdelt_e85/, via e85_features.load: the E85 de-duplication and
  province rule), by quarter: all records, food-themed (PRICE, FOODSEC or AGRI family) and per province;
- ../data/gdelt_doc_timeline_2017_2026.json: GDELT DOC 2.0 daily counts of Philippine articles matching
  (Batangas OR Cavite OR Laguna OR Rizal OR Calabarzon) AND (rice OR food OR hunger OR prices), with the number of
  articles GDELT monitored that day ("norm"), fetched once on 2026-11-03;
- the project news corpus (backend app.news.pipeline_v3): collected and admitted articles per quarter.
No model, feature or seal is touched.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
ROOT = EXP.parents[1]
sys.path.insert(0, str(EXP / "E85_GDELT_Events" / "runner"))
sys.path.insert(0, str(ROOT / "backend"))
import e85_features as G  # noqa: E402

NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def qlabel(q: int) -> str:
    return f"{q // 4}-Q{q % 4 + 1}"


def main():
    d = G.load()
    d["Q"] = d["q"].map(qlabel)
    food = d[["PRICE", "FOODSEC", "AGRI"]].sum(axis=1) > 0
    gkg = pd.DataFrame({"gkg_records": d.groupby("Q").size(), "gkg_food": d[food].groupby("Q").size(),
                        **{f"gkg_{n}": d[d[p] == 1].groupby("Q").size() for p, n in NAMES.items()}})
    doc = json.loads((HERE / "data" / "gdelt_doc_timeline_2017_2026.json").read_text(encoding="utf-8"))
    x = pd.DataFrame(doc["timeline"][0]["data"])
    x["date"] = pd.to_datetime(x["date"].str[:8])
    x["Q"] = x["date"].dt.year.astype(str) + "-Q" + x["date"].dt.quarter.astype(str)
    dq = x.groupby("Q").agg(doc_days=("value", "size"), doc_matching=("value", "sum"), doc_monitored=("norm", "sum"))
    dq["doc_per_100k_monitored"] = 1e5 * dq["doc_matching"] / dq["doc_monitored"]
    from app.news import pipeline_v3 as P
    c = pd.DataFrame([{"Q": a["quarter"]} for a in P.corpus()]).groupby("Q").size().rename("corpus_collected")
    a = pd.DataFrame([{"Q": a["quarter"]} for a in P.admitted()]).groupby("Q").size().rename("corpus_admitted")
    T = dq.join(gkg, how="outer").join(c, how="outer").join(a, how="outer").sort_index()
    (HERE / "out").mkdir(exist_ok=True)
    T.to_csv(HERE / "out" / "counts_quarterly.csv")

    def med(col, lo, hi):
        s = T.loc[lo:hi, col].dropna()
        return None if s.empty else float(s.median())
    summ = {"doc_matching_median": {"2017-2020": med("doc_matching", "2017-Q1", "2020-Q4"),
                                    "2021-2026Q3": med("doc_matching", "2021-Q1", "2026-Q3")},
            "doc_monitored_median": {"2017-2020": med("doc_monitored", "2017-Q1", "2020-Q4"),
                                     "2021-2026Q3": med("doc_monitored", "2021-Q1", "2026-Q3")},
            "doc_per_100k_median": {"2017-2020": med("doc_per_100k_monitored", "2017-Q1", "2020-Q4"),
                                    "2021-2026Q3": med("doc_per_100k_monitored", "2021-Q1", "2026-Q3")},
            "gkg_2021_2026Q3_median": {k: med(k, "2021-Q1", "2026-Q3") for k in ["gkg_records", "gkg_food"]
                                       + [f"gkg_{n}" for n in NAMES.values()]},
            "corpus_2021_2026Q3_median": {k: med(k, "2021-Q1", "2026-Q3") for k in ("corpus_collected", "corpus_admitted")},
            "corpus_quarters_before_2021": int(T.loc[:"2020-Q4", "corpus_collected"].fillna(0).sum())}
    (HERE / "out" / "counts_summary.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(T.round(2).to_string())
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
