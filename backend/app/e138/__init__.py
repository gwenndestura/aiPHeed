"""
app.e138
--------
E138: what the available indicators can and cannot tell about food-insecurity RISK (protocol E138-P1,
docs/e138/PROTOCOL.md). Two questions are kept apart:

    WHERE  structural relative risk between provinces (HFIAS moderate-or-severe vs the national level of the same
           survey). Controlled comparison of model classes and feature groups on E137's rows, folds and metrics.
    WHEN   change in a province's relative position between surveys (2015 -> ENNS 2018/2019), the only measured
           within-province change; plus the locked Layer T (SWS) record.

E137 (rejected) is not modified; its outcome and feature builders are imported unchanged. All rows were examined by
hfias-1.0 and E137, so every E138 result is development evidence. The confirmatory test is a sealed prediction for the
next provincial survey round.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e138-1.0"
PROTOCOL_VERSION = "E138-P1"
OUT = BACKEND_DIR / "data" / "e138" / "out"
RAW = BACKEND_DIR / "data" / "e138" / "raw"
