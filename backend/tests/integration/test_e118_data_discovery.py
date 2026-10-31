"""
tests/integration/test_e118_data_discovery.py
---------------------------------------------
E118: raw downloads match their logged hashes (unmodified); cleaned copies never contain Quezon City or non-CALABARZON
units; key provincial monthly series cover all five provinces; no annual value is spread into months; the inventory
classifies every dataset A-E with a reason; production model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E118_FAO_Data_Discovery"
pytestmark = pytest.mark.skipif(not (E / "data" / "acquisition_log.json").exists(), reason="E118 outputs missing")
PROVS = {"Cavite", "Laguna", "Batangas", "Rizal", "Quezon"}


def test_raw_files_unmodified():
    log = json.loads((E / "data" / "acquisition_log.json").read_text())
    for key, m in log["tables"].items():
        if "sha256" in m:
            assert hashlib.sha256((E / "data" / "raw" / f"psa_{key}.csv").read_bytes()).hexdigest() == m["sha256"], key
    for prov, m in log["power"].items():
        assert hashlib.sha256((E / "data" / "raw" / f"nasa_power_monthly_{prov}.json").read_bytes()).hexdigest() == m["sha256"], prov


def test_cleaned_geography_and_frequency():
    allowed = PROVS | {"Region IV-A", "Lucena City (HUC, Quezon)"}
    for f in (E / "data" / "clean").glob("*.csv"):
        d = pd.read_csv(f)
        assert set(d["unit"]) <= allowed, f.name
        assert set(d["freq"]) <= {"M", "Q"}, f.name                        # no annual values spread into periods
        assert not d.duplicated(["unit", "item", "period"]).any(), f.name


def test_key_series_cover_all_provinces():
    cov = pd.read_csv(E / "out" / "acquired_coverage.csv").set_index("dataset")
    for k in ("retail_cereals", "retail_fish", "farmgate_cereals", "prod_vegetables_rootcrops", "nasa_power"):
        assert cov.loc[k, "n_provinces"] == 5, k
    assert cov.loc["nasa_power", "first_period"] == "1981-01"
    ov = json.loads((E / "out" / "overlap_checks.json").read_text())
    assert ov["bottom30_food_yoy_vs_all_income_food_yoy"]["corr"] > .9      # recorded as largely redundant


def test_inventory_classified():
    inv = pd.read_csv(E / "FAO_FOOD_SECURITY_DATA_INVENTORY.csv")
    assert inv["id"].is_unique and set(inv["classification"]) <= set("ABCDE")
    assert inv["classification_reason"].notna().all() and inv["fao_dimension"].notna().all()
    t = pd.read_csv(E / "DIRECT_FOOD_INSECURITY_TARGETS.csv")
    assert not (t["frequency"].str.contains("monthly|quarterly") & t["geography"].str.startswith("province")).any()  # no repeated provincial FI target found
    for f in ("PROVINCIAL_MONTHLY_QUARTERLY_DATA.csv", "FOOD_AVAILABILITY_DATA.csv", "FOOD_ACCESS_DATA.csv", "FOOD_UTILIZATION_DATA.csv",
              "FOOD_STABILITY_DATA.csv", "DATA_SOURCE_AND_ACCESS_REGISTER.md", "GEOGRAPHIC_AND_TEMPORAL_COVERAGE_REPORT.md",
              "DATA_QUALITY_AND_RELEASE_TIMING_REPORT.md"):
        assert (E / f).exists(), f


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
