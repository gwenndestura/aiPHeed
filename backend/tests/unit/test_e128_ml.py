"""
tests/unit/test_e128_ml.py
--------------------------
E128 regional food-insecurity ML workstream: frozen protocol hash, 2021+ window, as-of training rows (no target published
on or after the issue date), identical outer origins for all five models, persistence definition, frozen R1-R7 logic
(not evaluable = not passed), predictions reproducible from the saved fold artifacts, recorded verdict, and FIRI v2 /
FIRI3 untouched.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E128_Food_Insecurity_ML_Development"
HAS = (E / "out" / "summary.json").exists()
pytestmark = pytest.mark.skipif(not HAS, reason="E128 outputs not built")


def load(name, path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def R():
    return load("e128_run", E / "runner" / "run_e128.py")


@pytest.fixture(scope="module")
def panel(R):
    p, _ = R.panel_with_targets()
    return p


@pytest.fixture(scope="module")
def preds():
    return pd.read_csv(E / "out" / "predictions_raw.csv")


def test_protocol_frozen(R):
    assert R.check_protocol() == "c7a92670d65da9ddf04233739341f6765b719cf8338be2642bda2a9f3e8618f3"
    assert json.load(open(E / "out" / "summary.json"))["protocol_sha256"] == R.check_protocol()


def test_window_and_target(panel):
    assert panel["t"].min() == 2021 * 4 and panel["target_q"].min() >= 2021 * 4
    q = panel[(panel["lead"] == 1) & panel["y_bl_hunger"].notna()]
    assert len(q) == 20 and int(q["T1"].sum()) == 13
    assert set(q.loc[q["target_quarter"] >= "2023-Q4", "T1"]) == {1.0}      # saturation documented in the audit
    assert "2025-Q1" not in set(q["target_quarter"])                          # commissioned round excluded


def test_training_rows_published_before_issue(R, panel):
    for k in (1, 2, 3, 4):
        for t in range(2022 * 4, 2026 * 4 + 3):
            tr = R.training_rows(panel, t, k, "T1")
            iss = pd.Timestamp(R.BP.qstart(t + 1))
            assert (tr["y_pub_date"] < iss).all()
            assert (tr["target_q"] <= t).all()


def test_identical_origins_all_models(preds):
    for (tg, k), g in preds.groupby(["target", "lead"]):
        sets = {m: frozenset(x["origin"]) for m, x in g.groupby("model")}
        assert len(sets) == 5 and len(set(sets.values())) == 1, (tg, k)


def test_persistence_definition(panel, preds):
    p = preds[(preds["model"] == "M2_Persistence") & (preds["target"] == "T1")].merge(panel[["origin", "lead", "H1_bl_latest"]], on=["origin", "lead"])
    assert ((p["H1_bl_latest"] > 11.3).astype(float) == p["q"]).all()


def test_reliability_rule_logic(R):
    rows = pd.DataFrame({"y": [1.0] * 12, "q_X": [0.9] * 12, "persist": [1.0] * 12, "clim": [0.5] * 12, "maj": [1.0] * 12,
                         "target_q": range(12)})
    m, Rr, ok, oks, _ = R.reliability(rows, "X")
    assert np.isnan(m["balanced_accuracy"]) and not Rr["R3"]                  # one class: not evaluable = not passed
    assert not Rr["R1"] and Rr["R1_quarters_only (sensitivity)"] and not ok and not oks


def test_predictions_reproduce_from_artifacts(R, panel, preds):
    import lightgbm as lgb
    man = pd.read_csv(E / "E128_MODEL_ARTIFACT_MANIFEST.csv")
    for _, a in man[man["model"] == "M1_LightGBM"].head(12).iterrows():
        path = E / a["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == a["sha256"]
        x = panel[(panel["origin"] == a["origin"]) & (panel["lead"] == a["lead"])][a["features"].split(";")]
        q = float(lgb.Booster(model_file=str(path)).predict(x)[0])
        rec = preds[(preds["target"] == a["target"]) & (preds["model"] == "M1_LightGBM") & (preds["lead"] == a["lead"]) & (preds["origin"] == a["origin"])]
        assert q == pytest.approx(float(rec["q"].iloc[0]), abs=1e-9)


def test_recorded_verdict():
    s = json.load(open(E / "out" / "summary.json"))
    assert all(v == 0 for tg in s["max_reliable_lead"].values() for v in tg.values())
    h = pd.read_csv(E / "E128_RELIABLE_HORIZON_COMPARISON.csv")
    assert (h["max_reliable_lead_q"] == 0).all() and len(h) == 10


def test_production_untouched():
    firi = REPO / "backend" / "app" / "ml" / "inference" / "firi.py"
    firi3 = REPO / "backend" / "app" / "ml" / "inference" / "firi3.py"
    assert hashlib.sha256(firi.read_bytes()).hexdigest() == "0e583131a7de3b9844241d3927eede813077d7cccbf949cd8313973436d0f8e3"
    assert hashlib.sha256(firi3.read_bytes()).hexdigest() == "d8298024541f48ae9a472179c836fc1428ebae7fd83e58a24e47ab616d8e2cd1"
