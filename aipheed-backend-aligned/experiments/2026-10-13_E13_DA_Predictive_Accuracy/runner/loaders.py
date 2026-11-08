"""E13 loaders. Every read goes through the guard (hash-verified allowlist; guard.install() first)."""
from __future__ import annotations

import io
import json

import pandas as pd

import guard


def load_components() -> pd.DataFrame:
    p = guard.E12_RUN / "realized_components_2021_2025.csv"
    df = pd.read_csv(io.StringIO(guard.read_allowed_text(p)), dtype={"province_code": str})
    if df["quarter"].map(lambda q: q > "2025-Q4").any():
        raise guard.AccessDenied("E13: components file contains a quarter after 2025-Q4")
    return df


def load_details() -> dict:
    return json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))


def load_rounds(details: dict) -> pd.DataFrame:
    r = pd.DataFrame(details["two_layer"]["regional_layer_rounds"])
    r["published"] = pd.to_datetime(r["published"])
    if (r["quarter"] > "2025-Q4").any():
        raise guard.AccessDenied("E13: a regional round after 2025-Q4 was found")
    return r


def load_external() -> dict:
    al = guard.AL / "data" / "processed"
    fies = guard.read_allowed_parquet(al / "nns_fies.parquet",
                                      ["survey_cycle", "year", "region_code", "region_name", "province_code",
                                       "province_name", "fies_moderate_severe_pct", "fies_severe_pct",
                                       "geographic_level", "verified", "provenance", "source_url", "source_note"])
    lgu = guard.read_allowed_parquet(al / "lgu_poverty.parquet",
                                     ["province_code", "province_name", "lgu_code", "lgu_name", "year",
                                      "poverty_incidence_pct", "source_url", "source_note"])
    sub = guard.read_allowed_parquet(guard.ROOT / "backend" / "data" / "processed" / "psa_subsistence.parquet",
                                     ["psgc_code", "area_name", "geographic_level", "year", "food_threshold_php",
                                      "subsistence_pct", "subsistence_cv", "subsistence_ci_low", "subsistence_ci_high",
                                      "discriminating", "usable_as_feature", "usable_for_validation", "source_url",
                                      "source_note"])
    return {"fies": fies, "lgu_poverty": lgu, "subsistence": sub}
