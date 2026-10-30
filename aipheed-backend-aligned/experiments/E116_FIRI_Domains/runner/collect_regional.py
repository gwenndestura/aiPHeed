"""E116 data acquisition (covariates only, never outcomes): region-level PSA OpenSTAT series aggregated to the four
SWS areas, so that market, fish and climate inputs can vary between areas instead of repeating one national value.

  CPI food and all items, monthly, by region: 0012M4ACP28 (1994-2017, 2018=100 back-cast) + 0012M4ACP22 (2018+).
  Fisheries production, quarterly, by region: 0132E4GVFP1 (1980+).
  Palay production, quarterly, by region: 0012E4EVCP0 (1987+).

SWS areas: NCR = NCR; Balance Luzon = CAR, I, II, III, IV-A, IV-B (MIMAROPA), V; Visayas = VI, VII, VIII (and NIR where
reported); Mindanao = IX, X, XI, XII, XIII, BARMM/ARMM. CPI YoY is the unweighted mean of the regions in the area
(regional weights are not in the tables; documented approximation). Production is summed over the area's regions.
Values after 2026-Q3 are dropped. Raw responses are saved with the fetch time.

    python collect_regional.py   # ../data/raw/*.csv, ../data/area_cpi.csv, ../data/area_fish.csv, ../data/area_palay.csv,
                                 # ../data/fetch_log.json
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LAST_Q = 2026 * 4 + 2
AREA = {"NCR": ["NCR", "NATIONAL CAPITAL"],
        "BL": ["CAR", "CORDILLERA", "REGION I ", "ILOCOS", "REGION II ", "CAGAYAN", "REGION III", "CENTRAL LUZON",
               "IV-A", "CALABARZON", "IV-B", "MIMAROPA", "REGION V ", "BICOL"],
        "VIS": ["REGION VI ", "WESTERN VISAYAS", "REGION VII", "CENTRAL VISAYAS", "REGION VIII", "EASTERN VISAYAS",
                "NEGROS ISLAND", "NIR"],
        "MIN": ["REGION IX", "ZAMBOANGA", "REGION X ", "NORTHERN MINDANAO", "REGION XI", "DAVAO", "REGION XII",
                "SOCCSKSARGEN", "REGION XIII", "CARAGA", "BARMM", "ARMM", "BANGSAMORO", "MUSLIM MINDANAO"]}


def curl(url, data=None, timeout=240):
    cmd = ["curl", "-s", "-m", str(timeout), "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, check=True, capture_output=True).stdout


NUM = {"I": "BL", "II": "BL", "III": "BL", "IV-A": "BL", "IV-B": "BL", "V": "BL", "VI": "VIS", "VII": "VIS", "VIII": "VIS",
       "IX": "MIN", "X": "MIN", "XI": "MIN", "XII": "MIN", "XIII": "MIN"}


def area_of(name: str) -> str | None:
    u = name.strip(". ").upper()
    if "OUTSIDE" in u or "AONCR" in u:
        return None
    if "NATIONAL CAPITAL" in u or u.startswith("NCR"):
        return "NCR"
    if "CORDILLERA" in u:
        return "BL"
    if "MIMAROPA" in u:
        return "BL"
    if "NEGROS ISLAND" in u:
        return "VIS"
    if "BANGSAMORO" in u or "MUSLIM MINDANAO" in u or "BARMM" in u or "ARMM" in u:
        return "MIN"
    m = re.match(r"REGION ([IVX]+(?:-[AB])?)(?![IVX])", u)
    return NUM.get(m.group(1)) if m else None


def region_rows(texts):
    """Indices of region-level geolocations (two leading dots), mapped to SWS areas."""
    return {i: a for i, t in enumerate(texts)
            if t.startswith("..") and not t.startswith("....") and (a := area_of(t)) is not None}


def px(path, keep):
    meta = json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))
    q, regions = [], None
    for v in meta["variables"]:
        if v["code"] == "Geolocation":
            regions = region_rows(v["valueTexts"])
            vals = [v["values"][i] for i in regions]
        elif v["code"] in keep:
            vals = [c for c, t in zip(v["values"], v["valueTexts"]) if t.strip(". ") in keep[v["code"]]]
        else:
            vals = v["values"]
        q.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
    raw = curl(f"{PX}/{path}", json.dumps({"query": q, "response": {"format": "csv"}}))
    name = path.split("/")[-1].replace(".px", "")
    (RAW / f"psa_{name}_regions.csv").write_bytes(raw)
    geo = {meta["variables"][0]["valueTexts"][i].strip(". "): a for i, a in regions.items()} if meta["variables"][0]["code"] == "Geolocation" else None
    if geo is None:
        g = [v for v in meta["variables"] if v["code"] == "Geolocation"][0]
        geo = {g["valueTexts"][i].strip(". "): a for i, a in regions.items()}
    df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    return df, geo, hashlib.sha256(raw).hexdigest()


def cpi():
    keep = {"Commodity Description": ["0 - ALL ITEMS", "01.1 - FOOD"]}
    frames, log = [], {}
    for p in ("2M/PI/CPI/2018NEW/0012M4ACP28.px", "2M/PI/CPI/2018NEW/0012M4ACP22.px"):
        df, geo, h = px(p, keep)
        log[p] = {"sha256": h, "regions": geo}
        idc = [c for c in df.columns if not c[:4].isdigit()]
        long = df.melt(id_vars=idc, var_name="yp", value_name="v")
        long = long[long["yp"].str.split(" ").str[1].isin(MON)]
        long["ym"] = long["yp"].str[:4].astype(int) * 12 + long["yp"].str.split(" ").str[1].map(MON.index)
        long["geo"] = long[idc[0]].str.strip(". ")
        long["com"] = long[idc[1]].str.strip(". ")
        long["v"] = pd.to_numeric(long["v"], errors="coerce")
        frames.append(long[["geo", "com", "ym", "v"]])
    c = pd.concat(frames).dropna().drop_duplicates(["geo", "com", "ym"], keep="last")
    c["area"] = c["geo"].map({**log[list(log)[0]]["regions"], **log[list(log)[1]]["regions"]})
    c = c.dropna(subset=["area"]).sort_values("ym")
    c["yoy"] = c.groupby(["geo", "com"])["v"].transform(lambda s: 100 * (s / s.shift(12) - 1))
    a = c.dropna(subset=["yoy"]).groupby(["area", "com", "ym"])["yoy"].mean().unstack("com").reset_index()
    a.columns = ["area", "ym", "all_yoy", "food_yoy"]
    a = a[a["ym"] <= 2026 * 12 + 8]
    a.to_csv(DATA / "area_cpi.csv", index=False, lineterminator="\n", float_format="%.6g")
    return log, len(a)


def quarterly(path, keep, out, label):
    df, geo, h = px(path, keep)
    idc = [c for c in df.columns if not c[:4].isdigit()]
    gcol = [c for c in idc if "Geolocation" in c][0]
    long = df.melt(id_vars=idc, var_name="yp", value_name="v")
    long = long[long["yp"].str.contains("Quarter")]
    long["q"] = long["yp"].str[:4].astype(int) * 4 + long["yp"].str.extract(r"Quarter (\d)")[0].astype(int) - 1
    long["geo"] = long[gcol].str.strip(". ")
    long["v"] = pd.to_numeric(long["v"], errors="coerce")
    long["area"] = long["geo"].map(geo)
    a = long.dropna(subset=["area", "v"]).groupby(["area", "q"])["v"].sum().reset_index()
    a = a[a["q"] <= LAST_Q].sort_values(["area", "q"])
    a["yoy"] = a.groupby("area")["v"].transform(lambda s: 100 * (s / s.shift(4) - 1))
    a.rename(columns={"v": label}).to_csv(DATA / out, index=False, lineterminator="\n", float_format="%.6g")
    return {"sha256": h, "regions": geo}, len(a)


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    log = {"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    log["cpi"], n1 = cpi()
    log["fish"], n2 = quarterly("2E/FS/0132E4GVFP1.px", {"Subsector": ["FISHERIES"]}, "area_fish.csv", "fish_t")
    log["palay"], n3 = quarterly("2E/CS/0012E4EVCP0.px", {"Ecosystem/Croptype": ["Palay"]}, "area_palay.csv", "palay_t")
    log["rows"] = {"area_cpi": n1, "area_fish": n2, "area_palay": n3}
    (DATA / "fetch_log.json").write_text(json.dumps(log, indent=1))
    print(json.dumps({k: (v if k != "cpi" else {p: len(x["regions"]) for p, x in v.items()}) for k, v in log.items() if k not in ("fish", "palay")} |
                     {"fish_regions": log["fish"]["regions"], "palay_regions": log["palay"]["regions"]}, indent=1))


if __name__ == "__main__":
    main()
