"""
tests/unit/test_e129_feasibility.py
-----------------------------------
E129 provincial target feasibility: all 14 deliverables present, no model trained, E128 preserved, CPI decomposition
reproducible, no food-insecurity target marked as Lead 1-4 evaluable, no SWS copy used as a provincial label, and
FIRI v2 / FIRI3 untouched.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E129_Provincial_Food_Insecurity_Feasibility"
E128 = REPO / "aipheed-backend-aligned" / "experiments" / "E128_Food_Insecurity_ML_Development"
pytestmark = pytest.mark.skipif(not (E / "out" / "cpi_audit.json").exists(), reason="E129 outputs not built")
FILES = ["E129_PROVINCIAL_TARGET_INVENTORY.csv", "E129_PROVINCIAL_DATA_AVAILABILITY.csv", "E129_PSA_PROVINCIAL_CPI_AUDIT.md",
         "E129_FIVE_TRIGGER_GROUP_GEOGRAPHIC_AUDIT.csv", "E129_SWS_REGIONAL_TARGET_LIMITATION.md", "E129_PRE_2021_SWS_FEASIBILITY.md",
         "E129_PROVINCIAL_TARGET_CONSTRUCTION_OPTIONS.md", "E129_TARGET_VALIDITY_DECISION.md", "E129_PROVINCIAL_PANEL_FEASIBILITY.csv",
         "E129_R1_R7_PROVINCIAL_APPLICABILITY.md", "E129_VALIDATION_DESIGN.md", "E129_LEAD_1_TO_4_DATA_SUFFICIENCY.csv",
         "E129_PROVINCIAL_FORECASTING_RECOMMENDATION.md", "E129_FINAL_DECISION.md"]


def test_deliverables_and_no_training():
    assert all((E / f).exists() for f in FILES)
    assert not list(E.rglob("*.pkl")) and not list(E.rglob("*.txt"))          # no model artifacts
    assert "PROVINCIAL TARGET NOT READY" in (E / "E129_FINAL_DECISION.md").read_text(encoding="utf-8")


def test_e128_preserved():
    assert hashlib.sha256((E128 / "E128_FROZEN_EXPERIMENT_PROTOCOL.md").read_bytes()).hexdigest() == \
        "c7a92670d65da9ddf04233739341f6765b719cf8338be2642bda2a9f3e8618f3"
    s = json.load(open(E / "out" / "e129_summary.json"))
    assert s["inputs"]["e128_summary"] == hashlib.sha256((E128 / "out" / "summary.json").read_bytes()).hexdigest()


def test_cpi_decomposition_reproducible():
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location("e129_cpi", E / "runner" / "cpi_audit.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    d = m.decompose(m.quarterly_yoy().loc["food"])
    rec = json.load(open(E / "out" / "cpi_audit.json"))["cpi_food_yoy"]
    assert d["quarters"] == 23 and d["share_time"] == pytest.approx(rec["share_time"], abs=1e-12)
    assert d["share_province_persistent"] < 0.02 and d["share_time"] > 0.7


def test_no_fi_target_lead_evaluable():
    inv = pd.read_csv(E / "E129_PROVINCIAL_TARGET_INVENTORY.csv")
    ok = inv[inv["supports_lead_1_4_evaluation"].str.startswith("yes")]
    assert list(ok["id"]) == ["P13"] and "food-price condition" in ok["what_it_measures"].iloc[0]
    assert inv.set_index("id").loc["P14", "e129_assessment"].startswith("rejected")
    suf = pd.read_csv(E / "E129_LEAD_1_TO_4_DATA_SUFFICIENCY.csv")
    fi = suf[suf["candidate"].str.startswith("P1-P3")]
    assert (fi["evaluation_rows"] == 0).all()


def test_shared_features_not_provincial():
    g = pd.read_csv(E / "E129_FIVE_TRIGGER_GROUP_GEOGRAPHIC_AUDIT.csv").set_index("feature")
    for f in ("oni_quarter_mean", "typhoons_PAR", "unemployment_rate_pct", "E2_remittance_decline_pct", "news_gdelt_shortage_share"):
        assert g.loc[f, "genuinely_varies_across_provinces"] == "no"
    assert g.loc["cpi_food_yoy_pct", "genuinely_varies_across_provinces"] == "yes"


def test_production_untouched():
    inf = REPO / "backend" / "app" / "ml" / "inference"
    assert hashlib.sha256((inf / "firi.py").read_bytes()).hexdigest() == "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3"
    assert hashlib.sha256((inf / "firi3.py").read_bytes()).hexdigest() == "d8298024541f48ae9a472179c836fc1428ebae7fd83e58a24e47ab616d8e2cd1"
