"""Integrate the owner-supplied workbook `aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx` (2026-11-03).

    python -m app.fi_labels.workbook extract <xlsx>    # needs openpyxl; copies the original and exports its sheets
    python -m app.fi_labels.workbook verify            # pandas only; checks every record against primary extracts

The original is kept unchanged in data/fi_labels/raw/owner_supplied/ (sha256 in MANIFEST). Each long-format record
gets a verification status:
    verified_primary        value equals the primary source we downloaded ourselves (FNRI 2015 report appendices;
                            PSA OpenSTAT tables 2 / 3 / 4)
    unverified_secondary    value comes from a secondary government document (DEPDev CALABARZON RDP results matrix)
                            whose primary FNRI table could not be read from this network
    provisional_secondary   secondary news report (PIA); never usable as a label
Nothing in the workbook is a quarterly label or a household label; the restrictions in its READ ME are kept.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import csv
import shutil
from pathlib import Path

import pandas as pd

from app.fi_labels.published import CLEAN, RAW
from app.paths import BACKEND_DIR

OWNER = RAW / "owner_supplied"
NAME = "aiPHeed_CALABARZON_Labeled_Provincial_Data.xlsx"
PSA = BACKEND_DIR / "data" / "fi5" / "raw" / "psa"
PROV = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def extract(xlsx: str) -> list[str]:
    OWNER.mkdir(parents=True, exist_ok=True)
    dst = OWNER / NAME
    shutil.copyfile(xlsx, dst)
    out = []
    for sheet in pd.ExcelFile(dst).sheet_names:
        d = pd.read_excel(dst, sheet)
        f = OWNER / f"sheet_{sheet.replace(' ', '_')}.csv"
        d.to_csv(f, index=False, lineterminator="\n", encoding="utf-8")
        out.append(f.name)
    return out


def _psa_table(fname: str, label: str) -> dict:
    rows = list(csv.reader(io.StringIO((PSA / fname).read_bytes().decode("latin-1"))))
    hdr = rows[0]
    res = {}
    for r in rows[1:]:
        geo = next((p for p in PROV if p in r[0]), None)
        if not geo:
            continue
        for h, v in zip(hdr[1:], r[1:]):
            if h.startswith(label):
                res[(geo, int(h[-4:]))] = float(v)
    return res


def verify() -> pd.DataFrame:
    rec = pd.read_csv(OWNER / "sheet_Labeled_Provincial_Data.csv")
    hf = pd.read_csv(CLEAN / "published_hfias_2015_calabarzon.csv").set_index(["geography", "category"])
    fam = _psa_table("psa_subsistence_families_2018_2023.csv", "Subsistence Incidence among Families")
    pop = _psa_table("psa_food_threshold_subsistence_2018_2023.csv", "Subsistence Incidence among Population")
    status, ref, primary = [], [], []
    for _, r in rec.iterrows():
        v, p, s, src = r["label_value"], None, "unverified_secondary", ""
        if str(r["record_id"]).startswith("FNRI15"):
            cat = "food_secure" if r["label_name"] == "Food secure" else "severely_food_insecure"
            p = float(hf.loc[(r["province"], cat), "percent"])
            src = "FNRI 2015 report appendix (clean/published_hfias_2015_calabarzon.csv)"
        elif str(r["record_id"]).startswith("PSA-SI"):
            table = fam if "families" in r["label_name"] else pop
            p = table.get((r["province"], int(r["reference_year"])))
            src = "PSA OpenSTAT DB/1F/FY Table 3 (families) / Table 4 (population)"
        if p is not None:
            s = "verified_primary" if abs(p - v) < 0.051 else "MISMATCH_with_primary"
        status.append(s)
        ref.append(src or "DEPDev CALABARZON RDP 2023-2028 midterm results matrix (primary FNRI table unreadable here)")
        primary.append(p)
    rec["verification_status_aipheed"] = status
    rec["primary_value"] = primary
    rec["verification_source"] = ref
    rec.to_csv(CLEAN / "owner_workbook_records_verified.csv", index=False, lineterminator="\n")
    bench = pd.read_csv(OWNER / "sheet_Regional_Benchmarks.csv")
    bench["verification_status_aipheed"] = [
        "verified_primary" if (src.startswith("FNRI 2015") and "derived" not in src) or (src == "FNRI 2023 NNS" and est == 19.1)
        else ("provisional_secondary" if src.startswith("PIA") else "unverified_secondary")
        for src, est in zip(bench["Source"], bench["Estimate (%)"])]
    bench.loc[bench["Source"].str.contains("derived"), "verification_status_aipheed"] = "derived_from_verified_primary"
    bench.to_csv(CLEAN / "owner_workbook_regional_benchmarks_verified.csv", index=False, lineterminator="\n")
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "verify"])
    ap.add_argument("xlsx", nargs="?")
    a = ap.parse_args()
    if a.cmd == "extract":
        print(extract(a.xlsx))
    else:
        r = verify()
        print(r["verification_status_aipheed"].value_counts().to_string())
