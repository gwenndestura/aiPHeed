"""
PSA official poverty statistics by province, all four bases, from PSA OpenSTAT (public API):
  poverty incidence among families      (pov_fam)    subsistence incidence among families   (sub_fam)
  poverty incidence among population    (pov_pop)    subsistence incidence among population (sub_pop)
Rounds 2006, 2009, 2012, 2015 (DB/3D, 2015 Full Year release) and 2018, 2021, 2023 (DB/1F/FY, 2023 Full Year release).
Each value keeps its coefficient of variation. PROVINCIAL rows only (regions and NCR districts are kept separately flagged).
No value is interpolated or derived; a round that PSA did not publish for a province stays missing.

Release rule used by the model (same as the existing poverty inputs, app/e137/features.py): round R usable from 1 January of R+2.

    python -m app.hcw.poverty_official fetch -> data/hcw_official/raw/psa_poverty_by_province.csv (+ provenance json)
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from app.paths import BACKEND_DIR

API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"
OUT = BACKEND_DIR / "data" / "hcw_official" / "raw"
FILE = OUT / "psa_poverty_by_province.csv"
TABLES = {  # indicator: [(path, incidence item prefix)]
    "pov_fam": [("3D/0013C3DP010.px", "Poverty Incidence among Families"), ("1F/FY/0011F3DF010.px", "Poverty Incidence Among Families")],
    "pov_pop": [("3D/0023C3DP020.px", "Poverty Incidence among Population"), ("1F/FY/0031F3DF020.px", "Poverty Incidence among Population")],
    "sub_fam": [("3D/0033C3DP030.px", "Subsistence Incidence among Families"), ("1F/FY/0051F3DF030.px", "Subsistence Incidence among Families")],
    "sub_pop": [("3D/0043C3DP040.px", "Subsistence Incidence among Population"), ("1F/FY/0071F3DF040.px", "Subsistence Incidence among Population")],
}


def _get(url: str, body: dict | None = None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "aiPHeed-research"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def clean_name(s: str) -> str:
    """'....Batangas 1/, a/' -> 'Batangas'; footnote markers and asterisks removed."""
    s = s.strip(".").strip()
    s = re.sub(r"(\s*(\*+|[a-z0-9]{1,2}/),?)+\s*$", "", s)
    return s.replace("*", "").strip()


def _table(path: str, item_prefix: str) -> tuple[pd.DataFrame, str | None]:
    meta = _get(API + path)
    var = meta["variables"]
    geo, item, year = var[0], var[1], var[-1]
    sel_items = [v for v, t in zip(item["values"], item["valueTexts"]) if t.strip().startswith(item_prefix) or t.strip() == "Coefficient of Variation"]
    q = {"query": [{"code": item["code"], "selection": {"filter": "item", "values": sel_items}}], "response": {"format": "json"}}
    res = _get(API + path, q)
    gtext = dict(zip(geo["values"], geo["valueTexts"]))
    itext = dict(zip(item["values"], item["valueTexts"]))
    ytext = dict(zip(year["values"], year["valueTexts"]))
    codes = [v["code"] for v in var]
    rows = []
    for r in res["data"]:
        k = dict(zip(codes, r["key"]))
        raw = r["values"][0]
        try:
            val = float(raw)
        except ValueError:
            val = None
        g = gtext[k[geo["code"]]]
        rows.append({"geo_raw": g, "item": itext[k[item["code"]]], "year": int(re.match(r"\d{4}", ytext[k[year["code"]]]).group()), "value": val})
    d = pd.DataFrame(rows)
    new_series = path.startswith("1F/")
    dots = d.geo_raw.str.match(r"^\.\.\.\.[^.]") if new_series else d.geo_raw.str.match(r"^\.\.[^.]")
    d["level"] = dots.map({True: "province_or_district", False: "region_or_national"})
    return d, meta.get("updated")


def fetch() -> pd.DataFrame:
    out, prov = [], {"source": API, "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "tables": {}}
    for ind, parts in TABLES.items():
        for path, prefix in parts:
            d, upd = _table(path, prefix)
            prov["tables"][path] = {"indicator": ind, "updated": upd}
            inc = d[d.item.str.strip().str.startswith(prefix)].rename(columns={"value": "value_pct"})
            cv = d[d.item.str.strip() == "Coefficient of Variation"][["geo_raw", "year", "value"]].rename(columns={"value": "cv"})
            m = inc.merge(cv, on=["geo_raw", "year"], how="left")
            m["indicator"], m["table"] = ind, path
            out.append(m[["indicator", "geo_raw", "level", "year", "value_pct", "cv", "table"]])
    D = pd.concat(out, ignore_index=True)
    D["name"] = D.geo_raw.map(clean_name)
    D = D[D.year >= 2006].sort_values(["indicator", "name", "year"])
    OUT.mkdir(parents=True, exist_ok=True)
    D.to_csv(FILE, index=False, lineterminator="\n")
    (OUT / "psa_poverty_by_province.provenance.json").write_text(json.dumps(prov, indent=1))
    return D


def load() -> pd.DataFrame:
    return pd.read_csv(FILE)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "fetch":
    D = fetch()
    p = D[D.level == "province_or_district"]
    print(p.pivot_table(index="indicator", columns="year", values="value_pct", aggfunc="count").to_string())
    print(p[p.name.isin(["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"])].pivot_table(index=["name", "indicator"], columns="year", values="value_pct").to_string())
