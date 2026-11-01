"""
E134 phase 1 acquisition (2021+ only; raw files with query, URL, hash and fetch time in data/acquisition_log.json):

  1. NASA POWER daily precipitation (PRECTOTCORR) and 2 m temperature (T2M), 2021-01-01 .. 2026-09-30, at one point
     per region of the four SWS areas (18 regional centres) and at the five CALABARZON province centroids (E118).
  2. PSA OpenSTAT palay and corn production by quarter, region and province (DB/2E/CS/0012E4EVCP0.px), Year >= 2021.
  3. PSA OpenSTAT FIES 2023 Table 8 (average income, expenditure and savings by province and income decile, constant
     2021 prices) and Table 7 (expenditure by major group incl. food, by decile and province).

    python -I runner/e134_acquire.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
UA = "Mozilla/5.0 (aiPHeed thesis research)"
POWER = ("https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M&community=AG"
         "&longitude={lon}&latitude={lat}&start=20210101&end=20260930&format=JSON")
# One representative point per region: the regional centre (city coordinates, rounded to 0.01 degree).
REGION_POINTS = {
    "NCR": ("metro_manila", 14.60, 120.98), "CAR": ("balance_luzon", 16.41, 120.60),
    "Region I": ("balance_luzon", 16.62, 120.32), "Region II": ("balance_luzon", 17.61, 121.73),
    "Region III": ("balance_luzon", 15.03, 120.69), "Region IV-A": ("balance_luzon", 14.21, 121.17),
    "MIMAROPA": ("balance_luzon", 13.41, 121.18), "Region V": ("balance_luzon", 13.14, 123.74),
    "Region VI": ("visayas", 10.72, 122.56), "Region VII": ("visayas", 10.32, 123.89),
    "Region VIII": ("visayas", 11.24, 125.00), "NIR": ("visayas", 10.68, 122.95),
    "Region IX": ("mindanao", 7.83, 123.44), "Region X": ("mindanao", 8.48, 124.65),
    "Region XI": ("mindanao", 7.07, 125.61), "Region XII": ("mindanao", 6.50, 124.85),
    "Region XIII": ("mindanao", 8.95, 125.54), "BARMM": ("mindanao", 7.22, 124.25)}
PROVINCE_POINTS = {"Cavite": (14.28, 120.87), "Laguna": (14.17, 121.33), "Batangas": (13.76, 121.06),
                   "Rizal": (14.60, 121.31), "Quezon": (14.03, 122.11)}
TABLES = {"psa_palay_corn_production_quarter_2021_2026": "DB/2E/CS/0012E4EVCP0.px",
          "psa_fies2023_t8_income_expenditure_savings": "DB/1E/IE/0081E3AIES0.px",
          "psa_fies2023_t7_expenditure_by_group": "DB/1E/IE/0071E3ATME0.px"}


def curl(url: str, data: str | None = None) -> bytes:
    cmd = ["curl", "-s", "-m", "300", "-A", UA, url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    return subprocess.run(cmd, capture_output=True, check=True).stdout


def _rec(name, url, raw, **kw):
    return {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), **kw}


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log = {}
    pts = {**{k: (a, la, lo) for k, (a, la, lo) in REGION_POINTS.items()},
           **{k: ("calabarzon_province", la, lo) for k, (la, lo) in PROVINCE_POINTS.items()}}
    for name, (area, la, lo) in pts.items():
        url = POWER.format(lat=la, lon=lo)
        raw = curl(url)
        assert raw[:1] == b"{" and b"PRECTOTCORR" in raw, name
        f = RAW / f"nasa_power_daily_{name.replace(' ', '_')}.json"
        f.write_bytes(raw)
        log[f.stem] = _rec(f.stem, url, raw, point=name, area=area, lat=la, lon=lo, source="NASA POWER (LaRC), daily, community AG")
        print("ok", name, len(raw), flush=True)
        time.sleep(1)
    for name, path in TABLES.items():
        meta = json.loads(curl(f"{PX}/{path}").decode("utf-8-sig"))
        q = []
        for v in meta["variables"]:
            codes, texts = v["values"], v["valueTexts"]
            if v["code"] == "Year":
                keep = [c for c, t in zip(codes, texts) if int(t.strip()[:4]) >= 2021]
            elif v["code"] == "Ecosystem/Croptype":
                keep = [c for c, t in zip(codes, texts) if t in ("Palay", "Corn")]
            elif v["code"] == "Period":
                keep = [c for c, t in zip(codes, texts) if t.startswith("Quarter")]
            else:
                keep = codes
            q.append({"code": v["code"], "selection": {"filter": "item", "values": keep}})
        body = json.dumps({"query": q, "response": {"format": "csv"}})
        raw = curl(f"{PX}/{path}", body)
        assert raw[:1] not in (b"{", b"<") and raw.count(b"\n") >= 10, name
        (RAW / f"{name}.csv").write_bytes(raw)
        (RAW / f"{name}_query.json").write_text(json.dumps(json.loads(body), indent=1), encoding="utf-8")
        log[name] = _rec(name, f"{PX}/{path}", raw, title=meta.get("title"))
        print("ok", name, len(raw), flush=True)
        time.sleep(1)
    (ROOT / "data" / "acquisition_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
