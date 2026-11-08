"""
Score the v2 prospective seal against SWS rounds published since (docs/aipheed/v2/PREREGISTRATION.md sections 6-7).

- Verifies the seal hash first; never edits the seal.
- A target is scored only when it has a published round and its quarter ended more than 120 days before today
  (so every round of the quarter is in); everything else stays AWAITING_GROUND_TRUTH.
- Applies the frozen tolerance and, per lead, the decision table (NOT_YET_TESTABLE until 10 unseen target quarters
  and 40 rows).
- Appends one line per run to docs/aipheed/v2/sealed/ACCESS_LOG.md.

    python -I backend/scripts/v2_score_sealed.py [YYYY-MM-DD today]
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from app.forecasting import sws as T  # noqa: E402
from app.forecasting.v2 import verdict as VD  # noqa: E402

SEALED = REPO / "docs" / "aipheed" / "v2" / "sealed"
OUT = REPO / "docs" / "aipheed" / "v2" / "results"


def main(today: date) -> dict:
    seal = SEALED / "V2_PROSPECTIVE_SEAL.csv"
    stored = (SEALED / "V2_SEAL_SHA256.txt").read_text().split()[0]
    actual = hashlib.sha256(seal.read_bytes()).hexdigest()
    if actual != stored:
        raise SystemExit("seal hash mismatch: the sealed forecasts were changed; scoring refused")
    d = pd.read_csv(seal)
    full = T.quarter_table(T.load_rounds())
    ended = lambda q: pd.Period(q.replace("-", ""), freq="Q").end_time.date() + timedelta(days=120) < today  # noqa: E731
    sc = d.merge(full[["area", "quarter", "y", "se", "tol"]].rename(columns={"quarter": "target"}), on=["area", "target"], how="left")
    sc["scorable"] = sc.y.notna() & sc.target.map(ended)
    sc["within"] = (sc.f - sc.y).abs() <= sc.tol
    res = {"today": today.isoformat(), "seal_sha256": actual, "rows": int(len(d)),
           "scorable_rows": int(sc.scorable.sum()), "by_lead": {}}
    for k, g in sc[sc.scorable & (sc.model == "V2")].groupby("lead"):
        res["by_lead"][int(k)] = {"rows": int(len(g)), "target_quarters": int(g.target.nunique()),
                                  "within": float(g.within.mean())}
    for k in (1, 2, 3, 4):
        r = res["by_lead"].get(k, {"rows": 0, "target_quarters": 0})
        r["label"] = VD.label(False, r["target_quarters"], r["rows"], future=True) if r["rows"] < 40 else "SEE_FULL_N1_N7_RUN"
        res["by_lead"][k] = r
    sc.to_csv(OUT / "v2_future_scores.csv", index=False)
    (OUT / "v2_future_verdict.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8", newline="\n")
    with open(SEALED / "ACCESS_LOG.md", "a", encoding="utf-8", newline="\n") as f:
        f.write(f"| {datetime.now().isoformat(timespec='seconds')} | today={today} | seal {actual[:12]} | "
                f"{res['scorable_rows']} of {res['rows']} rows scorable |\n")
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today())
