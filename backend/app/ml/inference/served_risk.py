"""
app/ml/inference/served_risk.py
-------------------------------
Which risk-forecast module the dashboard and reports serve: ch1_system (AIPHEED_MAP_MODEL=ch1, or the FIRI default,
where ch1_system.active() is False and nothing changes) or foodinsecurity_system (AIPHEED_MAP_MODEL=foodinsecurity).

Call sites import this module in place of ch1_system and keep reading the same names (CH1.active(), CH1.rows(), ...):
every name not defined here is looked up on the selected module at call time.
"""
from __future__ import annotations

from app.ml.inference import ch1_system as _CH1


def engine():
    from app.ml.inference import foodinsecurity_system as FI

    return FI if FI.active() else _CH1


def key() -> str:
    """Cache-key suffix: empty for ch1_system (its cache keys are unchanged), '+fi' for the food-insecurity mode."""
    return "" if engine() is _CH1 else "+fi"


def __getattr__(name: str):
    return getattr(engine(), name)
