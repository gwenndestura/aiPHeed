"""
Acquire the public inputs of the HFIAS panel (no requests to agencies; public endpoints only).

    python -m app.hfias.acquire psa        PSA OpenSTAT tables (all provinces) -> data/hfias/raw/psa/*.csv
    python -m app.hfias.acquire fnri <dir> copy FNRI provincial monographs (Internet Archive copies) into data/hfias/raw/fnri

Every file is recorded in data/hfias/raw/MANIFEST.csv with its URL, retrieval date and sha256.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

from app.hfias import RAW

PX = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/"
YEARS = [str(y) for y in range(2012, 2020)]
# name: (table, family, description, {variable code: predicate on the value text}); unlisted variables keep all values.
TABLES = {
    "poverty_1991_2015": ("DB/3D/0023C3DP020.px", "V1", "poverty incidence among population, provinces, 2012 and 2015",
                          {"Item": lambda t: "Incidence" in t or "Coefficient" in t, "Year": lambda t: t in ("2012", "2015")}),
    "subsistence_1991_2015": ("DB/3D/0033C3DP030.px", "V1", "subsistence incidence among families, provinces, 2012 and 2015",
                              {"Item": lambda t: "Incidence" in t or "Coefficient" in t, "Year": lambda t: t in ("2012", "2015")}),
    "cpi_2012base_1994_2018": ("DB/3L/FAC/0013L5ECPI0.px", "A1/A3", "annual provincial CPI by food group, 2012=100",
                               {"Year": lambda t: t in YEARS}),
    "palay_corn_quarterly": ("DB/2E/CS/0012E4EVCP0.px", "C3", "quarterly palay and corn production by province",
                             {"Ecosystem/Croptype": lambda t: t in ("Palay", "Corn"), "Year": lambda t: t in YEARS,
                              "Period": lambda t: t.startswith("Quarter")}),
    "fisheries_quarterly": ("DB/2E/FS/0132E4GVFP1.px", "C4", "quarterly fisheries production by province",
                            {"Subsector": lambda t: t == "FISHERIES", "Year": lambda t: t in YEARS,
                             "Quarter": lambda t: t.startswith("Quarter")}),
}
UA = {"User-Agent": "Mozilla/5.0 (aiPHeed research; public data)", "Content-Type": "application/json"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _manifest(rows: list[dict]) -> None:
    m = RAW / "MANIFEST.csv"
    old = list(csv.DictReader(m.open(encoding="utf-8"))) if m.exists() else []
    keep = {r["file"]: r for r in old}
    keep.update({r["file"]: r for r in rows})
    with m.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "source_url", "retrieved", "sha256", "family", "description"])
        w.writeheader()
        w.writerows(sorted(keep.values(), key=lambda r: r["file"]))


def psa() -> list[dict]:
    out = RAW / "psa"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (path, fam, desc, pick) in TABLES.items():
        meta = json.load(urllib.request.urlopen(urllib.request.Request(PX + path, headers=UA), timeout=120))
        query = []
        for v in meta["variables"]:
            if v["code"] in pick:
                vals = [c for c, t in zip(v["values"], v["valueTexts"]) if pick[v["code"]](t.strip())]
                query.append({"code": v["code"], "selection": {"filter": "item", "values": vals}})
        req = urllib.request.Request(PX + path, data=json.dumps({"query": query, "response": {"format": "csv"}}).encode(),
                                     headers=UA)
        body = urllib.request.urlopen(req, timeout=300).read()
        f = out / f"{name}.csv"
        f.write_bytes(body)
        rows.append({"file": f"psa/{f.name}", "source_url": PX + path, "retrieved": date.today().isoformat(),
                     "sha256": _sha(f), "family": fam, "description": desc})
        print(name, len(body))
    _manifest(rows)
    return rows


def fnri(src: str) -> list[dict]:
    """Copy monographs downloaded from web.archive.org (`<ts>id_/<original url>`); the source list is <src>/list.txt."""
    s = Path(src)
    out = RAW / "fnri"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for line in (s / "list.txt").read_text().splitlines():
        url, ts, _ = line.split()
        fname = url.split("/uploads/")[1].replace("%20", "_").replace("%2C", ",")
        p = s / "pdf" / fname
        if not p.exists() or p.stat().st_size < 10000 or p.read_bytes()[:4] != b"%PDF":
            continue
        shutil.copy(p, out / fname)
        rows.append({"file": f"fnri/{fname}", "source_url": f"https://web.archive.org/web/{ts}id_/{url}",
                     "retrieved": date.today().isoformat(), "sha256": _sha(out / fname), "family": "outcome",
                     "description": f"DOST-FNRI upload {url} (Internet Archive capture {ts})"})
    _manifest(rows)
    return rows


if __name__ == "__main__":
    if sys.argv[1] == "psa":
        psa()
    else:
        print(len(fnri(sys.argv[2])), "monographs")
