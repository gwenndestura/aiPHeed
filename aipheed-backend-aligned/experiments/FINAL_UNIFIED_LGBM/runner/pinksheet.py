"""World Bank Commodity Price Data (Pink Sheet), monthly nominal USD prices, parsed from the downloaded xlsx with the
standard library only (no openpyxl in the backend venv).

    python pinksheet.py      # data/pinksheet_monthly.csv: ym, month, and the selected series

Source: https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx
(link from worldbank.org/en/research/commodity-markets, downloaded 2026-10-26; the World Bank publishes it on the 2nd-3rd business day of each month for the month before).
"""
from __future__ import annotations

import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
KEEP = {"Rice, Thai 5% ": "rice_thai5", "Rice, Thai 5%": "rice_thai5", "Rice, Viet Namese 5%": "rice_viet5",
        "Wheat, US HRW": "wheat_hrw", "Maize": "maize", "Palm oil": "palm_oil", "Sugar, world": "sugar_world",
        "Urea ": "urea", "Urea": "urea", "Crude oil, average": "crude_avg", "Soybean oil": "soybean_oil"}


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(path: Path, name: str) -> list[list]:
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid = next(s.get("{%s}id" % NS["r"]) for s in wb.find("m:sheets", NS) if s.get("name") == name)
    target = next(r.get("Target") for r in rels if r.get("Id") == rid)
    sh = ET.fromstring(z.read("xl/" + target.lstrip("/").replace("xl/", "")))
    rows = []
    for row in sh.iter("{%s}row" % NS["m"]):
        cells = {}
        for c in row.findall("m:c", NS):
            v = c.find("m:v", NS)
            if v is None:
                isv = c.find("m:is", NS)
                val = "".join(t.text or "" for t in isv.iter("{%s}t" % NS["m"])) if isv is not None else None
            else:
                val = ss[int(v.text)] if c.get("t") == "s" else v.text
            cells[_col(c.get("r"))] = val
        rows.append([cells.get(i) for i in range(max(cells) + 1)] if cells else [])
    return rows


def main(src: str = "raw/pinksheet_monthly.xlsx"):
    rows = read_sheet(DATA / src, "Monthly Prices")
    hdr_i = next(i for i, r in enumerate(rows) if r and any(isinstance(x, str) and x.startswith("Crude oil") for x in r))
    hdr = rows[hdr_i]
    cols = {i: KEEP[h] for i, h in enumerate(hdr) if isinstance(h, str) and h in KEEP}
    out = []
    for r in rows[hdr_i + 1:]:
        if not r or not isinstance(r[0], str) or not re.match(r"^\d{4}M\d{2}$", r[0]):
            continue
        y, m = int(r[0][:4]), int(r[0][5:])
        if y < 2018:
            continue
        rec = {"month": f"{y}-{m:02d}", "ym": y * 12 + m - 1}
        for i, k in cols.items():
            v = r[i] if i < len(r) else None
            try:
                rec[k] = float(v)
            except (TypeError, ValueError):
                rec[k] = None
        out.append(rec)
    keys = ["month", "ym"] + sorted(set(cols.values()))
    with open(DATA / "pinksheet_monthly.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(out)
    print("series:", sorted(set(cols.values())), "months:", out[0]["month"], "-", out[-1]["month"], len(out))


if __name__ == "__main__":
    main(*sys.argv[1:])
