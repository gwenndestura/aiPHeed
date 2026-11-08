"""
Parse FNRI 2013 NNS Appendix 33 (food security status by province, HFIAS) into data/e141/clean/nns2013_hfias.csv.

    python -m app.e141.nns2013

Source: https://www.fnri.dost.gov.ph/images/facts_and_figures/Food-Security-2013.pdf, read from the Internet Archive
(web.archive.org/web/2020id_/<url>). The document prints n and the four category percentages, not standard errors.
Standard errors are therefore approximated as sqrt(deff x p(1-p)/n) with deff = the median province design effect of the
same binary split in FNRI 2015 (same PSA master-sample design, printed SEs) - an assumption recorded with every row.
HUCs printed as separate rows (Isabela City, Cotabato City) and NCR districts are excluded, as for ENNS.
"""
from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from datetime import date

import numpy as np
import pandas as pd

from app.e141 import DATA, RAW
from app.hfias import CLEAN as HCLEAN

PDF = RAW / "fnri" / "2013_NNS_Food_Security_Facts_and_Figures.pdf"
URL = "https://www.fnri.dost.gov.ph/images/facts_and_figures/Food-Security-2013.pdf"
WAYBACK = f"https://web.archive.org/web/2020id_/{URL}"
NATIONAL = {"food_secure": 34.1, "mild": 15.1, "moderate": 34.1, "severe": 16.7}     # PHILIPPINES row, n = 35,635
ROW = re.compile(r"^(?P<name>[A-Z][A-Z .()'\-]+?) (?P<n>[\d,]+) (?P<fs>\d+\.\d+) (?P<mi>\d+\.\d+) (?P<mo>\d+\.\d+) (?P<se>\d+\.\d+)$")
EXCLUDE = {"ISABELA CITY", "COTABATO CITY", "PHILIPPINES", "DISTRICT"}      # "DISTRICT" = wrapped NCR row


def text() -> str:
    return subprocess.run(["pdftotext", "-raw", str(PDF), "-"], capture_output=True, text=True, check=True).stdout


def parse(raw: str) -> pd.DataFrame:
    i = raw.index("Appendix 33. Percentage Distribution of Food Security Status by Province")
    j = raw.index("Appendix 34.", i)
    lines = [ln.strip() for ln in raw[i:j].splitlines()]
    joined, buf = [], ""
    for ln in lines:                                   # names split over two lines ("ZAMBOANGA DEL" / "NORTE 488 ...")
        if re.match(r"^[A-Z][A-Z .()'\-]+$", ln) and not ln.startswith(("NCR", "CAR")) and ln.isupper():
            buf = (buf + " " + ln).strip()
            continue
        joined.append((buf + " " + ln).strip() if buf else ln)
        buf = ""
    rows = []
    for ln in joined:
        m = ROW.match(ln)
        if not m or m["name"].startswith("NCR") or m["name"].strip() in EXCLUDE:
            continue
        name = m["name"].replace("DAVAO (DAVAO DEL NORTE)", "DAVAO DEL NORTE").strip().title()
        rows.append({"province": name, "n": int(m["n"].replace(",", "")), "food_secure_pct": float(m["fs"]),
                     "mild_pct": float(m["mi"]), "moderate_pct": float(m["mo"]), "severe_pct": float(m["se"])})
    return pd.DataFrame(rows)


def design_effect() -> float:
    """Median 2015 province design effect of the moderate-or-severe split, from FNRI 2015's printed SEs."""
    f = pd.read_csv(HCLEAN / "fnri2015_hfias.csv")
    p = f[f["level"] == "province"]
    d = pd.concat([p[f"{c}_se"] ** 2 / (p[f"{c}_pct"] * (100 - p[f"{c}_pct"]) / p["n"])
                   for c in ("food_secure", "moderate", "severe")], axis=1).max(axis=1)
    return float(d.median())


def build() -> pd.DataFrame:
    d = parse(text())
    deff = design_effect()
    d["mod_sev_pct"] = d["moderate_pct"] + d["severe_pct"]
    d["insecure_pct"] = 100 - d["food_secure_pct"]
    for c in ("mod_sev", "insecure"):
        d[f"{c}_se"] = np.sqrt(deff * d[f"{c}_pct"] * (100 - d[f"{c}_pct"]) / d["n"])
    d["sum_check"] = d[["food_secure_pct", "mild_pct", "moderate_pct", "severe_pct"]].sum(axis=1)
    d["se_method"] = f"approximate: sqrt(deff x p(1-p)/n), deff = {deff:.3f} (median FNRI 2015 province design effect)"
    d["year"], d["instrument"], d["source"] = 2013, "HFIAS", "FNRI 8th NNS 2013, Philippine Nutrition Facts and Figures 2013: Food Security, Appendix 33"
    out = DATA / "clean"
    out.mkdir(parents=True, exist_ok=True)
    d.to_csv(out / "nns2013_hfias.csv", index=False, lineterminator="\n")
    man = RAW / "MANIFEST.csv"
    with man.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "source_url", "retrieved", "sha256", "description"])
        w.writerow([f"fnri/{PDF.name}", WAYBACK, date.today().isoformat(), hashlib.sha256(PDF.read_bytes()).hexdigest(),
                    "FNRI Philippine Nutrition Facts and Figures 2013: Food Security (8th NNS), Internet Archive copy"])
    return d


if __name__ == "__main__":
    d = build()
    print(len(d), "provinces; sum check range", d["sum_check"].min(), d["sum_check"].max())
