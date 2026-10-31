"""List PSA OpenSTAT folders/tables recursively under given roots (metadata only; no data values)."""
import json, subprocess, sys, time
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
def get(path):
    r = subprocess.run(["curl", "-s", "-m", "90", "-A", UA, f"{PX}/{path}"], capture_output=True)
    return json.loads(r.stdout.decode("utf-8-sig")) if r.stdout.strip() else None
def walk(path, depth=0, out=None):
    out = [] if out is None else out
    items = get(path) or []
    for it in items:
        p = f"{path}/{it['id']}"
        if it.get("type") == "l":
            walk(p, depth + 1, out)
        else:
            out.append({"path": p, "text": it.get("text"), "updated": it.get("updated")})
        time.sleep(0.2)
    return out
if __name__ == "__main__":
    roots = sys.argv[1:] or ["DB"]
    res = []
    for r in roots:
        res += walk(r)
    json.dump(res, open("../out/openstat_tables.json", "w"), indent=1)
    print(len(res))
