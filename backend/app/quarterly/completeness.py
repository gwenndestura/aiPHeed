"""
app/quarterly/completeness.py
-----------------------------
Expected-versus-actual coverage. A missing cell is reported as MISSING, never as zero; duplicates and
conflicting values are reported separately.
"""
from __future__ import annotations

import pandas as pd

from app.quarterly.periods import Quarter


def quarters_between(first: str, last: str) -> list[str]:
    a, b = Quarter.parse(first), Quarter.parse(last)
    return [str(a.shift(i)) for i in range(b.index - a.index + 1)]


def province_quarter_matrix(df: pd.DataFrame, value_col: str, provinces: list[str], quarters: list[str],
                            province_col: str = "province_code", quarter_col: str = "quarter") -> pd.DataFrame:
    rows = []
    for q in quarters:
        for p in provinces:
            m = df[(df[province_col] == p) & (df[quarter_col] == q)]
            if m.empty:
                st, v = "MISSING", None
            elif len(m) > 1:
                st = "CONFLICT" if m[value_col].nunique(dropna=False) > 1 else "DUPLICATE"
                v = m[value_col].iloc[0]
            elif pd.isna(m[value_col].iloc[0]):
                st, v = "NULL", None
            else:
                st, v = "PRESENT", m[value_col].iloc[0]
            rows.append({"quarter": q, "province_code": p, "status": st, "value": v})
    return pd.DataFrame(rows)


def summarize(matrix: pd.DataFrame) -> dict:
    vc = matrix["status"].value_counts().to_dict()
    miss = matrix[matrix["status"] != "PRESENT"]
    return {"expected": int(len(matrix)), **{k: int(v) for k, v in vc.items()},
            "non_present_cells": miss[["quarter", "province_code", "status"]].to_dict("records")}
