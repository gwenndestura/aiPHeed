"""
Input validation for the SWS hunger rounds (the forecasting target) and the CALABARZON LGU reference. Checks columns,
dtypes, dates, quarters, geography IDs, duplicates, value ranges, units and staleness; returns every problem found
(empty list = valid) so the caller fails loudly with the full list.
"""
from __future__ import annotations

import re

import pandas as pd

from app.forecasting.evidence import AREAS

SWS_COLUMNS = ["quarter", "fieldwork", "published", "respondent_base", "commissioned", *AREAS, "area_moe_bl", "area_moe_other"]
QUARTER = re.compile(r"^\d{4}-Q[1-4]$")


class ValidationError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def validate_sws_rounds(r: pd.DataFrame, max_age_days: int | None = None, today: pd.Timestamp | None = None) -> list[str]:
    p: list[str] = []
    missing = [c for c in SWS_COLUMNS if c not in r.columns]
    if missing:
        return [f"missing columns: {missing}"]
    if not r["quarter"].astype(str).str.match(QUARTER).all():
        p.append("quarter not in YYYY-Qn form")
    pub = pd.to_datetime(r["published"], errors="coerce")
    if pub.isna().any():
        p.append(f"{int(pub.isna().sum())} unparseable published dates")
    field_end = pd.to_datetime(r["fieldwork"].astype(str).str.split("/").str[-1], errors="coerce")
    if (pub < field_end).any():
        p.append("published before the end of fieldwork")
    q_start = pd.PeriodIndex(r["quarter"].str.replace("-", ""), freq="Q").start_time
    fw_start = pd.to_datetime(r["fieldwork"].astype(str).str.split("/").str[0], errors="coerce")
    if ((fw_start < q_start) | (fw_start > q_start + pd.offsets.QuarterEnd(0))).any():
        p.append("fieldwork start outside its quarter")
    for a in AREAS:
        v = pd.to_numeric(r[a], errors="coerce")
        if v.isna().any() or ((v < 0) | (v > 100)).any():
            p.append(f"{a}: values missing or outside 0-100 (percent of families)")
    for c in ("area_moe_bl", "area_moe_other"):
        m = pd.to_numeric(r[c], errors="coerce")
        if ((m <= 0) | (m > 20)).any():
            p.append(f"{c}: margin of error outside (0, 20] percentage points")
    if r.duplicated(["quarter", "fieldwork"]).any():
        p.append("duplicate rounds (same quarter and fieldwork)")
    if not r["commissioned"].astype(str).str.lower().isin(["true", "false"]).all():
        p.append("commissioned not boolean")
    if (pd.to_datetime(r["published"], errors="coerce").dt.year < 2021).any() or (r["quarter"].str[:4].astype(int) < 2021).any():
        p.append("pre-2021 round (study window is 2021+)")
    if max_age_days is not None and len(pub.dropna()):
        today = today or pd.Timestamp.now()
        if (today - pub.max()).days > max_age_days:
            p.append(f"stale: newest round published {pub.max().date()}, more than {max_age_days} days ago")
    return p


def validate_lgus(d: pd.DataFrame) -> list[str]:
    p: list[str] = []
    if len(d) != 142:
        p.append(f"expected 142 CALABARZON LGUs, found {len(d)}")
    if d["lgu_code"].duplicated().any():
        p.append("duplicate LGU codes")
    prov = {"0410": "Batangas", "0421": "Cavite", "0434": "Laguna", "0456": "Quezon", "0458": "Rizal"}
    mism = d[d["lgu_code"].str[:4].map(prov) != d["province"]]
    if len(mism):
        p.append(f"{len(mism)} LGU code/province mismatches")
    if not d["lgu_code"].str.match(r"^04\d{7}$").all():
        p.append("LGU codes not 9-digit Region IV-A PSGC")
    return p
