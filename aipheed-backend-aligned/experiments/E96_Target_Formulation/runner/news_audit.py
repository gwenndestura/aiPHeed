"""E96 news-pipeline audit (descriptive, origin-time). Run from backend/. Writes news_audit.json and news_audit_quarters.csv.

Per quarter 2021-Q1..2026-Q3: collected articles, admitted (relevant, de-syndicated) articles, share with lead text,
share attributed to a CALABARZON province, de-duplicated events (by driver and polarity), relief/response events, and
how many admitted articles of quarter t were published before the forecast origin O(t) (always all, by construction
of the quarter) versus during the following quarter."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path.cwd()))
import pandas as pd  # noqa: E402

from app.news import events as EV  # noqa: E402
from app.news import pipeline_v3 as P  # noqa: E402

if __name__ == "__main__":
    vol = EV.volume()
    arts = EV.articles(True)
    evs = EV.events(True)
    rows = []
    for q in sorted(set(vol) | {a["quarter"] for a in arts}):
        if q < "2021-Q1":
            continue
        A = [a for a in arts if a["quarter"] == q]
        V = [e for e in evs if e["quarter"] == q]
        r = {"quarter": q, "collected": vol.get(q, 0), "admitted": len(A),
             "with_lead": sum(a["has_lead"] for a in A), "province_attributed": sum(a["province_code"] is not None for a in A),
             "events": len(V), "events_province": sum(e["province_code"] is not None for e in V),
             "relief_response_events": sum(e["polarity"] == "RESPONSE" for e in V),
             "severe_events": sum(e["severe"] for e in V)}
        for g in EV.DRIVERS:
            r[f"adv_{g}"] = sum(e["driver"] == g and e["polarity"] == "ADVERSE" for e in V)
        r["multi_article_events"] = sum(e["n_articles"] > 1 for e in V)
        rows.append(r)
    D = pd.DataFrame(rows)
    out = HERE.parent / "news_audit_quarters.csv"
    D.to_csv(out, index=False)
    tot = D.drop(columns="quarter").sum()
    summ = {"quarters": len(D), "totals": {k: int(v) for k, v in tot.items()},
            "quarters_with_zero_admitted": int((D["admitted"] == 0).sum()),
            "median_admitted_per_quarter": float(D["admitted"].median()),
            "median_events_per_quarter": float(D["events"].median()),
            "province_attribution_share": float(tot["province_attributed"] / max(tot["admitted"], 1)),
            "lead_share": float(tot["with_lead"] / max(tot["admitted"], 1)),
            "dedup_ratio_articles_per_event": float(tot["admitted"] / max(tot["events"], 1)),
            "triggers": dict(Counter(a["trigger"] for a in arts).most_common())}
    (HERE.parent / "news_audit.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k != "triggers"}, indent=1))
    print(D.to_string(index=False))
