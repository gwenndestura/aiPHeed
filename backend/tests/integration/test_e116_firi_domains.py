"""
tests/integration/test_e116_firi_domains.py
-------------------------------------------
PROTOCOL_E116: protocol frozen and data hashed; area mapping covers every region exactly once (Caraga in Mindanao);
area-level inputs vary between areas; every SWS reading and training target is published before the issue (via E114
rows); the corrected one-sided p agrees with the CI direction; frozen decisions recorded (fish at Lead 1 only); E115
issued no forecast; served model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E116_FIRI_Domains"
RES = E / "out" / "e116_results.json"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="E116 outputs missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


def test_protocol_and_data_hashes(res):
    assert hashlib.sha256((E / "PROTOCOL_E116.md").read_bytes()).hexdigest() == (E / "runner" / "PROTOCOL_SHA256.txt").read_text().strip() == res["protocol_sha256"]
    for f in ("area_cpi.csv", "area_fish.csv", "area_palay.csv"):
        assert hashlib.sha256((E / "data" / f).read_bytes()).hexdigest() == res["data_sha256"][f]


def test_area_mapping():
    log = json.loads((E / "data" / "fetch_log.json").read_text())
    assert Counter(log["fish"]["regions"].values()) == {"BL": 7, "MIN": 6, "VIS": 4, "NCR": 1}
    assert log["fish"]["regions"]["Region XIII (Caraga)"] == "MIN"
    for f in ("area_cpi.csv", "area_fish.csv"):
        d = pd.read_csv(E / "data" / f)
        assert set(d["area"]) == {"NCR", "BL", "VIS", "MIN"}
    c = pd.read_csv(E / "data" / "area_cpi.csv")
    assert c["ym"].max() <= 2026 * 12 + 8                       # nothing after September 2026


def test_rows_point_in_time_and_area_variation():
    R = pd.read_csv(E / "out" / "e116_rows.csv")
    assert (R["q"] == R["t"] + R["lead"]).all()
    assert (R["q_last"] <= R["t"]).all()                        # newest SWS reading used is never after the origin
    g = R[R["lead"] == 2].groupby("t")
    assert (g["AF_food"].nunique() > 1).mean() > .9 and (g["F_yoy"].nunique() > 1).mean() > .9
    assert (g["C-ONI"].nunique() <= 1).all()                     # national inputs stay national


def test_corrected_p_matches_direction_and_decisions(res):
    for key, c in res["contributions"].items():
        for d in ("market", "fish", "climate", "employment"):
            x = c[d]
            if x["ci90"][1] < 0:
                assert x["p_a_better"] < .5, (key, d)
            if x["ci90"][0] > 0:
                assert x["p_a_better"] > .5, (key, d)
    assert res["decision_domains"]["1"] == {"market": "not established", "fish": "adds information",
                                            "climate": "not established", "employment": "not established"}
    assert set(res["decision_domains"]["2"].values()) == {"not established"}
    assert "note_eval_fix" in res


def test_e115_suspended_without_forecasts():
    e115 = ROOT / "aipheed-backend-aligned" / "experiments" / "E115_Hunger_MeanReversion_Prospective"
    assert (e115 / "PROTOCOL_E115.md.SUSPENDED.txt").exists()
    assert not any((e115 / "out" / "forecasts").glob("*.csv")) if (e115 / "out" / "forecasts").exists() else True


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
