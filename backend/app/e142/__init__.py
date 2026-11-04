"""
app.e142
--------
E142: survey-anchored provincial risk-STATE model (protocol E142-P1, docs/e142/PROTOCOL.md).

The latent state s(p, t) is the province's true relative food-insecurity logit (HFIAS moderate-or-severe vs national)
in quarter t. Measured rounds observe it with their survey error. Between rounds it reverts toward an indicator-based
structural level mu(x) with quarterly persistence phi (AR(1)); phi and the stationary deviation variance tau^2 are
estimated only from measured survey-to-survey transitions in each training set. The forecast for any quarter is
mu(x at issue) + phi^h x (filtered deviation at the last survey), with variance that grows with h, the quarters since
that survey. The quarterly form of the transition is an assumption (only multi-year survey gaps are observed).

E137-E141 are imported, never modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e142-state-1.0"
PROTOCOL_VERSION = "E142-P1"
OUT = BACKEND_DIR / "data" / "e142" / "out"
