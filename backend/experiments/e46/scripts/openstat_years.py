"""E46 (read only): year range, commodities and province coverage of the candidate CPI / rice-price tables."""
import requests

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E46 feasibility)"}
TABLES = ["DB/2M/PI/CPI/2018/0012M4ACP15.px", "DB/2M/PI/CPI/2018/0012M4ACP09.px", "DB/2M/PI/CPI/2018/0012M4ACP23.px",
          "DB/2M/PI/CPI/2018/0012M4ACP10.px", "DB/2M/NRP/0042M4ARN01.px", "DB/2M/RP/0042M4ARP01.px",
          "DB/2M/2018/0042M4ARA01.px"]
for t in TABLES:
    try:
        m = requests.get(f"{API}/{t}", headers=H, timeout=90).json()
    except Exception as e:  # noqa: BLE001
        print(t, "ERROR", type(e).__name__)
        continue
    print(f"\n== {t}: {m.get('title')}")
    for v in m["variables"]:
        vals = v["valueTexts"]
        if v["code"].lower().startswith(("year",)):
            print(f"  {v['code']}: {vals[0]} .. {vals[-1]} ({len(vals)})")
        elif "commodity" in v["code"].lower():
            rice = [x for x in vals if "rice" in x.lower() or "food" in x.lower()][:6]
            print(f"  {v['code']}: {len(vals)} items; rice/food: {rice}")
        elif "geo" in v["code"].lower() or "province" in v["code"].lower():
            print(f"  {v['code']}: {len(vals)} areas; CALABARZON: "
                  f"{[x.strip('.') for x in vals if any(p in x for p in ('Batangas', 'Cavite', 'Laguna', 'Quezon', 'Rizal', 'IV-A'))][:7]}")
