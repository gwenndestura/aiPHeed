"""
Longer PSA predictor history for the 2013 round (python -m app.e141.acquire): the same OpenSTAT tables as
app.hfias.acquire, with years from 2006 (poverty rounds) and 2010 (CPI, production), written to data/e141/raw/psa/
under the file names E137's feature builder reads. app.hfias data are not modified.
"""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date

from app.e137.acquire import PX, _get
from app.e141 import RAW
from app.hfias.acquire import TABLES as HT

YEARS = [str(y) for y in range(2010, 2020)]
POV_YEARS = ("2006", "2009", "2012", "2015")
TABLES = {
    "poverty_1991_2015": (HT["poverty_1991_2015"][0], {"Item": lambda t: "Incidence" in t or "Coefficient" in t,
                                                      "Year": lambda t: t in POV_YEARS}),
    "subsistence_1991_2015": (HT["subsistence_1991_2015"][0], {"Item": lambda t: "Incidence" in t or "Coefficient" in t,
                                                              "Year": lambda t: t in POV_YEARS}),
    "cpi_2012base_1994_2018": (HT["cpi_2012base_1994_2018"][0], {"Year": lambda t: t in YEARS}),
    "palay_corn_quarterly": (HT["palay_corn_quarterly"][0], {"Ecosystem/Croptype": lambda t: t in ("Palay", "Corn"),
                                                            "Year": lambda t: t in YEARS, "Period": lambda t: t.startswith("Quarter")}),
    "fisheries_quarterly": (HT["fisheries_quarterly"][0], {"Subsector": lambda t: t == "FISHERIES", "Year": lambda t: t in YEARS,
                                                          "Quarter": lambda t: t.startswith("Quarter")}),
}


def run() -> None:
    out = RAW / "psa"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (path, pick) in TABLES.items():
        meta = json.loads(_get(PX + path, timeout=120))
        q = []
        for v in meta["variables"]:
            vals = v.get("values")
            if vals is None:
                q.append({"code": v["code"], "selection": {"filter": "all", "values": ["*"]}})
            else:
                keep = [c for c, t in zip(vals, v["valueTexts"]) if pick[v["code"]](t.strip())] if v["code"] in pick else vals
                q.append({"code": v["code"], "selection": {"filter": "item", "values": keep}})
        body = _get(PX + path, json.dumps({"query": q, "response": {"format": "csv"}}).encode())
        f = out / f"{name}.csv"
        f.write_bytes(body)
        rows.append([f"psa/{f.name}", PX + path, date.today().isoformat(), hashlib.sha256(body).hexdigest(), name])
        print(name, len(body))
    with (RAW / "MANIFEST_psa.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "source_url", "retrieved", "sha256", "description"])
        w.writerows(rows)


if __name__ == "__main__":
    run()
