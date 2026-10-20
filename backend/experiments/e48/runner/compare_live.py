"""Side by side for Q4 2026: current system (8000, E36) vs preview (8001, AIPHEED_RECORD=e48). Read only."""
import json
import urllib.request

PORTS = {"current (8000)": 8000, "preview (8001)": 8001}
ORDER = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
SUBJECTS = [("region", "calabarzon", "CALABARZON")] + [("province", s, s.capitalize())
                                                       for s in ("cavite", "laguna", "quezon", "rizal", "batangas")]


def g(port, path):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1{path}"))


for name, port in PORTS.items():
    cfg = g(port, "/quarters")
    print(f"\n=== {name}: default quarter {cfg['current']}")
    print(f"{'':12s} {'index':>7s}  " + "  ".join(f"{k:>14s}" for k in ORDER) + "   trigger keys")
    for scope, ident, label in SUBJECTS:
        f = g(port, f"/forecast?scope={scope}&id={ident}&quarter=2026-Q4")
        e = g(port, f"/explainability?scope={scope}&id={ident}&quarter=2026-Q4")
        pct = {t["key"]: t["pct"] for t in e["triggers"]}
        print(f"{label:12s} {f['riskScore']:7.4f}  " + "  ".join(f"{pct[k]:>13d}%" for k in ORDER)
              + f"   {list(e['triggers'][0].keys()) == ['key', 'label', 'share', 'pct', 'signedContribution', 'direction', 'color', 'newsSignalProportion']}")
    print("top-level keys:", list(e.keys()))
