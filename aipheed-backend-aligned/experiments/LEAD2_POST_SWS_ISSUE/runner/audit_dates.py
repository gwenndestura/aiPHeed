"""Step 1 data audit (before the protocol; no forecasting, no outcomes scored): every SWS round 2002-2026 with its
publication date and how that date is known, and the distribution of days from quarter end to the publication of the
LAST round assigned to each quarter. Read-only. Writes out/sws_rounds_audit.csv and out/audit_dates.json.

Sources (same series as every earlier study, via LEAD2_RELIABILITY_RESEARCH/runner/rlib.rounds):
  * BL 2021+ : backend/data/inputs/sws_rounds.csv (published = verified SWS release / news date)
  * all other area-rounds: FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_area_rounds_full.csv (source_type column)
  * pre-2021 spot checks: FINAL_FOOD_INSECURITY_LIGHTGBM/data/long/sws_release_date_evidence.csv

    python -B audit_dates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
OUT = HERE.parent / "out"
LONG = EXP / "FINAL_FOOD_INSECURITY_LIGHTGBM/data/long"


def q_end(q: str) -> pd.Timestamp:
    y, k = int(q[:4]), int(q[-1])
    return pd.Timestamp(year=y, month=3 * k, day=1) + pd.offsets.MonthEnd(0)


def main():
    a = pd.read_csv(LONG / "sws_area_rounds_full.csv")
    a["basis"] = np.where(a["source_type"].str.contains(r"\(rule\)"), "estimated (label month end + 60 days rule)",
                          "verified (SWS release or news report date)")
    rows = [{"quarter": r.quarter, "label": r.fieldwork, "published": r.published, "basis": r.basis, "series": "area file",
             "BL": r.balance_luzon} for r in a.itertuples() if r.quarter >= "2002-Q1" and not (r.quarter >= "2021-Q1")]
    p = pd.read_csv(EXP.parents[1] / "backend/data/inputs/sws_rounds.csv")
    rows += [{"quarter": r.quarter, "label": r.round, "published": r.published, "basis": f"verified ({r.date_type})",
              "series": "production BL (backend/data/inputs/sws_rounds.csv)", "BL": r.H} for r in p.itertuples()]
    d = pd.DataFrame(rows).sort_values(["quarter", "published"]).reset_index(drop=True)
    d["published"] = pd.to_datetime(d["published"])
    d["daysAfterQuarterEnd"] = [(pub - q_end(q)).days for q, pub in zip(d["quarter"], d["published"])]
    last = d.groupby("quarter").agg(lastPublished=("published", "max"), basis=("basis", "first"), rounds=("label", "size")).reset_index()
    last["daysAfterQuarterEnd"] = [(pub - q_end(q)).days for q, pub in zip(last["quarter"], last["lastPublished"])]
    ver = last[last["basis"].str.startswith("verified")]["daysAfterQuarterEnd"].to_numpy()
    est = last[last["basis"].str.startswith("estimated")]["daysAfterQuarterEnd"].to_numpy()
    nr = lambda x, pct: int(np.sort(x)[int(np.ceil(pct / 100 * len(x))) - 1])  # noqa: E731  nearest-rank percentile
    ev = pd.read_csv(LONG / "sws_release_date_evidence.csv")
    res = {"rounds2002_2026": len(d), "quarters": len(last),
           "verifiedQuarters": int(len(ver)), "estimatedQuarters": int(len(est)),
           "verifiedDaysAfterQuarterEnd_lastRound": {"min": int(ver.min()), "p25": nr(ver, 25), "median": nr(ver, 50),
                                                    "p75": nr(ver, 75), "p90": nr(ver, 90), "max": int(ver.max()), "values": sorted(int(x) for x in ver)},
           "estimatedDaysAfterQuarterEnd_lastRound": {"min": int(est.min()), "median": nr(est, 50), "max": int(est.max())},
           "pre2021SpotChecks": ev[["round", "release_or_report_date", "days_after_label_month_end", "verification"]].to_dict("records")}
    OUT.mkdir(exist_ok=True)
    d.to_csv(OUT / "sws_rounds_audit.csv", index=False, lineterminator="\n")
    (OUT / "audit_dates.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "pre2021SpotChecks"}, indent=1))
    print(last[last["basis"].str.startswith("verified")][["quarter", "lastPublished", "rounds", "daysAfterQuarterEnd"]].to_string(index=False))


if __name__ == "__main__":
    main()
