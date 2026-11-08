"""
app.pfi
-------
PFI: survey-anchored provincial food-insecurity estimation and next-quarter forecasting for CALABARZON.

Outcome: share of households moderately or severely food insecure (FIES, SDG 2.1.2; 12-month recall), the one
food-insecurity construct measured comparably across regions and waves (FNRI NNS/ENNS via PSA OpenSTAT).

Three layers, each with its own evidence (docs/pfi/METHODOLOGY.md):
  1. Level (small-area): logit FIES of the 17 regions in 2023 regressed on official structural covariates, validated
     leave-one-region-out; applied to provinces and benchmarked to the direct CALABARZON estimate (19.1%).
  2. Bridge (time): change in logit FIES = lambda x change in logit SWS hunger (12-month mean), fitted on the national
     2021->2023 waves and checked on a held-out wave (CALABARZON 2025, provisional).
  3. Projection: the next calendar quarter's SWS (FI9 damped persistence, release-aware) feeds the bridge.

Observed values, model estimates and forecasts are labelled separately everywhere. Nothing is trained on a request.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "pfi-1.0"
DATA = BACKEND_DIR / "data" / "pfi"
RAW = DATA / "raw"
OUT = DATA / "out"
MODEL = DATA / "model"
PROVINCES = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
