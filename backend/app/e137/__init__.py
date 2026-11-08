"""
app.e137
--------
E137 SARF: survey-anchored food-insecurity RISK model (two layers, see docs/e137/PROTOCOL.md).

Layer S ("where"): LightGBM learned on HFIAS province-rounds pooled nationally (FNRI 2015, ENNS 2018/2019). The target is
the province's moderate-or-severe food insecurity relative to the national value of the same survey (relative logit),
with its survey error. No quarterly label is created; indicators are predictors only.

Layer T ("when"): regional timing evidence. It is taken from the locked FI6/FI6-N studies (SWS Balance Luzon); it is not
re-run here, because those quarters have already been scored.

Experiment history: hfias-1.0 (rejected) used the same HFIAS rows as a prevalence target. E137 is a new protocol; the
ENNS rows are development evidence only (owner decision D-3, 2026-11-03).
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e137-sarf-1.0"
PROTOCOL_VERSION = "E137-P1"
DATA = BACKEND_DIR / "data" / "e137"
RAW = DATA / "raw"
OUT = DATA / "out"
CALABARZON = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
