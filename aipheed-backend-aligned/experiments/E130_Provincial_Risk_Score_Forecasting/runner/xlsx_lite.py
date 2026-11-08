"""
Minimal read-only .xlsx reader on the standard library (zipfile + ElementTree): no Excel library is installed in the
backend venv. Reads sheet names, shared strings and individual cells; never evaluates formulas or opens external links.

    python -I runner/xlsx_lite.py <workbook.xlsx>      # sheet names and header text only (no numeric values)
"""
from __future__ import annotations

import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "pr": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _shared(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root.findall("m:si", NS)]


def sheets(path: str) -> list[tuple[str, str]]:
    """[(sheet name, member path)] in workbook order."""
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels.findall("pr:Relationship", NS)}
        out = []
        for s in wb.find("m:sheets", NS).findall("m:sheet", NS):
            t = target[s.get(f"{{{NS['r']}}}id")].lstrip("/")
            out.append((s.get("name"), t if t.startswith("xl/") else "xl/" + t))
        return out


def col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def cells(path: str, member: str, rows: set[int] | None = None) -> dict[tuple[int, int], object]:
    """{(row, col): value} for the requested rows (all rows if None). Strings come back as str, numbers as float."""
    with zipfile.ZipFile(path) as z:
        sst = _shared(z)
        root = ET.fromstring(z.read(member))
    out = {}
    for row in root.iter(f"{{{NS['m']}}}row"):
        r = int(row.get("r"))
        if rows is not None and r not in rows:
            continue
        for c in row.findall("m:c", NS):
            ref, t = c.get("r"), c.get("t")
            v = c.find("m:v", NS)
            if t == "s" and v is not None:
                val = sst[int(v.text)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{{{NS['m']}}}t"))
            elif t == "str" and v is not None:
                val = v.text
            elif v is not None and v.text is not None:
                try:
                    val = float(v.text)
                except ValueError:
                    val = v.text
            else:
                continue
            out[(r, col_index(ref))] = val
    return out


def header_text(path: str, member: str, first_rows: int = 12) -> dict[int, list[str]]:
    """Text cells and year-like integers (2000-2035) of the first rows only: titles and column headers, no values."""
    got = cells(path, member, set(range(1, first_rows + 1)))
    out: dict[int, list[str]] = {}
    for (r, c), v in sorted(got.items()):
        if isinstance(v, str) and v.strip():
            out.setdefault(r, []).append(f"c{c}:{v.strip()[:90]}")
        elif isinstance(v, float) and v.is_integer() and 2000 <= v <= 2035:
            out.setdefault(r, []).append(f"c{c}:{int(v)}")
    return out


if __name__ == "__main__":
    wb = sys.argv[1]
    for name, member in sheets(wb):
        print(f"=== {name} ({member})")
        for r, items in header_text(wb, member, 10).items():
            print(f"  r{r}: " + " | ".join(items)[:400])
