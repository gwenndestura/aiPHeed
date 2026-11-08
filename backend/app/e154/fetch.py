"""
E154 regional income data from PSA OpenSTAT: per capita household consumption and per capita GRDP, by region, constant prices. Public; no outcome read.

    python -m app.e154.fetch -> data/e154/raw/regional_income.csv
"""
from __future__ import annotations

import json
import urllib.request as U

import pandas as pd

from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "e154" / "raw"
O = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"
H = {"User-Agent": "Mozilla/5.0 research-data", "Content-Type": "application/json"}
TABLES = {"hfce_pc": "2B/EA/BR/PHF_OS/0672B5BEPC1.px", "grdp_pc": "2B/GP/RG/PCI_OS/0772B5BPCP1.px"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, t in TABLES.items():
        m = json.load(U.urlopen(U.Request(O + t, headers=H), timeout=60))
        print(name, m["title"][:70], [(v["code"], len(v["values"]), v["valueTexts"][:2]) for v in m["variables"]])
        q = [{"code": v["code"], "selection": {"filter": "item", "values": v["values"]}} for v in m["variables"]]
        d = json.load(U.urlopen(U.Request(O + t, data=json.dumps({"query": q, "response": {"format": "json"}}).encode(), headers=H), timeout=120))
        codes = [c["code"] for c in d["columns"] if c.get("type") != "c"]
        mp = {v["code"]: dict(zip(v["values"], v["valueTexts"])) for v in m["variables"]}
        for r in d["data"]:
            lab = {c: mp[c][k] for c, k in zip(codes, r["key"])}
            try:
                val = float(r["values"][0])
            except ValueError:
                continue
            rows.append({"table": name, **{c.lower(): lab[c] for c in codes}, "value": val})
    t = pd.DataFrame(rows)
    t.to_csv(RAW / "regional_income_long.csv", index=False, lineterminator="\n")
    print(t.shape, t.columns.tolist())
    print(t.head(3).to_string())
    for c in t.columns:
        if c not in ("value",):
            print(c, t[c].nunique(), sorted(map(str, t[c].unique()))[:22])


if __name__ == "__main__":
    main()
