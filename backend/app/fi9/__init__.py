"""aiPHeed FI9: the final one-quarter-ahead (Lead 1) food-insecurity outlook, frozen protocol, audit and serving.

FI9 adds no new predictor and repeats no failed experiment. It
  * fixes the forecast target in writing (docs/fi9/FOOD_INSECURITY_TARGET_DEFINITION.md) before evaluation;
  * locks a selection protocol (development targets <= 2017, test targets >= 2018) and the FI7 reliability rules;
  * re-runs the FI7 walk-forward at Lead 1 for every baseline (reproducibility) and adds the controlled five-domain
    and news ablation, numeric level forecasts, calibration and label-uncertainty checks;
  * separates training (an artifact written at issue time) from inference (the API only reads files);
  * computes the issue and target quarters from the date, never from a constant.

Lead 1 = the calendar quarter after the issue quarter; issue = last day of the issue quarter's second month (FI7
operational timing). Outputs: data/fi9; reports: docs/fi9.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "fi9-1.0"
FI9 = BACKEND_DIR / "data" / "fi9"
OUT = FI9 / "out"
MODEL = FI9 / "model"
DOCS = BACKEND_DIR.parent / "docs" / "fi9"
for _d in (FI9, OUT, MODEL, DOCS):
    _d.mkdir(parents=True, exist_ok=True)
