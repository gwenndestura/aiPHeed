"""Y12 step 1b: parse the raw PSA downloads into tidy monthly series (ym = year * 12 + month - 1) and report coverage.
Writes data_acquired/tidy_*.csv and out/coverage.json. Checks the downloaded hashes against manifest.json first.

    python -B tidy.py
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ACQ = HERE.parent / "data_acquired"
OUT = HERE.parent / "out"
MON = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                   "October", "November", "December"])}
MON3 = {m[:3]: i for m, i in MON.items()}
# the project's province codes (backend/app ... ("PH040100000", "Cavite") ... ("PH040500000", "Batangas")), not PSGC order
PROV = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
        "Batangas": "PH040500000"}


def raw(name: str) -> pd.DataFrame:
    man = {m["file"]: m for m in json.loads((ACQ / "manifest.json").read_text())}
    b = (ACQ / f"{name}.csv").read_bytes()
    assert hashlib.sha256(b).hexdigest() == man[f"{name}.csv"]["sha256"], f"{name} changed since download"
    return pd.read_csv(io.BytesIO(b), dtype=str, encoding="latin-1")


def num(s):
    return pd.to_numeric(s, errors="coerce")


def geo(x: str) -> str:
    x = x.strip(".").strip()
    for k, v in PROV.items():
        if x.lower().startswith(k.lower()):
            return v
    return "PH" if x.upper() == "PHILIPPINES" else ("IV-A" if "IV-A" in x.upper() else x)


def melt_wide(d: pd.DataFrame, ids: list[str], pat: str, mon: dict) -> pd.DataFrame:
    rows = []
    for c in d.columns:
        if c in ids:
            continue
        m = re.match(pat, c)
        if not m or m.group(2) not in mon:
            continue
        y, mm = int(m.group(1)), mon[m.group(2)]
        for _, r in d.iterrows():
            rows.append({**{k: r[k] for k in ids}, "ym": y * 12 + mm, "value": num(r[c])})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    cov = {}
    # stocks (national)
    s = raw("stocks_national_monthly")
    st = s.melt(id_vars=["Sector", "Year"], var_name="month", value_name="value")
    st["ym"] = st["Year"].astype(int) * 12 + st["month"].map(MON)
    st["value"] = num(st["value"])
    st["sector"] = st["Sector"].str.replace("Rice: ", "", regex=False).str.replace(" Stock", "", regex=False).str.lower()
    st = st.pivot_table(index="ym", columns="sector", values="value").sort_index()
    st.to_csv(ACQ / "tidy_stocks_national.csv")
    cov["stocks_national"] = {c: [int(st[c].first_valid_index()), int(st[c].last_valid_index()), int(st[c].isna().sum())]
                              for c in st.columns}
    # regional stocks
    r = raw("stocks_regional_monthly")
    cov["stocks_regional"] = {"years": sorted({c.split()[0] for c in r.columns if c[:2] in ("19", "20")})}
    # farmgate palay (old 1990-2020, new 2010-2026)
    fg = []
    for name in ("farmgate_palay_old", "farmgate_palay_new"):
        d = raw(name)
        t = melt_wide(d, ["Geolocation", "Commodity"], r"^(\d{4}) (\w+)$", MON)
        t["geo"] = t["Geolocation"].map(geo)
        t["variety"] = np.where(t["Commodity"].str.contains("Fancy"), "fancy", "other")
        t["series"] = name.split("_")[-1]
        fg.append(t[["series", "geo", "variety", "ym", "value"]])
    fg = pd.concat(fg)
    fg.to_csv(ACQ / "tidy_farmgate_palay.csv", index=False)
    g = fg.dropna(subset=["value"]).groupby(["series", "geo", "variety"])["ym"].agg(["min", "max", "count"])
    cov["farmgate"] = {"|".join(k): [int(v["min"]), int(v["max"]), int(v["count"])] for k, v in g.iterrows()}
    ov = fg.dropna(subset=["value"]).pivot_table(index=["geo", "variety", "ym"], columns="series", values="value").dropna()
    cov["farmgate_old_vs_new_overlap"] = {"rows": int(len(ov)),
                                          "meanAbsDiffPesoPerKg": round(float((ov["old"] - ov["new"]).abs().mean()), 4),
                                          "corr": round(float(ov["old"].corr(ov["new"])), 4)}
    # CPI 2012=100 YoY
    cp = []
    for name in ("cpi2012_yoy_1995_2011", "cpi2012_yoy_2012_2021"):
        d = raw(name)
        t = melt_wide(d, ["Geolocation", "Commodity Description"], r"^(\d{4}) (\w{3})$", MON3)
        t["geo"] = t["Geolocation"].map(geo)
        t["commodity"] = t["Commodity Description"].map({"ALL ITEMS": "all_items", "Food": "food", "Rice": "rice"})
        cp.append(t[["geo", "commodity", "ym", "value"]])
    cp = pd.concat(cp).dropna(subset=["value"]).drop_duplicates(["geo", "commodity", "ym"])
    cp.to_csv(ACQ / "tidy_cpi2012_yoy.csv", index=False)
    g = cp.groupby(["geo", "commodity"])["ym"].agg(["min", "max", "count"])
    cov["cpi2012_yoy"] = {"|".join(k): [int(v["min"]), int(v["max"]), int(v["count"])] for k, v in g.iterrows()}
    # imports (2015-2026), sum over countries
    d = raw("imports_rice_monthly_2015_2026")
    t = melt_wide(d, ["GROUP", "COUNTRY"], r"^(\d{4}) Gross Kilo (\w+)$", MON)
    im = t.groupby("ym")["value"].sum(min_count=1)
    im.to_frame("rice_imports_kg").to_csv(ACQ / "tidy_imports_rice.csv")
    cov["imports_rice"] = [int(im.first_valid_index()), int(im.last_valid_index()), int(im.notna().sum())]
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    ym = lambda v: f"{v // 12}-{v % 12 + 1:02d}"  # noqa: E731
    for k, v in cov.items():
        if isinstance(v, dict):
            for kk, vv in v.items():
                print(k, kk, [ym(x) if isinstance(x, int) and x > 20000 else x for x in vv] if isinstance(vv, list) else vv)
        else:
            print(k, [ym(x) if x > 20000 else x for x in v])


if __name__ == "__main__":
    main()
