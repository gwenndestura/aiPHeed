"""E15 loaders. Every read goes through the guard (hash-verified allowlist). Each loader asserts that no loaded
row or record refers to a quarter later than 2025-Q4."""
from __future__ import annotations

import io
import json
import re

import pandas as pd

import guard

MAXQ = "2025-Q4"
_QRE = re.compile(r"\b(20\d\d)-Q([1-4])\b")


def qkey(q: str) -> int:
    y, n = q.split("-Q")
    return int(y) * 4 + int(n) - 1


def assert_quarters(values, what: str) -> None:
    bad = sorted({q for q in values if isinstance(q, str) and qkey(q) > qkey(MAXQ)})
    if bad:
        raise guard.AccessDenied(f"E15: {what} contains quarters after {MAXQ}: {bad}")


def assert_text_quarters(txt: str, what: str) -> None:
    assert_quarters([f"{y}-Q{n}" for y, n in _QRE.findall(txt)], what)


def load_components() -> pd.DataFrame:
    txt = guard.read_allowed_text(guard.E12_RUN / "realized_components_2021_2025.csv")
    df = pd.read_csv(io.StringIO(txt), dtype={"province_code": str})
    assert_quarters(df["quarter"], "components")
    return df


def load_rounds() -> pd.DataFrame:
    txt = guard.read_allowed_text(guard.E12_RUN / "details.json")
    d = json.loads(txt)
    r = pd.DataFrame(d["two_layer"]["regional_layer_rounds"])
    assert_quarters(r["quarter"], "regional rounds")
    r["published"] = pd.to_datetime(r["published"])
    r.attrs["regional_scope"] = d["two_layer"]["regional_scope"]
    r.attrs["tau0_recorded"] = d["tau0_recorded"]
    r.attrs["tau0_full_precision"] = d["tau0_full_precision"]
    return r


def load_e13_metrics() -> dict:
    txt = guard.read_allowed_text(guard.E13_RUN / "metrics.json")
    assert_text_quarters(txt, "E13 metrics")
    return json.loads(txt)


def load_e13_scored() -> pd.DataFrame:
    txt = guard.read_allowed_text(guard.E13_RUN / "scored_rows.csv")
    df = pd.read_csv(io.StringIO(txt), dtype={"province_code": str})
    assert_quarters(df["quarter"], "E13 scored rows")
    assert_quarters(df["H_last_quarter"].dropna(), "E13 scored rows (H_last_quarter)")
    return df
