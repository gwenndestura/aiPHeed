"""
scripts/supplementary/timing_audit.py

Temporal-validity audit for the MODEL-B candidate (Algorithm 3 on the
Section 3.3.2.6 matrix, one quarter ahead). Diagnostic only.

For every walk-forward test quarter it records what a forecast for that
quarter could have used, and evaluates three timing rules side by side:

  T0  as in the 2026-10-08 diagnostic: SWS of quarter t (forward-filled),
      government series of quarter t, poverty as published      [INVALID: SWS]
  T1  SWS = latest round PUBLISHED before the forecast quarter starts
      (release dates from the SWS article timestamps); government series of
      quarter t, i.e. a forecast issued once quarter t's data is out
  T2  strict Rule 3: as T1, and government series from quarter t-1, the
      latest quarter whose monthly/quarterly releases are complete before the
      forecast quarter starts. News features (FSSI, triggers) stay at t.

Writes data/supplementary/timing_audit.csv and timing_audit.json.

    python -m scripts.supplementary.timing_audit
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import scripts.supplementary.reliability_diagnostics as R

OUTDIR = Path("data/supplementary")

# SWS rounds whose article URL carries no timestamp: dates read from the
# release pages. The fourth-quarter-2024 page shows "Jan 14, 2024" for a
# December 2024 survey; 14 January 2025 is used.
MANUAL_RELEASES = {
    "2024-Q3": "2025-01-14", "2024-Q4": "2025-01-14",
    "2025-Q1": "2025-03-29", "2025-Q4": "2026-05-12",
}
POVERTY_RELEASES = [("2018 survey", None, "2022-Q3"),
                    ("2021 survey (released 2022-08-15)", "2022-Q4", "2024-Q3"),
                    ("2023 survey (released 2024-08)", "2024-Q4", None)]


def qstart(q: str) -> pd.Timestamp:
    y, p = q.split("-Q")
    return pd.Timestamp(int(y), 3 * (int(p) - 1) + 1, 1)


def nxt(q: str) -> str:
    y, p = map(int, q.split("-Q"))
    return f"{y + (p == 4)}-Q{1 if p == 4 else p + 1}"


def prev(q: str) -> str:
    y, p = map(int, q.split("-Q"))
    return f"{y - (p == 1)}-Q{4 if p == 1 else p - 1}"


def sws_release_dates() -> dict[str, pd.Timestamp]:
    rel: dict[str, list] = {}
    for x in json.loads(Path("docs/provenance/sws_hunger_sources.json").read_text()):
        m = re.search(r"ART-(\d{8})", x["source_url"])
        if m:
            rel.setdefault(x["quarter"], []).append(pd.Timestamp(m.group(1)))
    for q, d in MANUAL_RELEASES.items():
        rel[q] = [pd.Timestamp(d)]
    return {q: min(v) for q, v in rel.items()}   # value on file = first round


def poverty_vintage(q: str) -> str:
    for name, start, end in POVERTY_RELEASES:
        if (start is None or q >= start) and (end is None or q <= end):
            return name
    return "?"


def main() -> dict:
    f, labels, cand = R.load()
    rel = sws_release_dates()
    sws = pd.read_parquet("data/processed/sws_hunger.parquet").groupby("quarter")["pct_total_hunger"].first()

    avail = {}
    for q in sorted(f["quarter"].unique(), key=R.qi):
        cutoff = qstart(nxt(q))
        known = [(rel[s], s) for s in sws.index if s in rel and rel[s] < cutoff]
        avail[q] = max(known) if known else (None, None)

    t1 = f.copy()
    t1["sws_hunger"] = t1["quarter"].map(lambda q: sws.get(avail[q][1], 0.0) if avail[q][1] else 0.0)
    nlp = [c for c in cand if c.startswith(("FSSI", "trigger_"))]
    gov = [c for c in cand + ["cpi_dev"] if c not in nlp and c != "poverty_incidence"]
    t2 = t1.sort_values(["province_code", "t"]).copy()
    t2[gov] = t2.groupby("province_code")[gov].shift(1).fillna(0.0)

    cols = cand + ["cpi_dev", "sws_hunger"]
    results = {}
    for name, frame in (("T0 diagnostic (SWS of t)", f), ("T1 SWS as published, gov data of t", t1),
                        ("T2 strict Rule 3, gov data of t-1", t2)):
        rows = {}
        for mt in (6, 7, 8, 9, 10):
            R.MIN_TRAIN = mt
            r = R.walk(R.pairs(frame, labels, 1), cols, None)
            m = R.metrics(r["y"], (r["p"] >= 0.5).astype(int), r["p"].values, r["target_quarter"].values)
            if mt == 8:
                rows["metrics"] = {k: m[k] for k in ("accuracy_mean_fold", "precision_weighted",
                                                     "recall_weighted", "f1_weighted", "roc_auc",
                                                     "accuracy_by_year", "accuracy_by_fold")}
            rows[f"min_train={mt}"] = m["accuracy_mean_fold"]
        R.MIN_TRAIN = 8
        results[name] = rows

    # Per-quarter audit (T1 and T2 rules)
    d = R.pairs(f, labels, 1)
    tq = sorted(d["target_quarter"].unique(), key=R.qi)
    audit = []
    for i in range(R.MIN_TRAIN, len(tq)):
        target = tq[i]
        feat_q = prev(target)
        used = avail[feat_q]
        audit.append({
            "forecast_quarter": target,
            "lead_time_quarters": 1,
            "forecast_made_before": str(qstart(target).date()),
            "training_targets": f"{tq[0]} .. {tq[i - 1]}",
            "news_features_from": feat_q,
            "sws_value_from_quarter": used[1],
            "sws_published": str(used[0].date()) if used[0] is not None else None,
            "sws_of_quarter_t_published": str(rel[feat_q].date()) if feat_q in rel else "no SWS round",
            "sws_of_t_available_in_time": bool(feat_q in rel and rel[feat_q] < qstart(target)),
            "poverty_estimate": poverty_vintage(feat_q),
            "gov_series_T1": feat_q,
            "gov_series_T2_strict": prev(feat_q),
        })
    OUTDIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit).to_csv(OUTDIR / "timing_audit.csv", index=False)
    out = {"results": results, "audit": audit}
    (OUTDIR / "timing_audit.json").write_text(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    o = main()
    for k, v in o["results"].items():
        print(k, v["metrics"]["accuracy_mean_fold"], v["metrics"]["accuracy_by_year"],
              {x: v[x] for x in v if x.startswith("min_train")})
    print(pd.DataFrame(o["audit"])[["forecast_quarter", "sws_value_from_quarter", "sws_published",
                                    "sws_of_quarter_t_published", "sws_of_t_available_in_time",
                                    "poverty_estimate"]].to_string())
