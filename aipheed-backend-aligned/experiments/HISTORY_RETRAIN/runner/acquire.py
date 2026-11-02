"""HISTORY_RETRAIN data acquisition (EXPLORATORY; user decisions 1 and 3 of 2026-11-02).

Fetches the long provincial PSA series from the PSA OpenSTAT PXWeb API, keeps each raw response in data/raw/, writes
tidy files to data/, and logs URL, query, fetch time and SHA-256 in data/fetch_log.json. It also re-parses the held
World Bank Pink Sheet workbook from 1960 (the served CSV keeps 2018+ only) and recomputes provincial typhoon counts
from the held IBTrACS file. No gap is filled: a missing PSA cell ("..", "", "-") stays missing.

    python acquire.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True        # imports from other experiment folders must leave nothing behind

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
HR = HERE.parent
EXP = HR.parent
DATA = HR / "data"
RAW = DATA / "raw"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
PROVS = {"Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000",
         "Rizal": "PH040400000"}
REGION = "PH040000000"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LONG_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]
# table key: (path, item variable, item texts kept, period kind)
TABLES = {
    "cpi_backcast_ACP28": ("2M/PI/CPI/2018NEW/0012M4ACP28.px", "Commodity Description", ("0 - ALL ITEMS", "01.1 - FOOD"),
                           "month"),
    "cpi_ACP22": ("2M/PI/CPI/2018NEW/0012M4ACP22.px", "Commodity Description", ("0 - ALL ITEMS", "01.1 - FOOD"),
                  "month"),
    "rice_wholesale_AWB01": ("2M/NWSNEW/0052M4AWB01.px", "Commodity", ("Regular Milled Rice (RMR)",), "month"),
    "palay_corn_EVCP0": ("2E/CS/0012E4EVCP0.px", "Ecosystem/Croptype", ("Palay", "Corn"), "quarter"),
    "fisheries_GVFP1": ("2E/FS/0132E4GVFP1.px", "Subsector", ("FISHERIES",), "quarter"),
}
LOG: dict = {"fetched_utc": None, "files": {}}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def curl(url: str, body: str | None = None) -> bytes:
    cmd = ["curl", "-s", "-m", "180", "-A", UA, "--fail"]
    if body is not None:
        cmd += ["-H", "Content-Type: application/json", "-X", "POST", "--data-binary", "@-"]
    r = subprocess.run(cmd + [url], input=None if body is None else body.encode(), capture_output=True)
    if r.returncode:
        raise RuntimeError(f"curl failed ({r.returncode}) for {url}")
    return r.stdout


def geo_code(text: str) -> str | None:
    t = text.strip(". ").strip()
    if t in PROVS:
        return PROVS[t]
    return REGION if "IV-A" in t.upper() else None


def fetch(key: str) -> pd.DataFrame:
    path, item_var, items, kind = TABLES[key]
    meta = json.loads(curl(PX + path).decode("utf-8-sig"))
    query = []
    for v in meta["variables"]:
        pairs = list(zip(v["values"], v["valueTexts"]))
        if v["code"] in ("Geolocation", "Region Province"):
            sel = [c for c, t in pairs if geo_code(t)]
        elif v["code"] == item_var:
            sel = [c for c, t in pairs if t.strip(". ").strip() in items]
        elif v["code"] == "Year":
            sel = [c for c, _ in pairs]
        else:                                     # period: months or quarters only (no averages, semesters, annual)
            keep = MONTHS + LONG_MONTHS if kind == "month" else ["Quarter 1", "Quarter 2", "Quarter 3", "Quarter 4"]
            sel = [c for c, t in pairs if t.strip() in keep]
        assert sel, f"{key}: nothing selected for {v['code']}"
        query.append({"code": v["code"], "selection": {"filter": "item", "values": sel}})
    body = json.dumps({"query": query, "response": {"format": "csv"}})
    raw = curl(PX + path, body)
    rp = RAW / f"psa_{key}.csv"
    rp.write_bytes(raw)
    LOG["files"][rp.name] = {"source": "PSA OpenSTAT PXWeb", "url": PX + path, "title": meta.get("title"),
                             "query": json.loads(body), "sha256": sha(rp), "bytes": len(raw)}
    return tidy(key, raw.decode("utf-8-sig"), kind)


def tidy(key: str, text: str, kind: str) -> pd.DataFrame:
    d = pd.read_csv(io.StringIO(text), dtype=str)
    id_cols = [c for c in d.columns if not re.match(r"^\d{4} ", c)]
    long = d.melt(id_vars=id_cols, var_name="period", value_name="raw")
    geo_col = next(c for c in id_cols if c in ("Geolocation", "Region Province"))
    item_col = next(c for c in id_cols if c != geo_col)
    long["geo_code"] = long[geo_col].map(geo_code)
    long["item"] = long[item_col].str.strip(". ").str.strip()
    long["year"] = long["period"].str[:4].astype(int)
    per = long["period"].str[5:].str.strip()
    if kind == "month":
        long["month"] = per.map(lambda s: (MONTHS.index(s[:3]) + 1) if s[:3] in MONTHS else None)
        long["ym"] = long["year"] * 12 + long["month"] - 1
    else:
        long["quarter"] = per.str[-1].astype(int)
        long["q"] = long["year"] * 4 + long["quarter"] - 1
    long["value"] = pd.to_numeric(long["raw"].str.strip(), errors="coerce")     # "..", "", "-" -> NaN, never filled
    keep = ["geo_code", "item", "year"] + (["month", "ym"] if kind == "month" else ["quarter", "q"]) + ["value"]
    out = long[keep].sort_values(keep[:-1]).reset_index(drop=True)
    p = DATA / f"{key}.csv"
    out.to_csv(p, index=False)
    LOG["files"][p.name] = {"derived_from": f"raw/psa_{key}.csv", "sha256": sha(p), "rows": len(out),
                            "non_missing": int(out["value"].notna().sum())}
    return out


def pinksheet() -> None:
    """Held World Bank workbook re-parsed from 1960 with the served parser's column map (FINAL_UNIFIED_LGBM)."""
    sys.path.insert(0, str(EXP / "FINAL_UNIFIED_LGBM" / "runner"))
    import pinksheet as PS                                                     # read-only use of its functions
    src = EXP / "FINAL_UNIFIED_LGBM" / "data" / "raw" / "pinksheet_monthly.xlsx"
    rows = PS.read_sheet(src, "Monthly Prices")
    hdr_i = next(i for i, r in enumerate(rows) if r and any(isinstance(x, str) and x.startswith("Crude oil") for x in r))
    cols = {i: PS.KEEP[h] for i, h in enumerate(rows[hdr_i]) if isinstance(h, str) and h in PS.KEEP}
    out = []
    for r in rows[hdr_i + 1:]:
        if not r or not isinstance(r[0], str) or not re.match(r"^\d{4}M\d{2}$", r[0]):
            continue
        y, m = int(r[0][:4]), int(r[0][5:])
        rec = {"month": f"{y}-{m:02d}", "ym": y * 12 + m - 1}
        for i, k in cols.items():
            try:
                rec[k] = float(r[i]) if i < len(r) else None
            except (TypeError, ValueError):
                rec[k] = None
        out.append(rec)
    p = DATA / "pinksheet_monthly_1960.csv"
    pd.DataFrame(out).to_csv(p, index=False)
    LOG["files"][p.name] = {"derived_from": str(src.relative_to(EXP)), "source_sha256": sha(src), "sha256": sha(p),
                            "rows": len(out), "first": out[0]["month"], "last": out[-1]["month"]}


