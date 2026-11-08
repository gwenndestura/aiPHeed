"""
Acquire E137's public national inputs (public endpoints only; no requests to agencies).

    python -m app.e137.acquire psa       PSA OpenSTAT: poverty gap/severity, food threshold, population, land area
    python -m app.e137.acquire nasa      NASA POWER monthly rainfall at each province centroid, 2000-2019
    python -m app.e137.acquire ibtracs   NOAA IBTrACS v04r01, Western Pacific basin

Each file goes to data/e137/raw/<source>/ and is recorded in data/e137/raw/MANIFEST.csv (URL, date, sha256).
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

from app.e137 import RAW
from app.paths import BACKEND_DIR

PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/"
UA = {"User-Agent": "Mozilla/5.0 (aiPHeed research; public data)", "Content-Type": "application/json"}
TABLES = {
    "poverty_gap_severity_2006_2015": ("DB/3D/0153C3DP11A.px", "income gap, poverty gap, severity, provinces"),
    "food_threshold_subsistence_2006_2015": ("DB/3D/0033C3DP030.px", "per capita food threshold and subsistence incidence"),
    "population_2010_2024": ("DB/1A/PO_2024/0211A6DAPG0.px", "population by province, censuses 2010-2024"),
    "land_area_density_2024": ("DB/1A/PO_2024/0221A6DLPD0.px", "land area and density by province"),
}
GEO = BACKEND_DIR.parent / "frontend" / "public" / "ph-provinces.json"
NASA = ("https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR&community=AG"
        "&longitude={lon:.4f}&latitude={lat:.4f}&start=2000&end=2019&format=JSON")
IBTRACS = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/"
           "v04r01/access/csv/ibtracs.WP.list.v04r01.csv")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifest(rows: list[dict]) -> None:
    m = RAW / "MANIFEST.csv"
    old = list(csv.DictReader(m.open(encoding="utf-8"))) if m.exists() else []
    keep = {r["file"]: r for r in old}
    keep.update({r["file"]: r for r in rows})
    with m.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "source_url", "retrieved", "sha256", "description"])
        w.writeheader()
        w.writerows(sorted(keep.values(), key=lambda r: r["file"]))


def _get(url: str, data: bytes | None = None, timeout: int = 300) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=timeout).read()


def psa() -> list[dict]:
    out = RAW / "psa"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (path, desc) in TABLES.items():
        meta = json.loads(_get(PX + path, timeout=120))
        query = [{"code": v["code"], "selection": {"filter": "item", "values": v["values"]} if "values" in v
                  else {"filter": "all", "values": ["*"]}} for v in meta["variables"]]
        body = _get(PX + path, json.dumps({"query": query, "response": {"format": "csv"}}).encode())
        f = out / f"{name}.csv"
        f.write_bytes(body)
        rows.append({"file": f"psa/{f.name}", "source_url": PX + path, "retrieved": date.today().isoformat(),
                     "sha256": _sha(f), "description": desc})
        print(name, len(body))
    _manifest(rows)
    return rows


def centroids() -> dict[str, tuple[float, float]]:
    """Area-weighted centroid of each province polygon (planar, adequate at province scale)."""
    g = json.loads(GEO.read_text(encoding="utf-8"))
    out = {}
    for f in g["features"]:
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        ax = ay = at = 0.0
        for poly in polys:
            ring = poly[0]
            for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
                c = x0 * y1 - x1 * y0
                at += c
                ax += (x0 + x1) * c
                ay += (y0 + y1) * c
        out[f["properties"]["name"]] = (ax / (3 * at), ay / (3 * at))
    return out


def nasa() -> list[dict]:
    out = RAW / "nasa"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (lon, lat) in sorted(centroids().items()):
        f = out / f"power_{name}.json"
        if not f.exists():
            url = NASA.format(lon=lon, lat=lat)
            for attempt in range(4):
                try:
                    f.write_bytes(_get(url, timeout=120))
                    break
                except Exception as e:                       # noqa: BLE001 - retry transient API errors
                    print("retry", name, e)
                    time.sleep(5 * (attempt + 1))
            time.sleep(1)
        rows.append({"file": f"nasa/{f.name}", "source_url": NASA.format(lon=lon, lat=lat), "retrieved": date.today().isoformat(),
                     "sha256": _sha(f), "description": f"NASA POWER monthly PRECTOTCORR at the {name} centroid"})
    _manifest(rows)
    return rows


def ibtracs() -> list[dict]:
    out = RAW / "ibtracs"
    out.mkdir(parents=True, exist_ok=True)
    f = out / "ibtracs.WP.list.v04r01.csv"
    f.write_bytes(_get(IBTRACS, timeout=900))
    rows = [{"file": f"ibtracs/{f.name}", "source_url": IBTRACS, "retrieved": date.today().isoformat(), "sha256": _sha(f),
             "description": "NOAA IBTrACS v04r01 Western Pacific best tracks"}]
    _manifest(rows)
    return rows


if __name__ == "__main__":
    {"psa": psa, "nasa": nasa, "ibtracs": ibtracs}[sys.argv[1]]()
