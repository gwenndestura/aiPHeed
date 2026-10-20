"""Capture the /explainability response shape (keys and value types) and the forecast index from the running API.
usage: python capture_keys.py <before|after>"""
import json
import sys
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000/api/v1"
OUT = Path(__file__).resolve().parent / f"keys_{sys.argv[1]}.json"


def g(path):
    return json.load(urllib.request.urlopen(API + path))


def shape(o):
    if isinstance(o, dict):
        return {k: shape(v) for k, v in o.items()}
    if isinstance(o, list):
        return [shape(o[0])] if o else []
    return type(o).__name__


res = {}
for scope, ident in (("region", "calabarzon"), ("province", "batangas"), ("province", "laguna")):
    e = g(f"/explainability?scope={scope}&id={ident}&quarter=2026-Q4")
    res[f"{scope}:{ident}"] = {"top_level_keys": list(e.keys()), "trigger_keys": list(e["triggers"][0].keys()),
                               "trigger_keys_all_equal": all(list(t.keys()) == list(e["triggers"][0].keys()) for t in e["triggers"]),
                               "shape": shape(e), "pct": {t["key"]: t["pct"] for t in e["triggers"]},
                               "order": [t["key"] for t in e["triggers"]], "note": e.get("note")}
f = g("/forecast?scope=region&id=calabarzon&quarter=2026-Q4")
res["forecast_index"] = {"CALABARZON": f["riskScore"],
                         **{p["name"]: p["riskScore"] for p in g("/provinces?quarter=2026-Q4")["data"]}}
OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
print(json.dumps({k: (v if k == "forecast_index" else {"top": v["top_level_keys"], "trigger": v["trigger_keys"], "pct": v["pct"]})
                  for k, v in res.items()}, indent=1))
