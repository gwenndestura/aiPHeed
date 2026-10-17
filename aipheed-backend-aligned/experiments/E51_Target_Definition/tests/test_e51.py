"""E51 tests: protocol frozen; CPI-based labels and persistence as of the origin; S1 = SWS H + 2D alignment; RQ has
exactly 2 HIGH of 5 per quarter; the label override changes only labels; metric arithmetic. Guarded E38 code runs in
its own interpreter."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
E51 = HERE.parent
sys.path.insert(0, str(E51.parent / "E43_Five_Trigger_Risk" / "runner"))


def run(body: str) -> str:
    pre = f"import sys\nsys.dont_write_bytecode=True\nsys.path.insert(0, r'{E51 / 'runner'}')\n"
    r = subprocess.run([sys.executable, "-B", "-c", pre + textwrap.dedent(body)], capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stderr[-3000:]
    return r.stdout


def test_protocol_frozen():
    want = (E51 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E51 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_cpi_labels_and_persistence_are_as_of():
    import e43_lib as K
    pd = K.pd
    lab = pd.read_csv(E51 / "data" / "labels_cpi.csv", dtype={"province_code": str})
    t43 = K.label_frame(K.L.load())
    m = t43.merge(lab, on=["province_code", "q"])
    assert len(m) == len(t43) and (m["y"] == m["T43"]).all()
    assert lab["PS"].notna().all() and lab["q"].min() >= K.L.qi("2021-Q1")
    pr = pd.read_csv(E51 / "data" / "persistence_cpi.csv", dtype={"province_code": str}).dropna(subset=["PS_last_quarter"])
    assert (pr["PS_last_quarter"].map(K.L.qi) <= pr["t"] - 1).all()


def test_label_alignment_rq_balance_and_override():
    out = run("""
    import e51_compare as V
    import numpy as np
    d = V.E.Data()
    S1 = {k: v for k, v in d.Sv.items() if v == v}
    # S1 - 2D is one regional value per quarter (the SWS H), so the label's province content is the price deviation
    for q in {q for _, q in S1}:
        hs = [S1[(p, q)] - 2 * d.Dm[(p, q)] for p in V.PROVS if (p, q) in S1]
        assert max(hs) - min(hs) < 1e-9
    D = {k: v for k, v in d.Dm.items() if v == v}
    for q in {q for _, q in D}:
        vals = [D.get((p, q)) for p in V.PROVS]
        if all(v is not None for v in vals):
            m = float(np.median(vals))
            assert sum(v > m for v in vals) == 2
    lab = {(p, q): 1 for p in V.PROVS for q in range(V.qk("2021-Q1"), V.qk("2027-Q1"))}
    dl = V.DataLabel(lab, {})
    t = V.qk("2025-Q1")
    a, b = d.features(t, 2), dl.features(t, 2)
    same = [c for c in a.columns if c != "y_last"]
    assert a[same].equals(b[same]) and dl.label("PH040100000", t + 2, t) == 1
    print("ok")
    """)
    assert "ok" in out


def test_metric_arithmetic_and_acceptance_rule():
    out = run("""
    import e51_compare as V
    m = V.metrics([1, 1, 0, 0, 0], [1, 0, 1, 0, 0], [0.9, 0.2, 0.6, 0.1, 0.3])
    assert m["confusion"] == {"TP": 1, "TN": 2, "FP": 1, "FN": 1} and abs(m["accuracy"] - 0.6) < 1e-12
    good = {"accuracy": 0.8, "balanced_accuracy": 0.75, "recall_HIGH": 0.7, "recall_LOW": 0.8, "brier": 0.1}
    base = {"PERSIST": {"brier": 0.2}, "HIGH": {"brier": 0.5}, "LOW": {"brier": 0.3}}
    assert V.accepted(good, base) and not V.accepted(dict(good, recall_HIGH=0.5), base)
    assert not V.accepted(dict(good, brier=0.25), base)
    print("ok")
    """)
    assert "ok" in out
