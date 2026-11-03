"""
app.e139
--------
E139: the final aiPHeed food-insecurity RISK system (protocol E139-P1, docs/e139/PROTOCOL.md).

Target: measured HFIAS moderate-or-severe food insecurity relative to the national level of the same survey
(continuous relative logit with survey error; E137 outcome builder, unchanged). Probability of elevated risk =
P(true relative logit > 0).

Primary model: LightGBM with a linear prior. A weighted ridge on poverty and measured-history features gives the
base score (init_score); LightGBM trees, conservative and few, learn what the base misses from all available groups.
Why: E137/E138 showed the measured signal is close to linear in poverty and in the region's measured level, which
step-function trees approximate badly with 125 rows; boosting from a linear prior keeps LightGBM as the learner of
non-linear and cross-group structure, and lets inner validation choose zero trees if the trees add nothing.

E137 and E138 are imported, never modified. All HFIAS rows were examined before, so results are development evidence;
confirmation comes from sealed predictions scored against the next provincial round.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e139-lgbm-1.0"
PROTOCOL_VERSION = "E139-P1"
OUT = BACKEND_DIR / "data" / "e139" / "out"
