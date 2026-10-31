"""
Extracts the seal's target from an owner-supplied PSA 2025 full-year workbook: subsistence incidence among the
population (estimate and CV) for the five provinces, 2025 only, plus the 2023 estimate as a vintage check. The workbook
is hashed first; only the header rows and the five provinces' 2023/2025 estimate and CV cells are read. A workbook
without a subsistence-among-population table is recorded (titles, years, hash) and nothing is written.

Run:  python -I runner/extract_psa_2025.py <workbook.xlsx>
      -> data/owner_supplied/psa_subsistence_population_2025.csv (if the table exists), out/owner_workbook_check.json
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e130_lib as L  # noqa: E402
import xlsx_lite as X  # noqa: E402

OUT_CSV = L.ROOT / "data" / "owner_supplied" / "psa_subsistence_population_2025.csv"
TITLE = re.compile(r"subsistence\s+incidence\s+among\s+population", re.I)


def column_map(header: dict[tuple[int, int], object], block_rows=(3, 4), year_row: int = 5) -> dict[tuple[str, int], int]:
    """{(block, year): column} from the header rows: a block label (row 3 or 4) applies to its column and the columns
    to its right until the next label; the year comes from `year_row`."""
    labels = {}
    for r in block_rows:
        for (rr, c), v in header.items():
            if rr == r and isinstance(v, str) and v.strip():
                labels[c] = v.strip()
    out = {}
    for (rr, c), v in header.items():
        if rr != year_row or not isinstance(v, float) or not (2000 <= v <= 2035):
            continue
        left = [k for k in labels if k <= c]
        if left:
            out[(labels[max(left)], int(v))] = c
    return out


def pick(cmap: dict[tuple[str, int], int], pattern: str, year: int) -> int | None:
    hits = [c for (b, y), c in cmap.items() if y == year and re.search(pattern, b, re.I)]
    return min(hits) if hits else None


def extract(workbook: str) -> dict:
    digest = L.sha256(Path(workbook))                      # hashed before any value is read
    info = {"workbook": Path(workbook).name, "sha256": digest, "sheets": []}
    target = None
    for name, member in X.sheets(workbook):
        head = X.cells(workbook, member, set(range(1, 7)))
        title = next((v for (r, c), v in sorted(head.items()) if r == 1 and isinstance(v, str)), "")
        years = sorted({int(v) for (r, c), v in head.items() if r == 5 and isinstance(v, float) and 2000 <= v <= 2035})
        info["sheets"].append({"sheet": name, "title": title.strip(), "years": years})
        if TITLE.search(title):
            target = (name, member, head)
    info["pre_2021_years_present"] = sorted({y for s in info["sheets"] for y in s["years"] if y < 2021})
    if target is None:
        info["subsistence_population_table"] = False
        L.dump(info, L.OUT / "owner_workbook_check.json")
        return info
    name, member, head = target
    cmap = column_map(head)
    est = {y: pick(cmap, r"estimate|incidence", y) for y in (2023, 2025)}
    cv = pick(cmap, r"coefficient of variation", 2025)
    assert est[2025] and cv and est[2023], f"unexpected header layout in {name}: {cmap}"
    labels = X.cells(workbook, member)                     # column 1 labels locate the five provinces' rows
    rows = {p: next(r for (r, c), v in sorted(labels.items()) if c == 1 and isinstance(v, str) and v.strip() == p)
            for p in L.PROVINCES}
    rec = []
    for p, r in rows.items():
        rec.append({"province": p, "survey_year": 2025, "subsistence_incidence_pct": labels[(r, est[2025])],
                    "cv_pct": labels[(r, cv)], "value_2023_in_workbook": labels[(r, est[2023])],
                    "source": f"PSA 2025 Full Year Official Poverty Statistics, sheet {name}",
                    "publication_date": "2026-08-24 (workbook date)"})
    df = pd.DataFrame(rec)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    info.update(subsistence_population_table=True, table_sheet=name, rows=rows)
    L.dump(info, L.OUT / "owner_workbook_check.json")
    return info


if __name__ == "__main__":
    res = extract(sys.argv[1])
    for s in res["sheets"]:
        print(s["sheet"], s["years"], "|", s["title"][:110])
    if not res["subsistence_population_table"]:
        sys.exit("no 'Subsistence Incidence among Population' table in this workbook: nothing extracted, seal not scored")
    print("extracted ->", OUT_CSV)
