"""Historical government data: raw copies, cleaning and release-date (vintage) rules.

`acquire()` copies every raw public file FI5 uses into data/fi5/raw (from the repository's earlier acquisition
folders, or from the public APIs) and writes MANIFEST.csv with origin, sha256 and fetch notes. `series()` turns the
raw files into clean series, each row carrying the reference period, the value and the date from which the value
could have been known (available_from). The feature builder only ever sees rows with available_from <= issue date.

Release rules are conservative (never earlier than the agency's usual release):

    SWS hunger            the round's published date (2021+: dated releases; pre-2021: label month end + 60 days)
    PSA CPI (monthly)     10th day of the following month
    PSA palay production  45 days after the quarter ends
    PSA LFS               45 days after the survey month
    NASA POWER (monthly)  30 days after the month ends
    IBTrACS storm tracks  observation time (storms are tracked in real time by PAGASA/JTWC)
    NOAA ONI              10 days after the 3-month season ends
    GDELT DOC volume      the day itself
    BSP/WB remittances    15 February of the following year (BSP full-year release)
    PSA poverty           2 January two years after the reference year, except 2023 (2024-08-15) and
                          2025 (2026-08-24), whose release dates are documented
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from app.fi5.paths import BACKEND_DIR, RAW

REPO = BACKEND_DIR.parent
EXP = REPO / "aipheed-backend-aligned" / "experiments"

# (destination in data/fi5/raw, origin relative to the repository root, note)
COPIES = [
    ("sws/sws_area_rounds_full.csv", "aipheed-backend-aligned/experiments/E114_Final_Run/data/sws_area_rounds_full.csv",
     "SWS hunger by area, 1998-Q3..2026-Q3, with published dates (E114 extraction from SWS releases)"),
    ("psa/cpi_monthly_region_iva_1994_2026.csv", "aipheed-backend-aligned/experiments/E114_Final_Run/data/cov_cpi.csv",
     "PSA OpenSTAT CPI (2018=100 linked to 2012=100 history), PH and Region IV-A, all items / food / rice"),
    ("psa/prod_palay_corn_quarterly.csv", "aipheed-backend-aligned/experiments/E118_FAO_Data_Discovery/data/clean/prod_palay_corn.csv",
     "PSA OpenSTAT 2E4EVCP0 palay and corn production, Region IV-A and provinces, quarterly 1987+"),
    ("psa/lfs_unemployment_rate_national.csv", "aipheed-backend-aligned/experiments/E127_FIRI3_Amendment_3_Implementation/data/raw/psa_lfs_0021B3FKEI2_rates.csv",
     "PSA OpenSTAT 0021B3FKEI2 LFS unemployment rate, Philippines, 2005+ (2005 definition)"),
    ("nasa/nasa_power_monthly_1981_2025.csv", "aipheed-backend-aligned/experiments/E118_FAO_Data_Discovery/data/clean/nasa_power_monthly.csv",
     "NASA POWER monthly point data at the five province centroids, 1981-2025"),
    *[(f"nasa/nasa_power_monthly_2021_2026_{p}.json",
       f"aipheed-backend-aligned/experiments/E125_FIRI3_Pre_Issuance/data/raw/nasa_power_monthly_2021_2026_{p}.json",
       "NASA POWER monthly refresh (fetched 2026-10-31)") for p in ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]],
    ("noaa/noaa_oni.txt", "aipheed-backend-aligned/experiments/E114_Final_Run/data/raw/noaa_oni.txt", "NOAA CPC Oceanic Nino Index"),
    *[(f"gdelt/gdelt_doc_{c}.csv", f"aipheed-backend-aligned/experiments/E114_Final_Run/data/raw/gdelt_doc_{c}.csv",
       "GDELT DOC 2.0 timelinevol, sourcecountry:philippines, daily 2017-01..2026-10") for c in
      ["shortage", "agri_supply", "jobs_income", "assistance"]],
    ("psa/poverty_2021_2023_2025.csv", "aipheed-backend-aligned/experiments/E131_Objectives_Resolution/data/raw/psa_poverty_population_2021_2023_2025.csv",
     "PSA official poverty incidence among population 2021/2023/2025 (2025 FY workbook released 2026-08-24)"),
]
IBTRACS = [EXP / "E114_Final_Run/data/raw/ibtracs.WP.list.v04r01.csv",
           EXP / "E125_FIRI3_Pre_Issuance/data/raw/ibtracs.last3years.list.v04r01.csv"]
CENTROIDS = {"Cavite": (14.28, 120.87), "Laguna": (14.17, 121.33), "Batangas": (13.76, 121.06),
             "Rizal": (14.60, 121.31), "Quezon": (14.03, 122.11)}
TC_RADIUS_KM = 200.0


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _haversine(lat1, lon1, lat2, lon2):
    r = np.pi / 180
    a = np.sin((lat2 - lat1) * r / 2) ** 2 + np.cos(lat1 * r) * np.cos(lat2 * r) * np.sin((lon2 - lon1) * r / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def acquire() -> pd.DataFrame:
    """Copy raw inputs into data/fi5/raw and write MANIFEST.csv (idempotent)."""
    rows = []
    for dest, origin, note in COPIES:
        src, dst = REPO / origin, RAW / dest
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists() and (not dst.exists() or _sha(src) != _sha(dst)):
            shutil.copyfile(src, dst)
        if dst.exists():
            rows.append({"file": dest, "origin": origin, "sha256": _sha(dst), "note": note})
    # IBTrACS: keep only fixes within 600 km of the region (the full files are >100 MB and stay outside the repo).
    dst = RAW / "ibtracs/ibtracs_calabarzon_600km.csv"
    if any(p.exists() for p in IBTRACS):
        parts = []
        for p in IBTRACS:
            if not p.exists():
                continue
            d = pd.read_csv(p, skiprows=[1], usecols=["SID", "SEASON", "BASIN", "NAME", "ISO_TIME", "LAT", "LON", "USA_WIND", "WMO_WIND"],
                            low_memory=False, keep_default_na=False)
            d = d[d["BASIN"].astype(str).str.strip() == "WP"].copy()
            d["LAT"], d["LON"] = pd.to_numeric(d["LAT"], errors="coerce"), pd.to_numeric(d["LON"], errors="coerce")
            dist = _haversine(d["LAT"].to_numpy(), d["LON"].to_numpy(), 14.1, 121.5)
            parts.append(d[dist <= 600].assign(origin=p.name))
        tc = pd.concat(parts).drop_duplicates(["SID", "ISO_TIME"]).sort_values(["ISO_TIME", "SID"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        tc.to_csv(dst, index=False, lineterminator="\n")
    if dst.exists():
        rows.append({"file": "ibtracs/ibtracs_calabarzon_600km.csv", "origin": "; ".join(str(p.relative_to(REPO)) for p in IBTRACS),
                     "sha256": _sha(dst), "note": "NOAA NCEI IBTrACS v04r01 WP fixes within 600 km of CALABARZON"})
    for f, note in [("bsp/wdi_BX.TRF.PWKR.CD.DT_PHL.json", "World Bank WDI personal remittances received (BSP data), current USD, 1990-2025; api.worldbank.org, fetched 2026-11-02"),
                    ("psa/psa_poverty_2006_2015.csv", "PSA OpenSTAT DB/3D/0023C3DP020 poverty incidence among population 1991/2006-2015 (2009 methodology), fetched 2026-11-02"),
                    ("psa/psa_poverty_2018_2023.csv", "PSA OpenSTAT DB/1F/FY/0031F3DF020 poverty incidence among population 2018/2021/2023, fetched 2026-11-02")]:
        p = RAW / f
        if p.exists():
            rows.append({"file": f, "origin": "public API", "sha256": _sha(p), "note": note})
    man = pd.DataFrame(rows)
    man.to_csv(RAW / "MANIFEST.csv", index=False, lineterminator="\n")
    return man


# --------------------------------------------------------------------------------------------- series registry
@dataclass(frozen=True)
class SeriesInfo:
    key: str
    domain: str          # market | climate | employment | remittance | poverty | outcome
    kind: str            # government | news | outcome
    source: str
    geo_level: str
    definition: str
    release_rule: str
    first_period: str = ""


def _month_end(y, m):
    return pd.Timestamp(year=int(y), month=int(m), day=1) + pd.offsets.MonthEnd(0)


def _q_end(y, q):
    return pd.Timestamp(year=int(y), month=3 * int(q), day=1) + pd.offsets.MonthEnd(0)


def quarter_label(ts: pd.Timestamp) -> str:
    return f"{ts.year}-Q{(ts.month - 1) // 3 + 1}"


def sws_rounds() -> pd.DataFrame:
    d = pd.read_csv(RAW / "sws/sws_area_rounds_full.csv")
    d["published"] = pd.to_datetime(d["published"])
    return d


def cpi() -> pd.DataFrame:
    d = pd.read_csv(RAW / "psa/cpi_monthly_region_iva_1994_2026.csv").dropna(subset=["value"])
    d = d[d["geolocation"].str.contains("IV-A")]
    d["item"] = d["commodity_description"].map({"0 - ALL ITEMS": "all", "01.1 - FOOD": "food", "01.1.1.12 - Rice": "rice"})
    d["period_end"] = [_month_end(y, m) for y, m in zip(d["year"], d["month"])]
    w = d.pivot_table(index="period_end", columns="item", values="value").sort_index()
    out = pd.DataFrame(index=w.index)
    for it in ["all", "food", "rice"]:
        out[f"yoy_{it}"] = 100 * (w[it] / w[it].shift(12) - 1)
    out["available_from"] = out.index + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)
    return out.reset_index().rename(columns={"index": "period_end"})


def palay() -> pd.DataFrame:
    d = pd.read_csv(RAW / "psa/prod_palay_corn_quarterly.csv")
    d = d[(d["unit"] == "Region IV-A") & (d["item"] == "Palay") & (d["freq"] == "Q")].copy()
    d["year"], d["q"] = (d["period"] // 4).astype(int), (d["period"] % 4).astype(int) + 1
    d = d.sort_values("period")
    d["period_end"] = [_q_end(y, q) for y, q in zip(d["year"], d["q"])]
    d = d.set_index("period_end")
    out = pd.DataFrame({"yoy_palay": 100 * (d["value"] / d["value"].shift(4) - 1)})
    out["available_from"] = out.index + pd.Timedelta(days=45)
    return out.dropna().reset_index()


def _live(name: str):
    p = BACKEND_DIR / "data" / "e168" / "live_raw" / name
    return p if p.exists() else None


def _seen(source: str, period_end: pd.Timestamp, rule: pd.Timestamp) -> pd.Timestamp:
    from app.e168 import live_data as LD
    s = LD.effective_seen(source, f"{period_end.year}-{period_end.month:02d}" if source != "remittances" else str(period_end.year), period_end)
    return min(rule, s) if s is not None else rule


def lfs() -> pd.DataFrame:
    d = pd.read_csv(RAW / "psa/lfs_unemployment_rate_national.csv", dtype=str)
    months = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                              "August", "September", "October", "November", "December"])}
    d = d[d["Month"].isin(months)].copy()
    d["rate"] = pd.to_numeric(d["Unemployment Rate Both sexes"], errors="coerce")
    d = d.dropna(subset=["rate"])
    lv = _live("psa/lfs_unemployment_rate_national.csv")
    if lv is not None:                                    # months the archived file does not hold
        n = pd.read_csv(lv, dtype=str)
        n = n[n["Month"].isin(months)].copy()
        n["rate"] = pd.to_numeric(n["Unemployment Rate Both sexes"], errors="coerce")
        n = n.dropna(subset=["rate"])
        have = set(zip(d["Year"], d["Month"]))
        d = pd.concat([d, n[[(y, m) not in have for y, m in zip(n["Year"], n["Month"])]]], ignore_index=True)
    d["period_end"] = [_month_end(y, months[m]) for y, m in zip(d["Year"], d["Month"])]
    d = d.sort_values("period_end").set_index("period_end")
    # YoY: same survey month one year earlier (the pre-2021 rounds are Jan/Apr/Jul/Oct, so this always exists)
    prev = d["rate"].copy()
    prev.index = prev.index + pd.DateOffset(years=1)
    prev.index = prev.index + pd.offsets.MonthEnd(0)
    out = pd.DataFrame({"unemp_rate": d["rate"], "unemp_yoy": d["rate"] - prev.reindex(d.index)})
    out["available_from"] = [_seen("lfs", t, t + pd.Timedelta(days=45)) for t in out.index]
    return out.reset_index()


def nasa() -> pd.DataFrame:
    """CALABARZON mean of the five province centroids, monthly precipitation (mm/day) and max temperature."""
    d = pd.read_csv(RAW / "nasa/nasa_power_monthly_1981_2025.csv")
    d["year"], d["month"] = (d["period"] // 12).astype(int), (d["period"] % 12).astype(int) + 1
    d = d[d["item"].isin(["PRECTOTCORR", "T2M_MAX"])][["unit", "item", "year", "month", "value"]]
    extra = []
    for p in CENTROIDS:
        f = RAW / f"nasa/nasa_power_monthly_2021_2026_{p}.json"
        if not f.exists():
            continue
        par = json.loads(f.read_text())["properties"]["parameter"]
        for item in ["PRECTOTCORR", "T2M_MAX"]:
            for k, v in par.get(item, {}).items():
                y, m = int(k[:4]), int(k[4:])
                if m <= 12 and v is not None and v > -900:
                    extra.append({"unit": p, "item": item, "year": y, "month": m, "value": float(v)})
    if extra:
        e = pd.DataFrame(extra)
        d = pd.concat([d, e]).drop_duplicates(["unit", "item", "year", "month"], keep="last")
    w = d.groupby(["item", "year", "month"])["value"].mean().unstack("item").reset_index()
    w["period_end"] = [_month_end(y, m) for y, m in zip(w["year"], w["month"])]
    w = w.rename(columns={"PRECTOTCORR": "precip", "T2M_MAX": "tmax"}).sort_values("period_end")
    w["available_from"] = w["period_end"] + pd.Timedelta(days=30)
    return w[["period_end", "month", "precip", "tmax", "available_from"]].reset_index(drop=True)


def typhoons() -> pd.DataFrame:
    """Storms per quarter whose track passed within 200 km of any CALABARZON province centroid."""
    d = pd.read_csv(RAW / "ibtracs/ibtracs_calabarzon_600km.csv")
    d["t"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    near = np.zeros(len(d), bool)
    for lat, lon in CENTROIDS.values():
        near |= _haversine(d["LAT"].to_numpy(), d["LON"].to_numpy(), lat, lon) <= TC_RADIUS_KM
    hit = d[near].sort_values("t").groupby("SID").first().reset_index()
    hit["period_end"] = hit["t"].dt.to_period("Q").dt.end_time.dt.normalize()
    return hit[["SID", "NAME", "t", "period_end"]]


def oni() -> pd.DataFrame:
    rows = []
    seas = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    def parse(text):
        out = []
        for line in text.splitlines()[1:]:
            p = line.split()
            if len(p) == 4 and p[0] in seas:
                m = seas.index(p[0]) + 2            # season's last month (NDJ ends in January of the next year)
                y = int(p[1]) + (1 if m > 12 else 0)
                out.append({"period_end": _month_end(y, (m - 1) % 12 + 1), "oni": float(p[3])})
        return out
    rows = parse((RAW / "noaa/noaa_oni.txt").read_text())
    lv = _live("noaa/oni.txt")
    if lv is not None:                                    # seasons after the archived file only
        last = max(r["period_end"] for r in rows)
        rows += [r for r in parse(lv.read_text()) if r["period_end"] > last]
    d = pd.DataFrame(rows).sort_values("period_end")
    d["available_from"] = [_seen("oni", t, t + pd.Timedelta(days=10)) for t in d["period_end"]]
    return d


def gdelt() -> pd.DataFrame:
    """Quarterly mean GDELT volume intensity per theme group (Philippine sources), 2017+."""
    out = []
    for c in ["shortage", "agri_supply", "jobs_income", "assistance"]:
        f = RAW / f"gdelt/gdelt_doc_{c}.csv"
        if not f.exists():
            continue
        d = pd.read_csv(f, encoding="utf-8-sig")
        d["Date"] = pd.to_datetime(d["Date"])
        d["period_end"] = d["Date"].dt.to_period("Q").dt.end_time.dt.normalize()
        g = d.groupby("period_end").agg(v=("Value", "mean"), last=("Date", "max"), n=("Date", "count"))
        g = g[g["n"] >= 80]                       # complete quarters only
        out.append(g["v"].rename(f"gdelt_{c}"))
    q = pd.concat(out, axis=1).reset_index()
    q["available_from"] = q["period_end"]
    return q


def remittances() -> pd.DataFrame:
    d = json.loads((RAW / "bsp/wdi_BX.TRF.PWKR.CD.DT_PHL.json").read_text())[1]
    s = pd.Series({int(r["date"]): r["value"] for r in d if r["value"] is not None}).sort_index()
    lv = _live("worldbank/remittances.json")
    if lv is not None:                                    # years after the archived file only
        n = {int(r["date"]): r["value"] for r in json.loads(lv.read_text())[1] if r["value"] is not None}
        s = pd.concat([s, pd.Series({y: v for y, v in n.items() if y > s.index.max()}, dtype=float)]).sort_index()
    out = pd.DataFrame({"year": s.index, "remit_usd": s.values})
    out["remit_yoy"] = 100 * (out["remit_usd"] / out["remit_usd"].shift(1) - 1)
    out["period_end"] = [pd.Timestamp(year=y, month=12, day=31) for y in out["year"]]
    out["available_from"] = [_seen("remittances", pd.Timestamp(year=y, month=12, day=31), pd.Timestamp(year=y + 1, month=2, day=15)) for y in out["year"]]
    return out.dropna()


POVERTY_RELEASE = {2023: "2024-08-15", 2025: "2026-08-24"}


def poverty() -> pd.DataFrame:
    """CALABARZON poverty incidence among population (%). 2006-2015: 2009 methodology (region computed from the
    provinces' magnitudes and incidences); 2018+: 2018 methodology (region row as published)."""
    rows = []
    a = pd.read_csv(RAW / "psa/psa_poverty_2006_2015.csv", encoding="latin-1")
    a = a[a.iloc[:, 0].str.contains("Batangas|Cavite|Laguna|Quezon|Rizal", na=False)]
    for y in [2006, 2009, 2012, 2015]:
        inc = pd.to_numeric(a[f"Poverty Incidence among Population Estimate (%) {y}"], errors="coerce")
        mag = pd.to_numeric(a[f"Magnitude of Poor Population Estimate {y}"], errors="coerce")
        rows.append({"year": y, "poverty_inc": float(100 * mag.sum() / (mag / (inc / 100)).sum()),
                     "methodology": "2009", "region_row": "computed from provinces"})
    b = pd.read_csv(RAW / "psa/psa_poverty_2018_2023.csv", encoding="latin-1")
    r = b[b.iloc[:, 0].str.contains("CALABARZON", na=False)].iloc[0]
    for y in [2018, 2021, 2023]:
        rows.append({"year": y, "poverty_inc": float(r[f"Poverty Incidence among Population (%) {y}"]),
                     "methodology": "2018", "region_row": "published"})
    c = pd.read_csv(RAW / "psa/poverty_2021_2023_2025.csv")
    rc = c[c["geography"].str.contains("CALABARZON")].iloc[0]
    rows.append({"year": 2025, "poverty_inc": float(rc["pov_2025"]), "methodology": "2018", "region_row": "published"})
    d = pd.DataFrame(rows).sort_values("year")
    d["period_end"] = [pd.Timestamp(year=y, month=12, day=31) for y in d["year"]]
    d["available_from"] = [pd.Timestamp(POVERTY_RELEASE.get(y, f"{y + 2}-01-02")) for y in d["year"]]
    return d


REGISTRY = [
    SeriesInfo("hunger_last", "outcome", "outcome", "SWS", "Balance Luzon", "latest published hunger incidence (%)", "SWS published date", "1998-Q3"),
    SeriesInfo("hunger_last_anom", "outcome", "outcome", "SWS", "Balance Luzon", "latest reading minus its own five-year average (pp)", "SWS published date", "1998-Q3"),
    SeriesInfo("hunger_age_q", "outcome", "outcome", "SWS", "Balance Luzon", "quarters between the latest published reading and the target quarter", "SWS published date", "1998-Q3"),
    SeriesInfo("cpi_food_yoy", "market", "government", "PSA CPI", "Region IV-A", "food CPI, year-on-year % (latest released month)", "10th of next month", "1995-01"),
    SeriesInfo("cpi_rice_yoy", "market", "government", "PSA CPI", "Region IV-A", "rice CPI, year-on-year %", "10th of next month", "1995-01"),
    SeriesInfo("cpi_food_rel", "market", "government", "PSA CPI", "Region IV-A", "food minus all-items YoY inflation (pp)", "10th of next month", "1995-01"),
    SeriesInfo("cpi_food_accel", "market", "government", "PSA CPI", "Region IV-A", "change in food YoY over the last 3 released months (pp)", "10th of next month", "1995-04"),
    SeriesInfo("palay_yoy", "market", "government", "PSA crops", "Region IV-A", "palay production, YoY % (latest released quarter)", "quarter end + 45 days", "1988-Q1"),
    SeriesInfo("rain_anom_3m", "climate", "government", "NASA POWER", "5-province mean", "3-month precipitation, z-score vs same months in earlier years", "month end + 30 days", "1982-01"),
    SeriesInfo("tmax_anom_3m", "climate", "government", "NASA POWER", "5-province mean", "3-month max temperature, anomaly vs same months in earlier years (C)", "month end + 30 days", "1982-01"),
    SeriesInfo("tc_exposure_q", "climate", "government", "IBTrACS (PAGASA/JTWC tracks)", "within 200 km of a province", "storms passing near CALABARZON in the issue quarter", "real time", "1980"),
    SeriesInfo("tc_exposure_4q", "climate", "government", "IBTrACS", "within 200 km of a province", "storms passing near CALABARZON in the last 4 quarters", "real time", "1980"),
    SeriesInfo("oni", "climate", "government", "NOAA CPC", "Nino 3.4", "latest Oceanic Nino Index (El Nino > 0.5)", "season end + 10 days", "1950"),
    SeriesInfo("unemp_rate", "employment", "government", "PSA LFS", "Philippines", "unemployment rate % (latest released round)", "survey month + 45 days", "2005-04"),
    SeriesInfo("unemp_yoy", "employment", "government", "PSA LFS", "Philippines", "unemployment rate change vs same round a year earlier (pp)", "survey month + 45 days", "2006-01"),
    SeriesInfo("remit_yoy", "remittance", "government", "BSP via World Bank WDI", "Philippines", "personal remittances received, USD, YoY % (latest full year)", "15 Feb of next year", "1991"),
    SeriesInfo("poverty_inc", "poverty", "government", "PSA official poverty statistics", "Region IV-A", "poverty incidence among population % (latest release)", "documented / Y+2", "2006"),
    SeriesInfo("gdelt_shortage", "market", "news", "GDELT DOC (FOOD_SECURITY, STARVATION, FAMINE themes)", "Philippine sources", "quarterly mean volume intensity, z vs earlier quarters", "real time", "2017-Q1"),
    SeriesInfo("gdelt_agri_supply", "market", "news", "GDELT DOC (CROP_PRODUCTION, AGRICULTURE, FARMERS, FISHERMEN)", "Philippine sources", "quarterly mean volume intensity, z", "real time", "2017-Q1"),
    SeriesInfo("gdelt_jobs_income", "employment", "news", "GDELT DOC (UNEMPLOYMENT themes)", "Philippine sources", "quarterly mean volume intensity, z", "real time", "2017-Q1"),
    SeriesInfo("gdelt_assistance", "poverty", "news", "GDELT DOC (FOOD_AND_IN_KIND_TRANSFERS, AIDGROUPS)", "Philippine sources", "quarterly mean volume intensity, z", "real time", "2017-Q1"),
    *[SeriesInfo(f"fssi_{d}", d, "news", "aiPHeed corpus: XLM-R zero-shot + bias correction", "CALABARZON", f"bias-corrected Food Stress Sentiment Index, {d} domain, z vs earlier quarters", "quarter end", "2021-Q1")
      for d in ["market", "climate", "employment", "remittance", "poverty"]],
    *[SeriesInfo(f"topic_{d}", d, "news", "aiPHeed corpus: BERTopic (frozen 2021-2022 fit)", "CALABARZON", f"share of events in {d} topics, z vs earlier quarters", "quarter end", "2021-Q1")
      for d in ["market", "climate", "employment", "remittance", "poverty"]],
    SeriesInfo("hunger_news_share", "poverty", "news", "aiPHeed corpus: XLM-R", "CALABARZON", "share of events that report people going hungry, z", "quarter end", "2021-Q1"),
]
REG = {s.key: s for s in REGISTRY}
DOMAIN_ORDER = ["market", "climate", "employment", "remittance", "poverty"]
