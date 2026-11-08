"""
app.e141
--------
E141: a third provincial HFIAS round (FNRI 8th National Nutrition Survey 2013, "Philippine Nutrition Facts and Figures
2013: Food Security", Appendix 33) recovered from the FNRI site's Internet Archive copy. Same instrument as FNRI 2015
and ENNS 2018/2019 (9-item HFIAS, 30-day recall, Coates et al. 2007 categories), 78 provinces, n = 35,635 households,
fieldwork 19 June - 4 December 2013 (continued 16 February - 15 April 2014).

It is used for:
    (1) an UNTOUCHED test of the structural relative-risk models (no model in this project has seen 2013);
    (2) chronological survey-round validation with three rounds (2013 -> 2015 -> 2018/2019), where every row now has an
        earlier measured anchor.
Protocol E141-P1: docs/e141/PROTOCOL.md. Earlier experiments (E137-E140) are imported, never modified.
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "e141-1.0"
PROTOCOL_VERSION = "E141-P1"
DATA = BACKEND_DIR / "data" / "e141"
RAW = DATA / "raw"
OUT = DATA / "out"
