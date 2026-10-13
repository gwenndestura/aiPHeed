"""E17 loaders. Every read goes through the guard (hash-verified allowlist; guard.install() first).
Each loader asserts that nothing later than 2025-Q4 / 2025 is returned."""
from __future__ import annotations

import io
import json

import pandas as pd

import guard

MAXQ = "2025-Q4"
NLP = ["FSSI", "FSSI_lag1", "FSSI_lag2", "FSSI_accel", "trigger_market", "trigger_climate", "trigger_employment",
       "trigger_ofw_remittance", "trigger_fish_kill"]


def qkey(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def qstr(i: int) -> str:
    return f"{i // 4}-Q{i % 4 + 1}"


def _assert_q(values, what):
    bad = sorted({q for q in values if qkey(q) > qkey(MAXQ)})
    if bad:
        raise guard.AccessDenied(f"E17: {what} has quarters after {MAXQ}: {bad}")


def load_components() -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")),
                     dtype={"province_code": str})
    _assert_q(df["quarter"], "components")
    return df


def load_rounds() -> pd.DataFrame:
    d = json.loads(guard.read_allowed_text(guard.E12_RUN / "details.json"))
    r = pd.DataFrame(d["two_layer"]["regional_layer_rounds"])
    _assert_q(r["quarter"], "SWS rounds")
    r["published"] = pd.to_datetime(r["published"])
    return r


def load_governing() -> dict:
    return json.loads(guard.read_allowed_text(guard.AL / "config" / "governing_model.json"))


def load_features(governing: dict) -> pd.DataFrame:
    cols = ["province_code", "quarter"] + governing["feature_set"]["candidates_section_3_3_2_6"] + ["cpi_dev"]
    df = guard.read_allowed_parquet(guard.PROC / "features_fused.parquet", cols)
    _assert_q(df["quarter"], "features_fused")
    return df


def load_topics() -> pd.DataFrame:
    df = guard.read_allowed_parquet(guard.PROC / "topic_proportions.parquet", ["province_code", "quarter", "topic_other_pct",
                                                                               "topic_outlier_pct"])
    _assert_q(df["quarter"], "topic_proportions")
    return df


def load_lgu() -> tuple[pd.DataFrame, pd.DataFrame]:
    pov = guard.read_allowed_parquet(guard.PROC / "lgu_poverty.parquet",
                                     ["province_code", "province_name", "lgu_code", "lgu_name", "year",
                                      "poverty_incidence_pct", "poverty_normalized", "source_note"])
    cen = guard.read_allowed_parquet(guard.PROC / "lgu_census.parquet",
                                     ["province_code", "lgu_code", "lgu_name", "lgu_type", "population_2020",
                                      "density_per_km2", "density_normalized", "population_source"])
    return pov, cen


def load_fies() -> pd.DataFrame:
    return guard.read_allowed_parquet(guard.PROC / "nns_fies.parquet",
                                      ["survey_cycle", "year", "region_name", "fies_moderate_severe_pct",
                                       "geographic_level", "provenance"])
