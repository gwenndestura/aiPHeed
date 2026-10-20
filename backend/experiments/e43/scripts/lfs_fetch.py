"""E43 unemployment: PSA OpenStat LFS DB/1B/LFS/0021B3FKEI2.px (national, monthly), 2021-2026, NO fill.

Writes backend/experiments/e43/data/unemployment_monthly.csv (every month PSA returns a value for, observed = 1) and
unemployment_quarterly.{csv,parquet}: per quarter the mean of the released months (observed = 1 only when all three
months are released) plus the survey-round month (Jan/Apr/Jul/Oct) value the served pipeline used. Compares with
data/processed/psa_indicators.parquet (read only).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "experiments" / "e43" / "data"
API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
TABLE = "DB/1B/LFS/0021B3FKEI2.px"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E43 data refresh)"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]


def main():
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = requests.get(f"{API}/{TABLE}", headers=H, timeout=90).json()
    var = {v["code"]: v for v in meta["variables"]}

    def code(vcode, text):
        v = var[vcode]
        return v["values"][v["valueTexts"].index(text)]

    years = [y for y in var["Year"]["valueTexts"] if "2021" <= y <= "2026"]
    query = {"query": [
        {"code": "Year", "selection": {"filter": "item", "values": [code("Year", y) for y in years]}},
        {"code": "Month", "selection": {"filter": "item", "values": [code("Month", m) for m in MONTHS]}},
        {"code": "Rates", "selection": {"filter": "item", "values": [code("Rates", "Unemployment Rate")]}},
        {"code": "Sex", "selection": {"filter": "item", "values": [code("Sex", "Both sexes")]}}],
        "response": {"format": "json"}}
    r = requests.post(f"{API}/{TABLE}", headers=H, json=query, timeout=120)
    r.raise_for_status()
    js = json.loads(r.content.decode("utf-8-sig"))
    cols = [c["code"] for c in js["columns"]]
    rows = []
    for d in js["data"]:
        key = dict(zip([c for c in cols if c not in ("Unemployment Rate",)], d["key"]))
        val = d["values"][0]
        year = var["Year"]["valueTexts"][var["Year"]["values"].index(key["Year"])]
        month = var["Month"]["valueTexts"][var["Month"]["values"].index(key["Month"])]
        try:
            v = float(val)
        except ValueError:                      # PSA marks unreleased months with "..", "-", etc.
            continue
        m = MONTHS.index(month) + 1
        rows.append({"year": int(year), "month": m, "quarter": f"{year}-Q{(m - 1) // 3 + 1}", "value": v})
    mo = pd.DataFrame(rows).sort_values(["year", "month"])
    src = f"https://openstat.psa.gov.ph/PXWeb/pxweb/en/DB/DB__1B__LFS/0021B3FKEI2.px/ (API {API}/{TABLE})"
    mo = mo.assign(variable="unemployment_rate", level="national", source_url=src, release_date=None,
                   table_last_updated=None, fetched_at=fetched_at, observed=1)
    OUT.mkdir(parents=True, exist_ok=True)
    mo.to_csv(OUT / "unemployment_monthly.csv", index=False)
    print(f"monthly values released: {len(mo)}  ({mo['year'].min()}-{mo['month'].iloc[0]:02d} .. "
          f"{mo['year'].iloc[-1]}-{mo['month'].iloc[-1]:02d})")
    missing = [f"{y}-{m:02d}" for y in range(2021, 2027) for m in range(1, 13)
               if not ((mo["year"] == y) & (mo["month"] == m)).any() and (y < 2026 or m <= 9)]
    print("months 2021-01..2026-09 with no released value:", missing)

    q = mo.groupby("quarter").agg(value=("value", "mean"), months_released=("month", "count"),
                                  round_month_value=("value", lambda s: None)).reset_index()
    rm = mo[mo["month"].isin([1, 4, 7, 10])].set_index("quarter")["value"]
    q["round_month_value"] = q["quarter"].map(rm)
    q["observed"] = (q["months_released"] == 3).astype(int)
    q = q.assign(variable="unemployment_rate", level="national", source_url=src, release_date=None,
                 fetched_at=fetched_at,
                 note="value = mean of the released months of the quarter; observed=1 only if all 3 months are "
                      "released; round_month_value = Jan/Apr/Jul/Oct (the month the served pipeline used)")
    q.to_csv(OUT / "unemployment_quarterly.csv", index=False)
    q.to_parquet(OUT / "unemployment_quarterly.parquet", index=False)
    print(q[["quarter", "value", "months_released", "round_month_value", "observed"]].tail(8).to_string(index=False))

    p = pd.read_parquet(ROOT / "data" / "processed" / "psa_indicators.parquet")
    served = p.groupby("quarter")["unemployment_rate"].first()
    cmp = q.set_index("quarter")[["round_month_value", "value", "months_released"]].join(served.rename("served"), how="outer")
    cmp = cmp.loc[[x for x in cmp.index if "2021-Q1" <= x <= "2026-Q4"]]
    cmp["served_matches_round_month"] = (cmp["served"] - cmp["round_month_value"]).abs() < 0.01
    cmp.to_csv(OUT / "unemployment_served_vs_psa.csv")
    print("\nserved psa_indicators vs PSA release (2025-2026):")
    print(cmp.loc[[x for x in cmp.index if x >= "2025-Q1"]].to_string())
    print("quarters 2021-2026 where served != PSA round month:",
          [x for x, ok in cmp["served_matches_round_month"].items() if not ok])


if __name__ == "__main__":
    main()
