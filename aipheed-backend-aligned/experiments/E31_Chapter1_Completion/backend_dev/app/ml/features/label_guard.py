"""
app/ml/features/label_guard.py  (E29, decision D9)
---------------------------------------------------
The legacy label path is leaky: app.ml.features.label_generator labels a province-quarter HIGH when its stress score
exceeds the median over ALL labelled quarters (global_threshold), so every training label depends on test-period
outcomes. config/governing_model.json records the same rule ("global median 14.6"). Its consumers are the legacy
trainer, evaluator and feature selector (and the served MODEL-A built with them).

The valid rule (E25-E29) is the origin-specific threshold: the median of the labels PUBLISHED before the forecast
origin (app.ml.features.risk_score_v2.reference_threshold; E28 runner Target.tau).

This guard makes the leaky path refuse by default:
  * generate_labels() raises LeakyLabelError unless the caller opts in explicitly;
  * any loader that receives a labels table carrying `global_threshold` raises the same error.
Opt-in (only to reproduce historical legacy outputs, never for a new evaluation): set the environment variable
AIPHEED_ALLOW_LEGACY_LEAKY_LABELS=1. Outputs produced that way remain LEGACY and are not E25-E29 evidence.
"""
from __future__ import annotations

import os

ENV = "AIPHEED_ALLOW_LEGACY_LEAKY_LABELS"
MESSAGE = ("The legacy labels use a whole-period median threshold (global_threshold): every label depends on "
           "test-period outcomes. Use the origin-specific threshold (risk_score_v2.reference_threshold / the E28 "
           f"evaluator) for any evaluation. To reproduce a historical LEGACY output only, set {ENV}=1.")


class LeakyLabelError(RuntimeError):
    pass


def legacy_allowed() -> bool:
    return os.getenv(ENV, "").strip() == "1"


def require_legacy_opt_in(where: str) -> None:
    if not legacy_allowed():
        raise LeakyLabelError(f"{where}: {MESSAGE}")


def assert_not_leaky(labels, where: str):
    """Refuse a labels table built with the whole-period median unless legacy reproduction is explicitly allowed."""
    cols = set(getattr(labels, "columns", []))
    if "global_threshold" in cols and not legacy_allowed():
        raise LeakyLabelError(f"{where}: {MESSAGE}")
    return labels