def typhoons() -> None:
    """Distinct storms with a fix within 300 km of each province's area-weighted centroid, per quarter, from the held
    IBTrACS WP file, with FIRI_V2_DATA_AUDIT/runner/typhoons.py's own functions (imported, nothing written there)."""
    sys.path.insert(0, str(EXP / "FIRI_V2_DATA_AUDIT" / "runner"))
    import typhoons as TY
    src = TY.IBTRACS
    cen = TY.centroids()
    assert set(cen) == set(TY.PROVS), cen
    d = pd.read_csv(src, skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON"], low_memory=False)
    d["ISO_TIME"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    d = d[(d["ISO_TIME"] >= "1993-01-01") & (d["ISO_TIME"] < "2026-10-01")].copy()
    d["LAT"], d["LON"] = pd.to_numeric(d["LAT"], errors="coerce"), pd.to_numeric(d["LON"], errors="coerce")
    d["q"] = d["ISO_TIME"].dt.year * 4 + (d["ISO_TIME"].dt.month - 1) // 3
    rows = []
    for name, (lat, lon) in cen.items():
        cnt = d[TY.haversine(lat, lon, d["LAT"].to_numpy(), d["LON"].to_numpy()) <= TY.RADIUS_KM].groupby("q")[
            "SID"].nunique()
        for q in range(1993 * 4, 2026 * 4 + 3):        # every quarter 1993-Q1..2026-Q3: a count of 0 is observed, not filled
            rows.append({"province_code": TY.PROVS[name], "q": q, "quarter": f"{q // 4}-Q{q % 4 + 1}",
                         "tc_count": int(cnt.get(q, 0))})
    R = pd.DataFrame(rows)
    ref = pd.read_csv(EXP / "FIRI_V2_DATA_AUDIT" / "out" / "typhoons_recomputed.csv", dtype={"province_code": str})
    j = ref.merge(R, on=["province_code", "quarter"])
    assert len(j) == len(ref) and (j["tc_count"] == j["tc_count_recomputed"]).all(), "2021+ counts differ from FIRI_V2"
    p = DATA / "typhoons_province_quarter.csv"
    R.to_csv(p, index=False)
    LOG["files"][p.name] = {"derived_from": str(src.relative_to(EXP)), "source_sha256": sha(src), "sha256": sha(p),
                            "method": "FIRI_V2_DATA_AUDIT typhoons.py centroids() and haversine(), 300 km, 1993-Q1..2026-Q3",
                            "check": f"equal to FIRI_V2_DATA_AUDIT/out/typhoons_recomputed.csv on all {len(j)} rows 2021+"}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    LOG["fetched_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for key in TABLES:
        d = fetch(key)
        nn = d.dropna(subset=["value"])
        print(f"{key}: {len(d)} cells, {len(nn)} non-missing")
    pinksheet()
    typhoons()
    LOG["not_acquired"] = {"bsp_remittances": "BSP www.bsp.gov.ph/Statistics/External/*.xlsx returned HTTP 403 to "
                                              "automated requests on 2026-11-02 (4 URLs tried); not acquired, not filled"}
    (DATA / "fetch_log.json").write_text(json.dumps(LOG, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
