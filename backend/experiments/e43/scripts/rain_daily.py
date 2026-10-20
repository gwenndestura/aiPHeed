"""E43 rainfall, ONE service end to end: NASA POWER DAILY PRECTOTCORR, 1991-01-01 to the latest day available, at the
same 30 interior points (data/reference/calabarzon_rainfall_points.csv, read only) as the served monthly series.

Method = the served build's, with the daily endpoint: day -> point-month mean (mm/day) -> province-month mean over the
6 points -> 1991-2020 normal per province and calendar month -> monthly anomaly % -> quarter = mean of its 3 monthly
anomalies. A quarter is written only when every month in it is complete (all days of all 6 points present);
observed = 1 for those. Writes backend/experiments/e43/data/rainfall_daily_province.{parquet,csv} and prints the
2021-2025 comparison with data/processed/province_rainfall.parquet (monthly service; read only).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]                      # backend/
OUT = ROOT / "experiments" / "e43" / "data"
POINTS = ROOT / "data" / "reference" / "calabarzon_rainfall_points.csv"
SERVED = ROOT / "data" / "processed" / "province_rainfall.parquet"
URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAM = "PRECTOTCORR"
START, END = "19910101", datetime.now(timezone.utc).strftime("%Y%m%d")


def fetch(lon: float, lat: float) -> pd.Series:
    params = dict(parameters=PARAM, community="AG", longitude=lon, latitude=lat, start=START, end=END, format="JSON")
    for attempt in range(5):
        try:
            r = requests.get(URL, params=params, timeout=300)
            if r.status_code == 200:
                s = pd.Series(r.json()["properties"]["parameter"][PARAM], dtype="float64")
                s.index = pd.to_datetime(s.index, format="%Y%m%d")
                return s[s > -900]                              # -999 = POWER null
            print(f"  HTTP {r.status_code} for ({lon},{lat}); retry")
        except requests.RequestException as e:
            print(f"  {type(e).__name__} for ({lon},{lat}); retry")
        time.sleep(5 * (attempt + 1))
    raise SystemExit(f"POWER unreachable for ({lon},{lat}); nothing written")


def main():
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pts = pd.read_csv(POINTS, dtype={"province_code": str})
    rows = []
    for i, p in enumerate(pts.itertuples(index=False), 1):
        s = fetch(p.lon, p.lat)
        print(f"[{i}/{len(pts)}] {p.province_name} ({p.lon},{p.lat}) {s.index.min().date()}..{s.index.max().date()} {len(s)} days")
        d = s.to_frame("mm").assign(year=s.index.year, month=s.index.month)
        g = d.groupby(["year", "month"])["mm"].agg(["mean", "count"]).reset_index()
        g["days_in_month"] = pd.to_datetime(dict(year=g["year"], month=g["month"], day=1)).dt.days_in_month
        g = g.assign(province_code=p.province_code, province_name=p.province_name, lon=p.lon, lat=p.lat)
        rows.append(g)
        time.sleep(1.0)
    pm_pt = pd.concat(rows, ignore_index=True)
    pm_pt["complete"] = pm_pt["count"] == pm_pt["days_in_month"]
    pm = (pm_pt.groupby(["province_code", "province_name", "year", "month"])
          .agg(precip_mm_day=("mean", "mean"), points=("lon", "count"), complete=("complete", "all")).reset_index())
    pm["complete"] &= pm["points"] == 6
    base = (pm[pm["year"].between(1991, 2020) & pm["complete"]]
            .groupby(["province_code", "month"])["precip_mm_day"].mean().rename("normal_mm_day").reset_index())
    pm = pm.merge(base, on=["province_code", "month"], how="left")
    pm["anomaly_pct"] = 100 * (pm["precip_mm_day"] - pm["normal_mm_day"]) / pm["normal_mm_day"]
    pm["quarter"] = pm["year"].astype(str) + "-Q" + ((pm["month"] - 1) // 3 + 1).astype(str)
    q = (pm.groupby(["province_code", "province_name", "quarter"])
         .agg(precip_mm_day=("precip_mm_day", "mean"), normal_mm_day=("normal_mm_day", "mean"),
              value=("anomaly_pct", "mean"), n_months=("month", "count"), complete=("complete", "all")).reset_index())
    partial = q[~((q["n_months"] == 3) & q["complete"])]
    q = q[(q["n_months"] == 3) & q["complete"]].copy()
    q["value"] = q["value"].round(2)
    q = q.assign(variable="rainfall_anomaly_pct", level="province", source_url=URL + f"?parameters={PARAM}&community=AG",
                 release_date=None, fetched_at=fetched_at, observed=1,
                 note="NASA POWER daily PRECTOTCORR (MERRA-2 based; near real time, no formal release date); "
                      "6 interior points per province; anomaly vs 1991-2020 normal built from the same daily service")
    cols = ["province_code", "province_name", "quarter", "variable", "value", "precip_mm_day", "normal_mm_day",
            "level", "source_url", "release_date", "fetched_at", "observed", "note"]
    q = q[cols].sort_values(["province_code", "quarter"])
    OUT.mkdir(parents=True, exist_ok=True)
    q.to_parquet(OUT / "rainfall_daily_province.parquet", index=False)
    q.to_csv(OUT / "rainfall_daily_province.csv", index=False)
    print("written", len(q), "province-quarters,", q["quarter"].min(), "..", q["quarter"].max(),
          "| partial quarters not written:", sorted(partial["quarter"].unique())[-3:])

    # comparison with the served monthly-service anomaly, 2021-2025
    m = pd.read_parquet(SERVED)
    m["quarter"] = m["year"].astype(int).astype(str) + "-Q" + m["quarter"].astype(int).astype(str) \
        if not m["quarter"].astype(str).str.contains("Q").all() else m["quarter"].astype(str)
    m = m[m["source_url"].str.contains("/monthly/")][["province_code", "quarter", "rainfall_anomaly_pct"]]
    j = q.merge(m, on=["province_code", "quarter"])
    j = j[j["quarter"].between("2021-Q1", "2025-Q4")]
    print("\ncomparison 2021-2025 (daily-service anomaly vs served monthly-service anomaly, percentage points):")
    out = []
    for code, g in j.groupby("province_code"):
        mad = float((g["value"] - g["rainfall_anomaly_pct"]).abs().mean())
        r = float(np.corrcoef(g["value"], g["rainfall_anomaly_pct"])[0, 1])
        out.append({"province_code": code, "province": g["province_name"].iloc[0], "quarters": len(g),
                    "mean_abs_diff_pp": round(mad, 2), "max_abs_diff_pp": round(float((g["value"] - g["rainfall_anomaly_pct"]).abs().max()), 2),
                    "correlation": round(r, 4), "mean_daily": round(float(g["value"].mean()), 2),
                    "mean_monthly": round(float(g["rainfall_anomaly_pct"].mean()), 2)})
    cmp = pd.DataFrame(out)
    print(cmp.to_string(index=False))
    cmp.to_csv(OUT / "rainfall_daily_vs_monthly_2021_2025.csv", index=False)


if __name__ == "__main__":
    main()
