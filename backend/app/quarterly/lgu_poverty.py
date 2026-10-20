"""
app/quarterly/lgu_poverty.py  (E24)
-----------------------------------
Ingest and validate the official PSA city/municipal Small Area Estimates of poverty (e.g. the PSA workbook
"2018 - 2021 SAE_with PSGC_noHUC.xlsx") into a VERSIONED LGU poverty table, and build rankings that never present a
province average as a municipal measurement.

* PSGC codes are compared in the legacy 9-digit form used by the census table (RRPPMMBBB, e.g. 041001000). The
  2023 10-digit form (RRPPPMMBBB, e.g. 0401001000) is converted by dropping the leading province zero.
* Only rows whose code matches one of the 142 CALABARZON LGUs are kept; every non-match is reported.
* A municipal value is accepted only from the official workbook. An LGU without one keeps poverty_lgu_estimate =
  null and an explicit limitation; the ranking formula's province-mean substitute is labelled as a substitute.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

CALABARZON_PROVINCE_PREFIX = {"0410": "PH040500000", "0421": "PH040100000", "0434": "PH040200000",
                              "0456": "PH040300000", "0458": "PH040400000"}   # Batangas Cavite Laguna Quezon Rizal
POVERTY_WEIGHT, DENSITY_WEIGHT = 0.6, 0.4


def legacy_psgc(code) -> str | None:
    """Return the 9-digit legacy PSGC, or None.

    Strings keep their width: 9 digits = legacy (041001000), 10 digits = 2023 form (0401001000).
    NUMBERS have lost their leading zero (Excel stores PSGC as numbers): 8 digits = legacy, 9 digits = 2023 form.
    """
    if code is None or (isinstance(code, float) and np.isnan(code)):
        return None
    numeric = isinstance(code, (int, float, np.integer, np.floating))
    s = re.sub(r"\D", "", str(int(code)) if numeric else str(code).strip())
    if numeric:
        s = s.zfill(9) if len(s) <= 8 else s.zfill(10)
    if len(s) == 9:
        return s
    if len(s) == 10:
        return s[:2] + s[3:] if s[2] == "0" else None   # province code > 99 has no legacy form
    return None


def _find(cols, *needles):
    for c in cols:
        lc = str(c).lower()
        if all(n in lc for n in needles):
            return c
    return None


def parse_sae_table(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Normalize a PSA SAE sheet (header row already applied). Auto-detects columns; raises if none found."""
    cols = list(df.columns)
    c_code = _find(cols, "psgc") or _find(cols, "code")
    c_pi = (_find(cols, "poverty incidence", str(year)) or _find(cols, str(year), "estimate")
            or _find(cols, "poverty incidence"))
    if c_code is None or c_pi is None:
        raise ValueError(f"cannot find PSGC / poverty-incidence columns among {cols}")
    c_name = _find(cols, "municipal") or _find(cols, "city") or _find(cols, "name")
    c_se = _find(cols, "standard error", str(year)) or _find(cols, "standard error")
    c_cv = _find(cols, "cv", str(year)) or _find(cols, "coefficient of variation")
    c_lo = _find(cols, "lower", str(year)) or _find(cols, "lower")
    c_hi = _find(cols, "upper", str(year)) or _find(cols, "upper")
    out = pd.DataFrame({"psgc_raw": df[c_code], "name_source": df[c_name] if c_name else None,
                        "poverty_incidence_pct": pd.to_numeric(df[c_pi], errors="coerce"),
                        "se": pd.to_numeric(df[c_se], errors="coerce") if c_se else np.nan,
                        "cv": pd.to_numeric(df[c_cv], errors="coerce") if c_cv else np.nan,
                        "ci_low": pd.to_numeric(df[c_lo], errors="coerce") if c_lo else np.nan,
                        "ci_high": pd.to_numeric(df[c_hi], errors="coerce") if c_hi else np.nan})
    out["lgu_code"] = out["psgc_raw"].map(legacy_psgc)
    out["year"] = year
    return out


