"""E49 tests: protocol frozen; T43 export reproduces the E43 labels; T43 persistence is as of the origin; the E38->T43
adaptation changes only the labels; metric arithmetic. Guarded E38 code runs in its own interpreter."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
E49 = HERE.parent
sys.path.insert(0, str(E49.parent / "E43_Five_Trigger_Risk" / "runner"))


def run(body: str):
    pre = f"import sys\nsys.dont_write_bytecode=True\nsys.path.insert(0, r'{E49 / 'runner'}')\n"
    r = subprocess.run([sys.executable, "-B", "-c", pre + textwrap.dedent(body)], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-3000:]
    return r.stdout


def test_protocol_frozen():
    want = (E49 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E49 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_t43_export_matches_e43_labels_and_persistence_is_as_of():
    import e43_lib as K
    pd = K.pd
    lab = K.label_frame(K.L.load())
    ex = pd.read_csv(E49 / "data" / "t43_labels.csv", dtype={"province_code": str})
    m = lab.merge(ex, on=["province_code", "q"], suffixes=("", "_x"))
    assert len(m) == len(lab) == len(ex) and (m["y"] == m["y_x"]).all()
    pr = pd.read_csv(E49 / "data" / "t43_persistence.csv", dtype={"province_code": str})
    ok = pr.dropna(subset=["last_label_quarter"])
    assert (ok["last_label_quarter"].map(K.L.qi) <= ok["t"] - 1).all()


def test_e38_to_t43_adaptation_changes_only_labels():
    out = run("""
    import e49_compare as V
    import pandas as pd, numpy as np
    lab = pd.read_csv(V.E49 / "data" / "t43_labels.csv", dtype={"province_code": str})
    t43 = {(p, int(q)): int(y) for p, q, y in zip(lab["province_code"], lab["q"], lab["y"])}
    pr = pd.read_csv(V.E49 / "data" / "t43_persistence.csv", dtype={"province_code": str})
    pers = {(int(t), p): (np.nan if pd.isna(v) else float(v)) for t, p, v in zip(pr["t"], pr["province_code"], pr["y_last_t43"])}
    d0, d1 = V.E.Data(), V.DataT43(t43, pers)
    t = V.qk("2025-Q1")
    a, b = d0.features(t, 2), d1.features(t, 2)
    same = [c for c in a.columns if c != "y_last"]
    assert a[same].equals(b[same])
    tr = d1.training_pairs(t, 2)
    assert all(y == t43[(p, int(q))] for p, q, y in zip(tr["province_code"], tr["target_q"], tr["y"]))
    assert d1.label("PH040300000", V.qk("2024-Q4"), t) == t43[("PH040300000", V.qk("2024-Q4"))]
    print("ok")
    """)
    assert "ok" in out


def test_metric_arithmetic():
    out = run("""
    import e49_compare as V
    m = V.metrics([1, 1, 0, 0, 0], [1, 0, 1, 0, 0], [0.9, 0.2, 0.6, 0.1, 0.3])
    assert m["confusion"] == {"TP": 1, "TN": 2, "FP": 1, "FN": 1}
    assert abs(m["accuracy"] - 0.6) < 1e-12 and abs(m["balanced_accuracy"] - (0.5 + 2/3) / 2) < 1e-12
    assert abs(m["brier"] - (0.01 + 0.64 + 0.36 + 0.01 + 0.09) / 5) < 1e-12 and abs(m["share_HIGH_calls"] - 0.4) < 1e-12
    print("ok")
    """)
    assert "ok" in out
