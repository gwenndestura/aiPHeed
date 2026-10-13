"""Print value codes/texts of selected variables for OpenSTAT tables (metadata only)."""
import json, sys, requests
BASE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
S = requests.Session(); S.headers["User-Agent"] = "aiPHeed-E24v2-research"
pat = [p.lower() for p in sys.argv[2:]]
r = S.get(f"{BASE}/{sys.argv[1]}", timeout=60); r.raise_for_status()
for v in r.json()["variables"]:
    for code, text in zip(v["values"], v["valueTexts"]):
        if any(p in text.lower() for p in pat) or v["code"] in ("Year", "Period"):
            print(v["code"], "|", code, "|", text)
