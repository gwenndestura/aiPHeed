"""Verify the E49 preview (8001) against E49-C2, and that the current system (8000) still serves E36. Read only."""
import json
import urllib.request
from pathlib import Path

E49 = Path(__file__).resolve().parents[1]
c2 = json.loads((E49 / "E49_results.json").read_text(encoding="utf-8"))["index_history"]["C2"]
QS = ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]
ORDER = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]


def g(port, path):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1{path}"))


print("=== preview 8001 (AIPHEED_RECORD=e49) vs E49 C2")
ok = True
for q in QS:
    api = g(8001, f"/forecast?scope=region&id=calabarzon&quarter={q}")["riskScore"]
    want = c2[q]["CALABARZON"]
    ok &= abs(api - want) < 1e-3
    print(f"  {q}: API {api:.4f}  E49-C2 {want:.4f}  {'MATCH' if abs(api - want) < 1e-3 else 'DIFF'}")
print("  2026-Q4 provinces:")
for p in g(8001, "/provinces?quarter=2026-Q4")["data"]:
    want = c2["2026-Q4"][p["name"]]
    ok &= abs(p["riskScore"] - want) < 1e-3
    print(f"    {p['name']:9s} API {p['riskScore']:.4f}  E49-C2 {want:.4f}  level {p['riskLevel']}")
for scope, ident in (("region", "calabarzon"), ("province", "laguna")):
    e = g(8001, f"/explainability?scope={scope}&id={ident}&quarter=2026-Q4")
    print(f"  drivers {ident}: {({t['key']: t['pct'] for t in e['triggers']})}  keys {list(e['triggers'][0])}")
cfg = g(8001, "/config")
print("  default quarter", g(8001, "/quarters")["current"], "| all preview values match E49-C2:", ok)

print("=== current 8000 (default, E36)")
print("  CALABARZON 2026-Q4", g(8000, "/forecast?scope=region&id=calabarzon&quarter=2026-Q4")["riskScore"],
      {p["name"]: p["riskScore"] for p in g(8000, "/provinces?quarter=2026-Q4")["data"]})
e = g(8000, "/explainability?scope=region&id=calabarzon&quarter=2026-Q4")
print("  drivers CALABARZON", {t["key"]: t["pct"] for t in e["triggers"]})
