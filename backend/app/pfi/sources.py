"""
Loaders for PFI, each row carrying the date it became public (`available_from`) so that every fit and forecast can be
restricted to what was known at its issue date. Release dates marked `approximate` are conservative (late) dates
taken from the publication month; none of them falls near a forecast issue date used here.

Every outcome row keeps its construct (`instrument`) and verification status: FIES, HFIAS, subsistence incidence and
SWS hunger are different measurements and are never pooled into one label.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from app.paths import BACKEND_DIR
from app.pfi import PROVINCES, RAW

LABELS = BACKEND_DIR / "data" / "fi_labels" / "clean"
REF = BACKEND_DIR / "data" / "reference"

# Publication dates of the survey waves (approximate = month of first public release, end of month, conservative).
FIES_RELEASE = {2019: ("2020-12-31", "approximate"), 2021: ("2022-12-31", "approximate"),
                2023: ("2024-12-31", "approximate"), 2025: ("2026-09-30", "approximate")}
POVERTY_RELEASE = {2021: "2022-08-15", 2023: "2024-08-15"}      # PSA full-year official poverty statistics
LFS_RELEASE = {2021: "2022-06-30", 2022: "2023-06-30", 2023: "2024-06-30", 2025: "2026-06-30"}

# FIES region names (PSA OpenSTAT) -> names in the PSA poverty / CPI / LFS tables.
REGION_KEYS = {
    "National Capital Region (NCR)": "NCR", "Cordillera Administrative Region (CAR)": "CAR", "Region I": "I",
    "Region II": "II", "Region III": "III", "Region IV-A": "IV-A", "MIMAROPA Region": "MIMAROPA", "Region V": "V",
    "Region VI": "VI", "Region VII": "VII", "Region VIII": "VIII", "Region IX": "IX", "Region X": "X", "Region XI": "XI",
    "Region XII": "XII", "Region XIII": "XIII", "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)": "BARMM"}


def region_key(name: str) -> str | None:
    """Normalise any PSA region label ('..Region IV-A (CALABARZON) 1/, 2/', 'Region IV-A') to a short key."""
    s = re.sub(r"^\.+", "", str(name)).strip()
    s = re.sub(r"\s*(r\d,?\s*)?((\d|[a-z])/,?\s*|\*\*,?\s*)+$", "", s).strip()
    for full, k in REGION_KEYS.items():
        if s == full or s.startswith(full + " (") or s == k:
            return k
    if "BARMM" in s or "Bangsamoro" in s:
        return "BARMM"
    if s.startswith("Negros Island"):
        return "NIR"
    return None


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def expit(x):
    return 1 / (1 + np.exp(-np.asarray(x, float)))


# ------------------------------------------------------------------------------------------------------------ outcomes
def fies() -> pd.DataFrame:
    """FIES moderate-or-severe food insecurity (% of households). National 2019-2023 and 17 regions 2023 (PSA OpenSTAT,
    verified); CALABARZON 2025 (FNRI 2025 Updating Survey as reported by PIA; provisional, secondary, no CI)."""
    d = pd.read_csv(LABELS / "published_fies_psa_sdg212.csv")
    out = pd.DataFrame({"geography": d["geography"], "key": [("PH" if lv == "national" else region_key(g))
                                                              for g, lv in zip(d["geography"], d["level"])],
                        "level": d["level"], "year": d["year"].astype(int), "pct": d["percent"].astype(float),
                        "ci_low": d["ci95_low"].map(_num), "ci_high": d["ci95_high"].map(_num),
                        "status": "verified_primary", "source": d["source"]})
    b = pd.read_csv(LABELS / "owner_workbook_regional_benchmarks_verified.csv")
    r25 = b[(b["Reference period"].astype(str) == "2025") & b["Indicator"].str.contains("Moderate-to-severe")]
    for _, r in r25.iterrows():
        out.loc[len(out)] = {"geography": "Region IV-A", "key": "IV-A", "level": "region", "year": 2025,
                             "pct": float(r["Estimate (%)"]), "ci_low": np.nan, "ci_high": np.nan,
                             "status": str(r["verification_status_aipheed"]), "source": str(r["Source"])}
    out["available_from"] = pd.to_datetime(out["year"].map(lambda y: FIES_RELEASE[y][0]))
    out["release_date_status"] = out["year"].map(lambda y: FIES_RELEASE[y][1])
    out["instrument"] = "FIES"
    out["in_study_window"] = out["year"] >= 2021
    return out


def hfias_2015() -> pd.DataFrame:
    """FNRI 2015 HFIAS by province (verified, with SEs). A different instrument from FIES: used only as an independent
    check of the provincial ordering, never as a FIES value."""
    d = pd.read_csv(LABELS / "published_hfias_2015_calabarzon.csv")
    w = d.pivot_table(index="geography", columns="category", values="percent")
    se = d.pivot_table(index="geography", columns="category", values="se")
    out = pd.DataFrame({"geography": w.index,
                        "mod_sev_pct": w["moderately_food_insecure"] + w["severely_food_insecure"],
                        "se_pp": np.sqrt(se["moderately_food_insecure"] ** 2 + se["severely_food_insecure"] ** 2)})
    out["n_households"] = out["geography"].map(d.groupby("geography")["n_households"].first())
    return out.reset_index(drop=True)


def workbook_secondary() -> pd.DataFrame:
    """ENNS provincial values reproduced in the CALABARZON RDP results matrix (one year per province, no SE,
    instrument not stated, not verified against FNRI). Shown as dated references; a consistency check only."""
    d = pd.read_csv(LABELS / "owner_workbook_records_verified.csv")
    e = d[d["record_id"].str.startswith("ENNS")]
    return pd.DataFrame({"province": e["province"], "year": e["reference_year"].astype(int),
                         "indicator": e["label_name"], "pct": e["label_value"].astype(float),
                         "status": e["verification_status_aipheed"], "record_id": e["record_id"]}).reset_index(drop=True)


# ---------------------------------------------------------------------------------------------- structural covariates
def _psa_wide(fname: str, col_pat: str, year: int) -> pd.DataFrame:
    d = pd.read_csv(RAW / fname, dtype=str)
    g = d.iloc[:, 0]
    col = next(c for c in d.columns if re.search(col_pat, c) and c.endswith(str(year)))
    rows = []
    for name, v in zip(g, d[col]):
        depth = len(re.match(r"^\.*", name).group(0))
        clean = re.sub(r"\s*(r\d,?\s*)?((\d|[a-z])/,?\s*|\*\*,?\s*)+$", "", re.sub(r"^\.+", "", name)).strip()
        rows.append({"name": clean, "depth": depth, "key": region_key(name) if depth == 2 else None, "value": _num(v)})
    return pd.DataFrame(rows)


def poverty(year: int) -> pd.DataFrame:
    """Poverty incidence among population (%), PSA full-year official poverty statistics."""
    return _psa_wide("psa_poverty_incidence_all_regions_2018_2023.csv", r"Poverty Incidence among Population", year)


def subsistence(year: int) -> pd.DataFrame:
    """Subsistence (food-poverty) incidence among families (%), PSA."""
    return _psa_wide("psa_subsistence_families_2018_2023.csv", r"Subsistence Incidence among Families", year)


def unemployment_region(year: int) -> pd.DataFrame:
    d = pd.read_csv(RAW / "psa_sdg_unemployment_region.csv", dtype=str)
    d = d[(d["Age Group"] == "15 years and above") & (d["Sex"] == "Both sexes")]
    return pd.DataFrame({"key": d["Geolocation"].map(lambda s: "PH" if s == "PHILIPPINES" else region_key(s)),
                         "value": d[str(year)].map(_num)})


def unemployment_province(year: int) -> pd.DataFrame:
    d = pd.read_csv(RAW / "psa_lfs_calabarzon_provincial_2021_2025.csv")
    d = d[d["year"] == year]
    return pd.DataFrame({"name": d["province"], "value": d["unemployment_rate_pct"].astype(float)})


def _yoy_mean(series: pd.Series, year: int) -> float:
    """Annual mean of monthly year-on-year inflation (%), from a monthly index Series keyed by (year, month)."""
    vals = [100 * (series[(year, m)] / series[(year - 1, m)] - 1) for m in range(1, 13)
            if (year, m) in series.index and (year - 1, m) in series.index]
    return float(np.mean(vals)) if len(vals) == 12 else np.nan


def rice_inflation_region(year: int) -> pd.DataFrame:
    """Annual mean rice CPI inflation (%), by region (PSA CPI 2018=100; item 01.1.1.12, the same code as provinces)."""
    d = pd.read_csv(RAW / "psa_cpi_regional_2021_2026.csv")
    d = d[d["Commodity Description"] == "01.1.1.12 - Rice"]
    months = [c for c in d.columns if re.match(r"^\d{4} [A-Z][a-z]{2}$", c)]
    rows = []
    for _, r in d.iterrows():
        s = pd.Series({(int(c[:4]), pd.Timestamp(f"1 {c[5:]} 2000").month): _num(r[c]) for c in months})
        rows.append({"key": region_key(r["Geolocation"]), "value": _yoy_mean(s, year)})
    return pd.DataFrame(rows)


def rice_inflation_province(year: int) -> pd.DataFrame:
    d = pd.read_csv(BACKEND_DIR / "data" / "fi10" / "raw" / "cpi_monthly_long.csv")
    d = d[(d["commodity_description"] == "01.1.1.12 - Rice") & d["geolocation"].isin(PROVINCES)]
    rows = []
    for p, g in d.groupby("geolocation"):
        s = g.drop_duplicates(["year", "month"], keep="last").set_index(["year", "month"])["value"].astype(float)
        rows.append({"name": p, "value": _yoy_mean(s, year)})
    return pd.DataFrame(rows)


COVARIATES = {
    # name: (group, label, region loader, province loader, release date of the year-2023 value)
    "poverty": ("Poverty and social vulnerability", "Poverty incidence, population (%)", poverty, poverty, POVERTY_RELEASE[2023]),
    "subsistence": ("Poverty and social vulnerability", "Subsistence (food-poverty) incidence, families (%)",
                    subsistence, subsistence, POVERTY_RELEASE[2023]),
    "unemployment": ("Employment and remittances", "Unemployment rate (%)", unemployment_region, unemployment_province,
                     LFS_RELEASE[2023]),
    "rice_inflation": ("Market and food prices", "Rice inflation, annual mean (%)", rice_inflation_region,
                       rice_inflation_province, "2024-01-10"),
}


def region_table(year: int = 2023) -> pd.DataFrame:
    """One row per FIES region for `year`: outcome plus every covariate (NIR, created in 2024, is not a FIES region; the
    restated 2023 Region VI/VII poverty figures exclude it, a small mismatch recorded in the methodology)."""
    f = fies()
    f = f[(f["level"] == "region") & (f["year"] == year) & (f["status"] == "verified_primary")]
    t = f[["key", "geography", "pct", "ci_low", "ci_high"]].rename(columns={"pct": "fies"}).set_index("key")
    for name, (_, _, reg, _, _) in COVARIATES.items():
        c = reg(year)
        c = c[c["key"].notna()].drop_duplicates("key").set_index("key")["value"]
        t[name] = c.reindex(t.index)
    return t.reset_index()


def province_table(year: int = 2023) -> pd.DataFrame:
    t = pd.DataFrame({"province": PROVINCES}).set_index("province")
    for name, (_, _, _, prov, _) in COVARIATES.items():
        c = prov(year)
        if "depth" in c:
            c = c[c["depth"] == 4]
        t[name] = c.drop_duplicates("name").set_index("name")["value"].reindex(t.index)
    return t.reset_index()


def population() -> pd.DataFrame:
    """142 LGUs with province and 2024 population (POPCEN 2024), plus 2021 municipal poverty (PSA SAE) where published."""
    lg = pd.read_csv(REF / "calabarzon_lgus.csv", dtype={"lgu_psgc": str})
    sae = pd.read_csv(REF / "sae2021_calabarzon_municipal.csv", dtype={"lgu_code": str})
    lg = lg.merge(sae[["lgu_code", "poverty_incidence_2021", "cv_2021"]], left_on="lgu_psgc", right_on="lgu_code", how="left")
    return lg.drop(columns=["lgu_code"])


# ------------------------------------------------------------------------------------------------------- SWS hunger
def sws_quarterly(area: str, as_of=None) -> pd.DataFrame:
    """SWS involuntary hunger (% of families) by quarter for `area` ('balance_luzon' or 'national'), using only rounds
    published on or before `as_of`. Quarters with two rounds take the mean; `moe` is the 95% margin of error."""
    from app.fi5.sources import sws_rounds
    r = sws_rounds()
    if as_of is not None:
        r = r[r["published"] <= pd.Timestamp(as_of)]
    moe_col = "area_moe_bl" if area == "balance_luzon" else None
    r = r.dropna(subset=[area])
    g = r.groupby("quarter").agg(value=(area, "mean"), published=("published", "max"), rounds=(area, "size"),
                                 moe=(moe_col, "mean") if moe_col else (area, lambda s: 3.0))
    g = g.reset_index()
    g["qi"] = g["quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    return g.sort_values("qi").reset_index(drop=True)
