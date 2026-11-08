"""Parse FNRI 2015 Food Security Survey Appendices 1-4 (food secure, mild, moderate, severe) for every region and
province: n, proportion, SE, 95% CI and CV as printed. `python -m app.hfias.fnri2015` writes clean/fnri2015_hfias.csv."""
from __future__ import annotations

import re
import subprocess

import pandas as pd

from app.hfias import CLEAN
from app.paths import BACKEND_DIR

PDF = BACKEND_DIR / "data" / "fi_labels" / "raw" / "fnri" / "2015_FOOD_SECURITY_SURVEY.pdf"
CATEGORY = {"1": "food_secure", "2": "mild", "3": "moderate", "4": "severe"}
REGIONS = {"Philippines", "NCR", "CAR", "Ilocos", "Cagayan Valley", "Central Luzon", "CALABARZON", "MIMAROPA", "Bicol",
           "Western Visayas", "Central Visayas", "Eastern Visayas", "Zamboanga Peninsula", "Northern Mindanao", "Davao",
           "SOCCSKSARGEN", "ARMM", "Caraga"}
ROW = re.compile(r"^(?P<name>[A-Za-z][A-Za-z .'\-ñÑ]*?)(?P<foot>\d{0,2}) (?P<n>[\d,]+) (?P<pct>\d+\.\d) (?P<se>\d+\.\d) "
                 r"(?P<ll>\d+\.\d) (?P<ul>\d+\.\d) (?P<cv>\d+\.\d)$")


def text(pdf=PDF) -> str:
    return subprocess.run(["pdftotext", "-raw", "-f", "75", "-l", "90", str(pdf), "-"], capture_output=True, text=True,
                          check=True).stdout


def parse(raw: str) -> pd.DataFrame:
    rows, cat, region = [], None, None
    for line in raw.splitlines():
        m = re.match(r"^(?:Continuation\.\.\.)?Appendix (\d)", line.strip())
        if m:
            cat = CATEGORY.get(m.group(1))
            continue
        r = ROW.match(line.strip())
        if not r or cat is None:
            continue
        name = r["name"].strip()
        level = "national" if name == "Philippines" else "region" if name in REGIONS else (
            "district" if name.startswith("District") else "province")
        if level == "region":
            region = name
        rows.append({"category": cat, "name": name, "level": level, "region": None if level == "national" else region,
                     "n": int(r["n"].replace(",", "")), "pct": float(r["pct"]), "se": float(r["se"]),
                     "ci_low": float(r["ll"]), "ci_high": float(r["ul"]), "cv": float(r["cv"])})
    return pd.DataFrame(rows)


def wide(long: pd.DataFrame) -> pd.DataFrame:
    assert not long.duplicated(["category", "name"]).any(), "unit names must be unique within a category"
    w = long.pivot(index="name", columns="category", values=["pct", "se"])
    w.columns = [f"{c}_{v}" for v, c in w.columns]
    meta = long[long["category"] == "food_secure"].set_index("name")[["level", "region", "n"]]
    w = meta.join(w).reset_index()
    w["mod_sev_pct"] = w["moderate_pct"] + w["severe_pct"]
    w["mod_sev_se"] = (w["moderate_se"] ** 2 + w["severe_se"] ** 2) ** 0.5     # covariance ignored (conservative)
    w["insecure_pct"] = 100 - w["food_secure_pct"]
    w["year"] = 2015
    w["instrument"] = "HFIAS"
    w["source"] = "FNRI 2015 Food Security Survey, Appendices 1-4 (pp. 75-81)"
    return w


def build() -> pd.DataFrame:
    long = parse(text())
    CLEAN.mkdir(parents=True, exist_ok=True)
    long.to_csv(CLEAN / "fnri2015_hfias_long.csv", index=False, lineterminator="\n")
    w = wide(long)
    w.to_csv(CLEAN / "fnri2015_hfias.csv", index=False, lineterminator="\n")
    return w


if __name__ == "__main__":
    w = build()
    print(w["level"].value_counts().to_dict())
