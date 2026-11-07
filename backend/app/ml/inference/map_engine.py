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

from app.ml.inference import ch1_system, e168_system


def selected():
    return e168_system if e168_system.active() else ch1_system


def __getattr__(name: str):
    return getattr(selected(), name)
