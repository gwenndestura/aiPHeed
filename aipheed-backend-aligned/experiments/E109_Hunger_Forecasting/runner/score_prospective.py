"""Score the sealed E109 forecasts against SWS outcomes once they are published (PROTOCOL.md section 9).

    python score_prospective.py            # writes ../out/prospective_scores.json; never touches the sealed file

A target quarter is scored only when its primary SWS rounds appear in data/outcome_rounds.csv (added from the SWS
release, with its publication date). A quarter that has ended but whose release is not yet published stays 'pending'.
"""
from __future__ import annotations

import json
from datetime import date

import e109_lib as H

E, np, pd = H.E, H.np, H.pd


def main() -> None:
    f = H.OUT / "sealed_prospective.csv"
    want = (H.OUT / "sealed_prospective.csv.sha256").read_text().strip()
    assert H.sha256(f) == want, "sealed forecast file changed: refusing to score"
    s = pd.read_csv(f)
    today = date.today().isoformat()
    rows = []
    for r in s.itertuples():
        q = E.qi(r.target_quarter)
        y = H.outcome(q)
        posted = [p for p in H.rule_rounds("primary").query("q == @q")["published"].str[:10] if p <= today]
        if y is None or not posted:
            rows.append({"method": r.method, "lead": r.lead, "target_quarter": r.target_quarter, "status": "pending"})
            continue
        rows.append({"method": r.method, "lead": r.lead, "target_quarter": r.target_quarter, "status": "scored",
                     "observed": y, "forecast": r.forecast_pct, "abs_error": abs(r.forecast_pct - y),
                     "inside_pi80": bool(r.pi80_low <= y <= r.pi80_high), "outcome_published": max(posted)})
    out = {"sealed_sha256": want, "scored_on": today, "rows": rows,
           "n_scored": sum(x["status"] == "scored" for x in rows), "n_pending": sum(x["status"] == "pending" for x in rows)}
    H.write_json(H.OUT / "prospective_scores.json", out)
    print(f"scored {out['n_scored']}, pending {out['n_pending']}")


if __name__ == "__main__":
    main()
