"""C2 audit: recompute "distinct storms passing within 300 km of the province centroid" per province-quarter from the
NOAA IBTrACS v04r01 Western Pacific file downloaded 2026-10-25 (E114 raw), and compare with the held counts
(pagasa_climate.parquet, fetched 2026-09-09). Province centroids come from the dashboard's own province boundaries
(frontend/public/ph-provinces.json), area-weighted.

    python typhoons.py     # out/typhoons_recomputed.csv, out/typhoons_compare.json
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AUD = HERE.parent
EXP = AUD.parent
ROOT = EXP.parents[1]
OUT = AUD / "out"
IBTRACS = EXP / "E114_Final_Run" / "data" / "raw" / "ibtracs.WP.list.v04r01.csv"
PROVS = {"Cavite": "PH040100000", "Laguna": "PH040200000", "Quezon": "PH040300000", "Rizal": "PH040400000",
         "Batangas": "PH040500000"}
RADIUS_KM = 300.0


def _ring_centroid(ring):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    return (a / 2, cx / (3 * a) if a else 0.0, cy / (3 * a) if a else 0.0)


def centroids() -> dict:
    g = json.loads((ROOT / "frontend" / "public" / "ph-provinces.json").read_text(encoding="utf-8"))
    out = {}
    for f in g["features"]:
        props = f["properties"]
        name = next((v for v in props.values() if isinstance(v, str) and v.strip() in PROVS), None)
        if name is None:
            continue
        geom = f["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        acc = [_ring_centroid([tuple(p[:2]) for p in poly[0]]) for poly in polys]
        A = sum(abs(a) for a, _, _ in acc)
        out[name.strip()] = (sum(abs(a) * y for a, _, y in acc) / A, sum(abs(a) * x for a, x, _ in acc) / A)
    return out


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def main():
    cen = centroids()
    assert set(cen) == set(PROVS), cen
    d = pd.read_csv(IBTRACS, skiprows=[1], usecols=["SID", "NAME", "ISO_TIME", "LAT", "LON", "WMO_WIND"],
                    low_memory=False)
    d["ISO_TIME"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    d = d[d["ISO_TIME"] >= "2021-01-01"].copy()
    d["LAT"], d["LON"] = pd.to_numeric(d["LAT"], errors="coerce"), pd.to_numeric(d["LON"], errors="coerce")
    d["quarter"] = d["ISO_TIME"].dt.year.astype(str) + "-Q" + ((d["ISO_TIME"].dt.month - 1) // 3 + 1).astype(str)
    rows, near_storms = [], {}
    for name, (lat, lon) in cen.items():
        dist = haversine(lat, lon, d["LAT"].to_numpy(), d["LON"].to_numpy())
        near = d[dist <= RADIUS_KM]
        near_storms[name] = near.groupby("quarter")["SID"].apply(lambda s: sorted(set(s))).to_dict()
        cnt = near.groupby("quarter")["SID"].nunique()
        for q in [f"{y}-Q{k}" for y in range(2021, 2027) for k in range(1, 5) if f"{y}-Q{k}" <= "2026-Q3"]:
            rows.append({"province": name, "province_code": PROVS[name], "quarter": q,
                         "tc_count_recomputed": int(cnt.get(q, 0))})
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "typhoons_recomputed.csv", index=False)
    h = pd.read_parquet(EXP / "E107_Twelve_Indicator_LightGBM" / "data_inputs" / "pagasa_climate.parquet")
    j = h[["province_name", "quarter", "tc_count"]].rename(columns={"province_name": "province"}).merge(
        R, on=["province", "quarter"], how="left")
    diff = j[j["tc_count"] != j["tc_count_recomputed"]]
    res = {"ibtracs_file": str(IBTRACS.relative_to(ROOT)), "ibtracs_last_fix": str(d["ISO_TIME"].max()),
           "centroids_lat_lon": cen, "compared": int(len(j)), "equal": int((j["tc_count"] == j["tc_count_recomputed"]).sum()),
           "differing": diff.to_dict("records"),
           "storms_2026Q3": {p: s.get("2026-Q3", []) for p, s in near_storms.items()}}
    (OUT / "typhoons_compare.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({k: v for k, v in res.items() if k != "differing"}, default=str)[:900])
    print("differing rows:", len(diff)); print(diff.to_string(index=False)[:2000])


if __name__ == "__main__":
    main()
