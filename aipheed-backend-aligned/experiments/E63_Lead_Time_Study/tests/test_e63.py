"""E63 checks: the lead-h generalisation equals E56 at h = 2, the cutoffs hold at every lead, and the seals verify.

    backend/venv/Scripts/python.exe -B -m pytest -q tests/test_e63.py -p no:cacheprovider
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e63_lib as H  # noqa: E402

L, np, pd = H.L, H.np, H.pd


def test_folds_equal_e56_at_lead2():
    for n in range(4, 20):
        qs = list(range(8090, 8090 + n))
        assert H.folds_h(qs, 2) == H.I7.folds(qs, "forward")


def test_embargo_grows_with_lead():
    qs = list(range(8090, 8110))
    for h in H.LEADS:
        for q, fit in H.folds_h(qs, h):
            assert max(fit) <= q - h - 1


def test_lead4_base_month_after_cpi_cutoff():
    """PROTOCOL 1: a lead-4 target needs month 3 of quarter t as its year-earlier base; the cutoff is month 2 of t."""
    for t in range(L.qi("2023-Q1"), L.qi("2026-Q1")):
        assert max(m - 12 for m in L.target_months(t, 4)) > L.m0_of(t)
        for h in (1, 2, 3):
            assert max(m - 12 for m in L.target_months(t, h)) <= L.m0_of(t)


def test_training_targets_before_origin():
    raw = H.load_raw()
    d = raw[0]
    for h in (1, 3):
        _, X, B = H.inputs_h(raw, h)
        for t in (L.qi("2024-Q2"), L.qi("2025-Q3")):
            tr, te = H.frame_h(d, X, B, t, h)
            assert tr["q"].max() <= t - 1 and (tr["q"] - tr["t"] == h).all() and (te["t"] == t).all()


def test_seals_verify():
    E63 = H.E63
    want = (E63 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((E63 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want
    s = E63 / "sealed" / "predictions.csv"
    assert hashlib.sha256(s.read_bytes()).hexdigest() == (E63 / "sealed" / "predictions.csv.sha256").read_text().split()[0]
    S = pd.read_csv(s)
    assert S.groupby("lead").size().to_dict() == {1: 60, 2: 50, 3: 45}
    assert "y" not in S.columns and "T43" not in S.columns
