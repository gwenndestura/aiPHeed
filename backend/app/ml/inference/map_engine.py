"""
app/ml/inference/map_engine.py
------------------------------
The model behind the dashboard's map, rankings, explanations, summary, reports and early warnings: the registry's approved
production model E168 (app.ml.inference.e168_system) when it is in production and exported, otherwise the Chapter I
price-pressure index (app.ml.inference.ch1_system). AIPHEED_MAP_MODEL=ch1 forces the Chapter I index.

Attribute access is delegated at call time (PEP 562), so `from app.ml.inference import map_engine as CH1` works wherever
ch1_system was used.
"""
from __future__ import annotations

from app.ml.inference import ch1_system, e168_system, hcw_system


def selected():
    # Setup H + class weights (hcw-lgbm-1.0) when it is the registry's production model (branch aiPHeed/setup-h-cw-dashboard)
    if hcw_system.active():
        return hcw_system
    return e168_system if e168_system.active() else ch1_system


def __getattr__(name: str):
    mod = selected()
    value = getattr(mod, name)
    if mod is not e168_system or name in ("relabel", "served_id", "active", "rows", "row"):
        return value
    # E184 (docs/e184/PROTOCOL.md): when the owner has promoted E184, its name, id and accuracy replace E168's in every
    # text the dashboard reads through this engine. With E168 in production, relabel returns its argument unchanged.
    if callable(value):
        def wrapped(*a, **k):
            return e168_system.relabel(value(*a, **k))
        wrapped.__name__ = getattr(value, "__name__", name)
        return wrapped
    return e168_system.relabel(value)
