"""Read-only probe of PSA OpenStat (PXWeb API): the LFS folder listing, the national unemployment table's metadata,
and the fisheries table's metadata (title, last update, variables)."""
import json

import requests

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E43 data refresh)"}


def get(path):
    r = requests.get(f"{API}/{path}", headers=H, timeout=60)
    r.raise_for_status()
    return r.json()


print("== LFS folder DB/1B/LFS")
for it in get("DB/1B/LFS"):
    print(f"  {it.get('type')}  {it.get('id'):20s} {it.get('text')[:110]}  updated={it.get('updated')}")

for table in ("DB/1B/LFS/0021B3FKEI2.px", "DB/2E/FS/0132E4GVFP1.px"):
    m = get(table)
    print(f"\n== {table}: {m.get('title')}")
    for v in m["variables"]:
        vals = v["valueTexts"]
        print(f"  {v['code']:20s} n={len(vals):4d}  first={vals[:3]}  last={vals[-4:]}")
