"""FOOD_INSECURITY_SYSTEM PLAN section 8.2 (EXPLORATORY, report only): the stricter news-flag rule on the served rows.

    python strict_flag.py    # -> ../out/strict_flag.csv, ../out/strict_flag.json

Same E85 inputs, timing, families and window as the served rule (export_fi.province_news); only the three thresholds
differ (>= 2.0 sd, >= 10 points, >= 30 province articles). Not served, not staged, nothing in backend/ changes.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_fi as X  # noqa: E402

OUT = X.HERE / "out"


def main():
    plan_sha = X.check_plan()
    R = pd.read_csv(X.OUT / "rows.csv", dtype={"province_code": str})
    G = pd.read_csv(X.E85, dtype={"province_code": str})
    rows = []
    for r in R.itertuples():
        t = X.H.qi(r.origin)
        s = X.province_news(G, r.province_code, t, X.STRICT_RULE)
        rows.append({"province": r.province, "quarter": r.quarter, "origin": r.origin, "issue_date": r.issue_date,
                     "served_flag": bool(r.news_flag), "served_families": r.news_flag_family if r.news_flag else "",
                     "strict_flag": bool(s["news_flag"]), "strict_families": s["news_flag_family"],
                     "province_articles": s["province_news_n"]})
    D = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    D.to_csv(OUT / "strict_flag.csv", index=False)
    issued = D[D["issue_date"] >= "2026-10-01"]
    fam = D.loc[D["strict_flag"], "strict_families"].str.split(";").explode().value_counts().to_dict()
    res = {"plan_sha256": plan_sha, "rule": X.STRICT_RULE, "served_rule": X.SERVED_RULE, "rows": len(D),
           "strict": {"rows_flagged": int(D["strict_flag"].sum()),
                      "by_province": D[D["strict_flag"]].groupby("province").size().to_dict(),
                      "quarters": sorted(D.loc[D["strict_flag"], "quarter"].unique().tolist()),
                      "families": fam,
                      "issued": issued[issued["strict_flag"]][["province", "quarter", "strict_families"]]
                      .to_dict("records")},
           "served": {"rows_flagged": int(D["served_flag"].sum()),
                      "issued": issued[issued["served_flag"]][["province", "quarter"]].to_dict("records")},
           "strict_subset_of_served": bool((~D["strict_flag"] | D["served_flag"]).all()),
           "below_30_articles": int((pd.to_numeric(D["province_articles"], errors="coerce") < 30).sum())}
    (OUT / "strict_flag.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
