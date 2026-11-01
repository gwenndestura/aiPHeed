"""Y14: point-in-time FIRI-analog indicators at every Lead-2 issue date O(t) = first day of quarter t+1.
No outcome is read here. Writes out/indicators.csv (one row per origin) and out/indicator_coverage.json.

Indicator mapping (FIRI v2 key -> analog used for 1998+; see DATA_AUDIT.md for the observation/proxy status):
  A2  headline inflation, Region IV-A all-items CPI YoY, mean of m0-2..m0          (FIRI: province headline vs P60)
  A3  rice price change, Region IV-A retail rice CPI YoY at m0                    (FIRI: wholesale rice YoY) PROXY
  C1  El Nino in force: ONI of the season ending m0-1 >= 0.5                       (FIRI: PAGASA alert flag) PROXY
  C2  tropical cyclones in PAR, quarter t-1                                        (FIRI: within 300 km)      PROXY
  C3  production drop: -min(palay YoY, corn YoY), Region IV-A, quarter t-1
  C4  fisheries drop: -fisheries volume YoY, Region IV-A, quarter t-1             (driver label "Fish Kill":
                                                                                    production proxy, not fish-kill incidents)
  E1  unemployment change, national, newest LFS round <= m0-2, YoY difference
  E2  remittance decline: UNAVAILABLE (BSP download refused, HTTP 403) -> missing in every row
  H1  regional hunger outlook: RW probability that BL hunger > 11.3 at t+2 (rlib.forecast, four-area pooled sigma)
  V1  static vulnerability: constant (regional mean of the served V1), does not vary in time
  A1, N1: unavailable before 2021 (price model; news FSSI) -> missing

    python -B indicators.py
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).resolve().parent
Y14 = HERE.parent
RES = Y14.parent
ACQ, OUT = Y14 / "data_acquired", Y14 / "out"
sys.path.insert(0, str(RES / "common"))
import p2lib as P  # noqa: E402
import cov  # noqa: E402

R = P.R
T_FIRST, T_LAST = R.qi("1997-Q1"), R.qi("2026-Q2")


def _wide_quarters(name: str, ids: list[str]) -> pd.DataFrame:
    d = pd.read_csv(ACQ / f"{name}.csv", encoding="latin-1", dtype=str)
    rows = []
    for c in d.columns:
        m = re.match(r"^(\d{4}) Quarter (\d)$", c)
        if not m:
            continue
        q = int(m.group(1)) * 4 + int(m.group(2)) - 1
        for _, r in d.iterrows():
            rows.append({**{k: r[k].strip(". ") for k in ids}, "q": q, "v": pd.to_numeric(r[c], errors="coerce")})
    return pd.DataFrame(rows)


def series():
    f = _wide_quarters("fisheries_volume_subsector", ["Geolocation", "Subsector"])
    fish = f[f["Geolocation"].str.contains("IV-A") & (f["Subsector"] == "FISHERIES")].set_index("q")["v"]
    p = _wide_quarters("palay_corn_production", ["Ecosystem/Croptype", "Geolocation"])
    p = p[p["Geolocation"].str.contains("IV-A")]
    palay = p[p["Ecosystem/Croptype"] == "Palay"].set_index("q")["v"]
    corn = p[p["Ecosystem/Croptype"].str.endswith("Corn")].groupby("q")["v"].sum(min_count=2)
    c = pd.read_csv(R.LONG / "cov_cpi.csv")
    c = c[c["geolocation"].str.startswith("Region IV-A") & c["yoy"].notna()]
    allit = c[c["commodity_description"] == "0 - ALL ITEMS"].set_index("ym")["yoy"]
    rice = c[c["commodity_description"] == "01.1.1.12 - Rice"].set_index("ym")["yoy"]
    return fish, palay, corn, allit, rice


def yoy(s: pd.Series, q: int) -> float:
    if q in s.index and q - 4 in s.index and s[q - 4] and pd.notna(s[q]) and pd.notna(s[q - 4]) and s[q - 4] > 0:
        return float(100 * (s[q] / s[q - 4] - 1))
    return np.nan


def v_constant() -> float:
    """Regional mean of the served V1 (0.6 poverty_norm + 0.4 density_norm, min-max over the 5 provinces)."""
    v = pd.read_csv(R.ROOT / "backend" / "data" / "inputs" / "lgu_vulnerability.csv")
    g = v.groupby("province").agg(pov=("poverty_lgu_estimate", "mean"), pop=("population_2024", "sum"), area=("land_area_km2", "sum"))
    g["den"] = g["pop"] / g["area"]
    mm = lambda s: (s - s.min()) / (s.max() - s.min())  # noqa: E731
    return float((0.6 * mm(g["pov"]) + 0.4 * mm(g["den"])).mean())


def build() -> pd.DataFrame:
    fish, palay, corn, allit, rice = series()
    vc = v_constant()
    rows = []
    for t in range(T_FIRST, T_LAST + 1):
        m = R.m0(t)
        cf = dict(zip(cov.FEATS, cov.feats(t)))
        a2 = float(np.mean([allit[x] for x in (m - 2, m - 1, m)])) if all(x in allit.index for x in (m - 2, m - 1, m)) else np.nan
        crops = [x for x in (yoy(palay, t - 1), yoy(corn, t - 1)) if pd.notna(x)]
        f = R.forecast("BL", t, 2, tuple(R.AREAS))
        rows.append({"t": t, "origin": R.qs(t), "issue": str(R.issue(t).date()), "target": R.qs(t + 2),
                     "A2": a2, "A3": float(rice[m]) if m in rice.index else np.nan,
                     "C1": float(cf["oni_last"] >= 0.5) if pd.notna(cf["oni_last"]) else np.nan,
                     "C2": cf["tc_prev"], "C3": -min(crops) if crops else np.nan,
                     "C4": -yoy(fish, t - 1) if pd.notna(yoy(fish, t - 1)) else np.nan,
                     "E1": cf["unemp_chg"], "E2": np.nan,
                     "H1": f["RW"] if f else np.nan, "H_last": f["x_last"] if f else np.nan,
                     "h_true": f["h"] if f else np.nan, "V1": vc})
    return pd.DataFrame(rows)


def main():
    d = build()
    OUT.mkdir(exist_ok=True)
    d.to_csv(OUT / "indicators.csv", index=False, lineterminator="\n", float_format="%.5f")
    cov_ = {k: {"first": d.loc[d[k].first_valid_index(), "origin"] if d[k].notna().any() else None,
                "nonMissing": int(d[k].notna().sum()), "of": len(d)} for k in ("A2", "A3", "C1", "C2", "C3", "C4", "E1", "E2", "H1")}
    (OUT / "indicator_coverage.json").write_text(json.dumps(cov_, indent=1), encoding="utf-8")
    print(json.dumps(cov_))
    print(d.tail(3).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
