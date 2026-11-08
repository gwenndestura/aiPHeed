"""
tests/integration/test_e114_genuine_forecast.py
-----------------------------------------------
PROTOCOL_E114: protocol frozen; data hashed; leakage checks recorded true; untouched TEST 2013-2020 has 30 quarters
x 4 areas per lead; the unified LightGBM forecasts the change from the latest reading (not the reading itself); the
frozen success criteria are recorded and fail; the hunger-history group carries the skill; seals and served model
unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E114_Final_Run"
RES = E / "out" / "e114_results.json"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="E114 outputs missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


def test_protocol_and_data_hashes(res):
    assert hashlib.sha256((E / "PROTOCOL_E114.md").read_bytes()).hexdigest() == (E / "runner" / "PROTOCOL_SHA256.txt").read_text().strip() == res["protocol_sha256"]
    f = E / "data" / "sws_area_rounds_full.csv"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == res["data_sha256"][f.name]


def test_leakage_checks(res):
    assert res["leakage"]["train_targets_published_before_issue"] is True
    assert res["leakage"]["latest_reading_published_before_issue"] is True


def test_rows_point_in_time_and_not_carried_forward():
    R = pd.read_csv(E / "out" / "e114_rows.csv")
    assert (R["q"] == R["t"] + R["lead"]).all() and (R["q_last"] < R["t"] + 1).all()
    assert (R["issue"] > R["q_last"].map(lambda q: f"{q // 4}-{(q % 4) * 3 + 1:02d}-01")).all()
    t = R[(R["split"] == "TEST") & R["ULGBM"].notna() & R["y"].notna()]
    assert t.groupby("lead")["q"].nunique().to_dict() == {1: 30, 2: 30} and set(t["area"]) == {"NCR", "BL", "VIS", "MIN"}
    assert (t["ULGBM"] - t["RW"]).abs().mean() > .5             # forecasts move away from the latest reading


def test_frozen_criteria_fail_and_hunger_history_carries_skill(res):
    c = res["criteria"]
    assert c["1"]["passes"] is False and c["2"]["passes"] is False
    assert c["2"]["1_pooled_mse_below_RW_dm_p<0.10"] and not c["2"]["3_above_usual_brier_below_RW_and_MEAN"]
    ab = res["ablation_TEST"]
    assert ab["hunger_history"]["2"]["ci90"][0] > 0
    assert all(ab[g]["2"]["holm_p"] == 1.0 for g in ("market_prices", "climate", "employment", "news_nlp"))
    t2 = res["evaluation"]["L2|TEST"]
    assert t2["DAMP"]["mse"] < t2["ULGBM"]["mse"] < t2["RW"]["mse"]


def test_seals_and_served_model_unchanged(monkeypatch):
    lt = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER" / "sealed"
    for f, h in {"cr_prospective.csv": "dd293e2e", "cranc_prospective.csv": "07c99e56", "rizal_2027q1_companion.csv": "b1edb799"}.items():
        assert hashlib.sha256((lt / f).read_bytes()).hexdigest().startswith(h)
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
