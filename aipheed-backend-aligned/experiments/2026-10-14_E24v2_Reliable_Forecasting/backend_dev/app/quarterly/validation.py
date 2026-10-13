"""
app/quarterly/validation.py  (E24)
----------------------------------
Schema, duplicate, conflict and coverage checks for a registered input BEFORE it can satisfy a requirement, and
model/feature version records for the forecast archive.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from app.quarterly.completeness import province_quarter_matrix, quarters_between, summarize


def check_table(df: pd.DataFrame, required_columns: list[str], key: list[str] | None = None,
                value_col: str | None = None, provinces: list[str] | None = None,
                quarters: tuple[str, str] | None = None) -> dict:
    """Return a report; 'passes' is False on any missing column, duplicate/conflicting key or missing cell."""
    rep = {"rows": int(len(df)), "missing_columns": [c for c in required_columns if c not in df.columns]}
    if key and not rep["missing_columns"]:
        dup = df[df.duplicated(key, keep=False)]
        rep["duplicate_keys"] = int(dup[key].drop_duplicates().shape[0])
        if value_col and len(dup):
            rep["conflicting_keys"] = int((dup.groupby(key)[value_col].nunique(dropna=False) > 1).sum())
        else:
            rep["conflicting_keys"] = 0
    if provinces and quarters and value_col and not rep["missing_columns"]:
        m = province_quarter_matrix(df, value_col, provinces, quarters_between(*quarters))
        s = summarize(m)
        rep["coverage"] = {k: v for k, v in s.items() if k != "non_present_cells"}
        rep["non_present_cells"] = s["non_present_cells"]
    rep["passes"] = (not rep["missing_columns"] and not rep.get("duplicate_keys") and not rep.get("conflicting_keys")
                     and not rep.get("non_present_cells"))
    return rep


def model_version_record(model_path: str | Path, feature_list: list[str], trained_through: str,
                         protocol_sha256: str, selection_rule: str) -> dict:
    """Version record stored beside a promoted model and copied into every forecast record it produces."""
    b = Path(model_path).read_bytes()
    fv = hashlib.sha256(json.dumps(feature_list).encode()).hexdigest()
    return {"model_sha256": hashlib.sha256(b).hexdigest(), "feature_version": fv[:16], "features": feature_list,
            "trained_through_target_quarter": trained_through, "protocol_sha256": protocol_sha256,
            "selection_rule": selection_rule}
