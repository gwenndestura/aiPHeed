"""
AUDIT D3: models/thesis_food_insecurity_model.joblib was pickled with scikit-learn 1.7.2 while requirements.txt pins
1.8.0, so unpickling warns (InconsistentVersionWarning). This re-exports the SAME fitted objects under the pinned
version to a NEW file (the original is kept untouched), records it in MODEL_MANIFEST.json, and proves the blended
score is identical on every row of the thesis panel. Write-once: refuses if the new file exists.

    cd backend && python -I scripts/reexport_thesis_model.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.forecasting.safe_load import record, verified_joblib_load  # noqa: E402
from app.ml.inference import thesis_predictor as TP  # noqa: E402

OLD = BACKEND / "models" / "thesis_food_insecurity_model.joblib"
NEW = BACKEND / "models" / "thesis_food_insecurity_model_skl180.joblib"


def blended(bundle: dict, rows: pd.DataFrame) -> np.ndarray:
    p = bundle["lgbm_model"].predict_proba(rows[bundle["lgbm_feature_cols"]])[:, 1]
    lr = bundle["lr_model"].predict_proba(bundle["lr_scaler"].transform(rows[bundle["lr_feature_cols"]].fillna(0.0)))[:, 1]
    w = bundle.get("blend_weight_lgbm", 0.5)
    total = w * p + bundle.get("blend_weight_lr", 1 - w) * lr
    if bundle.get("weak_model") is not None and bundle.get("blend_weight_weak", 0.0) > 0:
        xw = bundle["weak_scaler"].transform(rows[bundle["weak_feature_cols"]].fillna(0.0))
        total = total + bundle["blend_weight_weak"] * bundle["weak_model"].predict_proba(xw)[:, 1]
    return total


def main() -> None:
    if NEW.exists():
        sys.exit(f"{NEW.name} exists: re-export is write-once")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        old = verified_joblib_load(OLD)
    old_warn = [str(x.message)[:120] for x in w if "InconsistentVersion" in type(x.message).__name__]
    panel = pd.read_parquet(TP.PANEL_PATH)
    s_old = blended(old, panel)
    joblib.dump(old, NEW)
    record(NEW)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        new = verified_joblib_load(NEW)
    new_warn = [str(x.message)[:120] for x in w if "InconsistentVersion" in type(x.message).__name__]
    s_new = blended(new, panel)
    diff = float(np.max(np.abs(s_old - s_new)))
    print(f"scikit-learn {sklearn.__version__}; panel rows {len(panel)}; max |score diff| = {diff}")
    print(f"warnings loading old: {len(old_warn)}; loading new: {len(new_warn)}")
    if diff != 0.0 or new_warn:
        NEW.unlink()
        sys.exit("re-export not identical or still version-inconsistent: removed the new file")


if __name__ == "__main__":
    main()
