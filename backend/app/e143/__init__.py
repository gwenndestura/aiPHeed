"""
app.e143
--------
E143: audit of the E142 provincial risk-state model and pre-registered successors (protocol E143-P1,
docs/e143/PROTOCOL.md).

The audit (app.e143.audit) reads E142's locked out-of-fold files and the E141 panel; it never rewrites E137-E142 or
their results. Counterfactual refits in the audit (e.g. an O1 model given a persistence value it could not have
estimated) are labelled DIAGNOSTIC and are never candidates.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e143-1.0"
PROTOCOL_VERSION = "E143-P1"
OUT = BACKEND_DIR / "data" / "e143" / "out"
