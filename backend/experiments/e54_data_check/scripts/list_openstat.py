"""List OpenStat PXWeb search / folder results (id, title, updated). usage: python -I list_openstat.py <json> [filter]"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

data = json.load(open(sys.argv[1], encoding="utf-8"))
flt = [w.lower() for w in sys.argv[2:]]
for x in data:
    title = x.get("title") or x.get("text") or ""
    path = x.get("path", "") + "/" + x.get("id", "")
    if all(w in (title + path).lower() for w in flt):
        print(f"{path:60s} | {title[:150]} | {x.get('updated', '')}")
