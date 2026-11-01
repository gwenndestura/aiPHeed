"""
app/forecasting
---------------
The auditable hunger-forecasting core (backend completion, 2026-11):
evidence.py (status enums), as_of.py (the one point-in-time selector), validation.py (input checks),
sws.py (the SWS target with sampling SE and the frozen tolerance), models.py (persistence, damped trend, SEAS-LLM),
artifact.py (frozen, hashed model parameters), inference.py (forecasts from an artifact, never retraining),
explain.py (exact additive explanations), geography.py (the 142 CALABARZON LGUs with explicit status).

Nothing here changes the served dashboard model (app.ml.inference.ch1_system / thesis_system).
"""
