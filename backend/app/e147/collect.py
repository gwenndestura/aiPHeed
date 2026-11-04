"""
Collect the public provincial food-insecurity estimates shown on DOST-FNRI's Hunger and Malnutrition Heat Map, one area every
2 seconds, using the same request the site's Data Visualization page makes when a province is selected.

    python -m app.e147.collect       -> data/e147/raw/heatmap_provincial.jsonl, collect_log.txt

Blind rule: this module writes values to disk and prints coverage counts only. It never prints a percentage, so the 2021 round
stays unread until the E147 protocol is locked.
"""
from __future__ import annotations

import collections
import json
import time
import urllib.parse
import urllib.request

from app.e147 import RAW

BASE = "https://heatmap.fnri.dost.gov.ph/api/"
UA = "Mozilla/5.0 (aiPHeed thesis research; food security forecasting; DA Region IV-A)"
DELAY = 2.0


def _get(path: str):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    names = [x["name"] for x in _get("foodinsecurity_province_list/")]
    time.sleep(DELAY)
    cov, fails = collections.Counter(), []
    with open(RAW / "heatmap_provincial.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for n in names:
            try:
                rows = _get("foodinsecurity_provincial_barchart/?province_name=" + urllib.parse.quote(n))
            except Exception as e:                       # noqa: BLE001  a failed area is logged, not hidden
                fails.append(f"{n}: {type(e).__name__}")
                rows = []
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                cov[(r["year_record"], r["actual_year"], r["fs_survey_category"])] += 1
            time.sleep(DELAY)
    (RAW / "collect_log.txt").write_text(json.dumps({"areas": len(names), "failed": fails}, indent=1), newline="\n")
    print("areas", len(names), "failed", len(fails))
    for k in sorted(cov):
        print(k, cov[k])


if __name__ == "__main__":
    main()
