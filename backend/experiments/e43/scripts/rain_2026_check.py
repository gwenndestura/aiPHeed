"""Read-only: the served 2026 rainfall (daily service, fetched 2026-09-04) vs the E43 rebuild (daily service, fetched
2026-10-15) for 2026-Q1/Q2: precipitation, normal and anomaly side by side."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
s = pd.read_parquet(ROOT / "data" / "processed" / "province_rainfall.parquet")
s["quarter"] = s["year"].astype(int).astype(str) + "-Q" + s["quarter"].astype(int).astype(str) \
    if not s["quarter"].astype(str).str.contains("Q").all() else s["quarter"].astype(str)
s = s[s["quarter"] >= "2026-Q1"][["province_code", "quarter", "precip_mm_day", "normal_mm_day", "rainfall_anomaly_pct",
                                  "n_months", "fetched_at"]]
n = pd.read_parquet(ROOT / "experiments" / "e43" / "data" / "rainfall_daily_province.parquet")
n = n[n["quarter"].isin(["2026-Q1", "2026-Q2"])][["province_code", "province_name", "quarter", "precip_mm_day",
                                                 "normal_mm_day", "value"]]
j = n.merge(s, on=["province_code", "quarter"], suffixes=("_new", "_served"))
j["precip_diff"] = j["precip_mm_day_new"] - j["precip_mm_day_served"]
j["anom_diff_pp"] = j["value"] - j["rainfall_anomaly_pct"]
pd.set_option("display.width", 200)
print(j[["province_name", "quarter", "precip_mm_day_served", "precip_mm_day_new", "precip_diff", "normal_mm_day_served",
         "normal_mm_day_new", "rainfall_anomaly_pct", "value", "anom_diff_pp", "n_months"]].round(3).to_string(index=False))
