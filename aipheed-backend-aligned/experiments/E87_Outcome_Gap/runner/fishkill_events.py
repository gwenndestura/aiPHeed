"""E87 Fish Kill driver: a dated, de-duplicated event dataset from the collected news (run from backend/).

An EVENT is a semantic cluster (app.news.events) of fish_kill-trigger articles within 7 days. Its date is the
publication time of its first article (the date the event became public, which bounds when a forecast could know it).
Each event records: first and last report, number of articles and outlets, province (geocoder) and water body (named in
the text), whether the text reports an actual kill or loss ("reported_kill") versus a ban, advisory or warning
("advisory"), and verification = "news-reported" (none are checked against BFAR records here).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, ".")
import pandas as pd  # noqa: E402

from app.news import events as EV  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data_derived" / "fishkill_events.csv"
WATER = re.compile(r"(Taal Lake|Taal|Laguna de Bay|Laguna Lake|Sampaloc Lake|Seven Lakes|Manila Bay|Batangas Bay|"
                   r"Balayan Bay|Verde Island|Tayabas Bay|Lamon Bay|Lake Yambo|Lake Pandin|Pasig River|Cavite coast|"
                   r"Bacoor|Rosario|Ternate|Polillo)", re.I)
KILL = re.compile(r"fish ?kill|(tilapia|bangus|milkfish|fish)\w* (die|died|deaths|dead)|fish deaths|kg of fish|"
                  r"tons? of (tilapia|fish|bangus)|losses", re.I)
NEGATION = re.compile(r"\bno (fish ?kill|fish deaths)|\bnot (a )?fish ?kill|ruled out", re.I)
ADVISORY = re.compile(r"\bban\b|advisory|warning|closed fishing|red tide|shellfish|no-?catch|oil spill|safe to eat", re.I)


def build() -> pd.DataFrame:
    rows = []
    arts = {a["article_key"]: a for a in EV.articles(True)}
    for e in EV.events(True):
        if e["trigger"] != "fish_kill":
            continue
        ms = [arts[k] for k in e["keys"] if k in arts]
        text = " ".join(m["title"] + " " + EV.lead_text(m["article_key"])[:300] for m in ms)
        wb = sorted({w.group(0).title() for w in WATER.finditer(text)})
        negated = bool(NEGATION.search(text))
        in_region = e["province_code"] is not None or bool(wb)
        kind = ("reported_kill" if KILL.search(text) and not negated and in_region else
                "advisory" if ADVISORY.search(text) else "other_or_outside_region")
        rows.append({"event_id": e["keys"][0][:12], "first_report_ph": e["start"].isoformat(), "quarter": e["quarter"],
                     "last_report_ph": max(m["published_ph"] for m in ms) if ms else e["start"].isoformat(),
                     "n_articles": e["n_articles"], "n_outlets": e["n_outlets"], "province_code": e["province_code"], "in_calabarzon": in_region,
                     "water_body": "; ".join(wb), "kind": kind, "polarity": e["polarity"], "severe_words": e["severe"],
                     "verification": "news-reported (not checked against BFAR records)",
                     "headline": ms[0]["title"][:160] if ms else "", "has_lead_text": any(m["has_lead"] for m in ms)})
    d = pd.DataFrame(rows).sort_values("first_report_ph")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_csv(OUT, index=False)
    return d


if __name__ == "__main__":
    d = build()
    print(len(d), "events")
    print(d["kind"].value_counts().to_dict())
    print(d.groupby("quarter").size().to_dict())
    print(d["province_code"].value_counts(dropna=False).to_dict())
    print(d[d["kind"] == "reported_kill"][["first_report_ph", "province_code", "water_body", "n_outlets", "headline"]]
          .head(40).to_string())
