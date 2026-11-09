"""
E183 (docs/e183/DESIGN.md): missing-input robustness for the E168 forecast rows.

LightGBM sends a missing value down the branch it learned for missing values. For an input that was NEVER missing in the
training rows, no such branch was learned and the value is read as zero, which for most E168 inputs means "no change",
so a missing source silently lowered the forecast (E178 scenario S2). Here such inputs are filled, in the forecast rows
only, with their median over the training rows, and every row records which inputs were filled.

Inputs that are sometimes missing in training (e.g. news before 2016) keep LightGBM's learned missing-value handling.
Training rows and inner cross-validation are untouched. Applied identically in validation (app.e168.lgbm_only.task) and
serving (app.e168.serve._forecast), right before run_proc.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

WARNING = ("Data incomplete: {n} model input(s) had no published value at the issue date ({names}) and were filled with "
           "their typical training value; treat this forecast with extra caution.")


def model_columns() -> list[str]:
    """Every column any E168 feature set can use."""
    from app.e168 import lgbm_only as E
    return list(dict.fromkeys(c for v in E.FS.values() for c in v))


def fill_unseen_missing(tr: pd.DataFrame, te: pd.DataFrame, cols: list[str] | None = None) -> tuple[pd.DataFrame, list[list[str]]]:
    """Return te with unseen-missing inputs filled by the training median, and the filled column names per te row."""
    cols = [c for c in (cols or model_columns()) if c in tr.columns and c in te.columns]
    never = [c for c in cols if tr[c].notna().all()]
    miss = te[never].isna()
    if not miss.values.any():
        return te, [[] for _ in range(len(te))]
    te = te.copy()
    med = tr[never].median()
    for c in miss.columns[miss.any()]:
        te[c] = te[c].fillna(med[c])
    filled = [sorted(miss.columns[miss.iloc[k].values].tolist()) for k in range(len(te))]
    return te, filled


def used_by(tag: str, filled: list[list[str]]) -> list[list[str]]:
    """Keep only the filled inputs that belong to the selected feature set (the configuration tag's second field)."""
    from app.e168 import lgbm_only as E
    fs = set(E.FS.get(tag.split("|")[1], []))
    return [[c for c in row if c in fs] for row in filled]


def warning(row: dict) -> str | None:
    """The dashboard's data-incomplete sentence for a forecast row, or None (rows from before E183 carry no flag)."""
    try:
        n = int(float(row.get("inputs_filled") or 0))
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    names = str(row.get("inputs_filled_names") or "").replace(";", ", ") or "unnamed"
    return WARNING.format(n=n, names=names)
