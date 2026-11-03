"""
app.hfias
---------
Provincial household food-access insecurity measured with the Household Food Insecurity Access Scale (HFIAS), the
instrument DOST-FNRI used in the 2015 Food Security Survey and in the 2018-2019 Expanded National Nutrition Survey
(ENNS) provincial monographs. Two comparable waves per province: 2015, then 2018 or 2019 (ENNS rolling design).

Target: share of households moderately or severely food insecure (HFIAS categories, FNRI scoring after Coates et al.
2007), % of households, province. HFIAS is not FIES: no value from FIES (SDG 2.1.2) is mixed into this target.

Sources (public; FNRI eNutrition is unreachable from this network, so the provincial monographs are read from the
Internet Archive's copies of the FNRI uploads; every value keeps its source URL, capture timestamp and file hash):
    data/fi_labels/raw/fnri/2015_FOOD_SECURITY_SURVEY.pdf  (Appendices 1-4)
    https://enutrition.fnri.dost.gov.ph/uploads/<year> ... <province>.pdf via web.archive.org
"""
from __future__ import annotations

from app.paths import BACKEND_DIR

VERSION = "hfias-1.0"
DATA = BACKEND_DIR / "data" / "hfias"
RAW = DATA / "raw"            # downloaded PDFs (gitignored, like other third-party FNRI PDFs); hashes in the manifest
CLEAN = DATA / "clean"
OUT = DATA / "out"
MODEL = DATA / "model"
CALABARZON = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
