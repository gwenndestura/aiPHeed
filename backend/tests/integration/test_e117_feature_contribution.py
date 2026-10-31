"""
tests/integration/test_e117_feature_contribution.py
---------------------------------------------------
E117: protocol frozen; panel hash recorded and identical to the corrected pipeline; strict mode uses only verified
features; every pre-declared variant and comparator scored for both leads; decisions follow the frozen rule; the
prospective forecasts are sealed only for targets with no SWS reading; served model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E117_Feature_Contribution"
PANEL = ROOT / "aipheed-backend-aligned" / "experiments" / "CORRECTED_PIPELINE" / "out" / "regional_forecast_panel.csv"
pytestmark = pytest.mark.skipif(not (E / "out" / "e117_results.json").exists(), reason="E117 outputs missing")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def res():
    return json.loads((E / "out" / "e117_results.json").read_text())


def test_protocol_and_panel_frozen(res):
    assert sha(E / "EXPERIMENT_PROTOCOL.md") == (E / "runner" / "PROTOCOL_SHA256.txt").read_text().strip() == res["protocol_sha256"]
    assert sha(PANEL) == res["panel_sha256"]


def test_all_variants_and_comparators_scored():
    A = pd.read_csv(E / "FEATURE_ABLATION_RESULTS.csv")
    need = {"A", "B", "C", "D", "E", "G", "H", "I", "IA1", "IA2", "IA3", "IC1", "IC2", "IC3", "IC4", "IE1", "IN1",
            "X1", "X1n", "X2", "X2n", "X3", "X3n", "S_A", "S_G", "S_C2", "S_ALL"}
    assert need <= set(A["variant"]) and set(A["lead"]) == {1, 2}
    M = pd.read_csv(E / "MODEL_COMPARISON_RESULTS.csv")
    assert {"RW", "MEAN", "DAMP", "AR1", "RIDGE", "A", "H", "I"} <= set(M["model"])
    pooled = M[M["period"] == "POOLED_2003_2026"]
    assert (pooled["level_quarters"] == 90).all() and (pooled["level_rows"] == 360).all()


def test_strict_mode_uses_only_verified_features():
    R = pd.read_csv(E / "out" / "e117_rows.csv")
    # strict base equals provisional base (no unverified feature in base); strict variants differ from provisional ones
    assert np.allclose(R["S_A"], R["A"], equal_nan=True)
    import sys
    sys.path.insert(0, str(E / "runner"))
    import run_e117 as E7
    for n, cols in E7.STRICT.items():
        assert not set(cols) & set(E7.UNVERIFIED), n


def test_decisions_follow_frozen_rule():
    D = pd.read_csv(E / "DOMAIN_CONTRIBUTION_RESULTS.csv")
    for r in D[D["decision"].isin(["improves", "possible noise", "conditional", "no measurable value"]) & D["pooled_ci90_high"].notna()].itertuples():
        if r.decision == "improves":
            assert r.pooled_ci90_high < 0
        if r.decision == "possible noise":
            assert r.pooled_ci90_low > 0
    assert (D.loc[D["domain"] == "ofw_remittances", "decision"].str.startswith("not testable")).all()
    I = pd.read_csv(E / "INDIVIDUAL_INDICATOR_RESULTS.csv")
    imp = I[I["decision"] == "improves"]
    assert set(zip(imp["indicator"], imp["lead"])) == {("C3", 1)}
    assert (imp["ci90_high"] < 0).all() and (imp["holm_p"] < .10).all()


def test_prospective_seal():
    man = json.loads((E / "out" / "prospective_forecasts.sha256").read_text())
    assert sha(E / "out" / "prospective_forecasts.csv") == man["sha256"]
    P = pd.read_csv(E / "out" / "prospective_forecasts.csv")
    assert set(P["target"]) == {"2026-Q4", "2027-Q1"} and len(P) == 12
    sws = pd.read_csv(ROOT / "aipheed-backend-aligned" / "experiments" / "E114_Final_Run" / "data" / "sws_area_rounds_full.csv")
    assert not set(sws["quarter"]) & set(P["target"])          # no reading of a sealed target exists in the data
    assert man["latest_sws_published_in_data"] < man["sealed_at_utc"][:10]


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
