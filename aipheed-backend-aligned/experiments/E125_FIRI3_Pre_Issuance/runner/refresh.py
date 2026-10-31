"""E125 source refresh: NASA POWER monthly (same query as E118, years 2021-2026), IBTrACS (last-3-years file) for the
local 100 km and PAR cyclone counts (same methods as the corrected pipeline and E114), and the PSA OpenSTAT LFS table
(same table and selection as E114). Raw responses are saved with fetch time and SHA-256 under data/raw; earlier
experiment files are not touched. No value is interpolated or estimated.

    python refresh.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
EXP = ROOT.parent
UA = "aiPHeed-research/1.0 (thesis; contact via repository owner)"
CENTROIDS = {"Cavite": (14.28, 120.87), "Laguna": (14.17, 121.33), "Batangas": (13.76, 121.06), "Rizal": (14.60, 121.31), "Quezon": (14.03, 122.11)}  # E118
IBTRACS_URL = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/"
               "v04r01/access/csv/ibtracs.last3years.list.v04r01.csv")


def curl(url: str, data: str | None = None, timeout: int = 600) -> tuple[bytes, dict]:
    cmd = ["curl", "-s", "-S", "-m", str(timeout), "-A", UA, "-D", "-", url]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "--data", data]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    head, _, body = out.partition(b"\r\n\r\n")
    while body.startswith(b"HTTP/"):                                   # skip intermediate (e.g. 100-continue) headers
        head, _, body = body.partition(b"\r\n\r\n")
    hdr = {}
    for line in head.decode("latin-1").splitlines()[1:]:
        k, _, v = line.partition(":")
        hdr[k.strip().lower()] = v.strip()
    return body, hdr


def main():
    log = {"fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "power": {}, "ibtracs": {}, "lfs": {}}
    for prov, (la, lo) in CENTROIDS.items():
        url = (f"https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR,T2M,T2M_MAX,RH2M"
               f"&community=AG&longitude={lo}&latitude={la}&start=2021&end=2026&format=JSON")
        body, hdr = curl(url)
        f = RAW / f"nasa_power_monthly_2021_2026_{prov}.json"
        f.write_bytes(body)
        log["power"][prov] = {"url": url, "lat": la, "lon": lo, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                              "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "api_version": json.loads(body)["header"]["api"]["version"]}
        print("power", prov, len(body), flush=True)
    body, hdr = curl(IBTRACS_URL, timeout=900)
    f = RAW / "ibtracs.last3years.list.v04r01.csv"
    f.write_bytes(body)
    log["ibtracs"] = {"url": IBTRACS_URL, "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body), "last_modified": hdr.get("last-modified"),
                      "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    print("ibtracs", len(body), hdr.get("last-modified"), flush=True)
    # PSA OpenSTAT LFS (E114 collect_covariates.lfs): same table and selection
    sys.path.insert(0, str(EXP / "E114_Final_Run" / "runner"))
    import collect_covariates as CC                                   # noqa: E402
    try:
        d = CC.lfs()
        f = RAW / "psa_lfs_0021B3FKEI2_unemployment.csv"
        d.to_csv(f, index=False)
        log["lfs"] = {"table": "1B/LFS/0021B3FKEI2.px", "sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "rows": int(len(d)),
                      "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        print("lfs", len(d), flush=True)
    except Exception as e:                                            # noqa: BLE001
        log["lfs"] = {"table": "1B/LFS/0021B3FKEI2.px", "error": f"{type(e).__name__}: {e}", "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        print("lfs ERROR", e, flush=True)
    (ROOT / "data" / "refresh_log.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    main()
