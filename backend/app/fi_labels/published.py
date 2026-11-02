"""Extract the published CALABARZON food-insecurity estimates into clean tables.

    python -m app.fi_labels.published        # needs `pypdf` (the extraction was run once; the CSVs are committed)

Sources (originals in data/fi_labels/raw, unchanged):
  * FNRI 2015 Food Security Survey report, Appendices 1-4 (pp. 75, 77, 79, 81): proportion of households food secure,
    mildly, moderately and severely food insecure (HFIAS), with SE, 95 % CI and CV, by region and province.
  * PSA OpenSTAT SDG 2.1.2.p1 (FIES-based household moderate-or-severe food insecurity): national 2019, 2021, 2023;
    regions 2023.
  * FNRI 2023 NNS "Household and Food Security" release: 95 % CI for the CALABARZON 2023 estimate.
"""
from __future__ import annotations

import csv
import io
import re

import pandas as pd

from app.paths import BACKEND_DIR

RAW = BACKEND_DIR / "data" / "fi_labels" / "raw"
CLEAN = BACKEND_DIR / "data" / "fi_labels" / "clean"
GEO = ["CALABARZON", "Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
APPENDIX = {75: "food_secure", 77: "mildly_food_insecure", 79: "moderately_food_insecure", 81: "severely_food_insecure"}


def hfias_2015() -> pd.DataFrame:
    from pypdf import PdfReader

    r = PdfReader(str(RAW / "fnri" / "2015_FOOD_SECURITY_SURVEY.pdf"))
    rows = []
    for page, cat in APPENDIX.items():
        text = r.pages[page - 1].extract_text() or ""
        for g in GEO:
            m = re.search(rf"^\s*{g}\s+([\d,]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", text, re.M)
            if not m:
                raise ValueError(f"{g} not found on page {page}")
            n, p, se, lo, hi, cv = m.groups()
            rows.append({"survey": "2015 NNS Food Security Survey (FNRI)", "instrument": "HFIAS", "reference_period": "past 30 days",
                         "year": 2015, "geography": g, "level": "region" if g == "CALABARZON" else "province",
                         "category": cat, "n_households": int(n.replace(",", "")), "percent": float(p), "se": float(se),
                         "ci95_low": float(lo), "ci95_high": float(hi), "cv_percent": float(cv),
                         "source": f"2015_FOOD_SECURITY_SURVEY.pdf, Appendix {list(APPENDIX).index(page) + 1}, p. {page}"})
    return pd.DataFrame(rows)


def fies_psa() -> pd.DataFrame:
    text = (RAW / "psa" / "psa_sdg_2_1_2_fies.csv").read_bytes().decode("latin-1")
    rows = list(csv.reader(io.StringIO(text)))
    hdr = rows[0]
    out = []
    for r in rows[1:]:
        geo = r[0].strip(". ")
        for y, v in zip(hdr[1:], r[1:]):
            if re.match(r"^\d+(\.\d+)?$", v.strip()):
                out.append({"survey": "PSA OpenSTAT SDG 2.1.2.p1 (FNRI ENNS/NNS)", "instrument": "FIES",
                            "reference_period": "past 12 months", "year": int(y), "geography": geo,
                            "level": "national" if geo == "PHILIPPINES" else "region",
                            "category": "moderate_or_severe_food_insecurity", "percent": float(v),
                            "source": "openstat.psa.gov.ph DB/3I/G02/0023I3B2121.px"})
    d = pd.DataFrame(out)
    ci = (d["geography"] == "Region IV-A") & (d["year"] == 2023)
    d.loc[ci, "ci95_low"], d.loc[ci, "ci95_high"] = 17.0, 21.1
    d.loc[ci, "source"] += "; 95% CI from 2._Household_and_Food_Security_.pdf (FNRI 2023 NNS)"
    return d


def build() -> dict:
    CLEAN.mkdir(parents=True, exist_ok=True)
    h = hfias_2015()
    h.to_csv(CLEAN / "published_hfias_2015_calabarzon.csv", index=False, lineterminator="\n")
    f = fies_psa()
    f.to_csv(CLEAN / "published_fies_psa_sdg212.csv", index=False, lineterminator="\n")
    return {"hfias_rows": len(h), "fies_rows": len(f)}


if __name__ == "__main__":
    print(build())
