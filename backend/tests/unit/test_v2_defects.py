"""
tests/unit/test_v2_defects.py
-----------------------------
v2 step 5 defect fixes: D3 (thesis pickle re-exported under the pinned scikit-learn, identical scores, no version
warning), D9 (the missing legacy pickle still fails loudly and is not silently replaced), and the P0H4 relabel
(price-pressure risk index, computation unchanged, never presented as food insecurity).
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pytest

from app.forecasting.safe_load import MODELS, manifest, verified_joblib_load
from app.ml.inference import ch1_system as CH1
from app.ml.inference import thesis_predictor as TP


def _blend(b: dict, rows: pd.DataFrame) -> np.ndarray:
    p = b["lgbm_model"].predict_proba(rows[b["lgbm_feature_cols"]])[:, 1]
    lr = b["lr_model"].predict_proba(b["lr_scaler"].transform(rows[b["lr_feature_cols"]].fillna(0.0)))[:, 1]
    w = b.get("blend_weight_lgbm", 0.5)
    return w * p + b.get("blend_weight_lr", 1 - w) * lr


def test_d3_reexport_identical_and_version_consistent():
    assert TP.MODEL_PATH.name == "thesis_food_insecurity_model_skl180.joblib"
    assert {"thesis_food_insecurity_model.joblib", TP.MODEL_PATH.name} <= set(manifest())
    panel = pd.read_parquet(TP.PANEL_PATH)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        new = verified_joblib_load(TP.MODEL_PATH)
    assert not [x for x in w if "InconsistentVersion" in type(x.message).__name__]
    old = verified_joblib_load(MODELS / "thesis_food_insecurity_model.joblib")
    assert np.array_equal(_blend(old, panel), _blend(new, panel))


def test_d9_missing_legacy_pickle_fails_loudly():
    from app.ml.inference import predictor as P
    assert not P.MODEL_PATH.exists()                      # deliberately removed in 8725531e; not restored
    p = P.Predictor.__new__(P.Predictor)
    with pytest.raises(FileNotFoundError):
        P.Predictor.load(p)


def test_p0h4_relabelled_as_price_pressure_not_food_insecurity():
    ind = CH1.INDICATOR
    assert ind["name"].startswith("Price-pressure risk index") and "food-insecurity" not in ind["name"].lower()
    assert ind["is_food_insecurity_measurement"] is False
    assert ind["food_insecurity_forecast"]["endpoint"] == "/api/v1/final/food-insecurity/outlook"     # release gate
    assert ind["id"] == "chapter1_food_insecurity_risk"   # clients key on the id; the computation is unchanged
    assert ind["caveat"].startswith("This is a price-pressure risk index, not a food-insecurity forecast")