def validate_against_census(sae: pd.DataFrame, census: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Keep CALABARZON rows matching the census LGUs. Returns (matched table, validation report)."""
    region = sae[sae["lgu_code"].fillna("").str[:4].isin(CALABARZON_PROVINCE_PREFIX)]
    dup = region[region["lgu_code"].duplicated(keep=False)]
    bad_range = region[(region["poverty_incidence_pct"] < 0) | (region["poverty_incidence_pct"] > 100)]
    m = census[["lgu_code", "lgu_name", "province_code"]].merge(region.drop_duplicates("lgu_code"), on="lgu_code",
                                                                 how="left", indicator=True)
    rep = {"sae_rows": int(len(sae)), "calabarzon_rows": int(len(region)),
           "census_lgus": int(len(census)), "matched": int((m["_merge"] == "both").sum()),
           "census_lgus_without_estimate": m.loc[m["_merge"] != "both", "lgu_name"].tolist(),
           "sae_codes_not_in_census": sorted(set(region["lgu_code"]) - set(census["lgu_code"])),
           "duplicate_codes": sorted(dup["lgu_code"].unique().tolist()),
           "out_of_range_values": bad_range["lgu_code"].tolist(),
           "province_prefix_consistent": bool((m.loc[m["_merge"] == "both", "lgu_code"].str[:4]
                                               .map(CALABARZON_PROVINCE_PREFIX) ==
                                               m.loc[m["_merge"] == "both", "province_code"]).all())}
    rep["passes"] = bool(not rep["duplicate_codes"] and not rep["out_of_range_values"]
                         and rep["province_prefix_consistent"])
    return m.drop(columns="_merge"), rep


def rank_lgus(census: pd.DataFrame, poverty: pd.DataFrame, province_probability: dict | None,
              exact_ranks: bool = False) -> pd.DataFrame:
    """Approved method (0.6 poverty_norm + 0.4 density_norm within province; x province probability; clamp [0,1]).

    `poverty` columns: lgu_code, poverty_lgu_estimate (null when PSA publishes none), poverty_source.
    Where the LGU estimate is null, the formula uses the province mean of the AVAILABLE municipal estimates if any
    exist, else the stored province value, and labels it 'province-mean substitute' (never 'municipal').
    Deterministic ranking: risk_index (rounded 4 dp) descending, ties share the same competition rank (1,2,2,4),
    listing order inside a tie = lgu_code ascending. A missing province probability gives risk_index = null.

    E66 (D-E66-3): with exact_ranks=True the ranks use the unrounded index (risk_index_exact); risk_index stays the
    4-dp display value. With small province probabilities (2027-Q1: 0.04-0.15) 4-dp rounding creates ties that are an
    artefact of display precision, not equal vulnerability. Default False keeps the approved behaviour."""
    m = census.merge(poverty, on="lgu_code", how="left", validate="one_to_one")
    assert len(m) == len(census)
    m["density"] = m["population_2024"] / m["land_area_km2"]
    sub = m.groupby("province_code")["poverty_lgu_estimate"].transform("mean")
    m["poverty_value_used"] = m["poverty_lgu_estimate"].fillna(m.get("poverty_province_value", sub)).fillna(sub)
    m["poverty_value_kind"] = np.where(m["poverty_lgu_estimate"].notna(), "PSA municipal SAE estimate",
                                       "province-mean substitute (no municipal estimate)")
    for c in ("poverty_value_used", "density"):
        g = m.groupby("province_code")[c]
        rng = (g.transform("max") - g.transform("min")).replace(0, 1)
        m[c + "_norm"] = (m[c] - g.transform("min")) / rng
    m["vulnerability_index"] = POVERTY_WEIGHT * m["poverty_value_used_norm"] + DENSITY_WEIGHT * m["density_norm"]
    if province_probability is None:
        m["province_probability"] = np.nan
    else:
        m["province_probability"] = m["province_code"].map(province_probability)
    m["risk_index_exact"] = (m["province_probability"] * m["vulnerability_index"]).clip(0, 1)
    m["risk_index"] = m["risk_index_exact"].round(4)
    key = "risk_index_exact" if exact_ranks else "risk_index"
    m = m.sort_values([key, "lgu_code"], ascending=[False, True], na_position="last").reset_index(drop=True)
    m["rank_region"] = m[key].rank(ascending=False, method="min")
    m["rank_in_province"] = m.groupby("province_code")[key].rank(ascending=False, method="min")
    m["vulnerability_rank_in_province"] = m.groupby("province_code")["vulnerability_index"].rank(
        ascending=False, method="min")
    n_sub = m.groupby("province_code")["poverty_lgu_estimate"].transform(lambda s: s.isna().sum())
    m["limitation"] = np.where(
        m["poverty_lgu_estimate"].isna(),
        "No PSA municipal poverty estimate in the authorized data: the poverty term is a province substitute, "
        "not a municipal measurement, so this LGU's position within its province is indicative only.",
        np.where(n_sub > 0, "Municipal estimate available; compared within province against LGUs that carry a "
                            "province-mean substitute.", "Municipal estimate available."))
    return m
