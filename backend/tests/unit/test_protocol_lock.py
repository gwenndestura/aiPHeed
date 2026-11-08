"""
tests/unit/test_protocol_lock.py
--------------------------------
The protocol lock (docs/aipheed/PROTOCOL_LOCK.md) is read-only: its SHA-256 must match the stored value, every quoted
excerpt must still equal the source lines in the working tree, and the frozen numbers must still hold in code
(tolerance multiplier 1.645, N2 at 0.75, N1 at 10 quarters / 40 rows, N7 in [0.70, 0.90]).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "docs" / "aipheed"


def _excerpt_sha(path: str, a: int, b: int) -> str:
    text = "\n".join((REPO / path).read_text(encoding="utf-8").splitlines()[a - 1:b])
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_lock_file_hash_unchanged():
    stored = (DOCS / "PROTOCOL_LOCK.sha256").read_text().split()[0]
    assert hashlib.sha256((DOCS / "PROTOCOL_LOCK.md").read_bytes()).hexdigest() == stored


def test_every_locked_source_unchanged():
    for m in json.loads((DOCS / "protocol_lock_manifest.json").read_text()):
        assert _excerpt_sha(m["path"], *m["lines"]) == m["sha256"], f"{m['id']} {m['path']} changed"


def test_excerpt_check_detects_an_edit(tmp_path):
    """The check is not vacuous: an edited copy of a locked line no longer matches its hash."""
    m = json.loads((DOCS / "protocol_lock_manifest.json").read_text())[0]
    lines = (REPO / m["path"]).read_text(encoding="utf-8").splitlines()
    a, b = m["lines"]
    edited = "\n".join(lines[a - 1:b]).replace("1.645", "2.000")
    assert hashlib.sha256(edited.encode("utf-8")).hexdigest() != m["sha256"]


def test_frozen_numbers_in_code():
    p = REPO / "aipheed-backend-aligned" / "experiments" / "E130_Provincial_Risk_Score_Forecasting" / "runner" / "e130_lib.py"
    spec = importlib.util.spec_from_file_location("e130_lib_lock", p)
    L = importlib.util.module_from_spec(spec)
    sys.modules["e130_lib_lock"] = L
    spec.loader.exec_module(L)
    assert abs(L.Z90 - 1.6448536) < 1e-6
    assert np.allclose(L.tolerance([2.0]), [2.0 * L.Z90])

    def rows(n_q, per_q, within_share):
        n = n_q * per_q
        k = int(round(within_share * n))
        y = np.full(n, 20.0)
        f = y + np.where(np.arange(n) < k, 0.0, 10.0)
        return pd.DataFrame({"y": y, "se": 1.0, "target_q": np.repeat(np.arange(n_q), per_q),
                             "province": np.tile(np.arange(per_q), n_q), "f_m": f, "f_persistence": y + 5,
                             "f_climatology": y + 6, "lo80_m": f - 1, "hi80_m": f + 1})
    r = L.numeric_reliability(rows(10, 4, 0.75), "m", ["persistence", "climatology"])["rules"]
    assert r["N1_data"] and r["N2_within_tolerance_75"]
    r = L.numeric_reliability(rows(10, 4, 0.725), "m", ["persistence", "climatology"])["rules"]
    assert not r["N2_within_tolerance_75"]
    assert not L.numeric_reliability(rows(9, 4, 1.0), "m", ["persistence", "climatology"])["rules"]["N1_data"]
