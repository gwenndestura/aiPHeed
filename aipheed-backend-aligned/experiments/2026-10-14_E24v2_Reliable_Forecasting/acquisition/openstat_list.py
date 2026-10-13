"""List OpenSTAT folders/tables (metadata only; no data values)."""
import json, sys, time, requests
BASE = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
S = requests.Session(); S.headers["User-Agent"] = "aiPHeed-E24v2-research (thesis; contact via repo owner)"
for path in sys.argv[1:]:
    r = S.get(f"{BASE}/{path}", timeout=60)
    print("==", path, r.status_code)
    if r.ok:
        try:
            js = r.json()
        except Exception:
            print(r.text[:300]); continue
        if isinstance(js, list):
            for it in js:
                print("  ", it.get("type"), it.get("id"), "|", it.get("text"), "|", it.get("updated", ""))
        else:
            print("  title:", js.get("title"))
            for v in js.get("variables", []):
                vals = v.get("valueTexts", [])
                print("   var", v.get("code"), "n=", len(vals), "first:", vals[:6], "last:", vals[-4:])
    time.sleep(0.6)
