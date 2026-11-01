"""Y14 data acquisition from PSA OpenSTAT (PXWeb API): food-insecurity outcomes and driver series not already in the
project. Raw responses are saved as served in data_acquired/ with data_acquired/manifest.json (API path, title, exact
query, UTC time, SHA-256). Reuses the read-only client from y12 (runner/psa.py).

    python -B acquire.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent / "data_acquired"
sys.path.insert(0, str(HERE.parents[1] / "y12_domestic_rice_supply" / "runner"))
import psa  # noqa: E402

GEO = ["PHILIPPINES", "IV-A", "CALABARZON", "Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def codes(meta, var, keep):
    for v in meta["variables"]:
        if v["code"] == var:
            return [c for c, x in zip(v["values"], v["valueTexts"]) if keep(x)]
    raise KeyError(var)


def allv(meta, var):
    return codes(meta, var, lambda x: True)


def fetch(name, path, sel):
    meta = psa.get(path)
    q = {"query": [{"code": k, "selection": {"filter": "item", "values": v}} for k, v in sel.items()],
         "response": {"format": "csv"}}
    b = psa.post(path, q)
    (ACQ / f"{name}.csv").write_bytes(b)
    return {"file": f"{name}.csv", "apiPath": psa.API + path, "title": meta.get("title"), "query": q,
            "fetchedUtc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def main():
    ACQ.mkdir(exist_ok=True)
    geo = lambda x: any(g.lower() in x.lower() for g in GEO)  # noqa: E731
    out = []
    # outcomes
    p = "3I/G02/0023I3B2121.px"
    m = psa.get(p)
    out.append(fetch("fies_sdg212_region", p, {v["code"]: allv(m, v["code"]) for v in m["variables"]}))
    p = "3D/0033C3DP030.px"
    m = psa.get(p)
    out.append(fetch("subsistence_families_2006_2015", p, {"Region/Province": codes(m, "Region/Province", geo),
                                                           "Item": allv(m, "Item"), "Year": allv(m, "Year")}))
    p = "1F/FY/0051F3DF030.px"
    m = psa.get(p)
    vv = m["variables"]
    out.append(fetch("subsistence_families_2018_2023", p, {vv[0]["code"]: codes(m, vv[0]["code"], geo),
                                                           vv[1]["code"]: allv(m, vv[1]["code"]), vv[2]["code"]: allv(m, vv[2]["code"])}))
    # drivers: fisheries volume by subsector (quarterly), palay and corn production (quarterly)
    p = "2E/FS/0132E4GVFP1.px"
    m = psa.get(p)
    out.append(fetch("fisheries_volume_subsector", p, {v["code"]: (codes(m, v["code"], geo) if "eo" in v["code"].lower()
                                                                    else allv(m, v["code"])) for v in m["variables"]}))
    p = "2E/CS/0012E4EVCP0.px"
    m = psa.get(p)
    out.append(fetch("palay_corn_production", p, {"Ecosystem/Croptype": codes(m, "Ecosystem/Croptype", lambda x: x in ("Palay", "Corn") or x.endswith("Corn")),
                                                  "Geolocation": codes(m, "Geolocation", geo), "Year": allv(m, "Year"),
                                                  "Period": codes(m, "Period", lambda x: x.startswith("Quarter"))}))
    mf = ACQ / "manifest.json"
    prev = json.loads(mf.read_text()) if mf.exists() else []
    mf.write_text(json.dumps(prev + out, indent=1), encoding="utf-8")
    for o in out:
        print(o["file"], o["bytes"], o["sha256"][:12], o["title"][:90])


if __name__ == "__main__":
    main()
