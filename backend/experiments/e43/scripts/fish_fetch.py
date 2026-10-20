"""E43 fisheries: PSA OpenStat DB/2E/FS/0132E4GVFP1.px (volume by geolocation, subsector, quarter), 2021-2026, for
Region IV-A and its five provinces. Records which quarters are released (2026-Q3?), the table's last-update stamp
(the only release-timing field the API exposes), and compares with data/processed/food_availability_panel.parquet
(read only). Writes backend/experiments/e43/data/fisheries_production.{csv,parquet}."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "experiments" / "e43" / "data"
API = "https://openstat.psa.gov.ph/PXWeb/api/v1/en"
TABLE = "DB/2E/FS/0132E4GVFP1.px"
H = {"User-Agent": "Mozilla/5.0 (aiPHeed research; E43 data refresh)"}
GEO = {"Region IV-A": "REGION", "Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000",
       "Quezon": "PH040300000", "Rizal": "PH040400000"}


def main():
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    folder = requests.get(f"{API}/DB/2E/FS", headers=H, timeout=90).json()
    updated = next(x["updated"] for x in folder if x["id"] == "0132E4GVFP1.px")
    meta = requests.get(f"{API}/{TABLE}", headers=H, timeout=90).json()
    var = {v["code"]: v for v in meta["variables"]}
    geo_vals = {}
    for val, txt in zip(var["Geolocation"]["values"], var["Geolocation"]["valueTexts"]):
        name = txt.strip(".").strip()
        for k in GEO:
            if name == k or (k == "Region IV-A" and ("IV-A" in name or "CALABARZON" in name.upper())):
                geo_vals[val] = k
    years = [(v, t) for v, t in zip(var["Year"]["values"], var["Year"]["valueTexts"]) if "2020" <= t <= "2026"]
    quarters = [(v, t) for v, t in zip(var["Quarter"]["values"], var["Quarter"]["valueTexts"]) if t != "Annual"]
    query = {"query": [
        {"code": "Geolocation", "selection": {"filter": "item", "values": list(geo_vals)}},
        {"code": "Subsector", "selection": {"filter": "item", "values": var["Subsector"]["values"]}},
        {"code": "Year", "selection": {"filter": "item", "values": [v for v, _ in years]}},
        {"code": "Quarter", "selection": {"filter": "item", "values": [v for v, _ in quarters]}}],
        "response": {"format": "json"}}
    r = requests.post(f"{API}/{TABLE}", headers=H, json=query, timeout=180)
    r.raise_for_status()
    js = json.loads(r.content.decode("utf-8-sig"))
    ytxt = dict(years)
    qtxt = dict(quarters)
    stxt = dict(zip(var["Subsector"]["values"], var["Subsector"]["valueTexts"]))
    rows = []
    for d in js["data"]:
        g, s, y, q = d["key"]
        raw = d["values"][0]
        try:
            v = float(raw)
        except ValueError:
            v = None
        rows.append({"geo": geo_vals[g], "province_code": GEO[geo_vals[g]], "subsector": stxt[s].strip(".").strip(),
                     "quarter": f"{ytxt[y]}-Q{qtxt[q].split()[-1]}", "value": v, "raw": raw})
    df = pd.DataFrame(rows)
    df = df.assign(variable="fisheries_volume_mt", level=df["geo"].map(lambda x: "regional" if x == "Region IV-A" else "province"),
                   source_url=f"{API}/{TABLE}", release_date=None, table_last_updated=updated, fetched_at=fetched_at,
                   observed=df["value"].notna().astype(int))
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "fisheries_production.csv", index=False)
    df.drop(columns=["raw"]).to_parquet(OUT / "fisheries_production.parquet", index=False)
    tot = df[df["subsector"] == "FISHERIES"]
    released = tot[tot["observed"] == 1].groupby("quarter")["geo"].count()
    print("table last updated (OpenStat):", updated)
    print("quarters with released totals, 2025-2026:", {q: n for q, n in released.items() if q >= "2025-Q1"})
    print("raw cells for 2026-Q3/Q4:", sorted(set(df[df["quarter"] >= "2026-Q3"]["raw"])))

    served = pd.read_parquet(ROOT / "data" / "processed" / "food_availability_panel.parquet")
    served = served[served["group"] == "fisheries"].groupby(["province_code", "quarter"])["volume"].sum()
    mine = tot[tot["province_code"] != "REGION"].set_index(["province_code", "quarter"])["value"]
    j = pd.concat([served.rename("served"), mine.rename("psa_now")], axis=1).dropna()
    j = j[j.index.get_level_values(1) >= "2021-Q1"]
    j["abs_diff"] = (j["served"] - j["psa_now"]).abs()
    print(f"\nserved total vs PSA now: {len(j)} province-quarters, max abs diff {j['abs_diff'].max():.2f} t, "
          f"cells differing by > 0.5 t: {int((j['abs_diff'] > 0.5).sum())}")
    print(j[j["abs_diff"] > 0.5].head(12).to_string())


if __name__ == "__main__":
    main()
