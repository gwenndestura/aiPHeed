"""Summarise a PXWeb table-metadata JSON: title, variables, value counts, geography values, time range.
usage: python -I px_meta.py <json>"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

m = json.load(open(sys.argv[1], encoding="utf-8"))
print("title:", m.get("title"))
for v in m.get("variables", []):
    vals = v.get("valueTexts", [])
    show = vals if len(vals) <= 12 else vals[:6] + ["..."] + vals[-4:]
    print(f"  {v.get('code')!r:28s} n={len(vals):4d} {show}")
