"""
app/quarterly/lgu_audit.py  (E28, Objective 3)
-----------------------------------------------
The 142-LGU audit table and the single ranking implementation used by the API, the dashboard, the PDF and the
stored record.

Chapter I, Objective 3 (verbatim): "To produce spatially disaggregated municipal and city food insecurity risk
rankings from validated province-level forecasts, using PSA published poverty incidence and population density as
vulnerability weights." Scope: "City and municipal estimates will be derived from province-level forecasts using PSA
Small Area Estimates and population data; therefore, these estimates will not represent official food insecurity
classifications."

Method (unchanged; app.quarterly.lgu_poverty.rank_lgus): within each province, min-max normalise the poverty value
used and the population density; vulnerability = 0.6 x poverty_norm + 0.4 x density_norm; risk_index = province
probability x vulnerability, clamped to [0, 1] and rounded to 4 dp; competition ranks (ties share a rank), listing order
inside a tie by PSGC ascending; a province without a probability gives null risk_index and null ranks.

What this module adds:
  * cross-checks of the authorized vulnerability table against the reference roster: 142 unique PSGC codes, the same
    name / province / type, identical population and land area, density > 0, poverty in [0, 100], province prefix
    consistent with the province, and namesakes across provinces resolved by PSGC;
  * per-LGU provenance (source, reference year, geographic unit, transformation) for every indicator;
  * the explicit kind of every poverty value: "PSA municipal SAE estimate" or "province-mean substitute". A substitute
    is never shown as a measured municipal value; its within-province position comes from density alone;
  * what drives the order inside each province (Spearman of risk_index with density and with poverty);
  * the meaning statement that travels with the ranking.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from app.quarterly.forecaster_v2 import lgu_table
from app.quarterly.lgu_poverty import CALABARZON_PROVINCE_PREFIX

PROV_NAME2CODE = {"Batangas": "PH040500000", "Cavite": "PH040100000", "Laguna": "PH040200000",
                  "Quezon": "PH040300000", "Rizal": "PH040400000"}
EXPECTED_COUNTS = {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 41, "Rizal": 14}

MEANING = (
    "Indicative, relative ordering of the 142 cities and municipalities for planning attention. It is the province "
    "estimate re-weighted by PSA 2021 poverty incidence (60%) and 2024 POPCEN population density (40%) inside each province. "
    "It is not a measured municipal food-insecurity rate, not an independent municipal forecast and not an official "
    "classification (Chapter I, 1.7). The province estimate it starts from has NOT been validated against baselines "
    "(E25-E28), so the ranking inherits that status: EXPERIMENTAL.")
DOES_NOT_MEAN = [
    "It does not say that any LGU is food insecure, or how many households are.",
    "Positions inside a province reflect the vulnerability weights only. Positions across provinces are not a "
    "measured comparison: the vulnerability index is scaled 0 to 1 inside each province, so the region-wide order "
    "mixes five different scales and follows the within-province index more than the province estimate (E35-D4). "
    "Compare LGUs within their province.",
    "For an LGU without a PSA municipal poverty estimate (Lucena City, a highly urbanized city that the PSA no-HUC "
    "table excludes), the poverty term is a province substitute, so its position inside the province comes from "
    "population density and the substitute value, not from a municipal measurement.",
    "Two LGUs with equal risk_index share a rank; their listing order (PSGC) carries no meaning.",
]

PROVENANCE = {
    "population_2024": {"source": "PSA 2024 Census of Population (POPCEN), Table B, 1 July 2024",
                        "reference_year": 2024,
                        "unit": "city/municipality", "transformation": "persons; density = population / land area"},
    "land_area_km2": {"source": "aiPHeed reference roster (data/reference/calabarzon_lgus.csv)", "reference_year": None,
                      "unit": "city/municipality", "transformation": "km2; denominator of density"},
    "poverty_lgu_estimate": {"source": "PSA 2021 City and Municipal Level Small Area Estimates of Poverty "
                                       "(no-HUC table, sheet 2018-2021_NoHUC, 2021 columns only)",
                             "reference_year": 2021, "unit": "city/municipality (141 LGUs; not Lucena City)",
                             "transformation": "poverty incidence among population, %"},
    "poverty_value_used": {"source": "LGU estimate where published; otherwise the PSA 2021 province value",
                           "reference_year": 2021, "unit": "city/municipality or province substitute",
                           "transformation": "min-max within province -> poverty_norm (weight 0.6)"},
    "density": {"source": "derived", "reference_year": 2024, "unit": "city/municipality",
                "transformation": "min-max within province -> density_norm (weight 0.4)"},
    "province_probability": {"source": "the stored province estimate the ranking is computed from",
                             "reference_year": None, "unit": "province",
                             "transformation": "risk_index = province estimate x vulnerability, clamp [0,1], 4 dp"},
}


def _code9(x) -> str:
    s = str(x).strip()
    return s.zfill(9) if s.isdigit() else s


def audit_inputs(vuln: pd.DataFrame, roster: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    v = vuln.copy()
    v["lgu_code"] = v["lgu_code"].map(_code9)
    r = roster.copy()
    r["lgu_psgc"] = r["lgu_psgc"].map(_code9)
    m = v.merge(r.rename(columns={"lgu_psgc": "lgu_code", "lgu_name": "roster_name", "lgu_type": "roster_type",
                                  "population_2024": "roster_population", "land_area_km2": "roster_area"}),
                on="lgu_code", how="outer", indicator=True)
    checks = {
        "rows_vulnerability": int(len(v)), "rows_roster": int(len(r)),
        "unique_codes_vulnerability": int(v["lgu_code"].nunique()),
        "codes_only_in_vulnerability": sorted(m.loc[m["_merge"] == "left_only", "lgu_code"].tolist()),
        "codes_only_in_roster": sorted(m.loc[m["_merge"] == "right_only", "lgu_code"].tolist()),
        "per_province": v.groupby("province").size().to_dict(),
        "per_province_matches_expected": v.groupby("province").size().to_dict() == EXPECTED_COUNTS,
    }
    both = m[m["_merge"] == "both"].copy()
    both["prov_code_from_name"] = both["province"].map(PROV_NAME2CODE)
    both["prefix_province"] = both["lgu_code"].str[:4].map(CALABARZON_PROVINCE_PREFIX)
    checks["name_mismatches"] = both.loc[both["lgu_name"].str.casefold() != both["roster_name"].str.casefold(),
                                         ["lgu_code", "lgu_name", "roster_name"]].to_dict("records")
    checks["province_mismatches"] = both.loc[both["prov_code_from_name"] != both["province_code"],
                                             "lgu_code"].tolist()
    checks["psgc_prefix_mismatches"] = both.loc[both["prefix_province"] != both["prov_code_from_name"],
                                                "lgu_code"].tolist()
    checks["type_mismatches"] = both.loc[both["lgu_type"] != both["roster_type"], "lgu_code"].tolist()
    checks["population_mismatches"] = both.loc[both["population_2024"] != both["roster_population"],
                                               "lgu_code"].tolist()
    checks["area_mismatches"] = both.loc[~np.isclose(both["land_area_km2"], both["roster_area"]), "lgu_code"].tolist()
    checks["nonpositive_area_or_population"] = both.loc[(both["land_area_km2"] <= 0) | (both["population_2024"] <= 0),
                                                        "lgu_code"].tolist()
    pv = both["poverty_lgu_estimate"]
    checks["poverty_out_of_range"] = both.loc[pv.notna() & ((pv < 0) | (pv > 100)), "lgu_code"].tolist()
    checks["poverty_value_used_missing"] = both.loc[both["poverty_value_used"].isna(), "lgu_code"].tolist()
    checks["lgu_specific_poverty_estimates"] = int(pv.notna().sum())
    checks["province_mean_substitutes"] = int(pv.isna().sum())
    names = both.groupby(both["lgu_name"].str.casefold())["province"].nunique()
    checks["namesakes_across_provinces_resolved_by_psgc"] = sorted(names[names > 1].index.tolist())
    # substitutes: is the value used really one value per province (a substitute must not vary inside a province)?
    sub = both[pv.isna()]
    checks["substitute_values_per_province"] = sub.groupby("province")["poverty_value_used"].nunique().to_dict()
    checks["passes"] = bool(
        checks["rows_vulnerability"] == 142 and checks["unique_codes_vulnerability"] == 142
        and not checks["codes_only_in_vulnerability"] and not checks["codes_only_in_roster"]
        and checks["per_province_matches_expected"] and not checks["province_mismatches"]
        and not checks["psgc_prefix_mismatches"] and not checks["population_mismatches"]
        and not checks["area_mismatches"] and not checks["nonpositive_area_or_population"]
        and not checks["poverty_out_of_range"] and not checks["poverty_value_used_missing"]
        and all(n == 1 for n in checks["substitute_values_per_province"].values()))
    return both, checks


def build_ranking(vuln: pd.DataFrame, roster: pd.DataFrame, province_probability: dict | None,
                  probability_source: dict, exact_ranks: bool = False) -> dict:
    """exact_ranks (E66, opt-in): rank on the unrounded index so 4-dp display rounding creates no ties."""
    both, checks = audit_inputs(vuln, roster)
    lg = vuln.copy()
    lg["lgu_code"] = lg["lgu_code"].map(_code9)
    rk = lgu_table(lg, province_probability, exact_ranks=exact_ranks)
    rk["lgu_code"] = rk["lgu_code"].map(_code9)
    # drivers of the within-province order
    drivers = {}
    for p, g in rk.groupby("province"):
        if g["risk_index"].notna().sum() >= 3:
            drivers[p] = {
                "spearman_risk_vs_density": float(g["risk_index"].rank().corr(g["density"].rank())),
                "spearman_risk_vs_poverty_used": (float(g["risk_index"].rank().corr(g["poverty_value_used"].rank()))
                                                  if g["poverty_value_used"].nunique() > 1 else None),
                "lgus_with_municipal_poverty_estimate": int(g["poverty_lgu_estimate"].notna().sum()),
                "lgus": int(len(g)),
            }
    tie_key = "risk_index_exact" if exact_ranks else "risk_index"
    ties = rk[rk[tie_key].notna()].groupby(tie_key).size()
    rows = []
    for r in rk.itertuples():
        rows.append({
            "lgu_code": r.lgu_code, "lgu_name": r.lgu_name, "lgu_type": r.lgu_type, "province": r.province,
            "province_code": r.province_code,
            "population_2024": int(r.population_2024), "land_area_km2": float(r.land_area_km2),
            "density_per_km2": round(float(r.density), 3),
            "poverty_lgu_estimate": None if pd.isna(r.poverty_lgu_estimate) else float(r.poverty_lgu_estimate),
            "poverty_value_used": float(r.poverty_value_used), "poverty_value_kind": r.poverty_value_kind,
            "poverty_norm": round(float(r.poverty_value_used_norm), 6), "density_norm": round(float(r.density_norm), 6),
            "vulnerability_index": round(float(r.vulnerability_index), 6),
            "province_probability": None if pd.isna(r.province_probability) else round(float(r.province_probability), 6),
            "risk_index": None if pd.isna(r.risk_index) else float(r.risk_index),
            "rank_region": None if pd.isna(r.rank_region) else int(r.rank_region),
            "rank_in_province": None if pd.isna(r.rank_in_province) else int(r.rank_in_province),
            "vulnerability_rank_in_province": int(r.vulnerability_rank_in_province),
            "tied": bool(pd.notna(getattr(r, tie_key)) and ties.get(getattr(r, tie_key), 0) > 1),
            "limitation": r.limitation,
            "evidence_status": "EXPERIMENTAL",
        })
    blob = json.dumps(rows, sort_keys=True).encode()
    return {"meaning": MEANING, "does_not_mean": DOES_NOT_MEAN, "provenance": PROVENANCE,
            "method": "vulnerability = 0.6 x poverty_norm + 0.4 x density_norm (min-max within province); "
                      "risk_index = province estimate (the served province score) x vulnerability, clamp [0,1], 4 dp; "
                      "competition ranks, "
                      + ("ranked on the unrounded index (E66), " if exact_ranks else "")
                      + "ties by PSGC; null province estimate -> null risk and ranks",
            "probability_source": probability_source, "input_checks": checks, "within_province_drivers": drivers,
            "rows": rows, "rows_sha256": hashlib.sha256(blob).hexdigest()}
