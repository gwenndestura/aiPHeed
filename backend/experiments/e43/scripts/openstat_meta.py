"""Read-only: metadata of candidate regional-unemployment tables, and the fisheries folder listing."""
import requests

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E43 data refresh)"}
CANDIDATES = ["DB/3K/E2/0193K3E2020.px",
              ]

for t in CANDIDATES:
    try:
        r = requests.get(f"{API}/{t}", headers=H, timeout=90)
        r.raise_for_status()
        m = r.json()
        print(f"\n== {t}: {m.get('title')}")
        for v in m["variables"]:
            vals = v["valueTexts"]
            reg = [x for x in vals if "IV-A" in x or "CALABARZON" in x.upper()]
            print(f"  {v['code']:22s} n={len(vals):4d} first={vals[:2]} last={vals[-3:]}" + (f"  Region IV-A: {reg}" if reg else ""))
    except Exception as e:  # noqa: BLE001
        print(f"\n== {t}: {type(e).__name__} {e}")

for folder in ("DB/3K", ):
    try:
        r = requests.get(f"{API}/{folder}", headers=H, timeout=90)
        r.raise_for_status()
        print(f"\n== {folder}")
        for it in r.json():
            print(f"  {it.get('id'):22s} {it.get('text')[:110]}  updated={it.get('updated')}")
    except Exception as e:  # noqa: BLE001
        print(f"\n== {folder}: {type(e).__name__} {e}")
