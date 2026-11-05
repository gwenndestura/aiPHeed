"""
E152 data fetch: public files only, into data/e152/raw. No outcome is read here.

    python -m app.e152.fetch
"""
from __future__ import annotations

import json
import time
import urllib.request as U

from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "e152" / "raw"
H = {"User-Agent": "Mozilla/5.0 research-data", "Content-Type": "application/json"}
OPEN = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"


def get(u, t=120):
    return json.load(U.urlopen(U.Request(u, headers=H), timeout=t))


def hdx(ds, pick):
    r = get("https://data.humdata.org/api/3/action/package_show?id=" + ds)["result"]
    for x in r["resources"]:
        if pick in x["name"]:
            p = RAW / x["name"].replace(" ", "_").replace(".csv", "") .__add__(".csv")
            if not p.exists():
                U.urlretrieve(x["url"], p)
            print(p.name, p.stat().st_size, flush=True)


def px(table, name, keep=None):
    """Whole table by province, month; commodities filtered by the substrings in keep."""
    p = RAW / f"{name}.json"
    if p.exists():
        print(p.name, "exists")
        return
    m = get(OPEN + table)
    q = []
    for v in m["variables"]:
        vals = v["values"]
        if keep and v["code"].lower().startswith("comm"):
            vals = [a for a, b in zip(v["values"], v["valueTexts"]) if any(k in b.lower() for k in keep)]
        q.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
    body = json.dumps({"query": q, "response": {"format": "json-stat2"}}).encode()
    r = U.urlopen(U.Request(OPEN + table, data=body, headers=H), timeout=280).read()
    p.write_bytes(r)
    print(p.name, len(r), flush=True)
    time.sleep(1)


def tree(path="", depth=0, found=None):
    """Lists tables whose title mentions labour, income or regional output."""
    found = [] if found is None else found
    if depth > 3:
        return found
    try:
        r = get(OPEN + path)
    except Exception:
        return found
    for x in r:
        if x.get("type") == "l":
            tree(path + x["id"] + "/", depth + 1, found)
        elif any(k in x.get("text", "").lower() for k in ("unemploy", "labor force", "employment rate", "family income", "gross regional", "grdp", "underemploy")):
            found.append((path + x["id"], x["text"][:90]))
    return found


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    hdx("phl-rainfall-subnational", "full")
    hdx("phl-ndvi-subnational", "full")
    hdx("wfp-food-prices-for-philippines", "Food Prices")
    hdx("wfp-food-prices-for-philippines", "Markets")
    ls = get(OPEN + "2M/NFG")
    print([(x["id"], x["text"][:40]) for x in ls])
    for x in ls:
        if "cereal" in x["text"].lower():
            px("2M/NFG/" + x["id"], "farmgate_cereals", keep=["palay", "corn"])
        if "fish" in x["text"].lower():
            px("2M/NFG/" + x["id"], "farmgate_fish", keep=["bangus", "galunggong", "tilapia"])
    ls = get(OPEN + "2M/NWSNEW")
    print([(x["id"], x["text"][:40]) for x in ls])
    for x in ls:
        if "cereal" in x["text"].lower():
            px("2M/NWSNEW/" + x["id"], "wholesale_cereals", keep=["rice"])
    f = tree()
    (RAW / "openstat_labour_tables.json").write_text(json.dumps(f, indent=0), newline="\n")
    print(len(f), json.dumps(f[:45]))


if __name__ == "__main__":
    main()
