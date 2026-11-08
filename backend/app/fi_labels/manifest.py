"""Source and download manifest for the food-insecurity label sources (acquired and not acquired).

    python -m app.fi_labels.manifest
"""
from __future__ import annotations

import hashlib

import pandas as pd

from app.fi_labels.published import CLEAN, RAW

ACQUIRED = [
    ("fnri/2015_FOOD_SECURITY_SURVEY.pdf", "https://enutrition.fnri.dost.gov.ph/uploads/2015_FOOD_SECURITY_SURVEY.pdf", 2015,
     "FNRI 2015 Food Security Survey report (HFIAS; region and province tables with SE/CI, Appendices 1-4)"),
    ("fnri/10_2023_NNS_REGIONAL_ESTIMATES_OF_SELECTED_INDICATORS.pdf",
     "https://enutrition.fnri.dost.gov.ph/uploads/10_2023_NNS_REGIONAL%20ESTIMATES%20OF%20SELECTED%20INDICATORS.pdf", 2023,
     "FNRI 2023 NNS regional estimates (summary ranking of household food insecurity by region)"),
    ("fnri/2._Household_and_Food_Security_.pdf",
     "https://enutrition.fnri.dost.gov.ph/images/nns-2023/2.%20Household%20%26%20Food%20Security%20.pdf", 2023,
     "FNRI 2023 NNS household and food security release (moderate-to-severe by region with 95% CI)"),
    ("owner_supplied/aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx", "owner-supplied (C:/Users/admin/Downloads)", "2015-2025",
     "owner-curated workbook: FNRI 2015 provinces, ENNS provincial (via DEPDev RDP), PSA subsistence/thresholds, regional benchmarks"),
    ("owner_supplied/2023_NNS_Overview.pdf", "owner-supplied (C:/Users/admin/Downloads/1. 2023 NNS - Overview.pdf)", 2023,
     "FNRI 2023 NNS overview: 117 survey areas (81 provinces, 33 HUCs, 3 urban areas), ~384 households each, designed for "
     "national and regional estimates"),
    ("psa/psa_sdg_2_1_2_fies.csv", "https://openstat.psa.gov.ph/PXWeb/api/v1/en/DB/3I/G02/0023I3B2121.px", "2019/2021/2023",
     "PSA OpenSTAT SDG 2.1.2.p1, FIES-based household moderate-or-severe food insecurity"),
]
NOT_ACQUIRED = [
    ("FNRI ENNS 2018, 2019, 2021 Food Security Survey public-use file", "https://enutrition.fnri.dost.gov.ph/puf-dataset.php?xx=2018747",
     "blocked: the site firewall returns 'Web Page Blocked! ... Attack ID 20000007' for this network address (curl and the "
     "in-app browser, 2026-11-03), later for the whole site; not bypassed"),
    ("FNRI NNS 2015 Food Security Survey public-use file", "https://enutrition.fnri.dost.gov.ph/puf-dataset.php?xx=2015480",
     "blocked: same firewall response"),
    ("FAO Philippines FIES microdata (Gallup World Poll 2015)", "https://microdata.fao.org/index.php/catalog/783",
     "not public: 'Data available from external repository. For access to microdata, please contact ...' (a data request); "
     "national only, and FAO discourages sub-national estimates"),
    ("DEPDev CALABARZON RDP 2023-2028 midterm results matrix (source of ENNS provincial values)",
     "https://calabarzon.depdev.gov.ph/wp-content/uploads/2026/02/RMs-Complete-ao-0128_compressed.pdf",
     "HTTP 403 to scripted download (retried 2026-11-03); the browser offered a file download; not read"),
    ("FNRI 2018/2019/2021 ENNS regional estimates (pooled 51.5% HFIAS)",
     "https://enutrition.fnri.dost.gov.ph/download.php?path=uploads%2F2018%2C+2019+and+2021+ENNS+Regional+Estimates_updated+as+of+11Apr24.pdf",
     "blocked: FNRI firewall page"),
    ("2023 NNS household food-security public-use file", "https://enutrition.fnri.dost.gov.ph/",
     "not verified: the PUF catalogue is unreachable from this network; only the published 2023 regional results were used"),
]


def build() -> pd.DataFrame:
    rows = []
    for rel, url, year, what in ACQUIRED:
        p = RAW / rel
        rows.append({"file": rel, "status": "acquired", "source_url": url, "survey_year": year, "downloaded": "2026-11-03",
                     "format": p.suffix.lstrip("."), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                     "content": what, "terms": "public download from the official site"})
    for name, url, why in NOT_ACQUIRED:
        rows.append({"file": name, "status": "not acquired", "source_url": url, "content": why})
    m = pd.DataFrame(rows)
    CLEAN.mkdir(parents=True, exist_ok=True)
    m.to_csv(RAW / "MANIFEST.csv", index=False, lineterminator="\n")
    return m


if __name__ == "__main__":
    print(build()[["file", "status", "bytes"]].to_string())
