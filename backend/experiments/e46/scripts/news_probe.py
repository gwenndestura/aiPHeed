"""E46 feasibility (read only; nothing written to the live system): does Google News RSS -- the source of the served
news store -- return CALABARZON food-insecurity titles for 2015-2020 quarters as it does for 2021-2026?

Uses the system's own 16 CALABARZON food queries (gnews_rss_fetcher._CALABARZON_FOOD) with the same quarterly
before:/after: window and locale. Counts per quarter: unique titles, titles naming a CALABARZON province, and titles
the existing trigger classifier tags with any driver. Writes backend/experiments/e46/data/news_probe.csv.
"""
from __future__ import annotations

import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from app.ml.nlp.trigger_classifier import classify_triggers  # noqa: E402

QUERIES = [
    "food prices CALABARZON Philippines", "CALABARZON food insecurity", "CALABARZON food security rice",
    "CALABARZON agriculture harvest", "Batangas food prices rice", "Cavite food prices market",
    "Laguna food prices rice", "Quezon Province food prices", "Rizal food prices market",
    "CALABARZON malnutrition stunting", "CALABARZON NFA rice distribution", "CALABARZON DSWD food relief",
    "CALABARZON 4Ps food beneficiaries", "CALABARZON hunger poverty relief", "Region IVA food Philippines",
    "CALABARZON food assistance calamity",
]
QUARTERS = ["2015-Q2", "2017-Q3", "2019-Q4", "2020-Q2", "2022-Q3", "2024-Q3", "2026-Q2"]
PROV = ("batangas", "cavite", "laguna", "quezon", "rizal", "calabarzon", "region iv-a", "region 4a")
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "en-PH,en;q=0.9"}


def window(q: str) -> tuple[str, str]:
    y, n = int(q[:4]), int(q[-1])
    after = f"{y}-{3 * n - 2:02d}-01"
    ny, nm = (y + 1, 1) if n == 4 else (y, 3 * n + 1)
    return after, f"{ny}-{nm:02d}-01"


def main():
    rows = []
    for q in QUARTERS:
        after, before = window(q)
        titles, statuses = {}, []
        for query in QUERIES:
            url = (f"https://news.google.com/rss/search?q={quote(query)}+before:{before}+after:{after}"
                   f"&hl=en-PH&gl=PH&ceid=PH:en")
            try:
                r = requests.get(url, headers=H, timeout=40)
                statuses.append(r.status_code)
                if r.status_code == 200:
                    for it in ET.fromstring(r.content).iter("item"):
                        t = (it.findtext("title") or "").strip()
                        pub = it.findtext("pubDate") or ""
                        if t:
                            titles[t] = pub
            except Exception as e:  # noqa: BLE001
                statuses.append(type(e).__name__)
            time.sleep(1.5)
        tl = list(titles)
        prov = [t for t in tl if any(p in t.lower() for p in PROV)]
        trig = [t for t in prov if classify_triggers(t)]
        rows.append({"quarter": q, "window": f"{after}..{before}", "queries": len(QUERIES),
                     "http_ok": sum(1 for s in statuses if s == 200), "unique_titles": len(tl),
                     "titles_naming_calabarzon_province": len(prov), "of_which_trigger_tagged": len(trig),
                     "example": prov[0][:110] if prov else ""})
        print(rows[-1])
    out = ROOT / "experiments" / "e46" / "data"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "news_probe.csv", index=False)


if __name__ == "__main__":
    main()
