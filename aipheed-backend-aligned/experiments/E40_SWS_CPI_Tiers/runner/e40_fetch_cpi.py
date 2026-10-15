"""E40 data acquisition: PSA-published monthly YoY (%) of the provincial CPI, All items (headline) and 01.1 Food, for
the five CALABARZON provinces, January 2021 - September 2026 only (no 2019/2020 year is requested). PSA OpenStat
table 0012M4ACP23 (2018=100), the same table and API E31 used for 2026 food.

    <backend venv python> -B runner/e40_fetch_cpi.py   -> data_acquired/psa_cpi_yoy_headline_food_2021_2026.csv
                                                         (+ the raw query/response and their SHA-256)
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

E40 = Path(__file__).resolve().parents[1]
OUT = E40 / "data_acquired"
URL = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/2M/PI/CPI/2018NEW/0012M4ACP23.px"
GEO = {"33": "PH040500000", "34": "PH040100000", "35": "PH040200000", "36": "PH040300000", "37": "PH040400000"}
COMMODITY = {"0": "all_items", "2": "food"}
YEARS = {"2": 2021, "3": 2022, "4": 2023, "5": 2024, "6": 2025, "7": 2026}       # 2019/2020 never requested


def main():
    query = {"query": [{"code": "Geolocation", "selection": {"filter": "item", "values": list(GEO)}},
                       {"code": "Commodity Description", "selection": {"filter": "item", "values": list(COMMODITY)}},
                       {"code": "Year", "selection": {"filter": "item", "values": list(YEARS)}},
                       {"code": "Period", "selection": {"filter": "item", "values": [str(i) for i in range(12)]}}],
             "response": {"format": "json"}}
    req = urllib.request.Request(URL, data=json.dumps(query).encode(), headers={"Content-Type": "application/json",
                                                                               "User-Agent": "aiPHeed-research/1.0"})
    raw = urllib.request.urlopen(req, timeout=120).read()
    OUT.mkdir(exist_ok=True)
    (OUT / "openstat_0012M4ACP23_query_2021_2026.json").write_bytes(json.dumps(query, indent=1).encode())
    (OUT / "openstat_0012M4ACP23_raw_2021_2026.json").write_bytes(raw)
    d = json.loads(raw.decode("utf-8-sig"))
    rows = ["province_code,commodity,reference_month,yoy_pct"]
    for r in d["data"]:
        g, c, y, m = r["key"]
        v = r["values"][0]
        if v in ("", "..", "...", "-"):
            continue
        assert YEARS[y] >= 2021
        rows.append(f"{GEO[g]},{COMMODITY[c]},{YEARS[y]}-{int(m) + 1:02d},{float(v)}")
    (OUT / "psa_cpi_yoy_headline_food_2021_2026.csv").write_bytes(("\n".join(rows) + "\n").encode())
    meta = {"retrieved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "url": URL,
            "raw_sha256": hashlib.sha256(raw).hexdigest(), "rows": len(rows) - 1}
    (OUT / "acquisition.json").write_bytes(json.dumps(meta, indent=1).encode())
    print(meta)


if __name__ == "__main__":
    main()
