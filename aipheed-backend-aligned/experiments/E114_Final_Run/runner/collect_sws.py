"""E114 Phase 1: the SWS Total Hunger series by area, July 1998 onward, from SWS's own published tables.

Source: SWS media release "Third Quarter 2026 Social Weather Survey: Hunger rises to 22.6% in September 2026 from 20.3%
in June 2026" (14 October 2026), Tables 1-6: national and area Total / Moderate / Severe Hunger for every survey since
July 1998. The PDF is downloaded once into data/raw/ and hashed; nothing is read from charts.

Checks (written to data/sws_extraction_checks.csv):
  - area summary table (Table 2) vs each area's own table (Tables 3-6): Total must agree;
  - inside each area table: Total = Moderate + Severe within rounding (0.15);
  - 2021+ rounds vs the E110 file compiled from news reports.
A Table-2 vs area-table conflict is resolved to the area table when that table is internally consistent, and flagged.

    python collect_sws.py        # writes data/sws_rounds_1998_2026.csv
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
E114 = HERE.parent
DATA = E114 / "data"
RAW = DATA / "raw"
URL = "https://sws.org.ph/wp-content/uploads/2026/10/pr20261014-SWR2026-III-Hunger-in-Families-media-release.pdf"
PDF = RAW / "pr20261014-SWR2026-III-Hunger-in-Families-media-release.pdf"
SECTIONS = {"TOTAL HUNGER: BY AREA": "AREA", "PHILIPPINES, % OF HOUSEHOLDS": "PH", "NATIONAL CAPITAL REGION": "NCR",
            "BALANCE LUZON, % OF": "BL", "VISAYAS, % OF": "VIS", "MINDANAO, % OF": "MIN"}
MONTHS = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
ROW = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|July|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d\d)(\*{0,2})\s+(.*)$")
NUM = re.compile(r"\d+\.\d")


def download() -> str:
    RAW.mkdir(parents=True, exist_ok=True)
    if not PDF.exists():
        subprocess.run(["curl", "-s", "-m", "120", "-A", "Mozilla/5.0", "-o", str(PDF), URL], check=True)
    return hashlib.sha256(PDF.read_bytes()).hexdigest()


def pages_text() -> list[str]:
    import pypdf
    r = pypdf.PdfReader(str(PDF))
    return [p.extract_text() or "" for p in r.pages]


def parse(text: str) -> tuple[list[dict], list[list[dict]]]:
    """4-number rows = the area summary (Table 2). 3-number rows = Tables 1, 3, 4, 5, 6 in document order; a new table
    starts wherever the survey date goes backwards (each table runs July 1998 -> latest). Titles are not used: the
    PDF text layer prints some titles after their first rows."""
    area, groups, last = [], [], None
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        mon, yy, star, rest = m.groups()
        vals = [float(v) for v in NUM.findall(rest)]
        yr = 1900 + int(yy) if int(yy) >= 90 else 2000 + int(yy)
        r = {"label": f"{mon[:3]} {yy}{star}", "year": yr, "month": MONTHS[mon[:3]],
             "star": star if (yr, MONTHS[mon[:3]]) == (2025, 4) else ""}
        if len(vals) == 4:
            area.append({**r, "vals": vals})
        elif len(vals) == 3:
            k = (yr, r["month"], r["star"])
            if last is None or k < last:
                groups.append([])
            groups[-1].append({**r, "vals": vals})
            last = k
    return area, groups


def main() -> None:
    import pandas as pd
    sha = download()
    area_rows, groups = parse("\n".join(pages_text()))
    assert len(groups) == 5, f"expected 5 Total/Moderate/Severe tables, found {len(groups)}"
    names = ["PH", "NCR", "BL", "VIS", "MIN"]
    for g in groups:
        ks = [(r["year"], r["month"], r["star"]) for r in g]
        assert ks == sorted(ks) and len(ks) == len(set(ks)), "table rows out of order"
    df = pd.DataFrame([{**r, "table": n} for n, g in zip(names, groups) for r in g] +
                      [{**r, "table": "AREA"} for r in area_rows])
    area_cols = ["metro_manila", "balance_luzon", "visayas", "mindanao"]
    key = ["year", "month", "star"]
    a = df[df["table"] == "AREA"].copy()
    a[area_cols] = pd.DataFrame(a["vals"].tolist(), index=a.index)
    out = a[key + ["label"] + area_cols].drop_duplicates(key).reset_index(drop=True)
    checks = []
    for tab, col in zip(["NCR", "BL", "VIS", "MIN"], area_cols):
        t = df[df["table"] == tab].copy()
        t[["total", "moderate", "severe"]] = pd.DataFrame(t["vals"].tolist(), index=t.index)
        t = t.drop_duplicates(key).set_index(key)
        assert len(t) == len(out), f"{tab}: {len(t)} rows vs {len(out)} in Table 2"
        for i, r in out.iterrows():
            k = (r["year"], r["month"], r["star"])
            tt = t.loc[k]
            internal = abs(tt["total"] - tt["moderate"] - tt["severe"]) <= 0.15
            if abs(tt["total"] - r[col]) > 1e-9:
                checks.append({"label": r["label"], "area": tab, "issue": "Table 2 vs area table",
                               "table2": r[col], "area_table": tt["total"], "area_table_internally_consistent": internal,
                               "used": tt["total"] if internal else r[col]})
                if internal:
                    out.loc[i, col] = tt["total"]
            elif not internal:
                checks.append({"label": r["label"], "area": tab, "issue": "Total != Moderate + Severe (kept)",
                               "total": tt["total"], "moderate": tt["moderate"], "severe": tt["severe"]})
            out.loc[i, f"{col}_moderate"] = tt["moderate"]
            out.loc[i, f"{col}_severe"] = tt["severe"]
    ph = df[df["table"] == "PH"].copy()
    ph["national"] = [v[0] for v in ph["vals"]]
    out = out.merge(ph.drop_duplicates(key)[key + ["national"]], on=key, how="left")
    out["quarter"] = out["year"].astype(str) + "-Q" + ((out["month"] - 1) // 3 + 1).astype(str)
    out["mode"] = ["mobile phone" if (y == 2020 and m in (5, 7, 9)) else "face-to-face" for y, m in zip(out["year"], out["month"])]
    out["respondent_base"] = ["household heads" if (y, m) <= (2024, 12) else
                              ("registered voters" if (y == 2025 and (m < 4 or s == "*")) else "adults")
                              for y, m, s in zip(out["year"], out["month"], out["star"])]
    out["source"] = URL
    out["source_table"] = "SWS media release 14 Oct 2026, Tables 1-6"
    out["source_sha256"] = sha
    DATA.mkdir(exist_ok=True)
    out.to_csv(DATA / "sws_rounds_1998_2026.csv", index=False, lineterminator="\n")
    pd.DataFrame(checks).to_csv(DATA / "sws_extraction_checks.csv", index=False, lineterminator="\n")
    print(len(out), "rounds;", len(checks), "check notes; sha", sha[:12])


if __name__ == "__main__":
    sys.exit(main())
