"""Provincial outcome table from the owner workbook, with sampling errors and conservative availability dates.

Values are taken unchanged from the workbook export (data/fi_labels/raw/owner_supplied/sheet_Labeled_Provincial_Data.csv)
and checked against the primary PSA tables; standard errors come from the source (FNRI 2015 report SEs; PSA CVs).
Availability (when a forecaster could first have used a value) is rule-based: 1 January of reference year + 2. Actual
release dates are earlier for PSA (about 8-20 months after the reference year), so the rule never admits a value early.
"""
from __future__ import annotations

import io
import csv

import numpy as np
import pandas as pd

from app.fi12 import PROVINCES
from app.paths import BACKEND_DIR

WB = BACKEND_DIR / "data" / "fi_labels" / "raw" / "owner_supplied" / "sheet_Labeled_Provincial_Data.csv"
VERIFIED = BACKEND_DIR / "data" / "fi_labels" / "clean" / "owner_workbook_records_verified.csv"
PSA = BACKEND_DIR / "data" / "fi5" / "raw" / "psa"

OUTCOMES = {
    "FNRI15_SEV": ("A", "FNRI 2015 FSS: severely food-insecure households (HFIAS), %", "Severely food insecure"),
    "FNRI15_INSEC": ("A", "FNRI 2015 FSS: not food secure (100 - food secure), % (derived complement)", "Food secure"),
    "ENNS_SEV": ("A", "ENNS severe food insecurity, % (secondary: DEPDev RDP matrix; one year per province)", "Severe food insecurity"),
    "ENNS_MODSEV": ("A", "ENNS moderate-to-severe food insecurity, % (secondary; one year per province)", "Moderate-to-severe food insecurity"),
    "PSA_SUB_FAM": ("B", "PSA subsistence incidence among families, % (food poverty)", "Subsistence incidence among families"),
    "PSA_SUB_POP": ("B", "PSA subsistence incidence among population, % (food poverty)", "Subsistence incidence among population"),
}


def _psa(fname: str, label: str) -> pd.DataFrame:
    rows = list(csv.reader(io.StringIO((PSA / fname).read_bytes().decode("latin-1"))))
    hdr, out = rows[0], []
    for r in rows[1:]:
        geo = next((p for p in PROVINCES if p in r[0]), "CALABARZON" if "IV-A" in r[0] else None)
        if not geo or (geo == "Quezon" and "Lucena" in r[0]):
            continue
        for h, v in zip(hdr[1:], r[1:]):
            yr = h.strip()[-4:]
            if not yr.isdigit():
                continue
            key = "value" if h.startswith(label) else "cv" if h.startswith("Coefficient of Variation") else None
            if key and v.strip() not in ("", ".."):
                out.append({"geo": geo, "year": int(yr), key: float(v)})
    d = pd.DataFrame(out).groupby(["geo", "year"]).first().reset_index()
    d["se"] = d["value"] * d["cv"] / 100
    return d


def psa_subsistence(kind: str) -> pd.DataFrame:
    if kind == "fam":
        return _psa("psa_subsistence_families_2018_2023.csv", "Subsistence Incidence among Families")
    return _psa("psa_food_threshold_subsistence_2018_2023.csv", "Subsistence Incidence among Population")


def psa_poverty() -> pd.DataFrame:
    a = _psa("psa_poverty_2018_2023.csv", "Poverty Incidence among Population")
    b = _psa("psa_poverty_2006_2015.csv", "Poverty Incidence among Population Estimate")
    return pd.concat([b[b["year"].isin([2012, 2015])], a]).reset_index(drop=True)


def build() -> pd.DataFrame:
    wb = pd.read_csv(WB)
    ver = pd.read_csv(VERIFIED).set_index("record_id")["verification_status_aipheed"]
    sub = {"PSA_SUB_FAM": psa_subsistence("fam"), "PSA_SUB_POP": psa_subsistence("pop")}
    rows = []
    for oid, (track, desc, name) in OUTCOMES.items():
        for _, r in wb[wb["label_name"] == name].iterrows():
            v, se, n = float(r["label_value"]), r["standard_error"], r["sample_size"]
            if oid == "FNRI15_INSEC":
                v = round(100 - v, 1)
            if oid in sub:
                s = sub[oid].set_index(["geo", "year"]).loc[(r["province"], int(r["reference_year"]))]
                assert abs(s["value"] - v) < 0.051, (oid, r["record_id"])
                se = s["se"]
            rows.append({"track": track, "outcome": oid, "description": desc, "province": r["province"],
                         "reference_year": int(r["reference_year"]), "value": v,
                         "se": float(se) if pd.notna(se) else np.nan, "n": float(n) if pd.notna(n) else np.nan,
                         "record_id": r["record_id"], "verification": ver.get(r["record_id"], "unverified"),
                         "available_from": f"{int(r['reference_year']) + 2}-01-01", "source": r["source_document"]})
    return pd.DataFrame(rows).sort_values(["outcome", "reference_year", "province"]).reset_index(drop=True)


def regional(oid: str, year: int) -> tuple[float, float] | None:
    """CALABARZON value and SE for the same outcome-year (FNRI 2015 regional severe from the workbook benchmarks)."""
    if oid == "FNRI15_SEV":
        return 19.0, np.nan
    if oid in ("PSA_SUB_FAM", "PSA_SUB_POP"):
        s = psa_subsistence("fam" if oid.endswith("FAM") else "pop").set_index(["geo", "year"])
        if ("CALABARZON", year) in s.index:
            r = s.loc[("CALABARZON", year)]
            return float(r["value"]), float(r["se"])
    return None
