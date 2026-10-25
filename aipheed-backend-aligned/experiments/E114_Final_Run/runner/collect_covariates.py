"""E114 Phase 1.2-1.3: long-history covariates (never outcomes), saved raw + tidy with source, fetch time and the
release rule used to cut them at issue dates (PROTOCOL_E114 §2).

  PSA CPI (OpenStat 0012M4ACP28 1994-2017 back-cast, 0012M4ACP22 2018+; 2018=100): all items, food, rice;
      Philippines and Region IV-A.        Release rule: month m usable from day 10 of month m+1.
  PSA palay production (0012E4EVCP0), Philippines, quarterly.   Rule: quarter q usable from day 1 of quarter q+2's
      ... second month (i.e. q is published ~45 days after quarter end; at O(t) quarter t-1 is usable).
  PSA LFS unemployment rate (0021B3FKEI2), Philippines, survey months from April 2005.
      Rule: round m usable from day 1 of month m+3.
  NOAA CPC ONI (3-month running ENSO index).   Rule: season ending in month m usable from day 10 of month m+1.
  IBTrACS v04r01 WP: tropical cyclones (any intensity) with a fix inside the Philippine Area of Responsibility
      (5-25N, 115-135E, simplified box), counted by quarter of first PAR fix. Rule: quarter t usable at O(t).
  GDELT DOC 2.0 timelinevol (share of all monitored articles, i.e. coverage-normalised), sourcecountry Philippines,
      2017+, the six E112 theme groups. Rule: month m usable from day 1 of month m+1. Requests paced >= 12 s.

    python collect_covariates.py [--skip-gdelt]
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd

HERE = Path(__file__).resolve().parent
E114 = HERE.parent
RAW = E114 / "data" / "raw"
OUT = E114 / "data"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
GDELT_THEMES = {
    "price": ("ECON_INFLATION", "WB_442_INFLATION", "TAX_ECON_PRICE", "FUELPRICES"),
    "shortage": ("FOOD_SECURITY", "TAX_DISEASE_STARVATION", "NATURAL_DISASTER_FAMINE"),
    "disaster": ("NATURAL_DISASTER",),
    "agri_supply": ("WB_174_CROP_PRODUCTION", "AGRICULTURE", "TAX_FNCACT_FARMERS", "TAX_FNCACT_FISHERMEN"),
    "jobs_income": ("UNEMPLOYMENT", "WB_2747_UNEMPLOYMENT"),
    "assistance": ("WB_1609_FOOD_AND_IN_KIND_TRANSFERS", "TAX_AIDGROUPS"),
}


def curl(url: str, data: str | None = None, timeout: int = 180) -> bytes:
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def px_meta(path: str) -> dict:
    return json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))


def px_query(path: str, select: dict[str, list[str]]) -> pd.DataFrame:
    meta = px_meta(path)
    q = []
    for v in meta["variables"]:
        texts = select.get(v["code"])
        if texts is None:
            vals = v["values"]
        else:
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if t.strip(". ") in texts or t in texts]
        q.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
    body = json.dumps({"query": q, "response": {"format": "csv"}})
    raw = curl(f"{PX}/{path}", body)
    name = path.split("/")[-1].replace(".px", "")
    (RAW / f"psa_{name}.csv").write_bytes(raw)
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1")


def melt_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """PX csv (wide over Year x Period columns) -> long monthly rows."""
    id_cols = [c for c in df.columns if not c[:4].isdigit()]
    long = df.melt(id_vars=id_cols, var_name="yp", value_name="value")
    long["year"] = long["yp"].str[:4].astype(int)
    long["mon"] = long["yp"].str[5:].str.strip()
    long = long[long["mon"].isin(MONTHS)].copy()
    long["month"] = long["mon"].map({m: i + 1 for i, m in enumerate(MONTHS)})
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    return long.drop(columns=["yp", "mon"])


def cpi() -> pd.DataFrame:
    geos = ["PHILIPPINES", "Region IV-A (CALABARZON)"]
    comm = ["0 - ALL ITEMS", "01.1 - FOOD", "01.1.1.12 - Rice"]
    frames = []
    for path in ("2M/PI/CPI/2018NEW/0012M4ACP28.px", "2M/PI/CPI/2018NEW/0012M4ACP22.px"):
        meta = px_meta(path)
        geo_texts = [t for t in next(v for v in meta["variables"] if v["code"] == "Geolocation")["valueTexts"]
                     if t.strip(". ") in geos]
        d = px_query(path, {"Geolocation": geo_texts, "Commodity Description": comm})
        frames.append(melt_monthly(d))
    d = pd.concat(frames, ignore_index=True)
    d.columns = [c.lower().replace(" ", "_") for c in d.columns]
    d["geolocation"] = d["geolocation"].str.strip(". ")
    d = d.drop_duplicates(["geolocation", "commodity_description", "year", "month"], keep="last")
    d = d.sort_values(["geolocation", "commodity_description", "year", "month"])
    d["ym"] = d["year"] * 12 + d["month"] - 1
    g = d.groupby(["geolocation", "commodity_description"])
    d["yoy"] = (d["value"] / g["value"].shift(12) - 1) * 100
    gap = d["ym"] - g["ym"].shift(12)
    d.loc[gap != 12, "yoy"] = float("nan")
    return d


def palay() -> pd.DataFrame:
    d = px_query("2E/CS/0012E4EVCP0.px", {"Ecosystem/Croptype": ["Palay"], "Geolocation": ["PHILIPPINES"],
                                          "Period": ["Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]})
    id_cols = [c for c in d.columns if not c[:4].isdigit()]
    long = d.melt(id_vars=id_cols, var_name="yp", value_name="value")
    long["year"] = long["yp"].str[:4].astype(int)
    long["quarter"] = long["yp"].str.extract(r"Quarter (\d)")[0].astype(float)
    long = long.dropna(subset=["quarter"])
    long["q"] = long["year"] * 4 + long["quarter"].astype(int) - 1
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.sort_values("q")
    long["yoy"] = (long["value"] / long["value"].shift(4) - 1) * 100
    return long[["year", "quarter", "q", "value", "yoy"]]


def lfs() -> pd.DataFrame:
    path = "1B/LFS/0021B3FKEI2.px"
    meta = px_meta(path)
    sel = {}
    for v in meta["variables"]:
        txt = v["valueTexts"]
        if any("Unemployment" in t for t in txt):
            sel[v["code"]] = [t for t in txt if t.strip() == "Unemployment Rate"]
        elif any(t.strip(". ").upper() == "PHILIPPINES" for t in txt):
            sel[v["code"]] = [t for t in txt if t.strip(". ").upper() == "PHILIPPINES"]
    d = px_query(path, sel)
    return d


def oni() -> pd.DataFrame:
    raw = curl("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt")
    (RAW / "noaa_oni.txt").write_bytes(raw)
    d = pd.read_csv(io.BytesIO(raw), sep=r"\s+")
    seas = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    d["end_month"] = d["SEAS"].map({s: (i + 1) % 12 + 1 for i, s in enumerate(seas)})
    d["end_year"] = d["YR"] + (d["SEAS"] == "NDJ").astype(int)
    return d.rename(columns={"ANOM": "oni"})[["end_year", "end_month", "SEAS", "YR", "oni"]]


def ibtracs() -> pd.DataFrame:
    f = RAW / "ibtracs.WP.list.v04r01.csv"
    if not f.exists():
        subprocess.run(["curl", "-s", "-m", "900", "-o", str(f), "https://www.ncei.noaa.gov/data/international-best-track-"
                        "archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.WP.list.v04r01.csv"], check=True)
    d = pd.read_csv(f, skiprows=[1], usecols=["SID", "SEASON", "ISO_TIME", "LAT", "LON", "USA_WIND"], low_memory=False)
    d["LAT"], d["LON"] = pd.to_numeric(d["LAT"], errors="coerce"), pd.to_numeric(d["LON"], errors="coerce")
    d = d[(d["SEASON"] >= 1996) & d["LAT"].between(5, 25) & d["LON"].between(115, 135)].copy()
    d["t"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    first = d.sort_values("t").groupby("SID").first().reset_index()
    first["q"] = first["t"].dt.year * 4 + (first["t"].dt.month - 1) // 3
    return first.groupby("q").size().rename("tc_par").reset_index()


def gdelt() -> pd.DataFrame:
    rows = []
    for cat, themes in GDELT_THEMES.items():
        q = "sourcecountry:philippines (" + " OR ".join(f"theme:{t}" for t in themes) + ")" if len(themes) > 1 else \
            f"sourcecountry:philippines theme:{themes[0]}"
        url = ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + quote(q) + "&mode=timelinevol&format=csv"
               "&startdatetime=20170101000000&enddatetime=20261001000000&timelinesmooth=0")
        for attempt in range(6):
            time.sleep(15 + 30 * attempt)
            raw = curl(url, timeout=300)
            if raw[:6] != b"Please" and len(raw) > 200:
                break
        else:
            print("GDELT throttled for", cat)
            continue
        (RAW / f"gdelt_doc_{cat}.csv").write_bytes(raw)
        t = pd.read_csv(io.BytesIO(raw))
        t["category"] = cat
        rows.append(t)
        print("GDELT", cat, len(t))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log = {"fetched_utc": stamp, "sources": {}}
    for name, fn in (("cpi", cpi), ("palay", palay), ("lfs", lfs), ("oni", oni), ("ibtracs_par", ibtracs)):
        try:
            d = fn()
            d.to_csv(OUT / f"cov_{name}.csv", index=False, lineterminator="\n")
            log["sources"][name] = {"rows": len(d), "status": "ok"}
            print(name, len(d))
        except Exception as e:  # recorded, never silently imputed
            log["sources"][name] = {"status": f"failed: {e!r}"}
            print(name, "FAILED", e)
    if "--skip-gdelt" not in sys.argv:
        d = gdelt()
        if len(d):
            d.to_csv(OUT / "cov_gdelt_doc.csv", index=False, lineterminator="\n")
        log["sources"]["gdelt_doc"] = {"rows": len(d), "status": "ok" if len(d) else "throttled/empty"}
    (OUT / "covariates_fetch_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
