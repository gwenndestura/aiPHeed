"""Read-only: search OpenStat for regional unemployment tables; list the fisheries folder with update dates."""
import requests

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E43 data refresh)"}


def get(path, **params):
    r = requests.get(f"{API}/{path}", headers=H, params=params, timeout=90)
    r.raise_for_status()
    return r.json()


for q in ("unemployment region", "unemployment rate region", "labor force region", "CALABARZON unemployment"):
    try:
        res = get("DB", query=q)
        print(f"\n== search '{q}': {len(res)} hits")
        for it in res[:25]:
            print(f"  {it.get('path', '')}/{it.get('id', '')}  {it.get('title', '')[:120]}  updated={it.get('updated')}")
    except Exception as e:  # noqa: BLE001
        print(f"search '{q}' failed: {type(e).__name__} {e}")

print("\n== top-level DB")
for it in get("DB"):
    print(f"  {it.get('id'):6s} {it.get('text')}")
print("\n== DB/2E/FS (fisheries)")
for it in get("DB/2E/FS"):
    print(f"  {it.get('id'):20s} {it.get('text')[:100]}  updated={it.get('updated')}")
